"""Puzzle data structure and the concrete puzzles the solver runs.

This is where all puzzle-specific knowledge lives: who the people are,
what attributes they have, what they say, and what constraints their
world must satisfy. solver.py never mentions any of this directly - it
only knows how to work with a `Puzzle` in the abstract.
"""

from dataclasses import dataclass

from expressions import (
    AtLeastN,
    And,
    Expr,
    ExactlyN,
    IsGuilty,
    IsKnave,
    IsKnight,
    Iff,
    Implies,
    Or,
)


@dataclass
class Puzzle:
    """Everything the solver needs to know about one Knights & Knaves puzzle.

    Attributes:
        name: A short human-readable label for the puzzle, used in
            printed output.
        people: The names of everyone involved, e.g. ["ada", "bo"].
        attributes: The boolean attributes each person has, e.g.
            ["is_knight", "is_guilty"]. Every person in `people` has
            every attribute in this list; there is no per-person
            variation in which attributes exist.
        statements: Maps each person's name to the Expr tree
            representing what they said. A person's statement must
            evaluate to True if they are a knight, and False if they
            are a knave.
        constraints: Expr trees that must ALL evaluate to True for an
            assignment to be considered a valid world at all, regardless
            of what anyone said.
    """

    name: str
    people: list[str]
    attributes: list[str]
    statements: dict[str, Expr]
    constraints: list[Expr]


# ---------------------------------------------------------------------------
# Puzzle 1: the Step 1 "whodunit" puzzle, re-expressed as Expr trees.
#
# This exists as a regression check: solving it with the new AST-based
# machinery must reproduce Step 1's exact numbers (16 candidates, 8 pass
# the constraint, 1 fully valid). If it doesn't, something is wrong with
# the AST or evaluator, not with the puzzle itself - Step 1 already
# proved the puzzle is well-posed.
# ---------------------------------------------------------------------------

PUZZLE_1_DESCRIPTION = """\
Two co-defendants, Ada and Bo, are on trial. Each of them is either a
knight (always tells the truth) or a knave (always lies). Each of them
is also either guilty or innocent of the crime under investigation.

Constraint: guilt is all-or-nothing between the two of them. If either
one is guilty, both of them are guilty.

Statements:
  Ada says: "I am a knave, and none of us are innocent."
  Bo says:  "Ada and I are either both guilty or both innocent."\
"""

PUZZLE_1 = Puzzle(
    name="Whodunit (regression check from Step 1)",
    people=["ada", "bo"],
    attributes=["is_knight", "is_guilty"],
    statements={
        # "I am a knave, and none of us are innocent." - a conjunction of
        # Ada being a knave and both co-defendants being guilty.
        "ada": And(IsKnave("ada"), IsGuilty("ada"), IsGuilty("bo")),
        # "Ada and I are either both guilty or both innocent." - their
        # guilt values must agree, which is exactly what Iff captures.
        "bo": Iff(IsGuilty("ada"), IsGuilty("bo")),
    },
    constraints=[
        # "If anyone is guilty, all co-defendants are guilty" collapses,
        # with exactly two people, to "their guilt values agree".
        Iff(IsGuilty("ada"), IsGuilty("bo")),
    ],
)


# ---------------------------------------------------------------------------
# Puzzle 2: a new, harder puzzle that Step 1's plain-function approach
# could not express cleanly. It needs a conditional (Bo's statement) and
# counting constraints (Cal's statement, and the puzzle's own
# constraint) - exactly the kind of statement the AST's Implies and
# counting nodes exist for.
# ---------------------------------------------------------------------------

PUZZLE_2_DESCRIPTION = """\
Three people, Ada, Bo, and Cal, are each either a knight (always tells
the truth) or a knave (always lies). There is no guilt axis in this
puzzle - only knight/knave status.

Constraint: at least one of them is a knave.

Statements:
  Ada says: "Cal is a knave, and Cal and Bo are the same type."
  Bo says:  "If at least two of us are knaves, then all of us are knaves."
  Cal says: "None of us are knaves, or exactly two of us are knaves."\
"""

PUZZLE_2 = Puzzle(
    name="The three-knave conditional",
    people=["ada", "bo", "cal"],
    attributes=["is_knight"],
    statements={
        # "Cal is a knave, and Cal and Bo are the same type." - a
        # conjunction of an atomic claim and a same-type (Iff) claim.
        "ada": And(IsKnave("cal"), Iff(IsKnight("cal"), IsKnight("bo"))),
        # "If at least two of us are knaves, then all of us are knaves."
        # - a direct Implies between two counting statements.
        "bo": Implies(
            AtLeastN(2, [IsKnave("ada"), IsKnave("bo"), IsKnave("cal")]),
            And(IsKnave("ada"), IsKnave("bo"), IsKnave("cal")),
        ),
        # "None of us are knaves, or exactly two of us are knaves." - a
        # disjunction of two counting statements (zero knaves, or
        # exactly two).
        "cal": Or(
            ExactlyN(0, [IsKnave("ada"), IsKnave("bo"), IsKnave("cal")]),
            ExactlyN(2, [IsKnave("ada"), IsKnave("bo"), IsKnave("cal")]),
        ),
    },
    constraints=[
        # "At least one of them is a knave."
        AtLeastN(1, [IsKnave("ada"), IsKnave("bo"), IsKnave("cal")]),
    ],
)
