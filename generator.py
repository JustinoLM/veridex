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
replaced. Richer grammars and more people are still left for a later
step.
"""

import random
from dataclasses import dataclass

from expressions import And, Expr, Iff, IsGuilty, IsInnocent, IsKnave, IsKnight, Or
from puzzles import Puzzle
from solver import solve

# The two people every generated puzzle has (see SPEC_step7.md: exactly
# 2 people, reusing the same naming style as Puzzle 1/2).
GENERATED_PEOPLE = ["ada", "bo"]

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

# The two possible leaf node types for each attribute a generated leaf
# can talk about. Step 7 only ever used the is_knight row; Step 8 adds
# the is_guilty row so whodunit puzzles can generate leaves about guilt
# too (see SPEC_step8.md).
_LEAF_TYPES_BY_ATTR = {
    "is_knight": (IsKnight, IsKnave),
    "is_guilty": (IsGuilty, IsInnocent),
}


def random_statement(people: list[str], max_depth: int, allowed_attrs: list[str]) -> Expr:
    """Generate one random statement (Expr tree) over the given people.

    This is a straightforward recursive random tree builder: at depth 0
    (or, with probability LEAF_PROBABILITY, at any depth) it stops and
    produces a leaf - a direct claim about one of `allowed_attrs` for
    some person. Otherwise it picks one of And/Or/Iff and recurses into
    two fresh sub-statements, each one depth shallower.

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

    Returns:
        A randomly generated Expr tree, built entirely out of leaves
        over `allowed_attrs` and And/Or/Iff connectives.
    """
    at_leaf = max_depth <= 0 or random.random() < LEAF_PROBABILITY
    if at_leaf:
        person = random.choice(people)
        attr = random.choice(allowed_attrs)
        leaf_type = random.choice(_LEAF_TYPES_BY_ATTR[attr])
        return leaf_type(person)

    connective = random.choice(_CONNECTIVES)
    left = random_statement(people, max_depth - 1, allowed_attrs)
    right = random_statement(people, max_depth - 1, allowed_attrs)
    return connective(left, right)


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
    max_attempts: int = 100, max_depth: int = DEFAULT_MAX_DEPTH
) -> GeneratedPuzzle:
    """Generate random puzzles until one has exactly one valid solution.

    Each attempt builds a brand new random statement (via
    random_statement()) for every person, assembles them into a Puzzle
    with no constraints, and runs it through the existing generic
    brute-force solver from Step 2 to see how many assignments are fully
    valid. Most random statements do not produce a well-posed puzzle -
    per SPEC_step7.md's calibration, roughly two out of three attempts
    have zero or multiple valid assignments - so this simply discards
    those and tries again, rather than trying to construct a unique
    puzzle directly.

    Args:
        max_attempts: The most attempts to make before giving up. The
            calibrated default of 100 is a wide safety margin over the
            worst case actually observed (20 attempts across 2000
            simulated trials), not a number expected to be reached in
            practice.
        max_depth: The max_depth passed through to random_statement()
            for every person's statement.

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
    people = list(GENERATED_PEOPLE)

    for attempt in range(1, max_attempts + 1):
        statements = {
            person: random_statement(people, max_depth, allowed_attrs=["is_knight"])
            for person in people
        }
        candidate = Puzzle(
            name="Generated puzzle",
            people=people,
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
    (IsKnight, IsKnave, IsGuilty, IsInnocent, And, Or, Iff) are handled -
    this is not a general-purpose renderer for every node type in
    expressions.py.

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
        case _:
            raise TypeError(f"render_statement() cannot render node: {expr!r}")


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
        puzzle: A puzzle produced by generate_puzzle().

    Returns:
        A multi-paragraph description string, in the same shape as the
        hand-written puzzle descriptions elsewhere in this project.
    """
    names = " and ".join(person.capitalize() for person in puzzle.people)
    lines = [
        f"Two people, {names}, are each either a knight (always tells the "
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
