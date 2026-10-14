"""Tests for the brute-force solver, including the Step 1 regression numbers."""

from veridex.puzzles import PUZZLE_1, PUZZLE_2
from veridex.solver import solve


def test_puzzle_1_matches_the_step_1_numbers():
    result = solve(PUZZLE_1)
    assert len(result.all_assignments) == 16
    assert len(result.constraint_passed) == 8
    assert len(result.fully_valid) == 1


def test_puzzle_1_unique_solution():
    (solution,) = solve(PUZZLE_1).fully_valid
    assert solution == {
        ("ada", "is_knight"): False,
        ("ada", "is_guilty"): False,
        ("bo", "is_knight"): True,
        ("bo", "is_guilty"): False,
    }


def test_puzzle_2_unique_solution():
    result = solve(PUZZLE_2)
    assert len(result.all_assignments) == 8
    (solution,) = result.fully_valid
    assert solution == {
        ("ada", "is_knight"): False,
        ("bo", "is_knight"): False,
        ("cal", "is_knight"): True,
    }
