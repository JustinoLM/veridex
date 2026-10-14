"""Tests for Puzzle construction-time validation and the built-in puzzles."""

import pytest

from expressions import AtLeastN, IsGuilty, IsKnave, IsKnight
from puzzles import PUZZLE_1, PUZZLE_2, Puzzle


def make(**overrides):
    fields = dict(
        name="t",
        people=["ada", "bo"],
        attributes=["is_knight"],
        statements={"ada": IsKnave("bo"), "bo": IsKnight("ada")},
        constraints=[],
    )
    fields.update(overrides)
    return Puzzle(**fields)


def test_a_well_formed_puzzle_is_accepted():
    assert make().people == ["ada", "bo"]


def test_builtin_puzzles_are_valid():
    assert PUZZLE_1.people == ["ada", "bo"]
    assert PUZZLE_2.people == ["ada", "bo", "cal"]


def test_empty_or_duplicate_people_are_rejected():
    with pytest.raises(ValueError, match="no people"):
        make(people=[], statements={})
    with pytest.raises(ValueError, match="more than once"):
        make(people=["ada", "ada"], statements={})


def test_unknown_or_duplicate_attributes_are_rejected():
    with pytest.raises(ValueError, match="unknown attribute"):
        make(attributes=["is_tall"])
    with pytest.raises(ValueError, match="more than once"):
        make(attributes=["is_knight", "is_knight"])


def test_statement_from_a_stranger_is_rejected():
    with pytest.raises(ValueError, match="'cal'"):
        make(statements={"cal": IsKnight("ada")})


def test_statement_mentioning_a_stranger_is_rejected_not_a_key_error():
    with pytest.raises(ValueError, match="'cal'"):
        make(statements={"ada": IsKnave("cal")})


def test_constraint_mentioning_a_stranger_is_rejected():
    with pytest.raises(ValueError, match="constraint 1"):
        make(constraints=[AtLeastN(1, [IsKnave("zed")])])


def test_expression_reading_an_undeclared_attribute_is_rejected():
    with pytest.raises(ValueError, match="is_guilty"):
        make(statements={"ada": IsGuilty("bo")})
