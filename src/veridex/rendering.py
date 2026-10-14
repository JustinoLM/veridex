"""Turn the structured records deduction.py produces into plain English.

This module is the natural-language layer this whole project was
originally motivated by: TacticStep, PropagationStep, and CaseSplitResult
(see deduction.py) each capture *what* was resolved and *why* in
structured form; the render_*() functions here turn one of those records
into the sentences a human explanation would actually contain.
run_propagation_checks() lives here too, since it exists specifically to
validate render_propagation_step() (and propagate() itself) against small,
hand-constructed cases neither hardcoded puzzle happens to exercise - see
SPEC_step4.md and SPEC_step6.md.
"""

from .expressions import And, AtLeastN, Expr, IsKnave, IsKnight, Iff, Implies, Not, Or
from .deduction import CaseSplitResult, PropagationStep, TacticStep, propagate
from .puzzles import Puzzle


def print_header(title: str) -> None:
    """Print a banner line to visually separate sections of the output.

    Args:
        title: The text to display inside the banner.
    """
    print("=" * 70)
    print(title)
    print("=" * 70)


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
    deduction.py), state what it was required to equal, and state the one
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


def _describe_unknown(key: tuple[str, str]) -> str:
    """Turn one (person, attribute) key into a plain-language "whether ..." phrase.

    The mirror image of _describe_fact(): that function names a value
    once it's known ("Bo is a knight"), this one names a value while it's
    still unknown ("whether Bo is a knight"). Used by render_case_split()
    to list what case-split still had to figure out.

    Args:
        key: A (person, attribute) pair, e.g. ("bo", "is_knight").

    Returns:
        A short "whether ..." phrase naming the still-unknown value.
    """
    person, attribute = key
    name = person.capitalize()
    if attribute == "is_knight":
        return f"whether {name} is a knight"
    if attribute == "is_guilty":
        return f"whether {name} is guilty"
    return f"whether {name}'s {attribute} is true"


def _join_naturally(items: list[str]) -> str:
    """Join phrases the way an ordinary sentence would, not with a bare separator.

    Produces "A", "A and B", or "A, B, and C" - comma-and-"and" list
    phrasing - instead of the "; "/", "-joined internals-log style
    render_case_split() used before Step 14's wording pass. Used for
    every list of phrases in that function's explanation.

    Args:
        items: The phrases to join, already in the order they should
            read (no reordering happens here).

    Returns:
        The phrases joined into one natural-language list. Empty string
        if `items` is empty.
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def render_case_split(result: CaseSplitResult) -> list[str]:
    """Turn one CaseSplitResult into a short sequence of natural-language lines.

    This is the harder writing problem flagged in SPEC_step5.md: unlike
    the tactic and propagation, case-split isn't a clever inference, it's
    exhaustive checking - and the explanation says so plainly rather than
    dressing it up. Per SPEC_step6.md, the explanation always covers, in
    order: (1) an honest statement of how many values were unknown and
    that every combination was checked, (2) the winning combination in
    plain language, (3) a per-person confirmation that each statement's
    truth value matches its speaker's resolved type, and (4) one concrete
    rejected combination as a counterexample.

    Step 14 rewrote the phrasing of all four elements to read like
    something written for a player, not an internals log (e.g. "3
    value(s) were still unknown (Bo.is_knight)" became "1 thing was
    still unknown: whether Bo is a knight"). The four elements, the
    CaseSplitResult fields each line is built from, and the underlying
    case-split logic are unchanged - this is a phrasing pass only.

    This returns one line per element (with the per-person consistency
    checks broken out further, one line each) rather than a single dense
    paragraph, purely so the caller can print it as a short, readable
    list instead of a wall of text - a cosmetic choice, not a change to
    what's being said. Lines meant to be printed as sub-points (the
    per-person consistency checks) already carry their own extra leading
    indentation, so the caller only needs to apply one consistent base
    indent to every line returned here.

    Args:
        result: A CaseSplitResult as produced by case_split_fallback().
            Assumed to have a winning_combination (not None), since this
            is only ever called once case-split has actually resolved a
            puzzle - an ambiguous or unsatisfiable result is reported as
            a warning elsewhere instead of rendered here.

    Returns:
        A list of short natural-language lines, meant to be printed in
        order, one per line.
    """
    lines = []

    # Element 1: honest framing. Exhaustive checking is the whole point
    # here, so the line says exactly that instead of implying insight -
    # phrased as a sentence naming each still-unknown value by what it
    # actually means, rather than a "(Bo.is_knight)" key dump.
    unknown_count = len(result.remaining_unknowns)
    unknown_phrases = [_describe_unknown(key) for key in result.remaining_unknowns]
    lines.append(
        f"{unknown_count} thing{'' if unknown_count == 1 else 's'} "
        f"{'was' if unknown_count == 1 else 'were'} still unknown: "
        f"{_join_naturally(unknown_phrases)}. Rather than being able to deduce the "
        f"answer directly, all {result.total_combinations} possible combinations "
        "were tried until the one that fit was found."
    )

    # Element 2: the winning combination, in the same "knight/knave,
    # guilty/innocent" phrasing used everywhere else in this project.
    winning_facts = [
        _describe_fact(key, result.winning_combination[key]) for key in result.remaining_unknowns
    ]
    lines.append(f"The combination that fit: {_join_naturally(winning_facts)}.")

    # Element 3: per-person consistency - each statement's truth value
    # matches its speaker's resolved type, confirmed using the truth
    # values already computed when the winning combination was found.
    # Printed as its own heading line plus one indented sub-point per
    # person, instead of one run-on clause, so each person's check is
    # easy to scan independently.
    if result.statement_truth_by_person:
        lines.append("That combination holds up against everyone's statement:")
        for person, statement_truth in result.statement_truth_by_person.items():
            is_knight = result.winning_combination[(person, "is_knight")]
            role = "knight" if is_knight else "knave"
            truth_word = "true" if statement_truth else "false"
            name = person.capitalize()
            lines.append(
                f"    {name}'s statement turns out to be {truth_word} — which fits, "
                f"since {name} is a {role}."
            )

    # Element 4: one concrete counterexample, naming the specific
    # combination tried and exactly which check it violated.
    rejected = result.example_rejected
    if rejected is not None:
        rejected_facts = [_describe_fact(key, value) for key, value in rejected.values.items()]
        expected_word = "true" if rejected.expected_value else "false"
        actual_word = "true" if rejected.actual_value else "false"
        lines.append(
            f"Not every combination works, though - for example, the one where "
            f"{_join_naturally(rejected_facts)} was ruled out: it needed "
            f"{rejected.failed_check} to come out {expected_word}, but that actually "
            f"came out {actual_word}."
        )

    return lines


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

    # Step 10 robustness check (see SPEC_step10.md): Implies with a
    # counting-node antecedent, required True, with a known-False
    # consequent. propagate() can only satisfy that by forcing the
    # antecedent False - which means calling propagate() directly on the
    # AtLeastN node, a node type it does not know how to propagate
    # through (see the ExactlyN/AtLeastN/AtMostN case in deduction.py).
    # This confirms that reaching one this way completes without raising
    # and without inventing any facts about the people (x, y, z) inside
    # it - only w was already known, and facts should stay empty.
    facts = {}
    steps = []
    propagate(
        Implies(AtLeastN(2, [IsKnave("x"), IsKnave("y"), IsKnave("z")]), IsKnight("w")),
        True,
        {("w", "is_knight"): False},
        facts,
        steps=steps,
    )
    checks.append(
        (
            "Implies with a counting-node antecedent, required True with a known-False "
            "consequent, completes without crashing and forces no incorrect facts about "
            "the people inside the counting node",
            facts == {},
        )
    )

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
    print()
    for rendered in rendered_examples:
        print(f"  - {rendered}")
    print()
