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
"""

from main import run_deduction_pipeline
from puzzles import PUZZLE_1, PUZZLE_1_DESCRIPTION, PUZZLE_2, PUZZLE_2_DESCRIPTION, Puzzle
from rendering import print_header
from solver import solve

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

    Args:
        prompt: The text to show the player before reading their input.
        parser: A function like parse_knight_or_knave() that turns raw
            text into True/False/None.

    Returns:
        The first successfully parsed boolean.
    """
    while True:
        raw = input(prompt)
        parsed = parser(raw)
        if parsed is not None:
            return parsed
        print("Sorry, I didn't understand that. Please try again.")


def show_menu_and_get_choice() -> tuple[Puzzle, str] | None:
    """Print the puzzle menu and read the player's choice.

    Loops on unrecognized input (anything that is not a listed menu key
    or a quit command) rather than crashing, matching the same
    re-prompt-on-bad-input requirement guess collection follows.

    Returns:
        A (puzzle, description) pair for the puzzle the player chose, or
        None if the player chose to quit.
    """
    while True:
        print()
        print("Choose a puzzle to play:")
        for key, puzzle, _ in MENU_ENTRIES:
            print(f"  {key}. {puzzle.name}")
        print("  q. Quit")

        raw = input("> ").strip().lower()

        for key, puzzle, description in MENU_ENTRIES:
            if raw == key:
                return puzzle, description
        if raw in ("q", "quit"):
            return None

        print("Sorry, that's not a valid choice. Please try again.")


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
            f"Is {name} a knight or a knave? (knight/knave): ", parse_knight_or_knave
        )
        guess[(person, "is_knight")] = is_knight

        if "is_guilty" in puzzle.attributes:
            is_guilty = ask_until_valid(
                f"Is {name} guilty or innocent? (guilty/innocent): ",
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

    Args:
        puzzle: The puzzle being played.
        guess: The player's (person, attribute) -> bool answers, as
            built by collect_guess().
        solution: The real (person, attribute) -> bool answer, as
            returned by get_solution().
    """
    print()
    print_header("YOUR RESULT")
    print()

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

            detail_lines.append(
                f"    {attribute}: you guessed "
                f"{_attribute_value_label(attribute, guessed_value)}, actual answer is "
                f"{_attribute_value_label(attribute, actual_value)} - "
                f"{'correct' if correct else 'wrong'}"
            )

        puzzle_fully_correct = puzzle_fully_correct and person_fully_correct
        print(f"{name}: {'CORRECT' if person_fully_correct else 'WRONG'}")
        for line in detail_lines:
            print(line)

    print()
    if puzzle_fully_correct:
        print("You got the whole puzzle right!")
    else:
        print("You didn't get everyone right this time.")
    print()


def play_puzzle(puzzle: Puzzle, description: str) -> None:
    """Run one full play session for a single puzzle: present, guess, check, reveal.

    This is steps 2-7 of SPEC_step13.md's play loop in order: the
    puzzle's plain-language description is shown (with no solution or
    explanation), the player's guess is collected and checked against
    the real solution, and only after that does run_deduction_pipeline()
    - reused unmodified from main.py - reveal the full tactic/
    propagation/case-split explanation.

    Args:
        puzzle: The puzzle to play.
        description: Its plain-language description (people, statements,
            constraint), printed before any guessing happens.
    """
    print()
    print_header(f"KNIGHTS & KNAVES PUZZLE - {puzzle.name}")
    print()
    print(description)
    print()

    guess = collect_guess(puzzle)
    solution = get_solution(puzzle)
    report_guess(puzzle, guess, solution)

    print("Here's the full explanation:")
    run_deduction_pipeline(puzzle, description)


def main() -> None:
    """Entry point: loop between the menu and playing puzzles until the player quits.

    Matches SPEC_step13.md's step 8: after finishing a puzzle, control
    returns to the menu rather than the program exiting, so the player
    can play the other puzzle (or the same one again) without restarting.
    """
    while True:
        choice = show_menu_and_get_choice()
        if choice is None:
            print("Goodbye!")
            break

        puzzle, description = choice
        play_puzzle(puzzle, description)


if __name__ == "__main__":
    main()
