"""Deduction techniques used to solve a puzzle without brute force.

solver.py's solve() only ever tries every possible assignment at once. The
three techniques in this module instead try to pin down a puzzle's people
one fact at a time, the way a human solver would:

1. The tactic (try_resolve_knight_status): hypothesize-and-check on a
   single person's own knight/knave status.
2. Backward propagation (propagate / propagate_round): given a truth
   value that is already required, work backward into an expression's
   sub-parts to see what that requirement forces.
3. The case-split fallback (case_split_fallback): once the two techniques
   above stop making progress, brute-force only whatever (person,
   attribute) values remain unknown, not the whole puzzle.

main.py's run_deduction_pipeline() drives all three together, round by
round, and difficulty.py's classify_difficulty() looks at which of them
actually had to contribute to reach a full solution.
"""

from dataclasses import dataclass
from itertools import product

from expressions import (
    And,
    AtLeastN,
    AtMostN,
    Expr,
    ExactlyN,
    Iff,
    Implies,
    IsGuilty,
    IsInnocent,
    IsKnave,
    IsKnight,
    Not,
    Or,
    evaluate,
    evaluate_partial,
)
from puzzles import Puzzle


# ---------------------------------------------------------------------------
# Deduction tactic: hypothesize-and-check on knight/knave status.
#
# This is a first, narrow deduction technique built on top of
# evaluate_partial(). It does not brute-force the whole puzzle; it only
# ever considers one person's is_knight value at a time, and only resolves
# that person if one of the two possibilities (knight or knave) can be
# ruled out by a contradiction. It deliberately does not reason about
# guilt, and it deliberately does not chain hypotheses about multiple
# people together - see SPEC_step3.md for what this tactic is and is not
# meant to do.
# ---------------------------------------------------------------------------


@dataclass
class TacticStep:
    """A structured record of one person the tactic resolved.

    Step 3-4's tactic only ever reported *who* it resolved (as a bare
    name), leaving any explanation to be reconstructed after the fact by
    re-running the losing hypothesis. This record instead captures
    everything a natural-language renderer needs at the moment the
    contradiction is actually found, so nothing has to be redone or
    guessed at later.

    Attributes:
        person: The name of the person this step resolved.
        statement: The Expr tree for this person's own statement, kept
            here so a renderer can describe *what* was said without
            needing separate access to the puzzle.
        resolved_value: The is_knight value the tactic settled on (True
            for knight, False for knave).
        surviving_hypothesis: The hypothesis that survived - always equal
            to resolved_value, since that is exactly why it was chosen.
        contradicting_hypothesis: The hypothesis that was ruled out (the
            opposite of resolved_value). This is only None for a
            TacticStep that was never actually produced by a
            contradiction, which does not currently happen - the tactic
            only ever builds one of these records when it finds exactly
            one surviving hypothesis, meaning the other one was always
            contradicted.
        contradiction_result: The definite truth value the statement
            evaluated to under contradicting_hypothesis - e.g. False,
            when a hypothesized knight's statement turned out to require
            being false.
    """

    person: str
    statement: Expr
    resolved_value: bool
    surviving_hypothesis: bool
    contradicting_hypothesis: bool | None
    contradiction_result: bool | None


def try_resolve_knight_status(puzzle: Puzzle, assignment: dict) -> list[TacticStep]:
    """Run one pass of hypothesize-and-check deduction over every unresolved person.

    For each person whose is_knight value is not yet in `assignment`, this
    tries both possibilities (knight, then knave) and evaluates that
    person's own statement under each hypothesis using evaluate_partial(),
    with everything else held at its currently known value. A hypothesis
    is contradicted (and therefore ruled out) only when it produces a
    definite mismatch: a knight's statement evaluating to a definite
    False, or a knave's statement evaluating to a definite True. An
    Unknown result never rules a hypothesis out, since "we can't tell yet"
    is not a contradiction.

    If exactly one of the two hypotheses survives, that is the only
    logically possible value left, so it is written into `assignment`,
    and a TacticStep is built recording both the resolved value and the
    contradiction that ruled out the other hypothesis (captured right
    here, while the evaluation that found it is still at hand, rather
    than reconstructed later). If both survive (not enough is known yet
    to decide) or - which should never happen for a well-posed puzzle -
    neither survives, the person is left unresolved for this pass.

    Note that `assignment` is mutated in place: a person resolved earlier
    in this same pass is visible (as a known value, not a hypothesis) to
    people processed later in the same pass, in whatever order
    `puzzle.people` lists them.

    Args:
        puzzle: The puzzle whose people and statements to reason about.
        assignment: The current partial (person, attribute) -> bool
            mapping. Updated in place with any newly resolved is_knight
            values.

    Returns:
        A list of TacticStep records, one per person newly resolved
        during this pass, in `puzzle.people` order. Empty if this pass
        resolved nobody, which is the signal callers use to detect that a
        fixed point has been reached.
    """
    newly_resolved: list[TacticStep] = []

    for person in puzzle.people:
        if (person, "is_knight") in assignment:
            continue  # Already known - nothing to hypothesize here.

        statement = puzzle.statements[person]
        surviving_hypotheses = []
        # Keep every hypothesis's evaluated result, not just whether it
        # survived, since the losing one's actual result is exactly what
        # a natural-language explanation needs to show as "the
        # contradiction" once resolution succeeds.
        results_by_hypothesis: dict[bool, bool | None] = {}

        for hypothesis in (True, False):
            # A trial assignment is a throwaway copy: it plugs in one
            # guess for this person only, without disturbing the shared
            # `assignment` that the rest of this pass (and future passes)
            # rely on.
            trial_assignment = dict(assignment)
            trial_assignment[(person, "is_knight")] = hypothesis
            statement_result = evaluate_partial(statement, trial_assignment)
            results_by_hypothesis[hypothesis] = statement_result

            # A hypothesis survives unless it is definitely contradicted:
            # a knight (hypothesis=True) whose statement is definitely
            # False, or a knave (hypothesis=False) whose statement is
            # definitely True. Either a matching definite result or a
            # still-Unknown result keeps the hypothesis alive.
            if statement_result is None or statement_result == hypothesis:
                surviving_hypotheses.append(hypothesis)

        if len(surviving_hypotheses) == 1:
            resolved_value = surviving_hypotheses[0]
            contradicting_hypothesis = not resolved_value
            assignment[(person, "is_knight")] = resolved_value
            newly_resolved.append(
                TacticStep(
                    person=person,
                    statement=statement,
                    resolved_value=resolved_value,
                    surviving_hypothesis=resolved_value,
                    contradicting_hypothesis=contradicting_hypothesis,
                    contradiction_result=results_by_hypothesis[contradicting_hypothesis],
                )
            )

    return newly_resolved


# ---------------------------------------------------------------------------
# Backward propagation: given that some expression is *required* to have a
# particular truth value, work backward into its sub-expressions and record
# any (person, attribute) fact that is the only way left to make that
# requirement hold, given what is already known.
#
# This is a second, independent deduction technique from the tactic above.
# The tactic hypothesizes a whole person's is_knight value and checks their
# own statement for a contradiction; propagation instead starts from a
# truth value that is *already* pinned down (a constraint, or a resolved
# person's statement) and asks what that forces about the pieces inside it.
# The two techniques are complementary and are run together, round by
# round, in propagate_round() below and in main.py's pipeline driver.
# ---------------------------------------------------------------------------


@dataclass
class PropagationStep:
    """A structured record of one (person, attribute) fact that propagate()
    forced, kept around so a natural-language renderer can explain it
    later without re-walking the expression tree.

    Attributes:
        person: The person the forced fact is about.
        attribute: The attribute forced ("is_knight" or "is_guilty").
        resolved_value: The boolean value that attribute was forced to.
        source_expr_description: A plain-language description of the
            local connective that did the forcing (e.g. "a conjunction
            that must be false, and every one of its other parts is
            already known to be true") - not the top-level statement or
            constraint's name, but the specific piece of reasoning that
            pinned this fact down. See _PropagationReason below.
        required_value: The truth value that connective itself was
            required to equal.
    """

    person: str
    attribute: str
    resolved_value: bool
    source_expr_description: str
    required_value: bool


@dataclass
class _PropagationReason:
    """The local justification propagate() is currently recursing under.

    Every connective case in propagate() that identifies a specific
    child as "the only way left to satisfy this requirement" builds one
    of these to describe *why*, and passes it down to the recursive call
    that eventually reaches the atomic node the fact is actually recorded
    against. This is deliberately not threaded from the very top of the
    expression tree (e.g. prefixed with "Ada's statement") - the
    surrounding statement/constraint identity is already reported
    separately by propagate_round()'s per-source labels, so the reason
    recorded here only needs to describe the immediate connective.

    Attributes:
        description: Plain-language description of the connective.
        required: The truth value that connective was required to equal.
    """

    description: str
    required: bool


def propagate(
    expr: Expr,
    required: bool,
    assignment: dict,
    facts: dict,
    steps: list | None = None,
    reason: _PropagationReason | None = None,
) -> None:
    """Derive forced (person, attribute) facts from a required truth value.

    Given that `expr` is required to evaluate to `required`, this walks
    the expression tree and records into `facts` any (person, attribute)
    value that is the *only* way left to satisfy that requirement, given
    everything already known in `assignment` and in `facts` itself (facts
    recorded earlier in this same walk are visible to later parts of it,
    since `facts` is mutated in place as the recursion proceeds).

    This is deliberately conservative: whenever a connective's required
    value could still be satisfied in more than one way given what is
    currently known (e.g. an And required False with two or more operands
    still unknown - any one of them could be the reason), nothing is
    recorded for that node. Recording a fact here is a claim that it is
    logically forced, not merely likely, so genuinely ambiguous cases are
    left alone rather than guessed at - see SPEC_step4.md for why this
    matters for the And/Or/Implies/Iff cases specifically.

    Args:
        expr: The root of the (sub-)expression currently required to
            equal `required`.
        required: The truth value `expr` must have.
        assignment: The current known (person, attribute) -> bool values.
            Read-only from this function's point of view - only `facts`
            is mutated.
        facts: Newly forced (person, attribute) -> bool values discovered
            so far in this walk. Mutated in place; also consulted
            (merged with `assignment`) to decide what already counts as
            "known" when deciding whether something new can be forced.
        steps: If given, every newly forced fact also gets a
            PropagationStep appended here, carrying the local reasoning
            that forced it (see `reason` below). Callers that only need
            the raw facts (e.g. earlier steps of this project) can leave
            this as None and get exactly the old behavior.
        reason: The local justification currently in force - which
            connective, and what it was required to equal. None only at
            the very first call for a given top-level expression, in
            which case a generic placeholder reason is used; every
            recursive call below either passes the incoming reason
            through unchanged (Not, which doesn't add new reasoning) or
            replaces it with a new one describing whichever connective is
            doing the forcing at that point.

    Returns:
        None. All output happens by mutating `facts` (and, if given,
        `steps`) in place.

    Raises:
        TypeError: If `expr` is not one of the known node types.
    """
    # Every "is this already known?" check below needs to see both the
    # values fixed before this walk started (assignment) and anything
    # this same walk has already forced (facts) - a fact forced by an
    # earlier sibling can unblock forcing a later one.
    known = {**assignment, **facts}

    # Only the outermost call for a given top-level expression arrives
    # with reason=None; every recursive call below supplies one
    # explicitly, so this default only ever applies once per walk.
    if reason is None:
        reason = _PropagationReason("this requirement", required)

    match expr:
        # Atomic nodes: each one reduces to a single (person, attribute)
        # fact, once the node's own polarity (Knave/Innocent negate,
        # Knight/Guilty don't) is folded into the required value.
        case IsKnight(person):
            _record_if_new((person, "is_knight"), required, known, facts, steps, reason)
        case IsKnave(person):
            _record_if_new((person, "is_knight"), not required, known, facts, steps, reason)
        case IsGuilty(person):
            _record_if_new((person, "is_guilty"), required, known, facts, steps, reason)
        case IsInnocent(person):
            _record_if_new((person, "is_guilty"), not required, known, facts, steps, reason)

        case Not(inner):
            # A Not doesn't itself add any new reasoning - the same
            # reason that applied to this Not still applies to `inner`,
            # just with the required value flipped.
            propagate(inner, not required, assignment, facts, steps, reason)

        case And(exprs):
            if required:
                # Every operand of a true And must itself be true - there
                # is no ambiguity here, so every operand can be pushed at
                # once.
                push_reason = _PropagationReason("a conjunction that must be true", True)
                for sub in exprs:
                    propagate(sub, True, assignment, facts, steps, push_reason)
            else:
                # A false And only pins down a specific operand when
                # exactly one operand is still unknown and every other
                # operand is already known True - only then is that one
                # operand unambiguously "the reason" the And is false.
                # With two or more unknowns, any combination of them
                # could be responsible, so nothing can be said yet.
                values = [evaluate_partial(sub, known) for sub in exprs]
                unknown_positions = [i for i, v in enumerate(values) if v is None]
                if len(unknown_positions) == 1:
                    only_unknown = unknown_positions[0]
                    rest_are_true = all(
                        v is True for i, v in enumerate(values) if i != only_unknown
                    )
                    if rest_are_true:
                        elim_reason = _PropagationReason(
                            "a conjunction that must be false, and every one of its "
                            "other parts is already known to be true",
                            False,
                        )
                        propagate(
                            exprs[only_unknown], False, assignment, facts, steps, elim_reason
                        )

        case Or(exprs):
            if not required:
                # Every operand of a false Or must itself be false - the
                # mirror image of And required True above.
                push_reason = _PropagationReason("a disjunction that must be false", False)
                for sub in exprs:
                    propagate(sub, False, assignment, facts, steps, push_reason)
            else:
                # Mirror of And required False: a true Or only pins down
                # a specific operand when exactly one operand is unknown
                # and every other operand is already known False.
                values = [evaluate_partial(sub, known) for sub in exprs]
                unknown_positions = [i for i, v in enumerate(values) if v is None]
                if len(unknown_positions) == 1:
                    only_unknown = unknown_positions[0]
                    rest_are_false = all(
                        v is False for i, v in enumerate(values) if i != only_unknown
                    )
                    if rest_are_false:
                        elim_reason = _PropagationReason(
                            "a disjunction that must be true, and every one of its "
                            "other parts is already known to be false",
                            True,
                        )
                        propagate(
                            exprs[only_unknown], True, assignment, facts, steps, elim_reason
                        )

        case Implies(antecedent, consequent):
            if not required:
                # The only way "antecedent -> consequent" can be false is
                # a true antecedent together with a false consequent -
                # both sides are pinned down unambiguously at once.
                false_reason = _PropagationReason("an implication that must be false", False)
                propagate(antecedent, True, assignment, facts, steps, false_reason)
                propagate(consequent, False, assignment, facts, steps, false_reason)
            else:
                # A true Implies is satisfied by a false antecedent OR a
                # true consequent - two different ways, so only the side
                # that is *not* already known lets the other side be
                # forced. The two checks are independent rather than
                # either/or: for a well-posed puzzle they should not both
                # fire in a way that conflicts, but each is sound on its
                # own regardless of what the other finds.
                antecedent_value = evaluate_partial(antecedent, known)
                consequent_value = evaluate_partial(consequent, known)
                if antecedent_value is True:
                    via_antecedent = _PropagationReason(
                        "an implication that must be true, and its condition is "
                        "already known to be true",
                        True,
                    )
                    propagate(consequent, True, assignment, facts, steps, via_antecedent)
                if consequent_value is False:
                    via_consequent = _PropagationReason(
                        "an implication that must be true, and its result is "
                        "already known to be false",
                        True,
                    )
                    propagate(antecedent, False, assignment, facts, steps, via_consequent)

        case Iff(left, right):
            # An Iff only forces its *other* side once one side's current
            # value is already known - if both sides are still unknown,
            # "they must agree (or disagree)" does not by itself say what
            # either one actually is. This is the exact case that stalls
            # propagation on Puzzle 1's constraint (see SPEC_step4.md).
            left_value = evaluate_partial(left, known)
            right_value = evaluate_partial(right, known)
            iff_reason = _PropagationReason(
                f"a biconditional that must be {'true' if required else 'false'}, "
                "and its other side is already known",
                required,
            )
            if left_value is not None:
                forced_right = left_value if required else not left_value
                propagate(right, forced_right, assignment, facts, steps, iff_reason)
            elif right_value is not None:
                forced_left = right_value if required else not right_value
                propagate(left, forced_left, assignment, facts, steps, iff_reason)

        case ExactlyN() | AtLeastN() | AtMostN():
            # Deliberately out of scope for this step (see SPEC_step4.md):
            # neither puzzle needs propagation into a counting node's own
            # operands, and the case-split fallback below covers whatever
            # this leaves unresolved. Doing nothing here is correct, not
            # a placeholder for a missing case. Step 4's two hand-written
            # puzzles never actually reached this branch mid-traversal -
            # Step 10's richer generated grammar can, since a counting
            # node can now be nested inside a resolved person's statement
            # (e.g. under an Implies). An explicit check in
            # run_propagation_checks() (see rendering.py) confirms this
            # stays a safe no-op rather than a crash (see SPEC_step10.md).
            pass

        case _:
            raise TypeError(f"Unknown expression node: {expr!r}")


def _record_if_new(
    key: tuple[str, str],
    value: bool,
    known: dict,
    facts: dict,
    steps: list | None,
    reason: _PropagationReason,
) -> None:
    """Record `key -> value` into `facts`, unless `key` is already known.

    Shared by every atomic-node case in propagate(), since IsKnight,
    IsKnave, IsGuilty, and IsInnocent all reduce to the same operation
    once translated into their underlying (person, attribute) key and
    value: record it only if it is genuinely new information.

    Args:
        key: The (person, attribute) pair the atomic node refers to.
        value: The value propagate() has determined is forced.
        known: The already-known values (assignment merged with facts
            recorded earlier in the same walk), consulted only to check
            whether `key` is new.
        facts: The dict that newly forced facts are recorded into.
        steps: If given, a PropagationStep describing this fact is
            appended here alongside recording it into `facts`.
        reason: The local justification (which connective, and what it
            required) that forced this particular fact.
    """
    if key not in known:
        facts[key] = value
        if steps is not None:
            person, attribute = key
            steps.append(
                PropagationStep(
                    person=person,
                    attribute=attribute,
                    resolved_value=value,
                    source_expr_description=reason.description,
                    required_value=reason.required,
                )
            )


def propagate_round(
    puzzle: Puzzle, assignment: dict
) -> tuple[list[tuple[str, dict]], list[PropagationStep]]:
    """Run one pass of backward propagation over a puzzle's constraints and
    already-resolved statements, merging any newly forced facts into
    `assignment`.

    Every constraint is always required to be True - that is what makes
    it a constraint. A person's statement is only propagated from once
    that person's own is_knight value is already known, using that value
    as the statement's required truth (a known knight's statement is
    required True; a known knave's is required False); propagating from
    a statement whose speaker's status is still unknown would not be
    sound, since "required" would itself be a guess rather than a fact.

    Args:
        puzzle: The puzzle whose constraints and statements to propagate
            from.
        assignment: The current partial (person, attribute) -> bool
            mapping. Updated in place with any newly forced facts.

    Returns:
        A (contributions, steps) pair:
          - contributions: a list of (source_description, facts) pairs,
            one per constraint or statement that forced at least one new
            fact this round, in the order they were processed. Empty if
            this round forced nothing at all - the signal callers use to
            detect a fixed point.
          - steps: a flat list of PropagationStep records, one per newly
            forced fact across every source this round, for a
            natural-language renderer to work from directly.
    """
    sources: list[tuple[str, Expr, bool]] = []

    for index, constraint in enumerate(puzzle.constraints, start=1):
        label = (
            "the puzzle's constraint"
            if len(puzzle.constraints) == 1
            else f"constraint {index}"
        )
        sources.append((label, constraint, True))

    for person in puzzle.people:
        if (person, "is_knight") in assignment:
            required = assignment[(person, "is_knight")]
            sources.append(
                (f"{person.capitalize()}'s statement", puzzle.statements[person], required)
            )

    contributions = []
    all_steps: list[PropagationStep] = []
    for description, expr, required in sources:
        # A fresh dict per source keeps the reported contributions
        # attributable to whichever constraint or statement produced
        # them. `assignment` is updated immediately after each source
        # runs, so later sources in this same round still see everything
        # forced so far.
        new_facts: dict = {}
        new_steps: list[PropagationStep] = []
        propagate(expr, required, assignment, new_facts, steps=new_steps)
        if new_facts:
            assignment.update(new_facts)
            contributions.append((description, new_facts))
            all_steps.extend(new_steps)

    return contributions, all_steps


# ---------------------------------------------------------------------------
# Case-split fallback: once the tactic and propagation both stop making
# progress, brute-force only whatever (person, attribute) values are still
# unknown - not the whole puzzle - and check full consistency on each
# possible completion.
# ---------------------------------------------------------------------------


@dataclass
class RejectedCombination:
    """A record of one case-split candidate that was tried and rejected.

    case_split_fallback() checks every remaining combination one at a
    time; this record captures the *first* one that failed, along with
    exactly which check it failed and why, so a natural-language renderer
    has a concrete counterexample to point to instead of just reporting
    "many combinations were tried".

    Attributes:
        values: The (person, attribute) -> bool values this candidate
            guessed for the still-unknown keys (not the full assignment -
            just the part that was actually being branched on).
        failed_check: A plain description of which statement or
            constraint this candidate violated, e.g. "Bo's statement" or
            "the puzzle's constraint" - the same phrasing style already
            used by propagate_round()'s source labels.
        expected_value: What that check required: True for a constraint
            (constraints must always hold), or the candidate's own
            hypothesized is_knight value for a statement check (a knight's
            statement must be true, a knave's must be false).
        actual_value: What the check actually evaluated to under this
            candidate - by definition different from expected_value,
            since that mismatch is exactly why the candidate was rejected.
    """

    values: dict
    failed_check: str
    expected_value: bool
    actual_value: bool


@dataclass
class CaseSplitResult:
    """Everything a natural-language renderer needs to explain one
    case-split fallback run.

    Attributes:
        remaining_unknowns: The (person, attribute) pairs that were still
            unknown going into the case split.
        total_combinations: How many True/False combinations of
            remaining_unknowns were checked (2 ** len(remaining_unknowns)).
        winning_combination: The single fully-specified assignment that
            passed every check, if exactly one did. None if the case
            split was ambiguous (more than one survivor) or unsatisfiable
            (none did) - a well-posed puzzle should never leave this None.
        example_rejected: The first rejected combination encountered, for
            use as an illustrative counterexample. None only if every
            combination happened to be consistent (no rejections to show).
        statement_truth_by_person: For each person, whether their
            statement evaluates to True or False under winning_combination.
            This is extra information beyond what SPEC_step6.md's
            illustrative dataclass listed, but render_case_split() needs
            it to state the per-person consistency check (element 3 of
            the spec) without re-evaluating every statement itself - the
            solver already has the puzzle's statements at hand when this
            result is built, so it is cheaper to compute it once here.
            Empty if winning_combination is None.
    """

    remaining_unknowns: list
    total_combinations: int
    winning_combination: dict | None
    example_rejected: RejectedCombination | None
    statement_truth_by_person: dict


def _check_candidate(
    puzzle: Puzzle, candidate: dict, unknown_keys: list, guessed: dict
) -> RejectedCombination | None:
    """Check one fully-specified candidate assignment, one check at a time.

    Unlike constraints_hold() and statements_consistent() (see solver.py),
    which only report pass/fail for the whole batch of constraints or
    statements at once, this stops at the *first* check that fails and
    reports exactly which one it was and why - the detail a case-split
    explanation needs to point to a concrete counterexample
    (SPEC_step6.md's RejectedCombination).

    Args:
        puzzle: The puzzle whose constraints and statements to check.
        candidate: One fully-specified (person, attribute) -> bool
            assignment.
        unknown_keys: The (person, attribute) pairs that were actually
            branched on to produce this candidate - used to fill in
            RejectedCombination.values with just the guessed part of the
            candidate, not the whole assignment.
        guessed: The values `candidate` assigned to `unknown_keys` this
            time around, already extracted by the caller.

    Returns:
        A RejectedCombination describing the first failing check, or None
        if `candidate` passes every constraint and every statement check.
    """
    for index, constraint in enumerate(puzzle.constraints, start=1):
        label = (
            "the puzzle's constraint"
            if len(puzzle.constraints) == 1
            else f"constraint {index}"
        )
        actual = evaluate(constraint, candidate)
        if not actual:
            # Constraints must always hold, so the expected value here is
            # always True.
            return RejectedCombination(
                values=guessed, failed_check=label, expected_value=True, actual_value=actual
            )

    for person, statement in puzzle.statements.items():
        actual = evaluate(statement, candidate)
        expected = candidate[(person, "is_knight")]
        if actual != expected:
            return RejectedCombination(
                values=guessed,
                failed_check=f"{person.capitalize()}'s statement",
                expected_value=expected,
                actual_value=actual,
            )

    return None


def case_split_fallback(puzzle: Puzzle, assignment: dict) -> CaseSplitResult:
    """Brute-force only the values left unknown once the tactic and
    propagation have both reached a fixed point.

    This mirrors solver.py's solve() whole-puzzle brute force, but scoped
    down to just the remaining unknowns: every value already resolved by
    the tactic or propagation is kept fixed rather than re-guessed. Each
    candidate completion is checked one constraint/statement at a time
    (via _check_candidate()) rather than in one batch, so the *first*
    rejected candidate encountered can be captured with a concrete reason
    - useful for a natural-language explanation, not just a pass/fail
    count. If exactly one combination of the remaining unknowns is fully
    consistent, that combination is merged into `assignment` in place.

    Args:
        puzzle: The puzzle being solved.
        assignment: The current (person, attribute) -> bool mapping,
            possibly partial. Mutated in place with the unique consistent
            completion, if exactly one is found.

    Returns:
        A CaseSplitResult summarizing what happened. winning_combination
        is set only when exactly one candidate was fully consistent -
        zero or more than one leaves it None, the same "don't silently
        pick one" treatment Step 1 gave an ambiguous or broken puzzle.
    """
    all_keys = [
        (person, attribute) for person in puzzle.people for attribute in puzzle.attributes
    ]
    unknown_keys = [key for key in all_keys if key not in assignment]

    consistent_completions = []
    example_rejected = None
    for values in product([True, False], repeat=len(unknown_keys)):
        guessed = dict(zip(unknown_keys, values))
        candidate = dict(assignment)
        candidate.update(guessed)

        rejection = _check_candidate(puzzle, candidate, unknown_keys, guessed)
        if rejection is None:
            consistent_completions.append(candidate)
        elif example_rejected is None:
            # Only the first rejection is kept - SPEC_step6.md only asks
            # for one illustrative counterexample, not an exhaustive log
            # of every failed combination.
            example_rejected = rejection

    winning_combination = None
    statement_truth_by_person: dict = {}
    if len(consistent_completions) == 1:
        winning_combination = consistent_completions[0]
        assignment.update(winning_combination)
        statement_truth_by_person = {
            person: evaluate(statement, winning_combination)
            for person, statement in puzzle.statements.items()
        }

    return CaseSplitResult(
        remaining_unknowns=unknown_keys,
        total_combinations=2 ** len(unknown_keys),
        winning_combination=winning_combination,
        example_rejected=example_rejected,
        statement_truth_by_person=statement_truth_by_person,
    )
