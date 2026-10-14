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

# Maps each atomic node class to the attribute it reads from an
# assignment, so code that needs to know which (person, attribute) pairs
# an expression touches does not have to repeat that mapping.
_ATOM_ATTRIBUTES = {
    IsKnight: "is_knight",
    IsKnave: "is_knight",
    IsGuilty: "is_guilty",
    IsInnocent: "is_guilty",
}


def atoms(expr: Expr) -> list[tuple[str, str]]:
    """List every (person, attribute) pair that `expr` reads, in tree order.

    Used to validate a puzzle up front: any pair returned here must exist
    in every assignment the solver builds, otherwise evaluate() would
    fail deep in the recursion with a bare KeyError.

    Args:
        expr: The root of the expression tree to inspect.

    Returns:
        One (person, attribute) pair per atomic node, duplicates included.

    Raises:
        TypeError: If `expr` is not one of the known node types.
    """
    match expr:
        case IsKnight(person) | IsKnave(person) | IsGuilty(person) | IsInnocent(person):
            return [(person, _ATOM_ATTRIBUTES[type(expr)])]
        case And(exprs) | Or(exprs):
            return [pair for sub in exprs for pair in atoms(sub)]
        case Not(sub):
            return atoms(sub)
        case Implies(left, right) | Iff(left, right):
            return atoms(left) + atoms(right)
        case ExactlyN(_, exprs) | AtLeastN(_, exprs) | AtMostN(_, exprs):
            return [pair for sub in exprs for pair in atoms(sub)]
        case _:
            raise TypeError(f"Unknown expression node: {expr!r}")


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


# ---------------------------------------------------------------------------
# Three-valued (partial) evaluator.
#
# `evaluate()` above assumes every attribute the expression touches is
# already known - that is fine for the brute-force solver, which only ever
# evaluates fully specified candidate worlds. A deduction tactic, by
# contrast, wants to know what can be said about a statement *before*
# everything is known: sometimes a statement's truth value is already
# pinned down even though some of its sub-expressions are not, and the
# whole point of this evaluator is to notice that.
#
# The key idea is short-circuiting on Unknown the same way boolean logic
# already short-circuits on True/False: an And is False the moment any
# operand is False, no matter what the rest turn out to be, so an Unknown
# elsewhere doesn't prevent that conclusion. Only when the known operands
# are not enough to decide the outcome by themselves does the result
# become Unknown.
# ---------------------------------------------------------------------------


def _flip(value: bool | None) -> bool | None:
    """Negate a three-valued truth value, leaving Unknown as Unknown.

    Args:
        value: True, False, or None (Unknown).

    Returns:
        The logical negation of `value` if it is a definite boolean;
        None unchanged, since the negation of "we don't know" is still
        "we don't know".
    """
    if value is None:
        return None
    return not value


def evaluate_partial(expr: Expr, assignment: dict) -> bool | None:
    """Recursively compute the three-valued truth value of an expression tree.

    Unlike evaluate(), this does not assume every attribute the expression
    touches is present in `assignment`. Missing (person, attribute) pairs
    are treated as Unknown rather than raising a KeyError, and each
    connective below is implemented so that Unknown sub-results only
    propagate to the final result when they actually matter - e.g. an
    And with one known-False operand is False regardless of what its
    other, still-Unknown operands are.

    Args:
        expr: The root of the expression tree to evaluate.
        assignment: A dict mapping (person, attribute) tuples to True or
            False for attributes that are currently known. Attributes not
            yet determined should simply be absent from the dict (though
            an explicit None value is also treated as Unknown).

    Returns:
        True or False if `expr`'s truth value is already fully determined
        by what's currently known, or None if it is still Unknown.

    Raises:
        TypeError: If `expr` is not one of the known node types.
    """
    match expr:
        # Atomic nodes: look the attribute up and treat a missing entry
        # (or an explicit None) as Unknown rather than an error.
        case IsKnight(person):
            return assignment.get((person, "is_knight"))
        case IsKnave(person):
            return _flip(assignment.get((person, "is_knight")))
        case IsGuilty(person):
            return assignment.get((person, "is_guilty"))
        case IsInnocent(person):
            return _flip(assignment.get((person, "is_guilty")))

        case And(exprs):
            values = [evaluate_partial(sub, assignment) for sub in exprs]
            # A single definite False operand already dooms the whole
            # conjunction, no matter how many other operands are still
            # Unknown - so check for that before checking for Unknown.
            if any(value is False for value in values):
                return False
            if any(value is None for value in values):
                return None
            return True
        case Or(exprs):
            values = [evaluate_partial(sub, assignment) for sub in exprs]
            # Symmetric to And: a single definite True operand already
            # guarantees the whole disjunction, regardless of the rest.
            if any(value is True for value in values):
                return True
            if any(value is None for value in values):
                return None
            return False
        case Not(inner):
            return _flip(evaluate_partial(inner, assignment))
        case Implies(antecedent, consequent):
            # A false antecedent makes the implication vacuously true
            # without needing to know the consequent at all - this is
            # the clearest example of why a three-valued evaluator is
            # useful, since it can resolve a statement even when a whole
            # sub-expression is still completely Unknown.
            antecedent_value = evaluate_partial(antecedent, assignment)
            if antecedent_value is False:
                return True
            consequent_value = evaluate_partial(consequent, assignment)
            if consequent_value is True:
                return True
            if antecedent_value is True and consequent_value is False:
                return False
            return None
        case Iff(left, right):
            left_value = evaluate_partial(left, assignment)
            right_value = evaluate_partial(right, assignment)
            if left_value is None or right_value is None:
                return None
            return left_value == right_value

        case ExactlyN(n, exprs):
            true_count, unknown_count = _count_true_and_unknown(exprs, assignment)
            # The final count can range anywhere from true_count (if every
            # still-Unknown operand turns out False) up to
            # true_count + unknown_count (if every one turns out True).
            # The result is only decidable now if n falls outside that
            # range (definite False) or the range has collapsed to a
            # single value that happens to equal n (definite True).
            if n < true_count or n > true_count + unknown_count:
                return False
            if unknown_count == 0:
                return True
            return None
        case AtLeastN(n, exprs):
            true_count, unknown_count = _count_true_and_unknown(exprs, assignment)
            if true_count >= n:
                return True
            if true_count + unknown_count < n:
                return False
            return None
        case AtMostN(n, exprs):
            true_count, unknown_count = _count_true_and_unknown(exprs, assignment)
            if true_count > n:
                return False
            if true_count + unknown_count <= n:
                return True
            return None

        case _:
            # Reaching this means a node type exists that this function
            # does not know how to evaluate - a bug, not a puzzle error.
            raise TypeError(f"Unknown expression node: {expr!r}")


def _count_true_and_unknown(exprs: list[Expr], assignment: dict) -> tuple[int, int]:
    """Evaluate a list of sub-expressions and tally the True and Unknown ones.

    Shared by ExactlyN, AtLeastN, and AtMostN, since all three need the
    same two numbers - how many operands are definitely True, and how
    many are still Unknown - to decide whether the count constraint is
    already resolved. The count of definite-False operands is not needed
    by any of the three, so it is not tracked.

    Args:
        exprs: The sub-expressions to evaluate.
        assignment: The (possibly partial) assignment to evaluate them
            under.

    Returns:
        A (true_count, unknown_count) pair.
    """
    values = [evaluate_partial(sub, assignment) for sub in exprs]
    true_count = sum(1 for value in values if value is True)
    unknown_count = sum(1 for value in values if value is None)
    return true_count, unknown_count
