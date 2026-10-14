"""Interactive entry point: let a human actually play the puzzles.

Every earlier step computed and printed a puzzle's full solution and
explanation in one shot. This module is what makes the project playable:
it shows a puzzle without its answer, collects the player's own guess
about each person through the terminal, checks that guess against the
real solution, and only then reveals the full tactic/propagation/
case-split explanation that demo.py already knows how to produce.

This is a separate entry point from demo.py (`uv run veridex-play`, vs.
`uv run veridex-demo`). It imports from the existing modules and reuses
pipeline.py's run_pipeline()/format_pipeline() for the reveal step - it
does not reimplement any solving or explanation logic of its own, and
it does not depend on demo.py at all.

Per SPEC_step13.md, this step only wires up the two hardcoded puzzles
(PUZZLE_1 and PUZZLE_2 from puzzles.py) - generated puzzles, difficulty
selection, and persistence are all out of scope here.

Step 14 (see SPEC_step14.md) restyles this module's terminal output using
`rich` - panels, color, and styled prompts instead of raw print()/input().
This is a purely visual change: every function below still drives the
exact same menu logic, guess validation, correctness checking, and reveal
sequence Step 13 established. demo.py stays plain-text; the explanation
itself is computed by pipeline.py, and this module only wraps it in nicer
presentation, described in detail on _reveal_explanation() below.
"""

import re
import textwrap

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .difficulty import Difficulty
from .pipeline import format_pipeline, run_pipeline
from .puzzles import PUZZLE_1, PUZZLE_1_DESCRIPTION, PUZZLE_2, PUZZLE_2_DESCRIPTION, Puzzle
from .solver import solve

# One shared Console for the whole play session, so every panel, prompt,
# and styled line renders through the same rich output pipeline instead
# of mixing rich rendering with raw print() calls.
console = Console()

# Border color used for each explanation panel in _reveal_explanation(),
# keyed by the section names of pipeline.PipelineSections.
# Giving each technique its own color is what lets a player visually tell
# tactic, propagation, and case-split apart at a glance, per SPEC_step14.md.
_SECTION_STYLES: dict[str, tuple[str, str]] = {
    "tactic": ("Tactic — Hypothesize & Check", "magenta"),
    "propagation": ("Backward Propagation", "cyan"),
    "case_split": ("Case-Split Fallback", "yellow"),
    "final": ("Final Solution", "green"),
}

# Color used to style the final "Difficulty: X" line, keyed by the
# Difficulty enum pipeline.PipelineResult carries.
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
    by demo.py's own regression check against Step 1, Puzzle 2 by the
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


def _reveal_explanation(puzzle: Puzzle) -> None:
    """Solve the puzzle with the real pipeline and show each technique in its own panel.

    The tactic, propagation, case-split, and final-solution sections each
    get a panel with a distinct title and accent color, so a player can
    visually tell which technique explains which resolved value
    (SPEC_step14.md). The text inside each panel comes straight from
    pipeline.format_pipeline(), the same function demo.py prints from, so
    there is no output capturing or text re-parsing involved: this module
    only chooses where each already-separated section goes and what color
    it gets.

    Args:
        puzzle: The puzzle to solve and explain.
    """
    result = run_pipeline(puzzle)
    sections = format_pipeline(puzzle, result)

    if sections.warning:
        console.print(Panel(sections.warning, title="Pipeline Warning", border_style="red"))

    for key in ("tactic", "propagation", "case_split", "final"):
        title, color = _SECTION_STYLES[key]
        console.print(Panel(textwrap.dedent(getattr(sections, key)).strip(), title=title, border_style=color))

    difficulty_color = _DIFFICULTY_COLORS.get(result.difficulty, "white")
    console.print(
        f"[bold {difficulty_color}]Difficulty: {sections.difficulty}[/bold {difficulty_color}]"
    )
    console.print()


def play_puzzle(puzzle: Puzzle, description: str) -> None:
    """Run one full play session for a single puzzle: present, guess, check, reveal.

    This is steps 2-7 of SPEC_step13.md's play loop in order: the
    puzzle's plain-language description is shown (with no solution or
    explanation), the player's guess is collected and checked against
    the real solution, and only after that does the full tactic/
    propagation/case-split explanation get revealed via
    _reveal_explanation() - which itself reuses pipeline.run_pipeline().

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
    _reveal_explanation(puzzle)


def main() -> None:
    """Entry point: loop between the menu and playing puzzles until the player quits.

    Matches SPEC_step13.md's step 8: after finishing a puzzle, control
    returns to the menu rather than the program exiting, so the player
    can play the other puzzle (or the same one again) without restarting.

    Ctrl-C and Ctrl-D (end of input) are treated as a request to quit,
    not as errors, so they exit cleanly instead of printing a traceback.
    """
    try:
        while True:
            choice = show_menu_and_get_choice()
            if choice is None:
                break

            puzzle, description = choice
            play_puzzle(puzzle, description)
    except (KeyboardInterrupt, EOFError):
        console.print()
    console.print("[bold]Goodbye![/bold]")


if __name__ == "__main__":
    main()
