"""Entry point: solve every puzzle and report the results.

Step 1's solver.py both solved and printed one hardcoded puzzle. Now
that solver.py is generic and puzzles live in puzzles.py, this module is
the only thing that knows how to run the pair of them and narrate the
results in plain language.
"""

from expressions import And, Expr, Iff, Implies, IsKnave, IsKnight, Not, Or
from puzzles import (
    PUZZLE_1,
    PUZZLE_1_DESCRIPTION,
    PUZZLE_2,
    PUZZLE_2_DESCRIPTION,
    Puzzle,
)
from solver import (
    CaseSplitResult,
    PropagationStep,
    SolveResult,
    TacticStep,
    case_split_fallback,
    propagate,
    propagate_round,
    solve,
    try_resolve_knight_status,
)

# Safety cap on how many rounds the tactic/propagation loop is allowed to
# run for before giving up on reaching a fixed point. Puzzles this size
# are expected to stabilize in one or two rounds; this cap exists only to
# guarantee termination if that assumption is ever wrong.
MAX_PIPELINE_ROUNDS = 10

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


def _find_self_type_claim(statement: Expr, person: str) -> IsKnight | IsKnave | None:
    """Search a statement for a direct claim about the speaker's own type.

    Some statements assert something about the speaker's own knight/knave
    status directly (e.g. Ada's "I am a knave", buried inside a larger
    And). When the tactic's contradiction comes from exactly this kind of
    clause, render_tactic_step() can name it specifically ("her statement
    includes 'I am a knave'") instead of only reporting the raw
    True/False mismatch. This walks the usual logical connectives looking
    for an IsKnight/IsKnave node about `person` themselves; it does not
    need to handle ExactlyN/AtLeastN/AtMostN, since neither puzzle this
    step covers has a self-referential claim buried inside one of those.

    Args:
        statement: The Expr tree to search (typically a person's own
            statement).
        person: The name to look for inside IsKnight/IsKnave nodes.

    Returns:
        The first matching IsKnight or IsKnave node found, or None if the
        statement contains no direct claim about `person`'s own type.
    """
    match statement:
        case IsKnight(p) if p == person:
            return statement
        case IsKnave(p) if p == person:
            return statement
        case And(exprs) | Or(exprs):
            for sub in exprs:
                found = _find_self_type_claim(sub, person)
                if found is not None:
                    return found
            return None
        case Not(inner):
            return _find_self_type_claim(inner, person)
        case Implies(antecedent, consequent):
            return _find_self_type_claim(antecedent, person) or _find_self_type_claim(
                consequent, person
            )
        case Iff(left, right):
            return _find_self_type_claim(left, person) or _find_self_type_claim(
                right, person
            )
        case _:
            # IsGuilty/IsInnocent (irrelevant here) and the counting nodes
            # (out of scope, per the docstring above) all fall through to
            # "no self-type claim found here".
            return None


def render_tactic_step(step: TacticStep) -> str:
    """Turn one TacticStep into a short natural-language explanation.

    This is the natural-language rendering this whole project was
    originally motivated by: it turns the raw hypothesize-and-check
    result recorded in `step` into a short paragraph that names the
    hypothesis tried, what it would have implied, why that implication is
    a contradiction, and the conclusion - mirroring the structure of the
    by-hand explanation this project started from.

    Args:
        step: A TacticStep as produced by try_resolve_knight_status().
            Its contradicting_hypothesis is assumed to be set (not None),
            since this function is only ever called on steps the tactic
            actually resolved via a contradiction.

    Returns:
        A 4-sentence natural-language explanation string.
    """
    name = step.person.capitalize()
    hypothesis_role = "knight" if step.contradicting_hypothesis else "knave"
    resolved_role = "knight" if step.resolved_value else "knave"
    required_str = "true" if step.contradicting_hypothesis else "false"

    sentences = [
        f"Suppose {name} is a {hypothesis_role}.",
        f"Then their statement would have to be {required_str}.",
    ]

    self_claim = _find_self_type_claim(step.statement, step.person)
    claimed_role = None
    if self_claim is not None:
        claimed_role = "knight" if isinstance(self_claim, IsKnight) else "knave"

    if self_claim is not None and claimed_role != hypothesis_role:
        # The statement directly claims the speaker is the *opposite*
        # type from the one being hypothesized - that single clause is
        # already enough to explain the contradiction in plain terms,
        # since a person of `hypothesis_role` type could never truthfully
        # make that claim about themselves.
        sentences.append(
            f"But their statement includes 'I am a {claimed_role}' — "
            f"which a {hypothesis_role} could never truthfully say."
        )
    else:
        # No single self-referential clause explains the contradiction on
        # its own (or the statement makes no claim about the speaker's
        # own type at all) - fall back to reporting the plain mismatch
        # between what was required and what the statement evaluated to.
        sentences.append(
            f"But under that assumption, the statement evaluates to "
            f"{step.contradiction_result} instead of the required {required_str}."
        )

    sentences.append(
        f"This is a contradiction, so {name} cannot be a {hypothesis_role} — "
        f"{name} is a {resolved_role}."
    )

    return " ".join(sentences)


def render_propagation_step(step: PropagationStep) -> str:
    """Turn one PropagationStep into a short natural-language explanation.

    Unlike render_tactic_step() (which explains a hypothesize-and-check
    contradiction), propagation never guesses - it only ever fires when a
    fact is the *sole* remaining way to satisfy an already-required truth
    value. The explanation follows that shape directly: name the
    connective that was doing the requiring (step.source_expr_description
    already carries the plain-language "why" - see _PropagationReason in
    solver.py), state what it was required to equal, and state the one
    conclusion that leaves.

    Args:
        step: A PropagationStep as produced by propagate().

    Returns:
        A 2-sentence natural-language explanation string.
    """
    fact_phrase = _describe_fact((step.person, step.attribute), step.resolved_value)
    required_word = "true" if step.required_value else "false"

    return (
        f"This follows from {step.source_expr_description}. "
        f"Since it must be {required_word}, the only remaining possibility is that "
        f"{fact_phrase}."
    )


def render_case_split(result: CaseSplitResult) -> str:
    """Turn one CaseSplitResult into a short natural-language paragraph.

    This is the harder writing problem flagged in SPEC_step5.md: unlike
    the tactic and propagation, case-split isn't a clever inference, it's
    exhaustive checking - and the explanation says so plainly rather than
    dressing it up. Per SPEC_step6.md, the paragraph always covers, in
    order: (1) an honest statement of how many values were unknown and
    that every combination was checked, (2) the winning combination in
    plain language, (3) a per-person confirmation that each statement's
    truth value matches its speaker's resolved type, and (4) one concrete
    rejected combination as a counterexample.

    Args:
        result: A CaseSplitResult as produced by case_split_fallback().
            Assumed to have a winning_combination (not None), since this
            is only ever called once case-split has actually resolved a
            puzzle - an ambiguous or unsatisfiable result is reported as
            a warning elsewhere instead of rendered here.

    Returns:
        A short natural-language paragraph (several sentences).
    """
    sentences = []

    # Element 1: honest framing. Exhaustive checking is the whole point
    # here, so the sentence says exactly that instead of implying insight.
    unknown_names = ", ".join(
        f"{person.capitalize()}.{attribute}" for person, attribute in result.remaining_unknowns
    )
    sentences.append(
        f"At this point {len(result.remaining_unknowns)} value(s) were still unknown "
        f"({unknown_names}), so every one of the {result.total_combinations} possible "
        "combinations was checked systematically rather than deduced directly."
    )

    # Element 2: the winning combination, in the same "knight/knave,
    # guilty/innocent" phrasing used everywhere else in this project.
    winning_facts = "; ".join(
        _describe_fact(key, result.winning_combination[key]) for key in result.remaining_unknowns
    )
    sentences.append(f"Exactly one combination survived every check: {winning_facts}.")

    # Element 3: per-person consistency - each statement's truth value
    # matches its speaker's resolved type, confirmed using the truth
    # values already computed when the winning combination was found.
    consistency_clauses = []
    for person, statement_truth in result.statement_truth_by_person.items():
        is_knight = result.winning_combination[(person, "is_knight")]
        role = "knight" if is_knight else "knave"
        truth_word = "true" if statement_truth else "false"
        consistency_clauses.append(
            f"{person.capitalize()}'s statement evaluates to {truth_word}, matching "
            f"{person.capitalize()} being a {role}"
        )
    if consistency_clauses:
        sentences.append("; ".join(consistency_clauses) + ".")

    # Element 4: one concrete counterexample, naming the specific
    # combination tried and exactly which check it violated.
    rejected = result.example_rejected
    if rejected is not None:
        rejected_facts = "; ".join(
            _describe_fact(key, value) for key, value in rejected.values.items()
        )
        expected_word = "true" if rejected.expected_value else "false"
        actual_word = "true" if rejected.actual_value else "false"
        sentences.append(
            f"For example, the combination where {rejected_facts} was rejected: it "
            f"required {rejected.failed_check} to be {expected_word}, but it actually "
            f"evaluated to {actual_word}."
        )

    return " ".join(sentences)


def _describe_fact(key: tuple[str, str], value: bool) -> str:
    """Turn one (person, attribute) -> bool fact into a plain-language phrase.

    Shared by the propagation-round report and the final-solution report,
    since both need to turn the same kind of raw fact into a sentence
    fragment like "Bo is guilty" or "Ada is a knave".

    Args:
        key: A (person, attribute) pair, e.g. ("bo", "is_guilty").
        value: The boolean value that attribute is forced or known to be.

    Returns:
        A short phrase describing the fact, e.g. "Bo is guilty".
    """
    person, attribute = key
    name = person.capitalize()
    if attribute == "is_knight":
        return f"{name} is {'a knight' if value else 'a knave'}"
    if attribute == "is_guilty":
        return f"{name} is {'guilty' if value else 'innocent'}"
    return f"{name}.{attribute} = {value}"


def run_deduction_pipeline(puzzle: Puzzle, description: str) -> dict:
    """Run the full Step 4 deduction pipeline against `puzzle` and report on it.

    Combines the three techniques described in SPEC_step4.md:
    1. The Step 3 tactic (try_resolve_knight_status) and backward
       propagation (propagate_round), alternated round by round until a
       round resolves and forces nothing new (a fixed point).
    2. The case-split fallback, scoped to whichever (person, attribute)
       values are still unknown once that fixed point is reached.

    Unlike Step 3's tactic-only demonstration, this is expected to fully
    solve both puzzles - see SPEC_step4.md's "Expected results" for the
    exact numbers this should produce for each one.

    Args:
        puzzle: The puzzle to solve.
        description: Plain-language puzzle description, printed first so
            the output is self-explanatory without the source code.

    Returns:
        The final assignment once the pipeline finishes - fully resolved
        for a well-posed puzzle, but returned as-is even if it is not, so
        callers can inspect what did and did not get resolved.
    """
    print_header(f"FULL DEDUCTION PIPELINE - {puzzle.name}")
    print()
    print(description)
    print()

    # Nothing is known at the start - the pipeline builds up everything
    # it knows purely from what the tactic and propagation resolve.
    assignment: dict = {}
    tactic_rounds: list[tuple[int, list[TacticStep]]] = []
    propagation_rounds: list[tuple[int, list[PropagationStep]]] = []

    for round_number in range(1, MAX_PIPELINE_ROUNDS + 1):
        # try_resolve_knight_status() now returns TacticStep records that
        # already capture the contradiction that ruled out the losing
        # hypothesis (see solver.py), so there is no need to snapshot the
        # assignment beforehand and reconstruct that after the fact.
        newly_resolved = try_resolve_knight_status(puzzle, assignment)
        if newly_resolved:
            tactic_rounds.append((round_number, newly_resolved))

        # Propagation runs after the tactic in the same round, so it can
        # see anything the tactic just resolved (e.g. propagating from a
        # statement whose speaker's status was only just determined).
        # propagate_round() now also returns the flat list of
        # PropagationStep records behind those contributions, which is
        # what render_propagation_step() below actually needs.
        propagation_contributions, propagation_steps = propagate_round(puzzle, assignment)
        if propagation_steps:
            propagation_rounds.append((round_number, propagation_steps))

        if not newly_resolved and not propagation_contributions:
            # Neither technique made progress this round - a fixed
            # point. Whatever remains unknown is left to the case-split
            # fallback below.
            break
    else:
        # The for/else only runs if the loop finished without `break`,
        # i.e. the round cap was hit without ever reaching a fixed
        # point. Not expected for puzzles this size, so reported as a
        # warning rather than silently treated as normal.
        print(
            f"WARNING: hit the {MAX_PIPELINE_ROUNDS}-round safety cap without "
            "reaching a fixed point."
        )
        print()

    # Step 6: every resolved value now gets a natural-language
    # explanation using whichever technique actually resolved it - the
    # tactic's render_tactic_step() (Step 5), propagation's
    # render_propagation_step(), and case-split's render_case_split()
    # (both new this step, see SPEC_step6.md).
    print("Tactic (hypothesize-and-check on knight/knave status):")
    if tactic_rounds:
        for round_number, steps in tactic_rounds:
            print(f"  Round {round_number}:")
            for step in steps:
                print(f"    {render_tactic_step(step)}")
    else:
        # Required by SPEC_step5.md: state this explicitly (as with
        # Puzzle 2, where the tactic resolves nobody) rather than just
        # printing nothing with no explanation of why.
        print("  The tactic made no progress on this puzzle.")
    print()

    print("Backward propagation:")
    if propagation_rounds:
        for round_number, steps in propagation_rounds:
            print(f"  Round {round_number}:")
            for step in steps:
                print(f"    {render_propagation_step(step)}")
    else:
        # Required by SPEC_step4.md (and still true in Step 6, per
        # SPEC_step6.md's stated limitation): state this explicitly
        # rather than just omitting the section when propagation
        # contributes nothing.
        print("  Propagation made no additional progress on this puzzle.")
    print()

    all_keys = [
        (person, attribute) for person in puzzle.people for attribute in puzzle.attributes
    ]
    unknown_before_case_split = [key for key in all_keys if key not in assignment]

    print("Case-split fallback:")
    if not unknown_before_case_split:
        print("  Not needed - the tactic and propagation already resolved everything.")
    else:
        case_result = case_split_fallback(puzzle, assignment)
        if case_result.winning_combination is not None:
            print(f"  {render_case_split(case_result)}")
        else:
            print(
                f"  WARNING: expected exactly one consistent completion of the "
                f"{len(case_result.remaining_unknowns)} remaining unknown value(s); "
                "this puzzle may be ambiguous or broken."
            )
    print()

    print("Final solution:")
    still_unknown = [key for key in all_keys if key not in assignment]
    if still_unknown:
        names = ", ".join(f"{person.capitalize()}.{attribute}" for person, attribute in still_unknown)
        print(f"  WARNING: could not fully resolve this puzzle. Still unknown: {names}.")
    else:
        for sentence in describe_assignment(puzzle, assignment):
            print(f"  {sentence}")
    print()

    return assignment


def run_propagation_checks() -> None:
    """Run small, hand-constructed checks that exercise propagate() directly.

    Neither puzzle's real trace happens to exercise every rule
    propagate() implements (see SPEC_step4.md) - Puzzle 1 stalls on the
    both-sides-unknown Iff case, and neither puzzle ever hits the
    two-or-more-unknowns And/Or cases that must NOT produce a guess.
    These standalone checks confirm propagate() is correct in exactly
    those cases, independent of either puzzle.
    """
    print_header("PROPAGATION UNIT CHECKS")
    print()

    checks = []
    # Every PropagationStep produced by a fact-forcing check below is
    # collected here too, so this function can also demonstrate
    # render_propagation_step() on real (if hand-constructed) data - see
    # SPEC_step6.md, which asks for exactly this validation since neither
    # puzzle's real trace forces anything via propagation.
    rendered_examples: list[str] = []

    # And(Var(X), Var(Y)) required True -> both X and Y forced True.
    facts: dict = {}
    steps: list = []
    propagate(And(IsKnight("x"), IsKnight("y")), True, {}, facts, steps=steps)
    checks.append(
        (
            "And(X, Y) required True forces both X and Y to True",
            facts == {("x", "is_knight"): True, ("y", "is_knight"): True},
        )
    )
    rendered_examples.extend(render_propagation_step(step) for step in steps)

    # And(<known True>, Var(Z)) required False -> Z forced False.
    facts = {}
    steps = []
    propagate(
        And(IsKnight("k"), IsKnight("z")), False, {("k", "is_knight"): True}, facts, steps=steps
    )
    checks.append(
        (
            "And(<True>, Z) required False forces Z to False",
            facts == {("z", "is_knight"): False},
        )
    )
    rendered_examples.extend(render_propagation_step(step) for step in steps)

    # And(Var(X), Var(Y)) required False, both still unknown -> no facts.
    facts = {}
    propagate(And(IsKnight("x"), IsKnight("y")), False, {}, facts)
    checks.append(
        (
            "And(X, Y) required False with both unknown forces nothing (no guess)",
            facts == {},
        )
    )

    # Iff(Var(A), Var(B)) required True, A already known -> B forced to match.
    facts = {}
    steps = []
    propagate(
        Iff(IsKnight("a"), IsKnight("b")), True, {("a", "is_knight"): True}, facts, steps=steps
    )
    checks.append(
        (
            "Iff(A, B) required True with A known forces B to match",
            facts == {("b", "is_knight"): True},
        )
    )
    rendered_examples.extend(render_propagation_step(step) for step in steps)

    # Iff(Var(A), Var(B)) required True, both unknown -> no facts.
    facts = {}
    propagate(Iff(IsKnight("a"), IsKnight("b")), True, {}, facts)
    checks.append(
        (
            "Iff(A, B) required True with both unknown forces nothing (no guess)",
            facts == {},
        )
    )

    # Implies(Var(P), Var(Q)) required False -> P forced True, Q forced False.
    facts = {}
    steps = []
    propagate(Implies(IsKnight("p"), IsKnight("q")), False, {}, facts, steps=steps)
    checks.append(
        (
            "Implies(P, Q) required False forces P to True and Q to False",
            facts == {("p", "is_knight"): True, ("q", "is_knight"): False},
        )
    )
    rendered_examples.extend(render_propagation_step(step) for step in steps)

    all_passed = True
    for check_description, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {check_description}")
        all_passed = all_passed and passed
    print()

    if all_passed:
        print("All propagation unit checks passed.")
    else:
        print("WARNING: at least one propagation unit check failed.")
    print()

    # Step 6: render a few of the checks above into English, as the
    # required validation of render_propagation_step() against real
    # (standalone) propagation output.
    print("Natural-language rendering of the fact-forcing checks above:")
    for rendered in rendered_examples:
        print(f"  {rendered}")
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
    # fully solved.
    run_deduction_pipeline(PUZZLE_1, PUZZLE_1_DESCRIPTION)
    run_deduction_pipeline(PUZZLE_2, PUZZLE_2_DESCRIPTION)


if __name__ == "__main__":
    main()
