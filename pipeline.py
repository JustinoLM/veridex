"""The full deduction pipeline, split into computation and presentation.

This used to live inside main.py's run_deduction_pipeline(), which solved
and printed in one pass. That forced play.py to capture main.py's stdout
and re-parse the text to restyle it. Splitting the two halves removes
that coupling: run_pipeline() produces a structured PipelineResult,
format_pipeline() turns it into plain-text sections, and each caller
(main.py's plain printing, play.py's rich panels) consumes the same
structured output directly.
"""

from dataclasses import dataclass

from deduction import (
    CaseSplitResult,
    PropagationStep,
    TacticStep,
    case_split_fallback,
    propagate_round,
    try_resolve_knight_status,
)
from difficulty import Difficulty, classify_difficulty
from puzzles import Puzzle
from rendering import (
    describe_assignment,
    render_case_split,
    render_propagation_step,
    render_tactic_step,
)

# Safety cap on how many rounds the tactic/propagation loop is allowed to
# run for before giving up on reaching a fixed point. Puzzles this size
# are expected to stabilize in one or two rounds; this cap exists only to
# guarantee termination if that assumption is ever wrong.
MAX_PIPELINE_ROUNDS = 10


@dataclass
class PipelineResult:
    """Everything one run of the deduction pipeline found, as data.

    Attributes:
        assignment: The final (person, attribute) -> bool assignment.
            Fully resolved for a well-posed puzzle; otherwise whatever
            did get resolved.
        tactic_rounds: (round number, steps) for each round in which the
            Step 3 tactic resolved at least one value.
        propagation_rounds: Same, for backward propagation.
        round_cap_hit: True if the loop used all MAX_PIPELINE_ROUNDS
            rounds without ever reaching a fixed point.
        unknown_before_case_split: The (person, attribute) keys still
            unknown once the tactic/propagation loop stopped.
        case_split_result: The fallback's result, or None if it was
            never needed.
        still_unknown: Keys still unresolved after everything ran.
        difficulty: The tier classify_difficulty() assigned.
    """

    assignment: dict
    tactic_rounds: list[tuple[int, list[TacticStep]]]
    propagation_rounds: list[tuple[int, list[PropagationStep]]]
    round_cap_hit: bool
    unknown_before_case_split: list[tuple[str, str]]
    case_split_result: CaseSplitResult | None
    still_unknown: list[tuple[str, str]]
    difficulty: Difficulty


@dataclass
class PipelineSections:
    """The pipeline's explanation as plain text, one string per section.

    Each field holds exactly the lines the pipeline prints under that
    section's heading (indentation included), joined by newlines, with
    no trailing blank line. `warning` is empty unless the round cap fired.
    """

    warning: str
    tactic: str
    propagation: str
    case_split: str
    final: str
    difficulty: str


def run_pipeline(puzzle: Puzzle) -> PipelineResult:
    """Run the tactic/propagation loop, then the case-split fallback.

    Pure computation: nothing is printed. See main.py's
    run_deduction_pipeline() for the narrated version.

    Args:
        puzzle: The puzzle to solve.

    Returns:
        A PipelineResult describing everything the three techniques did.
    """
    # Nothing is known at the start - the pipeline builds up everything
    # it knows purely from what the tactic and propagation resolve.
    assignment: dict = {}
    tactic_rounds: list[tuple[int, list[TacticStep]]] = []
    propagation_rounds: list[tuple[int, list[PropagationStep]]] = []
    round_cap_hit = False

    for round_number in range(1, MAX_PIPELINE_ROUNDS + 1):
        newly_resolved = try_resolve_knight_status(puzzle, assignment)
        if newly_resolved:
            tactic_rounds.append((round_number, newly_resolved))

        # Propagation runs after the tactic in the same round, so it can
        # see anything the tactic just resolved (e.g. propagating from a
        # statement whose speaker's status was only just determined).
        propagation_contributions, propagation_steps = propagate_round(puzzle, assignment)
        if propagation_steps:
            propagation_rounds.append((round_number, propagation_steps))

        if not newly_resolved and not propagation_contributions:
            # Neither technique made progress this round - a fixed
            # point. Whatever remains unknown is left to the case-split
            # fallback below.
            break
    else:
        # The for/else only runs if the loop finished without `break`,
        # i.e. the round cap was hit without ever reaching a fixed
        # point. Reported as a warning rather than treated as normal.
        round_cap_hit = True

    all_keys = [
        (person, attribute) for person in puzzle.people for attribute in puzzle.attributes
    ]
    unknown_before_case_split = [key for key in all_keys if key not in assignment]

    # Kept as None unless the fallback is actually invoked, so
    # classify_difficulty() can tell "never needed" apart from "needed
    # but somehow resolved nothing".
    case_split_result: CaseSplitResult | None = None
    if unknown_before_case_split:
        case_split_result = case_split_fallback(puzzle, assignment)

    still_unknown = [key for key in all_keys if key not in assignment]

    # tactic_rounds/propagation_rounds are flattened (round number
    # discarded) since classify_difficulty() only cares whether each
    # technique contributed at all, not when.
    all_tactic_steps = [step for _, steps in tactic_rounds for step in steps]
    all_propagation_steps = [step for _, steps in propagation_rounds for step in steps]
    difficulty = classify_difficulty(all_tactic_steps, all_propagation_steps, case_split_result)

    return PipelineResult(
        assignment=assignment,
        tactic_rounds=tactic_rounds,
        propagation_rounds=propagation_rounds,
        round_cap_hit=round_cap_hit,
        unknown_before_case_split=unknown_before_case_split,
        case_split_result=case_split_result,
        still_unknown=still_unknown,
        difficulty=difficulty,
    )


def format_pipeline(puzzle: Puzzle, result: PipelineResult) -> PipelineSections:
    """Render a PipelineResult as natural-language text, section by section.

    Args:
        puzzle: The puzzle `result` was computed for.
        result: The output of run_pipeline(puzzle).

    Returns:
        The text of each section, ready to print or to wrap in a panel.
    """
    warning = ""
    if result.round_cap_hit:
        warning = (
            f"WARNING: hit the {MAX_PIPELINE_ROUNDS}-round safety cap without "
            "reaching a fixed point."
        )

    # Tactic. Stating "no progress" explicitly (as with Puzzle 2, where
    # the tactic resolves nobody) beats printing nothing.
    tactic_lines: list[str] = []
    if result.tactic_rounds:
        for round_index, (round_number, steps) in enumerate(result.tactic_rounds):
            if round_index > 0:
                tactic_lines.append("")
            tactic_lines.append(f"  Round {round_number}:")
            for step in steps:
                tactic_lines.append(f"    - {render_tactic_step(step)}")
    else:
        tactic_lines.append("  The tactic made no progress on this puzzle.")

    propagation_lines: list[str] = []
    if result.propagation_rounds:
        for round_index, (round_number, steps) in enumerate(result.propagation_rounds):
            if round_index > 0:
                propagation_lines.append("")
            propagation_lines.append(f"  Round {round_number}:")
            for step in steps:
                propagation_lines.append(f"    - {render_propagation_step(step)}")
    else:
        propagation_lines.append("  Propagation made no additional progress on this puzzle.")

    case_split_lines: list[str] = []
    case_split = result.case_split_result
    if case_split is None:
        case_split_lines.append(
            "  Not needed - the tactic and propagation already resolved everything."
        )
    elif case_split.winning_combination is not None:
        case_split_lines.extend(f"  {line}" for line in render_case_split(case_split))
    else:
        case_split_lines.append(
            f"  WARNING: expected exactly one consistent completion of the "
            f"{len(case_split.remaining_unknowns)} remaining unknown value(s); "
            "this puzzle may be ambiguous or broken."
        )

    final_lines: list[str] = []
    if result.still_unknown:
        names = ", ".join(
            f"{person.capitalize()}.{attribute}" for person, attribute in result.still_unknown
        )
        final_lines.append(f"  WARNING: could not fully resolve this puzzle. Still unknown: {names}.")
    else:
        final_lines.extend(f"  {s}" for s in describe_assignment(puzzle, result.assignment))

    return PipelineSections(
        warning=warning,
        tactic="\n".join(tactic_lines),
        propagation="\n".join(propagation_lines),
        case_split="\n".join(case_split_lines),
        final="\n".join(final_lines),
        difficulty=result.difficulty.value.upper(),
    )
