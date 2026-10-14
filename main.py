"""Entry point: solve every puzzle and report the results.

Step 1's solver.py both solved and printed one hardcoded puzzle. Now
that solver.py is generic and puzzles live in puzzles.py, this module is
the only thing that knows how to run the pair of them and narrate the
results in plain language.
"""

from difficulty import Difficulty
from generator import (
    GENERATED_PEOPLE,
    NAME_POOL,
    describe_generated_puzzle,
    describe_generated_whodunit_puzzle,
    generate_puzzle,
    generate_whodunit_puzzle,
)
from puzzles import (
    PUZZLE_1,
    PUZZLE_1_DESCRIPTION,
    PUZZLE_2,
    PUZZLE_2_DESCRIPTION,
    Puzzle,
)
from pipeline import format_pipeline, run_pipeline
from rendering import (
    describe_assignment,
    print_header,
    run_propagation_checks,
)
from solver import SolveResult, solve

# How many freshly generated puzzles to run the full pipeline on, per
# SPEC_step7.md's output requirements.
NUM_GENERATED_PUZZLES = 3

# How many freshly generated whodunit puzzles to run the full pipeline
# on, per SPEC_step8.md's output requirements.
NUM_GENERATED_WHODUNIT_PUZZLES = 3

# How many people the Step 9 is_knight-only demonstration puzzle uses -
# large enough to be meaningfully bigger than anything generated in
# Step 7 or Step 8 (which both stay at 2), small enough that 2**4 = 16
# brute-force candidates keeps verification instant (see SPEC_step9.md).
STEP_9_DEMO_PEOPLE_COUNT = 4

# How many freshly generated rich-grammar puzzles (Implies and counting
# nodes) to run the full pipeline on, and how many people each one uses
# - three people gives a good chance of hitting both a generated Implies
# and a counting node across the set, per SPEC_step10.md.
NUM_STEP_10_PUZZLES = 3
STEP_10_DEMO_PEOPLE_COUNT = 3

# Step 1's original printed numbers for this exact puzzle. Puzzle 1 in
# this step is meant to reproduce them exactly using the new AST-based
# machinery, so they are kept here as a fixed reference to check against
# rather than just trusted by eye.
STEP_1_TOTAL_ASSIGNMENTS = 16
STEP_1_CONSTRAINT_PASSED = 8
STEP_1_FULLY_VALID = 1


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


def run_deduction_pipeline(puzzle: Puzzle, description: str) -> tuple[dict, Difficulty]:
    """Run the full deduction pipeline against `puzzle` and narrate it.

    The computation lives in pipeline.run_pipeline() and the wording in
    pipeline.format_pipeline(); this function only prints the result in
    the fixed section order (tactic, propagation, case-split, final
    solution, difficulty). It combines the three techniques described in
    SPEC_step4.md: the Step 3 tactic and backward propagation alternated
    until a fixed point, then the case-split fallback for whatever is
    still unknown, followed by the Step 11 difficulty classification.

    Args:
        puzzle: The puzzle to solve.
        description: Plain-language puzzle description, printed first so
            the output is self-explanatory without the source code.

    Returns:
        A (assignment, difficulty) pair: the final assignment once the
        pipeline finishes - fully resolved for a well-posed puzzle, but
        returned as-is even if it is not, so callers can inspect what did
        and did not get resolved - alongside the Difficulty this run
        classified as.
    """
    print_header(f"FULL DEDUCTION PIPELINE - {puzzle.name}")
    print()
    print(description)
    print()

    result = run_pipeline(puzzle)
    sections = format_pipeline(puzzle, result)

    if sections.warning:
        print(sections.warning)
        print()

    for heading, body in (
        ("Tactic (hypothesize-and-check on knight/knave status):", sections.tactic),
        ("Backward propagation:", sections.propagation),
        ("Case-split fallback:", sections.case_split),
        ("Final solution:", sections.final),
    ):
        print(heading)
        print()
        print(body)
        print()

    print(f"Difficulty: {sections.difficulty}")
    print()

    return result.assignment, result.difficulty


def run_generated_puzzles() -> list[Difficulty]:
    """Generate NUM_GENERATED_PUZZLES new random puzzles and solve each one.

    Step 7's whole point is to confirm that the full Steps 3-6 deduction
    pipeline is genuinely generic, not something that happens to work
    only because it was written and tuned against Puzzle 1 and Puzzle
    2's specific shape. generate_puzzle() only guarantees a *unique*
    solution via the Step 2 brute-force solver - it says nothing about
    whether the tactic, propagation, or case-split fallback will be able
    to resolve it. Calling run_deduction_pipeline() unmodified on its
    output, and getting a full resolution back, is exactly that
    confirmation.

    For each generated puzzle, this prepends how many attempts it took
    to find a unique-solution puzzle onto the usual plain-language
    description, so that line appears alongside the puzzle statement and
    the full explanation without needing any change to
    run_deduction_pipeline() itself.

    Returns:
        The Difficulty each generated puzzle classified as, in the order
        generated, so main() can fold them into the overall Step 11
        summary across every puzzle the program runs.
    """
    print_header("GENERATED PUZZLES")
    print()

    difficulties = []
    for index in range(1, NUM_GENERATED_PUZZLES + 1):
        generated = generate_puzzle(GENERATED_PEOPLE)
        # Give each generated puzzle a distinct, numbered name so the
        # section headers below don't all read identically.
        generated.puzzle.name = f"Generated puzzle {index}"

        description = (
            f"Found after {generated.attempts} attempt(s) - a candidate "
            "puzzle is discarded and a new one generated unless it has "
            "exactly one valid solution.\n\n"
            f"{describe_generated_puzzle(generated.puzzle)}"
        )

        _, difficulty = run_deduction_pipeline(generated.puzzle, description)
        difficulties.append(difficulty)

    return difficulties


def run_generated_whodunit_puzzles() -> list[Difficulty]:
    """Generate NUM_GENERATED_WHODUNIT_PUZZLES whodunit puzzles and solve each one.

    Step 8's whole point (see SPEC_step8.md) is the same kind of
    confirmation as Step 7's run_generated_puzzles(), but for the richer
    whodunit shape: both is_knight and is_guilty attributes, statements
    that can reference either, and a randomly generated guilt
    constraint - exactly Puzzle 1's structure, but generated rather than
    hand-written. generate_whodunit_puzzle() only guarantees a unique
    solution via the Step 2 brute-force solver; calling
    run_deduction_pipeline() unmodified on its output, and getting a
    full resolution back, confirms the tactic/propagation/case-split
    pipeline handles this richer shape too, with no puzzle-specific
    code.

    For each generated puzzle, this prepends how many attempts it took
    onto the usual plain-language description (built with
    describe_generated_whodunit_puzzle() so the constraint is included),
    exactly as run_generated_puzzles() does for Step 7's puzzles.

    Returns:
        The Difficulty each generated whodunit puzzle classified as, in
        the order generated, so main() can fold them into the overall
        Step 11 summary across every puzzle the program runs.
    """
    print_header("GENERATED WHODUNIT PUZZLES")
    print()

    difficulties = []
    for index in range(1, NUM_GENERATED_WHODUNIT_PUZZLES + 1):
        generated = generate_whodunit_puzzle()
        # Give each generated puzzle a distinct, numbered name so the
        # section headers below don't all read identically.
        generated.puzzle.name = f"Generated whodunit puzzle {index}"

        description = (
            f"Found after {generated.attempts} attempt(s) - a candidate "
            "puzzle is discarded and a new one generated unless it has "
            "exactly one valid solution.\n\n"
            f"{describe_generated_whodunit_puzzle(generated.puzzle)}"
        )

        _, difficulty = run_deduction_pipeline(generated.puzzle, description)
        difficulties.append(difficulty)

    return difficulties


def run_generated_n_person_puzzle() -> list[Difficulty]:
    """Generate one is_knight-only puzzle with more than 2 people and solve it.

    Step 7's generate_puzzle() was fixed to exactly two people. Step 9
    generalizes it to take any `people` list (see SPEC_step9.md,
    including the calibration confirming acceptance rate stays roughly
    stable as people are added), and this demonstrates that
    generalization with a single puzzle at STEP_9_DEMO_PEOPLE_COUNT
    people - meaningfully bigger than anything generated in Step 7 or
    Step 8, both of which stay at 2. As with every other generated
    puzzle in this project, the attempt count is printed so it can be
    compared against SPEC_step9.md's calibration table, and the puzzle
    is run through the exact same unmodified Steps 3-6 pipeline as
    every hand-written and generated puzzle before it.

    Returns:
        A single-element list holding this puzzle's Difficulty, kept as
        a list (rather than the bare Difficulty) so main() can fold it
        into the overall Step 11 summary the same way as every other
        run_generated_*() function's result.
    """
    print_header("GENERATED N-PERSON PUZZLE")
    print()

    people = NAME_POOL[:STEP_9_DEMO_PEOPLE_COUNT]
    generated = generate_puzzle(people)
    generated.puzzle.name = f"Generated {STEP_9_DEMO_PEOPLE_COUNT}-person puzzle"

    description = (
        f"Found after {generated.attempts} attempt(s) - a candidate "
        "puzzle is discarded and a new one generated unless it has "
        "exactly one valid solution.\n\n"
        f"{describe_generated_puzzle(generated.puzzle)}"
    )

    _, difficulty = run_deduction_pipeline(generated.puzzle, description)
    return [difficulty]


def run_generated_rich_grammar_puzzles() -> list[Difficulty]:
    """Generate NUM_STEP_10_PUZZLES rich-grammar is_knight-only puzzles and solve each one.

    Step 10 (see SPEC_step10.md) extends random_statement()'s grammar,
    for the is_knight-only generator only, to include Implies and
    counting nodes (ExactlyN/AtLeastN/AtMostN) alongside And/Or/Iff -
    the connectives this whole project was originally motivated by (the
    vacuous-truth-of-implication gap, and Puzzle 2's "exactly N knaves"
    style reasoning). generate_puzzle() takes an allow_rich_grammar flag
    (default False, so the Step 7 and Step 9 demonstration puzzles keep
    their exact prior behavior); this is the one caller that passes
    True. Calling it here at STEP_10_DEMO_PEOPLE_COUNT people - chosen
    for a good chance of hitting both a generated Implies and a counting
    node across the set, per SPEC_step10.md's calibration - and running
    the same unmodified Steps 3-6 pipeline on the result confirms that
    pipeline handles the richer grammar too, with no puzzle-specific
    code, same as every other generated puzzle in this project.

    Returns:
        The Difficulty each generated rich-grammar puzzle classified as,
        in the order generated, so main() can fold them into the overall
        Step 11 summary across every puzzle the program runs.
    """
    print_header("GENERATED PUZZLES (RICH GRAMMAR: IMPLIES & COUNTING NODES)")
    print()

    difficulties = []
    people = NAME_POOL[:STEP_10_DEMO_PEOPLE_COUNT]
    for index in range(1, NUM_STEP_10_PUZZLES + 1):
        generated = generate_puzzle(people, allow_rich_grammar=True)
        # Give each generated puzzle a distinct, numbered name so the
        # section headers below don't all read identically.
        generated.puzzle.name = f"Generated rich-grammar puzzle {index}"

        description = (
            f"Found after {generated.attempts} attempt(s) - a candidate "
            "puzzle is discarded and a new one generated unless it has "
            "exactly one valid solution.\n\n"
            f"{describe_generated_puzzle(generated.puzzle)}"
        )

        _, difficulty = run_deduction_pipeline(generated.puzzle, description)
        difficulties.append(difficulty)

    return difficulties


def print_difficulty_summary(
    difficulties: list[Difficulty],
    puzzle_1_difficulty: Difficulty,
    puzzle_2_difficulty: Difficulty,
    step_9_difficulty: Difficulty,
) -> None:
    """Print the end-of-program difficulty tally and check it against SPEC_step11.md's expectations.

    The tally itself is a plain count of every Difficulty returned by
    every puzzle run() this execution, across every step's output - not
    just the ones generated in this call. On top of that, this also
    checks three specific expectations SPEC_step11.md calls out by name
    (Puzzle 1 and Puzzle 2 both HARD, Step 9's demo puzzle EASY) and a
    fourth, softer one (MEDIUM may turn out to be entirely unobserved).
    These are printed as explicit [PASS]/[WARNING] lines, the same
    honest-reporting style print_regression_check() already uses for
    Puzzle 1's brute-force numbers - a mismatch here means the actual
    run's puzzles didn't behave the way earlier steps found, and that is
    worth surfacing plainly rather than silently accepting a number that
    doesn't match.

    Args:
        difficulties: Every Difficulty this execution classified, one
            per puzzle run, across every step's output.
        puzzle_1_difficulty: Puzzle 1's own Difficulty, checked
            separately since SPEC_step11.md expects it to be HARD.
        puzzle_2_difficulty: Puzzle 2's own Difficulty, checked
            separately since SPEC_step11.md expects it to be HARD.
        step_9_difficulty: Step 9's 4-person demo puzzle's own
            Difficulty, checked separately since SPEC_step11.md expects
            it to be EASY.
    """
    print_header("DIFFICULTY SUMMARY")
    print()

    counts = {tier: 0 for tier in Difficulty}
    for difficulty in difficulties:
        counts[difficulty] += 1

    print(f"Total puzzles classified: {len(difficulties)}")
    for tier in (Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD):
        print(f"  {tier.value.upper()}: {counts[tier]}")
    print()

    if counts[Difficulty.MEDIUM] == 0:
        # Not a bug - see SPEC_step11.md's "Known expected results".
        # Propagation has not resolved a single fact on any real puzzle
        # generated through Steps 7-10, only in Step 4/10's standalone
        # constructed checks, so MEDIUM turning up empty here is a real
        # finding about this generator and grammar, not a classifier
        # defect - stated explicitly rather than left to be noticed (or
        # missed) by silence.
        print(
            "No puzzle in this run classified as MEDIUM. This matches "
            "the documented expectation: propagation has not resolved a "
            "single fact on any real puzzle generated through Steps 7-10, "
            "only in Step 4/10's standalone constructed checks - so this "
            "reflects the current generator and grammar, not a bug in "
            "classify_difficulty()."
        )
        print()

    expectation_checks = [
        ("Puzzle 1 classifies as HARD", puzzle_1_difficulty == Difficulty.HARD),
        ("Puzzle 2 classifies as HARD", puzzle_2_difficulty == Difficulty.HARD),
        (
            "Step 9's 4-person demo puzzle classifies as EASY",
            step_9_difficulty == Difficulty.EASY,
        ),
    ]
    for check_description, passed in expectation_checks:
        # Generated puzzles are unseeded, so a mismatch on the Step 9
        # demo can be a legitimate run-to-run variation, not a bug.
        status = "PASS" if passed else "WARNING - does not match the expected tier"
        print(f"  [{status}] {check_description}")
    print()


def main() -> None:
    """Entry point: run every puzzle in sequence and report on each."""
    result_1 = run_puzzle(PUZZLE_1, PUZZLE_1_DESCRIPTION)
    print_regression_check(result_1)

    run_puzzle(PUZZLE_2, PUZZLE_2_DESCRIPTION)

    # Step 4: validate propagate() on its own before trusting it inside
    # the pipeline below - see SPEC_step4.md for why neither puzzle's
    # real trace exercises every branch it implements.
    run_propagation_checks()

    # Step 4: run the full three-technique pipeline (tactic, propagation,
    # case-split fallback) against both puzzles. Unlike Step 3's
    # tactic-only demonstration, both puzzles are expected to come out
    # fully solved. Step 11 also collects each one's Difficulty, for the
    # end-of-program summary below.
    _, puzzle_1_difficulty = run_deduction_pipeline(PUZZLE_1, PUZZLE_1_DESCRIPTION)
    _, puzzle_2_difficulty = run_deduction_pipeline(PUZZLE_2, PUZZLE_2_DESCRIPTION)

    # Step 7: generate new puzzles (not hand-written) and confirm the
    # same pipeline solves them too, with no puzzle-specific code.
    generated_difficulties = run_generated_puzzles()

    # Step 8: generate whodunit puzzles (both attributes, plus a guilt
    # constraint) and confirm the same pipeline solves those too.
    generated_whodunit_difficulties = run_generated_whodunit_puzzles()

    # Step 9: generate an is_knight-only puzzle with more than 2 people,
    # confirming generate_puzzle()'s generalization to N people and that
    # the same unmodified pipeline still solves it.
    n_person_difficulties = run_generated_n_person_puzzle()

    # Step 10: generate is_knight-only puzzles using the richer grammar
    # (Implies and counting nodes), confirming the same unmodified
    # pipeline handles them too.
    rich_grammar_difficulties = run_generated_rich_grammar_puzzles()

    # Step 11: fold every Difficulty classified above - hand-written and
    # generated alike - into one end-of-program summary (see
    # SPEC_step11.md's output requirements).
    all_difficulties = (
        [puzzle_1_difficulty, puzzle_2_difficulty]
        + generated_difficulties
        + generated_whodunit_difficulties
        + n_person_difficulties
        + rich_grammar_difficulties
    )
    print_difficulty_summary(
        all_difficulties,
        puzzle_1_difficulty=puzzle_1_difficulty,
        puzzle_2_difficulty=puzzle_2_difficulty,
        step_9_difficulty=n_person_difficulties[0],
    )


if __name__ == "__main__":
    main()
