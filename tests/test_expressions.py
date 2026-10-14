"""Tests for the expression AST: evaluation, three-valued evaluation, atoms()."""

import pytest

from veridex.expressions import (
    And,
    AtLeastN,
    AtMostN,
    ExactlyN,
    Iff,
    Implies,
    IsGuilty,
    IsInnocent,
    IsKnave,
    IsKnight,
    Not,
    Or,
    atoms,
    evaluate,
    evaluate_partial,
)

WORLD = {
    ("ada", "is_knight"): True,
    ("bo", "is_knight"): False,
    ("ada", "is_guilty"): False,
    ("bo", "is_guilty"): True,
}


def test_atomic_nodes_read_the_assignment():
    assert evaluate(IsKnight("ada"), WORLD) is True
    assert evaluate(IsKnave("ada"), WORLD) is False
    assert evaluate(IsGuilty("bo"), WORLD) is True
    assert evaluate(IsInnocent("bo"), WORLD) is False


def test_connectives():
    assert evaluate(And(IsKnight("ada"), IsKnave("bo")), WORLD)
    assert not evaluate(And(IsKnight("ada"), IsKnight("bo")), WORLD)
    assert evaluate(Or(IsKnight("bo"), IsKnight("ada")), WORLD)
    assert evaluate(Not(IsKnight("bo")), WORLD)
    assert evaluate(Iff(IsKnight("ada"), IsInnocent("ada")), WORLD)


def test_implication_is_vacuously_true_for_a_false_antecedent():
    assert evaluate(Implies(IsKnave("ada"), IsKnight("bo")), WORLD)
    assert not evaluate(Implies(IsKnight("ada"), IsKnight("bo")), WORLD)


def test_counting_nodes():
    knaves = [IsKnave("ada"), IsKnave("bo")]
    assert evaluate(ExactlyN(1, knaves), WORLD)
    assert evaluate(AtLeastN(1, knaves), WORLD)
    assert not evaluate(AtLeastN(2, knaves), WORLD)
    assert evaluate(AtMostN(1, knaves), WORLD)
    assert not evaluate(AtMostN(0, knaves), WORLD)


def test_unknown_node_type_raises_type_error():
    with pytest.raises(TypeError):
        evaluate("not an expression", WORLD)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        atoms("not an expression")  # type: ignore[arg-type]


def test_partial_evaluation_short_circuits_on_known_operands():
    # ada is unknown, bo is a known knave.
    partial = {("bo", "is_knight"): False}
    assert evaluate_partial(IsKnight("ada"), partial) is None
    assert evaluate_partial(And(IsKnight("ada"), IsKnight("bo")), partial) is False
    assert evaluate_partial(Or(IsKnight("ada"), IsKnave("bo")), partial) is True
    assert evaluate_partial(Or(IsKnight("ada"), IsKnight("bo")), partial) is None


def test_partial_evaluation_agrees_with_full_evaluation_on_complete_worlds():
    expr = Implies(Or(IsKnight("ada"), IsGuilty("bo")), Iff(IsKnave("bo"), IsInnocent("ada")))
    assert evaluate_partial(expr, WORLD) == evaluate(expr, WORLD)


def test_atoms_lists_every_pair_read_by_an_expression():
    expr = And(IsKnave("ada"), Iff(IsGuilty("bo"), Not(IsInnocent("ada"))), AtLeastN(1, [IsKnight("bo")]))
    assert atoms(expr) == [
        ("ada", "is_knight"),
        ("bo", "is_guilty"),
        ("ada", "is_guilty"),
        ("bo", "is_knight"),
    ]
