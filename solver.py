"""Brute-force solver for a single, hardcoded Knights & Knaves puzzle.

This is a "whodunit" variant: two co-defendants, Ada and Bo, are each
either a knight (always truthful) or a knave (always lies). They are
also each either guilty or innocent of a crime. The puzzle is solved by
enumerating every possible combination of these attributes and keeping
only the combinations that are logically consistent.
"""

from dataclasses import dataclass
from itertools import product


@dataclass
class Person:
    """A single co-defendant's two independent boolean attributes.

    Attributes:
        is_knight: True if the person always tells the truth (a knight),
            False if the person always lies (a knave).
        is_guilty: True if the person is guilty of the crime, False if
            they are innocent.
    """

    is_knight: bool
    is_guilty: bool


def statement_ada(assignment):
    """Evaluate Ada's statement under one candidate assignment.

    Ada says: "I am a knave, and none of us are innocent."
    That is a conjunction of two separate claims, both of which must
    hold for the statement as a whole to be true:
      1. Ada herself is a knave (i.e. is_knight is False).
      2. Nobody is innocent, meaning both Ada and Bo are guilty.

    Args:
        assignment: A dict with keys "ada" and "bo" mapping to Person
            instances, describing one candidate world.

    Returns:
        True if Ada's statement is true in this candidate world, False
        otherwise. This is the statement's truth value, independent of
        whether Ada is actually a knight or a knave.
    """
    ada = assignment["ada"]
    bo = assignment["bo"]
    ada_claims_to_be_knave = not ada.is_knight
    ada_claims_nobody_innocent = ada.is_guilty and bo.is_guilty
    return ada_claims_to_be_knave and ada_claims_nobody_innocent


def statement_bo(assignment):
    """Evaluate Bo's statement under one candidate assignment.

    Bo says: "Ada and I are either both guilty or both innocent."
    This is true exactly when Ada's guilt matches Bo's guilt, since
    those are the only two ways for them to be "both the same".

    Args:
        assignment: A dict with keys "ada" and "bo" mapping to Person
            instances, describing one candidate world.

    Returns:
        True if Bo's statement is true in this candidate world, False
        otherwise.
    """
    ada = assignment["ada"]
    bo = assignment["bo"]
    return ada.is_guilty == bo.is_guilty


def guilt_constraint_holds(assignment):
    """Check the puzzle's "all-or-nothing guilt" constraint.

    The puzzle states that if anyone is guilty, all co-defendants are
    guilty. With exactly two people, that rule collapses to a simple
    equality check: their guilt values must match (both guilty, or
    both innocent). A world where exactly one of them is guilty would
    violate the rule and must be rejected before we even look at what
    anyone said.

    Args:
        assignment: A dict with keys "ada" and "bo" mapping to Person
            instances, describing one candidate world.

    Returns:
        True if the assignment respects the all-or-nothing rule, False
        otherwise.
    """
    ada = assignment["ada"]
    bo = assignment["bo"]
    return ada.is_guilty == bo.is_guilty


def statement_matches_speaker(statement_is_true, speaker):
    """Check that a statement's truth value fits its speaker's nature.

    Knights always tell the truth, so a knight's statement must be
    true. Knaves always lie, so a knave's statement must be false.
    This helper captures that single rule so it is not duplicated for
    both Ada and Bo in the main brute-force loop.

    Args:
        statement_is_true: The truth value of the statement, as
            computed by statement_ada or statement_bo.
        speaker: The Person who made the statement.

    Returns:
        True if the statement's truth value is consistent with the
        speaker being a knight or a knave, False otherwise.
    """
    if speaker.is_knight:
        return statement_is_true
    return not statement_is_true


def describe_puzzle():
    """Print the puzzle's setup so the output is self-explanatory.

    Someone running this script with no other context should be able
    to read this description and understand exactly what is being
    solved and why, before seeing a single line of solving logic run.
    """
    print("=" * 70)
    print("KNIGHTS & KNAVES PUZZLE")
    print("=" * 70)
    print()
    print("Two co-defendants, Ada and Bo, are on trial. Each of them is")
    print("either a knight (always tells the truth) or a knave (always")
    print("lies). Each of them is also either guilty or innocent of the")
    print("crime under investigation.")
    print()
    print("Constraint: guilt is all-or-nothing between the two of them.")
    print("If either one is guilty, both of them are guilty.")
    print()
    print("Statements:")
    print('  Ada says: "I am a knave, and none of us are innocent."')
    print('  Bo says:  "Ada and I are either both guilty or both innocent."')
    print()
    print("Goal: find the one assignment of (knight/knave, guilty/")
    print("innocent) to Ada and Bo that is fully consistent with the")
    print("constraint above and with both statements.")
    print()


def generate_all_assignments():
    """Build every candidate assignment of attributes to Ada and Bo.

    There are two people, each with two independent boolean attributes
    (is_knight and is_guilty), giving 2^4 = 16 total combinations. This
    function enumerates all of them without applying any puzzle logic;
    filtering happens later.

    Returns:
        A list of dicts, each with keys "ada" and "bo" mapping to
        Person instances, covering all 16 possible worlds.
    """
    assignments = []
    # itertools.product over four independent True/False choices gives
    # every combination of (Ada knight?, Ada guilty?, Bo knight?, Bo
    # guilty?) exactly once, in a fixed, predictable order.
    for ada_knight, ada_guilty, bo_knight, bo_guilty in product(
        [True, False], repeat=4
    ):
        assignment = {
            "ada": Person(is_knight=ada_knight, is_guilty=ada_guilty),
            "bo": Person(is_knight=bo_knight, is_guilty=bo_guilty),
        }
        assignments.append(assignment)
    return assignments


def solve():
    """Run the full brute-force search and report the results.

    This is the core of the solver: it generates every candidate
    world, checks each one against the puzzle's constraint and both
    statements, and keeps track of how many candidates survive each
    stage so the final output can explain the process, not just the
    answer.

    Returns:
        A list of assignments (dicts with "ada" and "bo" keys) that
        satisfy both the guilt constraint and both statements. For a
        well-posed puzzle like this one, this list should contain
        exactly one entry.
    """
    all_assignments = generate_all_assignments()

    constraint_passed = []
    constraint_failed = []
    for assignment in all_assignments:
        # Reject any world where guilt is split between Ada and Bo
        # before spending any effort evaluating their statements.
        if guilt_constraint_holds(assignment):
            constraint_passed.append(assignment)
        else:
            constraint_failed.append(assignment)

    fully_valid = []
    for assignment in constraint_passed:
        ada_statement_true = statement_ada(assignment)
        bo_statement_true = statement_bo(assignment)

        # Each speaker's statement must line up with whether they are
        # a knight (truth-teller) or a knave (liar). Both checks must
        # pass for the assignment to be a valid solution.
        ada_consistent = statement_matches_speaker(
            ada_statement_true, assignment["ada"]
        )
        bo_consistent = statement_matches_speaker(
            bo_statement_true, assignment["bo"]
        )

        if ada_consistent and bo_consistent:
            fully_valid.append(assignment)

    print(f"Total candidate assignments checked: {len(all_assignments)}")
    print(f"  Passed the all-or-nothing guilt constraint: "
          f"{len(constraint_passed)}")
    print(f"  Failed the all-or-nothing guilt constraint: "
          f"{len(constraint_failed)}")
    print(f"Passed the full check (constraint + statements): "
          f"{len(fully_valid)}")
    print()

    return fully_valid


def describe_person(name, person):
    """Turn one person's attributes into a plain-language sentence.

    Args:
        name: The person's name, e.g. "Ada".
        person: The Person instance describing their attributes.

    Returns:
        A human-readable sentence describing this person's role and
        guilt, e.g. "Ada is a knave and is innocent."
    """
    role = "knight" if person.is_knight else "knave"
    guilt = "guilty" if person.is_guilty else "innocent"
    return f"{name} is a {role} and is {guilt}."


def report_solution(valid_assignments):
    """Print the final solution, or a warning if something went wrong.

    A well-posed Knights & Knaves puzzle has exactly one valid
    assignment. Finding zero or more than one would indicate a bug in
    the puzzle logic above, so both of those cases are reported as
    explicit warnings rather than silently picking an answer.

    Args:
        valid_assignments: The list of assignments returned by solve().
    """
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    if len(valid_assignments) == 0:
        print("WARNING: no assignment satisfies every constraint.")
        print("This puzzle is known to have a unique solution, so this")
        print("indicates a bug in the statement or constraint logic.")
        return

    if len(valid_assignments) > 1:
        print(f"WARNING: {len(valid_assignments)} assignments satisfy every")
        print("constraint, but this puzzle is known to have a unique")
        print("solution. This indicates a bug in the statement or")
        print("constraint logic.")
        for assignment in valid_assignments:
            print(f"  - {describe_person('Ada', assignment['ada'])} "
                  f"{describe_person('Bo', assignment['bo'])}")
        return

    solution = valid_assignments[0]
    print(describe_person("Ada", solution["ada"]))
    print(describe_person("Bo", solution["bo"]))


def main():
    """Entry point: describe the puzzle, solve it, and report the result."""
    describe_puzzle()
    valid_assignments = solve()
    report_solution(valid_assignments)


if __name__ == "__main__":
    main()
