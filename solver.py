"""Generic brute-force solver for Knights & Knaves puzzles.

Step 1's solver had the puzzle (people, statements, constraint) baked
directly into its functions. This version takes a `Puzzle` (see
puzzles.py) as data and works purely off it: nothing here refers to
Ada, Bo, Cal, or any specific statement. The same code solves any puzzle
that can be expressed as a `Puzzle`.
"""

from dataclasses import dataclass
from itertools import product

from expressions import evaluate
from puzzles import Puzzle


@dataclass
class SolveResult:
    """Everything a caller needs to report on one run of the solver.

    Keeping all three assignment lists (not just the final answer) lets
    the caller print the same "how many survived each stage" narration
    Step 1 printed, without solve() itself knowing anything about how
    that narration should look.

    Attributes:
        all_assignments: Every candidate assignment that was generated,
            before any filtering.
        constraint_passed: The subset of all_assignments that satisfies
            every constraint in the puzzle.
        fully_valid: The subset of constraint_passed whose statements are
            also all consistent with their speakers' knight/knave status.
            For a well-posed puzzle, this should contain exactly one
            assignment.
    """

    all_assignments: list[dict]
    constraint_passed: list[dict]
    fully_valid: list[dict]


def generate_all_assignments(puzzle: Puzzle) -> list[dict]:
    """Enumerate every possible candidate assignment for a puzzle.

    A candidate assignment fixes a boolean value for every (person,
    attribute) pair - e.g. ("ada", "is_knight") - with no regard yet for
    whether that combination makes any logical sense. There are
    2^(len(people) * len(attributes)) such combinations in total, since
    each attribute of each person is an independent True/False choice.

    Args:
        puzzle: The puzzle whose people and attributes define the shape
            of each assignment.

    Returns:
        A list of dicts, each mapping every (person, attribute) pair to
        a boolean, covering all possible combinations exactly once.
    """
    # Fix a canonical order for the (person, attribute) keys so that
    # itertools.product's output positions line up with them one-to-one.
    keys = [
        (person, attribute)
        for person in puzzle.people
        for attribute in puzzle.attributes
    ]

    assignments = []
    for values in product([True, False], repeat=len(keys)):
        assignments.append(dict(zip(keys, values)))
    return assignments


def constraints_hold(puzzle: Puzzle, assignment: dict) -> bool:
    """Check whether an assignment satisfies every one of the puzzle's constraints.

    Args:
        puzzle: The puzzle whose constraints to check.
        assignment: One candidate (person, attribute) -> bool mapping.

    Returns:
        True iff every expression in puzzle.constraints evaluates to True
        under this assignment. An empty constraint list is vacuously
        satisfied.
    """
    return all(evaluate(constraint, assignment) for constraint in puzzle.constraints)


def statements_consistent(puzzle: Puzzle, assignment: dict) -> bool:
    """Check that every person's statement matches their knight/knave status.

    A knight always tells the truth, so a knight's statement must
    evaluate to True. A knave always lies, so a knave's statement must
    evaluate to False. In both cases, this is exactly the condition
    "the statement's truth value equals is_knight".

    Args:
        puzzle: The puzzle whose statements to check.
        assignment: One candidate (person, attribute) -> bool mapping.

    Returns:
        True iff, for every person in puzzle.statements, the truth value
        of their statement equals their is_knight value in `assignment`.
    """
    for person, statement in puzzle.statements.items():
        statement_is_true = evaluate(statement, assignment)
        speaker_is_knight = assignment[(person, "is_knight")]
        if statement_is_true != speaker_is_knight:
            return False
    return True


def solve(puzzle: Puzzle) -> SolveResult:
    """Run the full brute-force search for one puzzle.

    This mirrors Step 1's solve() function, but generalized: it no
    longer knows anything about Ada, Bo, guilt, or any specific
    statement. It just enumerates every assignment the puzzle's shape
    allows, keeps the ones that satisfy the puzzle's constraints, and
    from those keeps the ones whose statements are all consistent with
    their speakers.

    Args:
        puzzle: The puzzle to solve.

    Returns:
        A SolveResult with the full breakdown of which assignments
        survived each filtering stage.
    """
    all_assignments = generate_all_assignments(puzzle)

    # First filter: reject worlds that violate the puzzle's own rules,
    # before spending any effort evaluating what anyone said.
    constraint_passed = [
        assignment
        for assignment in all_assignments
        if constraints_hold(puzzle, assignment)
    ]

    # Second filter: among the worlds that respect the puzzle's rules,
    # keep only those where every statement lines up with its speaker's
    # knight/knave status.
    fully_valid = [
        assignment
        for assignment in constraint_passed
        if statements_consistent(puzzle, assignment)
    ]

    return SolveResult(
        all_assignments=all_assignments,
        constraint_passed=constraint_passed,
        fully_valid=fully_valid,
    )
