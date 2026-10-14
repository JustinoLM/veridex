"""Tests for the random puzzle generators."""

import random

import pytest

from generator import NAME_POOL, generate_puzzle, generate_whodunit_puzzle
from solver import solve


@pytest.mark.parametrize("seed", range(5))
def test_generated_puzzles_have_exactly_one_solution(seed):
    random.seed(seed)
    for generated in (generate_puzzle(NAME_POOL[:2]), generate_whodunit_puzzle()):
        assert len(solve(generated.puzzle).fully_valid) == 1
        assert generated.attempts >= 1


def test_same_seed_gives_the_same_puzzle():
    random.seed(7)
    first = generate_puzzle(NAME_POOL[:3], allow_rich_grammar=True)
    random.seed(7)
    second = generate_puzzle(NAME_POOL[:3], allow_rich_grammar=True)
    assert first.puzzle == second.puzzle
    assert first.attempts == second.attempts


def test_exhausting_the_attempt_budget_raises_instead_of_returning_garbage():
    with pytest.raises(RuntimeError, match="Failed to generate"):
        generate_puzzle(NAME_POOL[:2], max_attempts=0)
    with pytest.raises(RuntimeError, match="Failed to generate"):
        generate_whodunit_puzzle(max_attempts=0)
