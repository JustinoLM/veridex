"""Expression tree (AST) for Knights & Knaves statements, and its evaluator.

Step 1 encoded each person's statement as a plain Python function that
inspected an assignment directly. That approach does not scale: every new
puzzle needs its own hand-written functions, and there is no shared
structure a generic solver can walk. This module replaces that with a
small tree of dataclass nodes (one class per kind of logical statement)
plus a single recursive `evaluate` function that walks any such tree.

Building a puzzle's statements now means composing these node classes,
e.g. `And(IsKnave("ada"), IsGuilty("ada"))`, instead of writing a bespoke
function per statement.
"""

from __future__ import annotations

from dataclasses import dataclass

# `from __future__ import annotations` makes all type annotations in this
# file lazy strings, so classes can refer to the `Expr` alias in their own
# field types even though `Expr` itself is only defined at the bottom of
# this file, after every node class it refers to.


# ---------------------------------------------------------------------------
# Atomic nodes: each one reads a single boolean attribute of a single
# person out of the assignment. These are the leaves of every expression
# tree - evaluating them never requires recursing further.
# ---------------------------------------------------------------------------


@dataclass
class IsKnight:
    """True iff `person` is a knight (i.e. their is_knight attribute is True)."""

    person: str


@dataclass
class IsKnave:
    """True iff `person` is a knave (the negation of IsKnight)."""

    person: str


@dataclass
class IsGuilty:
    """True iff `person` is guilty (i.e. their is_guilty attribute is True)."""

    person: str


@dataclass
class IsInnocent:
    """True iff `person` is innocent (the negation of IsGuilty)."""

    person: str


# ---------------------------------------------------------------------------
# Logical connectives: these combine other expressions (atomic or
# themselves connectives) into larger statements. They are the internal
# nodes of the tree.
# ---------------------------------------------------------------------------


@dataclass
class And:
    """True iff every one of `exprs` is true.

    `And` is variadic (`And(expr1, expr2, ...)`) rather than taking an
    explicit list, since conjunctions read most naturally that way when
    writing out a statement (e.g. "X, and Y, and Z"). A custom __init__
    is needed to accept a variable number of positional arguments instead
    of the single positional argument a plain dataclass field would
    require; dataclass leaves a user-defined __init__ alone rather than
    overwriting it.
    """

    exprs: tuple[Expr, ...]

    def __init__(self, *exprs: Expr) -> None:
        self.exprs = exprs


@dataclass
class Or:
    """True iff at least one of `exprs` is true. Variadic, like And."""

    exprs: tuple[Expr, ...]

    def __init__(self, *exprs: Expr) -> None:
        self.exprs = exprs


@dataclass
class Not:
    """True iff `expr` is false."""

    expr: Expr


@dataclass
class Implies:
    """Material implication: `antecedent -> consequent`.

    This is only false when the antecedent is true and the consequent is
    false. In particular, a false antecedent makes the whole expression
    true regardless of the consequent - that is the standard logical
    reading of "if...then...", not a colloquial one.
    """

    antecedent: Expr
    consequent: Expr


@dataclass
class Iff:
    """True iff `left` and `right` have the same truth value.

    Used for statements like "X and Y are the same type", since two
    people are "the same type" exactly when their IsKnight (or IsGuilty)
    values agree.
    """

    left: Expr
    right: Expr


# ---------------------------------------------------------------------------
# Counting nodes: these look at how many of a group of expressions are
# true, for statements like "exactly two of us are knaves". Unlike And/Or,
# these take their sub-expressions as an explicit list rather than
# variadically, since the count `n` is itself an argument that comes first.
# ---------------------------------------------------------------------------


@dataclass
class ExactlyN:
    """True iff exactly `n` of `exprs` are true."""

    n: int
    exprs: list[Expr]


@dataclass
class AtLeastN:
    """True iff `n` or more of `exprs` are true."""

    n: int
    exprs: list[Expr]


@dataclass
class AtMostN:
    """True iff `n` or fewer of `exprs` are true."""

    n: int
    exprs: list[Expr]


# A type alias covering every node class above, used purely for type hints.
# Defined last since it needs every class above to already exist.
Expr = (
    IsKnight
    | IsKnave
    | IsGuilty
    | IsInnocent
    | And
    | Or
    | Not
    | Implies
    | Iff
    | ExactlyN
    | AtLeastN
    | AtMostN
)


def evaluate(expr: Expr, assignment: dict) -> bool:
    """Recursively compute the truth value of an expression tree.

    Args:
        expr: The root of the expression tree to evaluate. This is one of
            the node classes defined above.
        assignment: A dict mapping (person, attribute) tuples - e.g.
            ("ada", "is_knight") - to booleans. It describes one fully
            specified candidate world: the value of every attribute for
            every person. This function assumes every attribute the
            expression touches is present in the dict; the solver is
            responsible for generating complete assignments.

    Returns:
        The boolean truth value of `expr` under `assignment`.

    Raises:
        TypeError: If `expr` is not one of the known node types. This
            should only happen if a new node class is added without a
            matching case here.
    """
    # Structural pattern matching dispatches on the *shape* of the node
    # (which dataclass it is, and its fields) rather than on an explicit
    # "kind" tag, which keeps each case's logic right next to the pattern
    # that triggers it and mirrors how the tree itself is built.
    match expr:
        case IsKnight(person):
            return assignment[(person, "is_knight")]
        case IsKnave(person):
            return not assignment[(person, "is_knight")]
        case IsGuilty(person):
            return assignment[(person, "is_guilty")]
        case IsInnocent(person):
            return not assignment[(person, "is_guilty")]

        case And(exprs):
            # Conjunction: every sub-expression must hold. `all()` on an
            # empty tuple is vacuously True, matching standard logic.
            return all(evaluate(sub, assignment) for sub in exprs)
        case Or(exprs):
            # Disjunction: at least one sub-expression must hold. `any()`
            # on an empty tuple is vacuously False, matching standard logic.
            return any(evaluate(sub, assignment) for sub in exprs)
        case Not(inner):
            return not evaluate(inner, assignment)
        case Implies(antecedent, consequent):
            # Material implication is equivalent to "not antecedent, or
            # consequent" - short-circuiting on a false antecedent avoids
            # evaluating the consequent unnecessarily.
            if not evaluate(antecedent, assignment):
                return True
            return evaluate(consequent, assignment)
        case Iff(left, right):
            return evaluate(left, assignment) == evaluate(right, assignment)

        case ExactlyN(n, exprs):
            true_count = sum(evaluate(sub, assignment) for sub in exprs)
            return true_count == n
        case AtLeastN(n, exprs):
            true_count = sum(evaluate(sub, assignment) for sub in exprs)
            return true_count >= n
        case AtMostN(n, exprs):
            true_count = sum(evaluate(sub, assignment) for sub in exprs)
            return true_count <= n

        case _:
            # Reaching this means a node type exists that this function
            # does not know how to evaluate - a bug, not a puzzle error.
            raise TypeError(f"Unknown expression node: {expr!r}")
