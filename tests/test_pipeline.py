"""Tests for the deduction pipeline and its text formatting."""

import random

import pytest

from veridex.difficulty import Difficulty
from veridex.generator import NAME_POOL, generate_puzzle, generate_whodunit_puzzle
from veridex.pipeline import MAX_PIPELINE_ROUNDS, format_pipeline, run_pipeline
from veridex.puzzles import PUZZLE_1, PUZZLE_2
from veridex.solver import solve


@pytest.mark.parametrize("puzzle", [PUZZLE_1, PUZZLE_2])
def test_hand_written_puzzles_are_fully_resolved_and_hard(puzzle):
    result = run_pipeline(puzzle)
    assert result.still_unknown == []
    assert result.assignment == solve(puzzle).fully_valid[0]
    assert result.difficulty is Difficulty.HARD
    assert result.case_split_result is not None
    assert not result.round_cap_hit


@pytest.mark.parametrize("seed", range(10))
def test_pipeline_agrees_with_brute_force_on_generated_puzzles(seed):
    random.seed(seed)
    for generated in (
        generate_puzzle(NAME_POOL[:3], allow_rich_grammar=True),
        generate_puzzle(NAME_POOL[:4]),
        generate_whodunit_puzzle(),
    ):
        puzzle = generated.puzzle
        result = run_pipeline(puzzle)
        assert result.still_unknown == []
        assert result.assignment == solve(puzzle).fully_valid[0]


def test_format_pipeline_produces_every_section():
    sections = format_pipeline(PUZZLE_2, run_pipeline(PUZZLE_2))
    assert sections.warning == ""
    assert sections.tactic
    assert sections.propagation
    assert sections.case_split
    assert "Cal is a knight" in sections.final
    assert sections.difficulty == "HARD"


def test_format_pipeline_reports_the_round_cap():
    result = run_pipeline(PUZZLE_1)
    result.round_cap_hit = True
    assert str(MAX_PIPELINE_ROUNDS) in format_pipeline(PUZZLE_1, result).warning
