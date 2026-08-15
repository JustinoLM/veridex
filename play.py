"""Interactive entry point: let a human actually play the puzzles.

Every earlier step computed and printed a puzzle's full solution and
explanation in one shot. This module is what makes the project playable:
it shows a puzzle without its answer, collects the player's own guess
about each person through the terminal, checks that guess against the
real solution, and only then reveals the full tactic/propagation/
case-split explanation that main.py already knows how to produce.

This is a separate entry point from main.py (`uv run play.py`, vs.
`uv run main.py`). It imports from the existing modules and reuses
main.py's run_deduction_pipeline() for the reveal step - it does not
reimplement any solving or explanation logic of its own. main.py itself
is untouched: importing this module does not run main.py's main()
function, since that call is guarded by main.py's own
`if __name__ == "__main__":` block.

Per SPEC_step13.md, this step only wires up the two hardcoded puzzles
(PUZZLE_1 and PUZZLE_2 from puzzles.py) - generated puzzles, difficulty
selection, and persistence are all out of scope here.

Step 14 (see SPEC_step14.md) restyles this module's terminal output using
`rich` - panels, color, and styled prompts instead of raw print()/input().
This is a purely visual change: every function below still drives the
exact same menu logic, guess validation, correctness checking, and reveal
sequence Step 13 established. main.py stays plain-text and untouched, and
is still the module that actually computes the explanation - this module
only wraps that output in nicer presentation, described in detail on
_reveal_explanation() below.
"""

import contextlib
import io
import re

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from difficulty import Difficulty
from main import run_deduction_pipeline
from puzzles import PUZZLE_1, PUZZLE_1_DESCRIPTION, PUZZLE_2, PUZZLE_2_DESCRIPTION, Puzzle
from solver import solve

# One shared Console for the whole play session, so every panel, prompt,
# and styled line renders through the same rich output pipeline instead
# of mixing rich rendering with raw print() calls.
console = Console()

# Border color used for each explanation panel in _reveal_explanation(),
# keyed by the same section labels _split_pipeline_sections() produces.
# Giving each technique its own color is what lets a player visually tell
# tactic, propagation, and case-split apart at a glance, per SPEC_step14.md.
_SECTION_STYLES: dict[str, tuple[str, str]] = {
    "tactic": ("Tactic — Hypothesize & Check", "magenta"),
    "propagation": ("Backward Propagation", "cyan"),
    "case_split": ("Case-Split Fallback", "yellow"),
    "final": ("Final Solution", "green"),
}

# Color used to style the final "Difficulty: X" line, keyed by the
# Difficulty enum run_deduction_pipeline() returns alongside its output.
_DIFFICULTY_COLORS: dict[Difficulty, str] = {
    Difficulty.EASY: "green",
    Difficulty.MEDIUM: "yellow",
    Difficulty.HARD: "red",
}

# The menu entries this play session offers, in display order. Each
# entry is (menu key the player types, the Puzzle itself, its
# plain-language description). Kept as one list so the menu-printing,
# menu-matching, and puzzle-selection logic below all walk the same
# source of truth instead of three separately maintained copies.
MENU_ENTRIES: list[tuple[str, Puzzle, str]] = [
    ("1", PUZZLE_1, PUZZLE_1_DESCRIPTION),
    ("2", PUZZLE_2, PUZZLE_2_DESCRIPTION),
]


def parse_knight_or_knave(text: str) -> bool | None:
    """Interpret one line of player input as a knight/knave choice.

    Accepts a couple of reasonable forms, case-insensitively, per
    SPEC_step13.md: the full word ("knight"/"knave") or its first
    letter ("k"/"n").

    Args:
        text: The raw line the player typed.

    Returns:
        True for knight, False for knave, or None if the text does not
        match either recognized form - the caller is responsible for
        re-prompting on None rather than guessing.
    """
    normalized = text.strip().lower()
    if normalized in ("knight", "k"):
        return True
    if normalized in ("knave", "n"):
        return False
    return None


def parse_guilty_or_innocent(text: str) -> bool | None:
    """Interpret one line of player input as a guilty/innocent choice.

    Mirrors parse_knight_or_knave(): accepts the full word or its first
    letter, case-insensitively.

    Args:
        text: The raw line the player typed.

    Returns:
        True for guilty, False for innocent, or None if the text does
        not match either recognized form.
    """
    normalized = text.strip().lower()
    if normalized in ("guilty", "g"):
        return True
    if normalized in ("innocent", "i"):
        return False
    return None


def ask_until_valid(prompt: str, parser) -> bool:
    """Repeatedly prompt the player until their input parses to a boolean.

    This is the one place defensive re-prompting lives for guess
    collection: every question the play loop asks (knight/knave,
    guilty/innocent) goes through this function, so unrecognized input
    always gets a re-prompt of the *same* question instead of crashing
    or silently defaulting to a guess.

    Step 14 swaps the raw input() call for rich.prompt.Prompt.ask(), so
    the question itself renders through the same styled console as
    everything else, and swaps the plain re-prompt print() for a styled
    (red) console message - purely presentational, the parser and the
    "keep asking until it parses" logic are unchanged from Step 13.

    Args:
        prompt: The text to show the player before reading their input.
            Rich markup (e.g. "[bold]...[/bold]") is honored.
        parser: A function like parse_knight_or_knave() that turns raw
            text into True/False/None.

    Returns:
        The first successfully parsed boolean.
    """
    while True:
        raw = Prompt.ask(prompt, console=console)
        parsed = parser(raw)
        if parsed is not None:
            return parsed
        console.print("[red]Sorry, I didn't understand that. Please try again.[/red]")


def show_menu_and_get_choice() -> tuple[Puzzle, str] | None:
    """Print the puzzle menu and read the player's choice.

    Loops on unrecognized input (anything that is not a listed menu key
    or a quit command) rather than crashing, matching the same
    re-prompt-on-bad-input requirement guess collection follows.

    Step 14 renders the menu as a rich Table inside a Panel instead of
    plain print lines, and reads the choice with Prompt.ask() - the set
    of accepted keys and the quit words ("q"/"quit") are exactly what
    Step 13 accepted, only the rendering changed.

    Returns:
        A (puzzle, description) pair for the puzzle the player chose, or
        None if the player chose to quit.
    """
    while True:
        menu_table = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
        for key, puzzle, _ in MENU_ENTRIES:
            menu_table.add_row(f"[bold cyan]{key}[/bold cyan]", puzzle.name)
        menu_table.add_row("[bold cyan]q[/bold cyan]", "Quit")

        console.print()
        console.print(Panel(menu_table, title="Choose a Puzzle", border_style="blue"))

        raw = Prompt.ask("Enter your choice", console=console).strip().lower()

        for key, puzzle, description in MENU_ENTRIES:
            if raw == key:
                return puzzle, description
        if raw in ("q", "quit"):
            return None

        console.print("[yellow]Sorry, that's not a valid choice. Please try again.[/yellow]")


def collect_guess(puzzle: Puzzle) -> dict:
    """Ask the player to guess every person's attributes, one question at a time.

    Every person is asked their knight/knave status. Puzzle 1 also
    tracks guilt (its `attributes` list includes "is_guilty"), so for
    that puzzle - and any future puzzle shaped the same way - this also
    asks a guilty/innocent question per person, exactly mirroring how
    describe_assignment() in rendering.py decides which clauses apply to
    a given puzzle's attribute list.

    Args:
        puzzle: The puzzle being played.

    Returns:
        A (person, attribute) -> bool dict in the same shape solve()
        produces, built entirely from the player's answers.
    """
    guess: dict = {}
    for person in puzzle.people:
        name = person.capitalize()

        is_knight = ask_until_valid(
            f"Is [bold]{name}[/bold] a knight or a knave? (knight/knave)",
            parse_knight_or_knave,
        )
        guess[(person, "is_knight")] = is_knight

        if "is_guilty" in puzzle.attributes:
            is_guilty = ask_until_valid(
                f"Is [bold]{name}[/bold] guilty or innocent? (guilty/innocent)",
                parse_guilty_or_innocent,
            )
            guess[(person, "is_guilty")] = is_guilty

    return guess


def get_solution(puzzle: Puzzle) -> dict:
    """Brute-force the real solution to a puzzle, using the existing solver.

    Both PUZZLE_1 and PUZZLE_2 are already verified well-posed (Puzzle 1
    by main.py's own regression check against Step 1, Puzzle 2 by the
    Step 4 pipeline fully resolving it), so solve() is expected to return
    exactly one fully valid assignment here.

    Args:
        puzzle: The puzzle to solve.

    Returns:
        The single fully valid (person, attribute) -> bool assignment.
    """
    result = solve(puzzle)
    return result.fully_valid[0]


def _attribute_value_label(attribute: str, value: bool) -> str:
    """Turn one attribute/value pair into the word a player would recognize.

    Small formatting helper local to this module - rendering.py's
    equivalent (_describe_fact) builds a full "Name is a knave" sentence
    and is private to that module, whereas the per-attribute report
    below needs just the bare word ("knave", "guilty") to slot into its
    own "guessed ... / actual ..." phrasing.

    Args:
        attribute: Either "is_knight" or "is_guilty".
        value: The boolean value of that attribute.

    Returns:
        The plain-language word for that attribute/value combination.
    """
    if attribute == "is_knight":
        return "knight" if value else "knave"
    return "guilty" if value else "innocent"


def report_guess(puzzle: Puzzle, guess: dict, solution: dict) -> None:
    """Print, person by person, whether the player's guess matches the real solution.

    Every attribute of every person is compared individually and
    reported as correct or wrong, then each person gets an overall
    CORRECT/WRONG verdict, and finally the whole puzzle gets an overall
    verdict - exactly the granularity SPEC_step13.md's "check the guess"
    and "report the result" steps ask for.

    Step 14 color-codes this report (green for correct, red for wrong)
    instead of the plain CORRECT/WRONG text Step 13 printed - the
    comparison logic and the CORRECT/WRONG structure itself are
    unchanged, only the color is new.

    Args:
        puzzle: The puzzle being played.
        guess: The player's (person, attribute) -> bool answers, as
            built by collect_guess().
        solution: The real (person, attribute) -> bool answer, as
            returned by get_solution().
    """
    console.print()
    console.rule("[bold]YOUR RESULT[/bold]", style="blue")
    console.print()

    puzzle_fully_correct = True
    for person in puzzle.people:
        name = person.capitalize()

        person_fully_correct = True
        detail_lines = []
        for attribute in puzzle.attributes:
            guessed_value = guess[(person, attribute)]
            actual_value = solution[(person, attribute)]
            correct = guessed_value == actual_value
            person_fully_correct = person_fully_correct and correct

            color = "green" if correct else "red"
            status_word = "correct" if correct else "wrong"
            detail_lines.append(
                f"    {attribute}: you guessed "
                f"{_attribute_value_label(attribute, guessed_value)}, actual answer is "
                f"{_attribute_value_label(attribute, actual_value)} - "
                f"[{color}]{status_word}[/{color}]"
            )

        puzzle_fully_correct = puzzle_fully_correct and person_fully_correct
        verdict_color = "green" if person_fully_correct else "red"
        verdict_word = "CORRECT" if person_fully_correct else "WRONG"
        console.print(f"[bold]{name}[/bold]: [{verdict_color}]{verdict_word}[/{verdict_color}]")
        for line in detail_lines:
            console.print(line)

    console.print()
    if puzzle_fully_correct:
        console.print("[bold green]You got the whole puzzle right![/bold green]")
    else:
        console.print("[bold red]You didn't get everyone right this time.[/bold red]")
    console.print()


def _style_person_names(text: str, people: list[str]) -> str:
    """Wrap every occurrence of a puzzle's person names in rich bold markup.

    Applied to puzzle descriptions before they go into a Panel, so names
    like "Ada" and "Bo" stand out from the surrounding sentence per
    SPEC_step14.md ("style person names consistently ... so they stand
    out"). Matches on capitalized, whole-word occurrences only (\\b word
    boundaries) - the descriptions always refer to people by their
    capitalized name, so this does not need to handle lowercase mentions
    or touch any other word that merely contains a name as a substring.

    Args:
        text: The plain-language text to style (typically a puzzle
            description).
        people: The puzzle's person names, e.g. ["ada", "bo"].

    Returns:
        The same text with each person's capitalized name wrapped in
        "[bold]...[/bold]" rich markup.
    """
    styled = text
    for person in people:
        name = person.capitalize()
        styled = re.sub(rf"\b{re.escape(name)}\b", f"[bold]{name}[/bold]", styled)
    return styled


def _split_pipeline_sections(captured_output: str) -> dict[str, str]:
    """Split run_deduction_pipeline()'s captured plain-text output into named sections.

    run_deduction_pipeline() (main.py) always prints its explanation in a
    fixed order - the puzzle header/description, then "Tactic (...):",
    "Backward propagation:", "Case-split fallback:", "Final solution:",
    and finally "Difficulty: X" - and that order is not something this
    step is allowed to change (main.py's logic and output text must stay
    exactly as-is, per SPEC_step14.md). To give each technique its own
    panel and color without reimplementing any of that explanation logic,
    this function locates each section's fixed marker text in the
    captured output and slices the string between consecutive markers,
    rather than recomputing what each section should say.

    Args:
        captured_output: Everything run_deduction_pipeline() printed,
            captured via contextlib.redirect_stdout() by
            _reveal_explanation().

    Returns:
        A dict with keys "preamble", "tactic", "propagation",
        "case_split", "final", and "difficulty", each holding the
        stripped text between that section's marker and the next one.
    """
    markers = [
        ("tactic", "Tactic (hypothesize-and-check on knight/knave status):"),
        ("propagation", "Backward propagation:"),
        ("case_split", "Case-split fallback:"),
        ("final", "Final solution:"),
        ("difficulty", "Difficulty:"),
    ]

    # Locate every marker in order, searching forward from the previous
    # match so a marker string that happened to recur inside an earlier
    # section's rendered explanation could never be mistaken for the
    # next section's heading.
    positions: list[tuple[str, int, int]] = []
    search_from = 0
    for key, marker in markers:
        idx = captured_output.index(marker, search_from)
        positions.append((key, idx, len(marker)))
        search_from = idx + len(marker)

    sections: dict[str, str] = {"preamble": captured_output[: positions[0][1]].strip()}
    for i, (key, idx, marker_len) in enumerate(positions):
        body_start = idx + marker_len
        body_end = positions[i + 1][1] if i + 1 < len(positions) else len(captured_output)
        sections[key] = captured_output[body_start:body_end].strip()

    return sections


def _reveal_explanation(puzzle: Puzzle, description: str) -> None:
    """Run the real deduction pipeline and re-present its output as styled panels.

    This is the "explanation reveal" SPEC_step14.md asks for: the tactic,
    propagation, case-split, and final-solution sections each get their
    own panel with a distinct title and accent color, so a player can
    visually tell which technique explains which resolved value.

    Doing that without reimplementing any explanation logic - which
    SPEC_step14.md and this module's own docstring both require - means
    this cannot just call render_tactic_step() etc. directly, since it
    has no way to independently know which rounds ran or which technique
    resolved which fact without duplicating run_deduction_pipeline()'s
    own bookkeeping. Instead, run_deduction_pipeline() is called exactly
    as Step 13 called it, with its stdout temporarily captured instead of
    going straight to the terminal; the captured plain text (produced
    entirely by main.py, unmodified) is then split by
    _split_pipeline_sections() and each piece is re-printed inside its
    own Panel. The words on screen are exactly what
    run_deduction_pipeline() printed - only where they're printed, and in
    what color, changes.

    Args:
        puzzle: The puzzle to solve and explain.
        description: Its plain-language description, passed straight
            through to run_deduction_pipeline() exactly as main.py
            itself would.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        _, difficulty = run_deduction_pipeline(puzzle, description)
    sections = _split_pipeline_sections(buffer.getvalue())

    # Extremely unlikely for puzzles this size (see MAX_PIPELINE_ROUNDS in
    # main.py), but if the round-cap warning ever did fire, it would land
    # in the preamble alongside the re-printed header/description - surface
    # it rather than silently swallowing it.
    if "WARNING" in sections["preamble"]:
        console.print(Panel(sections["preamble"], title="Pipeline Warning", border_style="red"))

    for key in ("tactic", "propagation", "case_split", "final"):
        title, color = _SECTION_STYLES[key]
        console.print(Panel(sections[key], title=title, border_style=color))

    difficulty_color = _DIFFICULTY_COLORS.get(difficulty, "white")
    console.print(f"[bold {difficulty_color}]Difficulty: {sections['difficulty']}[/bold {difficulty_color}]")
    console.print()


def play_puzzle(puzzle: Puzzle, description: str) -> None:
    """Run one full play session for a single puzzle: present, guess, check, reveal.

    This is steps 2-7 of SPEC_step13.md's play loop in order: the
    puzzle's plain-language description is shown (with no solution or
    explanation), the player's guess is collected and checked against
    the real solution, and only after that does the full tactic/
    propagation/case-split explanation get revealed via
    _reveal_explanation() - which itself reuses run_deduction_pipeline()
    from main.py unmodified, per that function's own docstring.

    Args:
        puzzle: The puzzle to play.
        description: Its plain-language description (people, statements,
            constraint), printed before any guessing happens.
    """
    console.print()
    console.print(
        Panel(
            _style_person_names(description, puzzle.people),
            title=f"Knights & Knaves Puzzle — {puzzle.name}",
            border_style="blue",
        )
    )

    guess = collect_guess(puzzle)
    solution = get_solution(puzzle)
    report_guess(puzzle, guess, solution)

    console.print("[bold]Here's the full explanation:[/bold]")
    console.print()
    _reveal_explanation(puzzle, description)


def main() -> None:
    """Entry point: loop between the menu and playing puzzles until the player quits.

    Matches SPEC_step13.md's step 8: after finishing a puzzle, control
    returns to the menu rather than the program exiting, so the player
    can play the other puzzle (or the same one again) without restarting.
    """
    while True:
        choice = show_menu_and_get_choice()
        if choice is None:
            console.print("[bold]Goodbye![/bold]")
            break

        puzzle, description = choice
        play_puzzle(puzzle, description)


if __name__ == "__main__":
    main()
