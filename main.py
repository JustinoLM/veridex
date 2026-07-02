"""Entry point: solve every puzzle and report the results.

Step 1's solver.py both solved and printed one hardcoded puzzle. Now
that solver.py is generic and puzzles live in puzzles.py, this module is
the only thing that knows how to run the pair of them and narrate the
results in plain language.
"""

from puzzles import (
    PUZZLE_1,
    PUZZLE_1_DESCRIPTION,
    PUZZLE_2,
    PUZZLE_2_DESCRIPTION,
    Puzzle,
)
from solver import SolveResult, solve

# Step 1's original printed numbers for this exact puzzle. Puzzle 1 in
# this step is meant to reproduce them exactly using the new AST-based
# machinery, so they are kept here as a fixed reference to check against
# rather than just trusted by eye.
STEP_1_TOTAL_ASSIGNMENTS = 16
STEP_1_CONSTRAINT_PASSED = 8
STEP_1_FULLY_VALID = 1


def describe_assignment(puzzle: Puzzle, assignment: dict) -> list[str]:
    """Turn one candidate assignment into plain-language sentences.

    Args:
        puzzle: The puzzle the assignment belongs to. Used to know which
            attributes each person has, since not every puzzle tracks
            guilt as well as knight/knave status.
        assignment: One (person, attribute) -> bool mapping, typically a
            member of a SolveResult's fully_valid list.

    Returns:
        A list with one sentence per person, e.g.
        ["Ada is a knave and is innocent.", "Bo is a knight and is innocent."].
    """
    sentences = []
    for person in puzzle.people:
        clauses = []
        if "is_knight" in puzzle.attributes:
            role = "a knight" if assignment[(person, "is_knight")] else "a knave"
            clauses.append(f"is {role}")
        if "is_guilty" in puzzle.attributes:
            guilt = "guilty" if assignment[(person, "is_guilty")] else "innocent"
            clauses.append(f"is {guilt}")
        name = person.capitalize()
        sentences.append(f"{name} {' and '.join(clauses)}.")
    return sentences


def print_header(title: str) -> None:
    """Print a banner line to visually separate sections of the output.

    Args:
        title: The text to display inside the banner.
    """
    print("=" * 70)
    print(title)
    print("=" * 70)


def report_solution(puzzle: Puzzle, result: SolveResult) -> None:
    """Print the final solution for a puzzle, or a warning if something went wrong.

    A well-posed Knights & Knaves puzzle has exactly one valid
    assignment. Zero or more than one indicates a bug in the puzzle's
    statements or constraints, so both cases are reported explicitly
    rather than silently guessing an answer.

    Args:
        puzzle: The puzzle whose result is being reported.
        result: The SolveResult returned by solve(puzzle).
    """
    print_header("RESULT")

    if len(result.fully_valid) == 0:
        print("WARNING: no assignment satisfies every constraint.")
        print("This puzzle is expected to have a unique solution, so this")
        print("indicates a bug in the statement or constraint logic.")
        return

    if len(result.fully_valid) > 1:
        print(
            f"WARNING: {len(result.fully_valid)} assignments satisfy every "
            "constraint, but this puzzle is expected to have a unique "
            "solution. This indicates a bug in the statement or "
            "constraint logic."
        )
        for assignment in result.fully_valid:
            print(f"  - {' '.join(describe_assignment(puzzle, assignment))}")
        return

    for sentence in describe_assignment(puzzle, result.fully_valid[0]):
        print(sentence)


def run_puzzle(puzzle: Puzzle, description: str) -> SolveResult:
    """Describe, solve, and report on a single puzzle.

    Args:
        puzzle: The puzzle to solve.
        description: Plain-language text (people, constraint,
            statements) to print before solving, so the output is
            self-explanatory without needing the source code.

    Returns:
        The SolveResult produced by solving `puzzle`, so callers such as
        the regression check can inspect its numbers afterwards.
    """
    print_header(f"KNIGHTS & KNAVES PUZZLE - {puzzle.name}")
    print()
    print(description)
    print()

    result = solve(puzzle)

    print(f"Total candidate assignments checked: {len(result.all_assignments)}")
    print(f"  Passed all constraints: {len(result.constraint_passed)}")
    print(
        f"  Failed at least one constraint: "
        f"{len(result.all_assignments) - len(result.constraint_passed)}"
    )
    print(
        f"Passed the full check (constraints + statements): "
        f"{len(result.fully_valid)}"
    )
    print()

    report_solution(puzzle, result)
    print()

    return result


def print_regression_check(result: SolveResult) -> None:
    """Compare Puzzle 1's numbers against Step 1's original output.

    Re-implementing Puzzle 1 with the new AST is only a valid step if it
    produces the exact same numbers Step 1 did with its plain-function
    approach - anything else means the AST or evaluator introduced a
    discrepancy, not that the puzzle changed.

    Args:
        result: The SolveResult produced by solving PUZZLE_1.
    """
    print_header("REGRESSION CHECK")

    matches = (
        len(result.all_assignments) == STEP_1_TOTAL_ASSIGNMENTS
        and len(result.constraint_passed) == STEP_1_CONSTRAINT_PASSED
        and len(result.fully_valid) == STEP_1_FULLY_VALID
    )

    if matches:
        print("Regression check: matches Step 1 output.")
    else:
        print("WARNING: Puzzle 1's numbers do NOT match Step 1's original output.")
        print(
            f"Expected {STEP_1_TOTAL_ASSIGNMENTS} total / "
            f"{STEP_1_CONSTRAINT_PASSED} constraint-passed / "
            f"{STEP_1_FULLY_VALID} fully-valid, got "
            f"{len(result.all_assignments)} / {len(result.constraint_passed)} / "
            f"{len(result.fully_valid)}."
        )
    print()


def main() -> None:
    """Entry point: run every puzzle in sequence and report on each."""
    result_1 = run_puzzle(PUZZLE_1, PUZZLE_1_DESCRIPTION)
    print_regression_check(result_1)

    run_puzzle(PUZZLE_2, PUZZLE_2_DESCRIPTION)


if __name__ == "__main__":
    main()
