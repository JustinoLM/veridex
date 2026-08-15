"""Random Knights & Knaves puzzle generation.

Steps 1-6 only ever solved puzzles that were written by hand in
puzzles.py. This module generates new ones instead: it builds random
statements out of the same Expr tree nodes those hand-written puzzles
use, assembles them into a Puzzle, and checks (using the existing
brute-force solver from Step 2) that the result actually has exactly
one valid solution before handing it back. A randomly generated puzzle
is not guaranteed to be well-posed on the first try - most are not - so
generate_puzzle() below keeps retrying until it finds one that is.

Deliberately narrow scope for this first generator (see SPEC_step7.md):
exactly two people, only the is_knight attribute (no guilt axis, no
global constraints), and a statement grammar limited to And/Or/Iff over
IsKnight/IsKnave leaves. Richer grammars and more people are left for a
later step.
"""

import random
from dataclasses import dataclass

from expressions import And, Expr, Iff, IsKnave, IsKnight, Or
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

# The two possible leaf node types: a direct claim about a person's
# knight/knave status.
_LEAF_TYPES = (IsKnight, IsKnave)


def random_statement(people: list[str], max_depth: int) -> Expr:
    """Generate one random statement (Expr tree) over the given people.

    This is a straightforward recursive random tree builder: at depth 0
    (or, with probability LEAF_PROBABILITY, at any depth) it stops and
    produces a leaf - a direct claim that some person is a knight or a
    knave. Otherwise it picks one of And/Or/Iff and recurses into two
    fresh sub-statements, each one depth shallower.

    The two recursive calls are independent: each one separately decides
    whether to stop early and which person to talk about, so a single
    generated statement can (and often does) mix claims about both
    people, or nest connectives inside each other's operands.

    Args:
        people: The names to draw leaf statements' subjects from.
        max_depth: How many more levels of connective nesting are still
            allowed. 0 means "leaf only, no recursion".

    Returns:
        A randomly generated Expr tree, built entirely out of
        IsKnight/IsKnave leaves and And/Or/Iff connectives.
    """
    at_leaf = max_depth <= 0 or random.random() < LEAF_PROBABILITY
    if at_leaf:
        person = random.choice(people)
        leaf_type = random.choice(_LEAF_TYPES)
        return leaf_type(person)

    connective = random.choice(_CONNECTIVES)
    left = random_statement(people, max_depth - 1)
    right = random_statement(people, max_depth - 1)
    return connective(left, right)


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
        statements = {person: random_statement(people, max_depth) for person in people}
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


def render_statement(expr: Expr, speaker: str) -> str:
    """Render a generated statement's Expr tree as an English sentence fragment.

    Hand-written puzzles (see puzzles.py) have their English descriptions
    written by hand alongside their Expr trees. A generated statement has
    no such hand-written text, so this walks the tree and produces one
    instead - using first person ("I am a knave") when a leaf is about
    the statement's own speaker, and the person's name otherwise, which
    mirrors the phrasing already used in Puzzle 1 and Puzzle 2's
    descriptions.

    Only the node types random_statement() can actually produce
    (IsKnight, IsKnave, And, Or, Iff) are handled - this is not a
    general-purpose renderer for every node type in expressions.py.

    Args:
        expr: The statement (or sub-statement) to render.
        speaker: The name of the person who made this statement, used to
            decide when to render a leaf as "I" instead of their name.

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


def _render_self_or_named(person: str, speaker: str, role: str) -> str:
    """Render a single "person is <role>" claim, using "I am" for self-claims.

    Shared by the IsKnight and IsKnave cases in render_statement(), which
    differ only in which role ("a knight" vs "a knave") they pass in.

    Args:
        person: The person the claim is about.
        speaker: The person who made the enclosing statement.
        role: "a knight" or "a knave".

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
