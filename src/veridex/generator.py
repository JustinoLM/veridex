"""Random Knights & Knaves puzzle generation.

Steps 1-6 only ever solved puzzles that were written by hand in
puzzles.py. This module generates new ones instead: it builds random
statements out of the same Expr tree nodes those hand-written puzzles
use, assembles them into a Puzzle, and checks (using the existing
brute-force solver from Step 2) that the result actually has exactly
one valid solution before handing it back. A randomly generated puzzle
is not guaranteed to be well-posed on the first try - most are not - so
generate_puzzle() and generate_whodunit_puzzle() below keep retrying
until they find one that is.

Step 7 (see SPEC_step7.md) added the first generator, deliberately
narrow: exactly two people, only the is_knight attribute (no guilt
axis, no global constraints), and a statement grammar limited to
And/Or/Iff over IsKnight/IsKnave leaves. Step 8 (see SPEC_step8.md)
extends random_statement() to also generate leaves over is_guilty, and
adds a second generation mode - "whodunit" puzzles, matching Puzzle 1's
shape - that use both attributes plus a randomly generated guilt
constraint. Step 7's is_knight-only mode is kept intact rather than
replaced. Step 9 (see SPEC_step9.md) generalizes generate_puzzle() (the
is_knight-only mode only) to any calibrated number of people instead of
a hardcoded two - random_statement() itself already worked for any
number of people, so the only real change needed was generate_puzzle()
taking `people` as a parameter instead of hardcoding it internally. The
whodunit generator stays fixed at exactly two people; see
SPEC_step9.md's "Why whodunit stays at 2 people" for the calibration
finding behind that decision. Step 10 (see SPEC_step10.md) extends
random_statement()'s grammar further, but only for the is_knight-only
path: a new `allow_rich_grammar` flag (default False, so the whodunit
generator and random_constraint() are unaffected) lets it also produce
Implies connectives and ExactlyN/AtLeastN/AtMostN counting nodes.
generate_puzzle() takes the same flag and passes it straight through,
also defaulting to False so the Step 7 and Step 9 demonstration
puzzles keep their exact pre-Step-10 behavior; only the new Step 10
demonstration puzzles pass True.
"""

import random
from dataclasses import dataclass

from .expressions import (
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
    Or,
)
from .puzzles import Puzzle
from .solver import solve

# The pool of names generated puzzles draw people from, in order. Ada
# and Bo match Puzzle 1's names; Cal onward reuses Puzzle 2's naming
# convention (see SPEC_step9.md). Sized to 5 - the highest people count
# generate_puzzle() has actually been calibrated at (see the table in
# SPEC_step9.md) - since going beyond that is explicitly out of scope.
NAME_POOL = ["ada", "bo", "cal", "dee", "eli"]

# The two people Step 7's is_knight-only demo and Step 8's whodunit
# generator both use. Step 9 keeps the whodunit generator fixed at
# exactly these two people (see SPEC_step9.md's "Why whodunit stays at
# 2 people") and keeps Step 7's original 2-person demonstration puzzles
# unchanged (regression check), so this stays a fixed 2-person slice of
# NAME_POOL rather than becoming configurable.
GENERATED_PEOPLE = NAME_POOL[:2]

# The recursion depth used unless a caller overrides it. This is the
# exact value the calibration numbers in SPEC_step7.md were measured
# against (roughly 1 in 3 random puzzles unique, ~3 attempts needed on
# average, worst case 20 over 2000 trials) - changing it would need
# re-calibrating those numbers, not just editing this constant.
DEFAULT_MAX_DEPTH = 2

# Probability of producing a leaf even when max_depth would still allow
# recursing further. Without this, every generated statement would be
# maximally deep, which would make for a much narrower (and much less
# interesting) space of generated puzzles than intended.
LEAF_PROBABILITY = 0.3

# The connectives random_statement() can introduce at an internal node.
# And and Or are variadic in expressions.py but happily accept exactly
# two positional arguments; Iff's dataclass-generated __init__ takes
# exactly two (left, right). So all three can be constructed the same
# way here: connective(left_subexpr, right_subexpr).
_CONNECTIVES = (And, Or, Iff)

# The connectives available when allow_rich_grammar is enabled: the
# original three plus Implies, whose dataclass-generated __init__ also
# takes exactly two positional arguments (antecedent, consequent), so it
# fits the same connective(left_subexpr, right_subexpr) construction
# pattern as the other three. See SPEC_step10.md.
_RICH_CONNECTIVES = (And, Or, Iff, Implies)

# Probability of producing a counting node (ExactlyN/AtLeastN/AtMostN)
# instead of a connective at a non-leaf branch point, when
# allow_rich_grammar is enabled. Kept modest (per SPEC_step10.md) so
# counting nodes appear regularly without dominating every generated
# statement.
COUNTING_NODE_PROBABILITY = 0.15

# The three counting node types _random_counting_node() picks from
# uniformly at random.
_COUNTING_NODE_TYPES = (ExactlyN, AtLeastN, AtMostN)

# The two possible leaf node types for each attribute a generated leaf
# can talk about. Step 7 only ever used the is_knight row; Step 8 adds
# the is_guilty row so whodunit puzzles can generate leaves about guilt
# too (see SPEC_step8.md).
_LEAF_TYPES_BY_ATTR = {
    "is_knight": (IsKnight, IsKnave),
    "is_guilty": (IsGuilty, IsInnocent),
}


def random_statement(
    people: list[str],
    max_depth: int,
    allowed_attrs: list[str],
    allow_rich_grammar: bool = False,
) -> Expr:
    """Generate one random statement (Expr tree) over the given people.

    This is a straightforward recursive random tree builder: at depth 0
    (or, with probability LEAF_PROBABILITY, at any depth) it stops and
    produces a leaf - a direct claim about one of `allowed_attrs` for
    some person. Otherwise it picks a connective (And/Or/Iff, plus
    Implies when allow_rich_grammar is True - see SPEC_step10.md) and
    recurses into two fresh sub-statements, each one depth shallower -
    except that, when allow_rich_grammar is True, a non-leaf branch point
    has a COUNTING_NODE_PROBABILITY chance of instead producing a
    counting node (ExactlyN/AtLeastN/AtMostN) via
    _random_counting_node(), which is terminal rather than recursive.

    The two recursive calls are independent: each one separately decides
    whether to stop early, which attribute to talk about, and which
    person to talk about, so a single generated statement can (and often
    does) mix claims about both people and, when allowed_attrs has more
    than one entry, both attributes - matching how Puzzle 1's Ada mixes
    a knight/knave claim with a guilt claim in one sentence.

    Args:
        people: The names to draw leaf statements' subjects from.
        max_depth: How many more levels of connective nesting are still
            allowed. 0 means "leaf only, no recursion".
        allowed_attrs: Which attributes ("is_knight", "is_guilty", or
            both) a leaf is allowed to make a claim about. Step 7's
            puzzles pass ["is_knight"] only, to keep that generator's
            calibrated behavior unchanged; whodunit puzzles pass both.
        allow_rich_grammar: Whether Implies connectives and counting
            nodes may be produced, on top of the original
            And/Or/Iff-over-leaves grammar. Defaults to False so
            existing callers (random_constraint(), and
            generate_whodunit_puzzle() via _WHODUNIT_ATTRS) are
            unaffected - per SPEC_step10.md, this only applies to the
            is_knight-only generator, which passes True explicitly.

    Returns:
        A randomly generated Expr tree, built out of leaves over
        `allowed_attrs`, And/Or/Iff connectives, and - when
        allow_rich_grammar is True - Implies connectives and counting
        nodes as well.
    """
    at_leaf = max_depth <= 0 or random.random() < LEAF_PROBABILITY
    if at_leaf:
        person = random.choice(people)
        attr = random.choice(allowed_attrs)
        leaf_type = random.choice(_LEAF_TYPES_BY_ATTR[attr])
        return leaf_type(person)

    if allow_rich_grammar and random.random() < COUNTING_NODE_PROBABILITY:
        return _random_counting_node(people)

    connectives = _RICH_CONNECTIVES if allow_rich_grammar else _CONNECTIVES
    connective = random.choice(connectives)
    left = random_statement(people, max_depth - 1, allowed_attrs, allow_rich_grammar)
    right = random_statement(people, max_depth - 1, allowed_attrs, allow_rich_grammar)
    return connective(left, right)


def _random_counting_node(people: list[str]) -> Expr:
    """Generate one random counting node (ExactlyN/AtLeastN/AtMostN) over IsKnave leaves.

    Mirrors how Puzzle 2's hand-written statements use counting nodes:
    wrapping a plain list of IsKnave(person) terms, not arbitrarily
    nested sub-expressions - this is a terminal production, not a
    recursive one (see SPEC_step10.md's grammar extension). The subset
    of people it talks about, which of the three counting node types is
    used, and the threshold are all chosen independently at random.

    Args:
        people: The full list of people in the puzzle. The counting
            node's subset is drawn from this list, sized between 2 and
            len(people) - "2 to N people", where N is the puzzle's total
            people count, per SPEC_step10.md.

    Returns:
        A randomly generated ExactlyN, AtLeastN, or AtMostN node,
        wrapping IsKnave terms for a random subset of `people`.
    """
    subset_size = random.randint(2, len(people))
    subset = random.sample(people, subset_size)
    exprs = [IsKnave(person) for person in subset]
    node_type = random.choice(_COUNTING_NODE_TYPES)
    n = random.randint(0, subset_size)
    return node_type(n, exprs)


def random_constraint(people: list[str], max_depth: int = DEFAULT_MAX_DEPTH) -> Expr:
    """Generate one random global constraint (Expr tree) over guilt only.

    Reuses random_statement()'s exact generation logic, but restricted
    to allowed_attrs=["is_guilty"] - per SPEC_step8.md, constraints in
    this project describe facts about guilt (like Puzzle 1's "guilt is
    all-or-nothing" constraint), never about knight/knave status.

    Args:
        people: The names to draw leaf constraints' subjects from.
        max_depth: How many more levels of connective nesting are still
            allowed, passed straight through to random_statement().

    Returns:
        A randomly generated Expr tree built entirely out of
        IsGuilty/IsInnocent leaves and And/Or/Iff connectives.
    """
    return random_statement(people, max_depth, allowed_attrs=["is_guilty"])


@dataclass
class GeneratedPuzzle:
    """A freshly generated Puzzle, together with how it was found.

    Attributes:
        puzzle: The generated Puzzle itself - verified, by the time this
            is returned, to have exactly one fully valid assignment.
        attempts: How many random candidates (including the one that
            finally succeeded) were tried before finding this one. Kept
            alongside the puzzle purely for reporting - it plays no
            further role in solving it.
    """

    puzzle: Puzzle
    attempts: int


def generate_puzzle(
    people: list[str],
    max_attempts: int = 100,
    max_depth: int = DEFAULT_MAX_DEPTH,
    allow_rich_grammar: bool = False,
) -> GeneratedPuzzle:
    """Generate random is_knight-only puzzles until one has exactly one valid solution.

    Step 7 first wrote this fixed to exactly GENERATED_PEOPLE (two
    people, hardcoded internally). Step 9 generalizes it to any
    calibrated number of people by taking `people` as a parameter
    instead (see SPEC_step9.md) - random_statement() and Puzzle
    construction already worked for any number of people without
    modification, so this signature change is the only thing that was
    actually needed to unblock larger puzzles.

    Each attempt builds a brand new random statement (via
    random_statement(), passing `allow_rich_grammar` straight through -
    see SPEC_step10.md) for every person, assembles them into a Puzzle
    with no constraints, and runs it through the existing generic
    brute-force solver from Step 2 to see how many assignments are fully
    valid. Most random statements do not produce a well-posed puzzle -
    per SPEC_step7.md's calibration, roughly two out of three attempts
    have zero or multiple valid assignments - so this simply discards
    those and tries again, rather than trying to construct a unique
    puzzle directly. SPEC_step10.md's calibration confirms the richer
    grammar (Implies and counting nodes) does not make this any worse -
    if anything, slightly better, since a vacuously-true Implies doesn't
    hurt uniqueness.

    Args:
        people: The names of the people this puzzle should have. Every
            generated statement draws its subjects from this list, and
            the resulting Puzzle's `people` field is set to it directly.
        max_attempts: The most attempts to make before giving up.
            SPEC_step9.md's calibration (1500 trials per size) found the
            acceptance rate stays roughly stable as people are added -
            26-34% for 2 to 5 people, with observed worst cases no
            higher than 23 attempts - so the original default of 100
            (calibrated against 2 people alone, worst case 20 across
            2000 trials) still gives a wide safety margin at every
            people count this has actually been calibrated at.
        max_depth: The max_depth passed through to random_statement()
            for every person's statement.
        allow_rich_grammar: Whether to build statements with the Step 10
            richer grammar (Implies and counting nodes) instead of the
            original And/Or/Iff-only grammar. Defaults to False so
            existing callers - the Step 7 two-person demo and the Step
            9 N-person demo (see SPEC_step10.md's "Definition of done":
            Step 7-9 output must remain unchanged) - keep their exact
            pre-Step-10 behavior. The Step 10 demo is the only caller
            that passes True.

    Returns:
        A GeneratedPuzzle wrapping the first well-posed puzzle found and
        the number of attempts it took.

    Raises:
        RuntimeError: If max_attempts is exhausted without finding a
            puzzle with exactly one valid solution. This should not
            happen in practice given the calibration above; if it does,
            it signals something is actually wrong rather than just bad
            luck, so this is raised rather than silently returning a
            broken puzzle or looping forever.
    """
    for attempt in range(1, max_attempts + 1):
        statements = {
            person: random_statement(
                people,
                max_depth,
                allowed_attrs=["is_knight"],
                allow_rich_grammar=allow_rich_grammar,
            )
            for person in people
        }
        candidate = Puzzle(
            name="Generated puzzle",
            people=list(people),
            attributes=["is_knight"],
            statements=statements,
            constraints=[],
        )

        result = solve(candidate)
        if len(result.fully_valid) == 1:
            return GeneratedPuzzle(puzzle=candidate, attempts=attempt)

    raise RuntimeError(
        f"Failed to generate a unique-solution puzzle within {max_attempts} attempts. "
        "This should not happen given the grammar's calibrated success rate - it "
        "likely indicates a bug in random_statement() or the solver, not bad luck."
    )


# Both attributes together - the leaf grammar a whodunit puzzle's
# per-person statements are generated over (see SPEC_step8.md: a leaf
# can be a knight/knave claim or a guilt claim, mixing both is allowed).
_WHODUNIT_ATTRS = ["is_knight", "is_guilty"]


def generate_whodunit_puzzle(
    max_attempts: int = 300, max_depth: int = DEFAULT_MAX_DEPTH
) -> GeneratedPuzzle:
    """Generate random whodunit puzzles until one has exactly one valid solution.

    Same retry-until-unique approach as generate_puzzle(), but building a
    richer puzzle each attempt: both is_knight and is_guilty attributes,
    per-person statements that can mix claims about either one (via
    random_statement() with both attributes allowed), and one randomly
    generated global constraint about guilt (via random_constraint()) -
    matching Puzzle 1's structure exactly (see SPEC_step8.md).

    With both attributes and a constraint in play there are 16 candidate
    assignments per attempt instead of Step 7's 4, so a much smaller
    fraction land on a unique solution - per SPEC_step8.md's calibration,
    about 1 in 8, needing ~8 attempts on average and 43 in the observed
    worst case.

    Args:
        max_attempts: The most attempts to make before giving up. The
            calibrated default of 300 is a wide safety margin (7x) over
            the worst case actually observed (43 attempts across 2000
            simulated trials), not a number expected to be reached in
            practice.
        max_depth: The max_depth passed through to random_statement()
            and random_constraint() alike.

    Returns:
        A GeneratedPuzzle wrapping the first well-posed whodunit puzzle
        found and the number of attempts it took.

    Raises:
        RuntimeError: If max_attempts is exhausted without finding a
            puzzle with exactly one valid solution - see
            generate_puzzle()'s docstring for why this is raised rather
            than handled silently.
    """
    people = list(GENERATED_PEOPLE)

    for attempt in range(1, max_attempts + 1):
        statements = {
            person: random_statement(people, max_depth, allowed_attrs=_WHODUNIT_ATTRS)
            for person in people
        }
        constraint = random_constraint(people, max_depth)
        candidate = Puzzle(
            name="Generated whodunit puzzle",
            people=people,
            attributes=_WHODUNIT_ATTRS,
            statements=statements,
            constraints=[constraint],
        )

        result = solve(candidate)
        if len(result.fully_valid) == 1:
            return GeneratedPuzzle(puzzle=candidate, attempts=attempt)

    raise RuntimeError(
        f"Failed to generate a unique-solution whodunit puzzle within {max_attempts} "
        "attempts. This should not happen given the grammar's calibrated success rate "
        "- it likely indicates a bug in random_statement(), random_constraint(), or "
        "the solver, not bad luck."
    )


def render_statement(expr: Expr, speaker: str | None) -> str:
    """Render a generated statement's Expr tree as an English sentence fragment.

    Hand-written puzzles (see puzzles.py) have their English descriptions
    written by hand alongside their Expr trees. A generated statement has
    no such hand-written text, so this walks the tree and produces one
    instead - using first person ("I am a knave") when a leaf is about
    the statement's own speaker, and the person's name otherwise, which
    mirrors the phrasing already used in Puzzle 1 and Puzzle 2's
    descriptions.

    Only the node types random_statement() can actually produce
    (IsKnight, IsKnave, IsGuilty, IsInnocent, And, Or, Iff, and - when
    allow_rich_grammar was used, see SPEC_step10.md - Implies and the
    counting nodes) are handled - this is not a general-purpose renderer
    for every node type in expressions.py. In particular, the counting
    node cases assume every sub-expression they wrap is an IsKnave node,
    since that is the only shape _random_counting_node() ever produces.

    Args:
        expr: The statement (or sub-statement) to render.
        speaker: The name of the person who made this statement, used to
            decide when to render a leaf as "I" instead of their name.
            Passing None (used by render_constraint() below) means no
            leaf is ever treated as self-referential, since a constraint
            is a global fact rather than something one person said.

    Returns:
        An English sentence fragment describing `expr`.

    Raises:
        TypeError: If `expr` contains a node type outside the ones
            listed above.
    """
    match expr:
        case IsKnight(person):
            return _render_self_or_named(person, speaker, "a knight")
        case IsKnave(person):
            return _render_self_or_named(person, speaker, "a knave")
        case IsGuilty(person):
            return _render_self_or_named(person, speaker, "guilty")
        case IsInnocent(person):
            return _render_self_or_named(person, speaker, "innocent")
        case And(exprs):
            return ", and ".join(render_statement(sub, speaker) for sub in exprs)
        case Or(exprs):
            return ", or ".join(render_statement(sub, speaker) for sub in exprs)
        case Iff(left, right):
            left_text = render_statement(left, speaker)
            right_text = render_statement(right, speaker)
            return f"({left_text}) if and only if ({right_text})"
        case Implies(antecedent, consequent):
            antecedent_text = render_statement(antecedent, speaker)
            consequent_text = render_statement(consequent, speaker)
            return f"if {antecedent_text}, then {consequent_text}"
        case ExactlyN(n, exprs):
            return f"exactly {_render_knave_count(n, exprs)}"
        case AtLeastN(n, exprs):
            return f"at least {_render_knave_count(n, exprs)}"
        case AtMostN(n, exprs):
            return f"at most {_render_knave_count(n, exprs)}"
        case _:
            raise TypeError(f"render_statement() cannot render node: {expr!r}")


def _render_knave_count(n: int, exprs: list[Expr]) -> str:
    """Render a counting node's "N of <people> are knaves" core phrase.

    Shared by the ExactlyN/AtLeastN/AtMostN cases in render_statement(),
    which differ only in which qualifier ("exactly", "at least", "at
    most") gets prepended to this phrase. Assumes every entry in `exprs`
    is an IsKnave node - the only shape _random_counting_node() ever
    produces (see SPEC_step10.md) - so it reads `.person` directly off
    each one rather than recursing through render_statement().

    Args:
        n: The threshold count.
        exprs: The IsKnave(person) terms the counting node wraps.

    Returns:
        A phrase like "2 of Ada, Bo, and Cal are knaves" or "1 of Ada
        and Bo is a knave".
    """
    names = _join_people([expr.person for expr in exprs])
    verb = "is a knave" if n == 1 else "are knaves"
    return f"{n} of {names} {verb}"


def render_constraint(expr: Expr) -> str:
    """Render a generated global constraint's Expr tree as an English sentence fragment.

    A constraint (see random_constraint()) is a fact about the world, not
    something any one person said, so it should never be rendered in the
    first person the way a person's own statement is. This is exactly
    render_statement() with speaker=None, which makes every leaf take the
    "named" branch in _render_self_or_named() instead of the "I" branch,
    since no real person is ever named None.

    Args:
        expr: The constraint Expr tree to render (typically the sole
            entry in a generated whodunit Puzzle's constraints list).

    Returns:
        An English sentence fragment describing `expr`.
    """
    return render_statement(expr, speaker=None)


def _render_self_or_named(person: str, speaker: str | None, role: str) -> str:
    """Render a single "person is <role>" claim, using "I am" for self-claims.

    Shared by every leaf case in render_statement(), which differ only in
    which role ("a knight", "a knave", "guilty", "innocent") they pass
    in.

    Args:
        person: The person the claim is about.
        speaker: The person who made the enclosing statement, or None if
            it is a constraint with no speaker at all (see
            render_constraint()).
        role: "a knight", "a knave", "guilty", or "innocent".

    Returns:
        "I am <role>" if person == speaker, otherwise "<Name> is <role>".
    """
    if person == speaker:
        return f"I am {role}"
    return f"{person.capitalize()} is {role}"


# English count words for describe_generated_puzzle()'s opening
# sentence ("Two people, ...", "Four people, ..."), covering every
# people count generate_puzzle() has actually been calibrated at (see
# SPEC_step9.md). Puzzle 2's hand-written description already uses this
# same word-form convention ("Three people, Ada, Bo, and Cal, ...").
# Before Step 9, this sentence hardcoded the literal word "Two" - that
# worked only because generate_puzzle() always produced exactly two
# people; generalizing it to more people (see generate_puzzle()) would
# otherwise have silently printed "Two people" on a puzzle with four.
_COUNT_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def _join_people(people: list[str]) -> str:
    """Join capitalized person names into a natural English list.

    Two names join with a plain "and" ("Ada and Bo"); three or more use
    an Oxford comma before the final "and" ("Ada, Bo, and Cal"),
    matching the convention Puzzle 2's hand-written description already
    uses. Before Step 9, describe_generated_puzzle() only ever had
    exactly two names to join, so a plain " and ".join() sufficed; that
    stops reading naturally once generate_puzzle() can produce more than
    two people (see SPEC_step9.md).

    Args:
        people: The person names to join, in order. Assumed to have at
            least two entries, since every puzzle has at least two
            people.

    Returns:
        A single English string naming everyone in `people`.
    """
    names = [person.capitalize() for person in people]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def describe_generated_puzzle(puzzle: Puzzle) -> str:
    """Build a plain-language description of a generated puzzle.

    Matches the style of the hand-written PUZZLE_1_DESCRIPTION and
    PUZZLE_2_DESCRIPTION text blocks in puzzles.py: a short setup
    paragraph followed by each person's statement in quotes. Unlike
    those, this is built programmatically from the puzzle's actual Expr
    trees via render_statement(), since a generated puzzle's statements
    are not known ahead of time. There is no constraint section, since
    generated puzzles never have any (see SPEC_step7.md).

    Args:
        puzzle: A puzzle produced by generate_puzzle(), with any number
            of people (see SPEC_step9.md).

    Returns:
        A multi-paragraph description string, in the same shape as the
        hand-written puzzle descriptions elsewhere in this project.
    """
    count_word = _COUNT_WORDS.get(len(puzzle.people), str(len(puzzle.people)))
    names = _join_people(puzzle.people)
    lines = [
        f"{count_word} people, {names}, are each either a knight (always tells the "
        "truth) or a knave (always lies). There is no guilt axis in this "
        "puzzle - only knight/knave status.",
        "",
        "Statements:",
    ]
    for person in puzzle.people:
        statement_text = render_statement(puzzle.statements[person], person)
        lines.append(f'  {person.capitalize()} says: "{statement_text}."')

    return "\n".join(lines)


def describe_generated_whodunit_puzzle(puzzle: Puzzle) -> str:
    """Build a plain-language description of a generated whodunit puzzle.

    Same purpose as describe_generated_puzzle(), but for the Step 8
    whodunit mode: both knight/knave and guilty/innocent are described
    in the setup paragraph, and - unlike Step 7's puzzles, which never
    have any - a constraint section is included, rendered with
    render_constraint() so it reads as a fact about the world rather
    than something a specific person said. Matches the shape of Puzzle
    1's hand-written description in puzzles.py.

    Args:
        puzzle: A whodunit puzzle produced by generate_whodunit_puzzle().
            Assumed to have exactly one constraint, matching how that
            function builds it.

    Returns:
        A multi-paragraph description string, in the same shape as the
        hand-written puzzle descriptions elsewhere in this project.
    """
    names = " and ".join(person.capitalize() for person in puzzle.people)
    constraint_text = render_constraint(puzzle.constraints[0])
    lines = [
        f"Two people, {names}, are each either a knight (always tells the "
        "truth) or a knave (always lies). Each of them is also either "
        "guilty or innocent of the crime under investigation.",
        "",
        f"Constraint: {constraint_text}.",
        "",
        "Statements:",
    ]
    for person in puzzle.people:
        statement_text = render_statement(puzzle.statements[person], person)
        lines.append(f'  {person.capitalize()} says: "{statement_text}."')

    return "\n".join(lines)
