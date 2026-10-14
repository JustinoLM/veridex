"""Difficulty classification: a structural rating of how hard a puzzle was
to resolve, based purely on which of the three techniques in deduction.py
actually had to contribute - not on any message-based or play-data-derived
rating (e.g. Glicko-2), since this project has no real user play data to
calibrate one against. See SPEC_step11.md for the full rationale.
"""

from enum import Enum

from .deduction import CaseSplitResult, PropagationStep, TacticStep


class Difficulty(Enum):
    """The three structural difficulty tiers a puzzle can classify as.

    Each tier corresponds to the strongest technique that was actually
    required to fully resolve the puzzle, not to any measure of how many
    steps were involved - see classify_difficulty() for the exact rule.
    """

    EASY = "easy"  # The tactic alone fully resolved the puzzle.
    MEDIUM = "medium"  # Propagation was needed too, but never case-split.
    HARD = "hard"  # The case-split fallback was needed for at least one value.


def classify_difficulty(
    tactic_steps: list[TacticStep],
    propagation_steps: list[PropagationStep],
    case_split_result: CaseSplitResult | None,
) -> Difficulty:
    """Classify a puzzle's difficulty from what the deduction pipeline needed.

    This is a purely structural classification: it looks only at which
    techniques actually contributed to fully resolving the puzzle, not at
    how many steps each one took or how the puzzle would play for a human
    solver. The three tiers form a strict hierarchy, checked in this
    order, since needing a stronger technique at all is treated as a
    bigger jump in difficulty than doing more work within a weaker one:

    1. HARD: the case-split fallback was actually needed to resolve at
       least one value. Falling back to systematic checking at all is the
       qualitative jump that matters here, regardless of how much the
       tactic or propagation contributed before that point - so this
       check is done first and, if it fires, overrides everything else.
    2. MEDIUM: no case-split was needed, but propagation resolved at
       least one fact the tactic could not.
    3. EASY: the tactic alone, with no propagation and no case-split,
       fully resolved the puzzle.

    Args:
        tactic_steps: Every TacticStep the pipeline's tactic resolved
            across all rounds, flattened into one list. Not actually
            inspected beyond being a parameter of the classification
            rule (see SPEC_step11.md) - EASY is simply whatever is left
            once MEDIUM and HARD are ruled out, whether or not the tactic
            resolved anything.
        propagation_steps: Every PropagationStep propagation forced
            across all rounds, flattened into one list. A non-empty list
            here (with no case-split needed) is exactly what makes a
            puzzle MEDIUM rather than EASY.
        case_split_result: The CaseSplitResult from the pipeline's
            case-split fallback, or None if the fallback was never
            invoked because the tactic and propagation already resolved
            everything. A result whose winning_combination is None means
            the fallback ran but did not actually resolve anything (an
            ambiguous or broken puzzle) - see CaseSplitResult - so that
            case does not count as "needing" case-split either.

    Returns:
        The Difficulty tier this combination of pipeline results
        represents.
    """
    # Checked first, and overrides everything else: actually needing the
    # case-split fallback to resolve at least one value is the
    # qualitative jump in difficulty this project cares about, regardless
    # of how much the tactic or propagation did beforehand.
    case_split_was_needed = (
        case_split_result is not None and case_split_result.winning_combination is not None
    )
    if case_split_was_needed:
        return Difficulty.HARD

    if propagation_steps:
        return Difficulty.MEDIUM

    return Difficulty.EASY
