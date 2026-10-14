# Veridex

[![Tests](https://github.com/JustinoLM/veridex/actions/workflows/tests.yml/badge.svg)](https://github.com/JustinoLM/veridex/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-46%20tests-0A9EDC?logo=pytest&logoColor=white)
![Rich](https://img.shields.io/badge/Rich-terminal%20UI-FAE042)
![License](https://img.shields.io/badge/License-MIT-green)

A Knights & Knaves logic-puzzle toolkit in Python: a brute-force solver, a
human-style deduction engine that explains *how* it solves each puzzle, a
random puzzle generator, and an interactive terminal game.

<!-- demo.gif is recorded from docs/demo.tape with VHS: `vhs docs/demo.tape` -->
<p align="center">
  <img src="docs/images/demo.gif" width="720" alt="Playing a puzzle in the terminal and reading the step-by-step explanation">
</p>

In a Knights & Knaves puzzle, each person is either a knight (always tells
the truth) or a knave (always lies). Given what each person says, work out
who is which. Statements are expression trees (`expressions.py`), puzzles
declare their people, attributes, statements and constraints as plain data
(`puzzles.py`), and the solver contains no knowledge of any specific puzzle.

## Example

The exact output of `uv run veridex-demo` for the second built-in puzzle:

```text
======================================================================
FULL DEDUCTION PIPELINE - The three-knave conditional
======================================================================

Three people, Ada, Bo, and Cal, are each either a knight (always tells
the truth) or a knave (always lies). There is no guilt axis in this
puzzle - only knight/knave status.

Constraint: at least one of them is a knave.

Statements:
  Ada says: "Cal is a knave, and Cal and Bo are the same type."
  Bo says:  "If at least two of us are knaves, then all of us are knaves."
  Cal says: "None of us are knaves, or exactly two of us are knaves."

Tactic (hypothesize-and-check on knight/knave status):

  The tactic made no progress on this puzzle.

Backward propagation:

  Propagation made no additional progress on this puzzle.

Case-split fallback:

  3 things were still unknown: whether Ada is a knight, whether Bo is a knight, and whether Cal is a knight. Rather than being able to deduce the answer directly, all 8 possible combinations were tried until the one that fit was found.
  The combination that fit: Ada is a knave, Bo is a knave, and Cal is a knight.
  That combination holds up against everyone's statement:
      Ada's statement turns out to be false — which fits, since Ada is a knave.
      Bo's statement turns out to be false — which fits, since Bo is a knave.
      Cal's statement turns out to be true — which fits, since Cal is a knight.
  Not every combination works, though - for example, the one where Ada is a knight, Bo is a knight, and Cal is a knight was ruled out: it needed the puzzle's constraint to come out true, but that actually came out false.

Final solution:

  Ada is a knave.
  Bo is a knave.
  Cal is a knight.

Difficulty: HARD
```

The engine reports which techniques it needed, and that is what sets the
difficulty: this puzzle resists the first two, so it is rated `HARD`.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). The only runtime
dependency is [`rich`](https://github.com/Textualize/rich), which `uv`
installs on first run.

```sh
git clone https://github.com/JustinoLM/veridex.git
cd veridex
uv run veridex-demo   # solve and narrate every built-in and generated puzzle
uv run veridex-play   # play the puzzles yourself, then see the full explanation
```

Run the test suite:

```sh
uv run --group dev pytest
```

## What it does

- **Brute-force solver** (`solver.py`): enumerates every assignment of
  attributes to people, keeps those that satisfy the constraints and make
  every speaker's statement consistent with their type. A well-posed puzzle
  has exactly one survivor.
- **Deduction pipeline** (`deduction.py`, `pipeline.py`): solves puzzles the
  way a person would, using three techniques and explaining each step in
  plain language:
  1. *Hypothesize and check*: assume a person is a knight, then a knave,
     and rule out whichever assumption contradicts their own statement.
     This relies on a three-valued (True / False / Unknown) evaluator.
  2. *Backward propagation*: given that a statement must be true (or false),
     force any sub-claim that has exactly one consistent value.
  3. *Case split*: when the first two stall, brute-force only the values
     still unknown, and show one rejected combination as a counterexample.
- **Difficulty rating** (`difficulty.py`): `EASY` if the tactic alone solved
  the puzzle, `MEDIUM` if propagation was also needed, `HARD` if the case
  split was. It is structural (which technique was *required*), not a
  prediction of how a human would fare.
- **Puzzle generator** (`generator.py`): builds random statements out of
  `And` / `Or` / `Iff` (optionally `Implies` and counting nodes such as
  `ExactlyN`), and keeps retrying until the brute-force solver confirms
  exactly one solution. Supports 2-5 people, plus a "whodunit" mode with a
  guilt axis and a global constraint.
- **Interactive game** (`play.py`): shows a puzzle, collects your guess about
  each person, checks it, and then reveals the full explanation in colored
  panels, one per technique.

## Architecture

The code is a pipeline of small modules that pass structured data
(dataclasses), never formatted text, between each other:

```
src/veridex/
  expressions.py   expression AST (dataclasses) + full and three-valued evaluators
  puzzles.py       Puzzle dataclass (validated on construction) + built-in puzzles
  solver.py        brute-force solve() -> SolveResult
  deduction.py     tactic / propagation / case-split -> TacticStep, PropagationStep, CaseSplitResult
  difficulty.py    classify_difficulty() from those step records
  rendering.py     step records -> natural-language sentences
  pipeline.py      run_pipeline() -> PipelineResult;  format_pipeline() -> PipelineSections
  generator.py     random puzzle generation with uniqueness verification
  demo.py          plain-text entry point (batch demo of everything)  ->  veridex-demo
  play.py          interactive entry point (rich panels and prompts)  ->  veridex-play
tests/             pytest suite
docs/specs/        the per-step specs the project was built from
```

Design decisions worth knowing about:

- **Computation and presentation are separate.** `pipeline.run_pipeline()`
  returns data; `pipeline.format_pipeline()` turns it into text sections.
  `demo.py` prints those sections, `play.py` wraps each one in a colored
  panel. Neither entry point parses the other's output.
- **Fail early with clear errors.** `Puzzle` validates itself on
  construction: a statement that mentions someone outside `people`, or reads
  an attribute the puzzle does not declare, raises a `ValueError` naming the
  problem instead of a bare `KeyError` deep in the evaluator.
- **Every loop is bounded.** The deduction loop stops after
  `MAX_PIPELINE_ROUNDS` and says so, and the generator raises a
  `RuntimeError` after `max_attempts` rather than retrying forever or
  returning an ill-posed puzzle.
- **Bad input never crashes the game.** Unrecognized answers and menu
  choices are re-prompted; Ctrl-C / Ctrl-D quit cleanly.
- **Generated puzzles are unseeded by default.** Each run produces different
  puzzles (and therefore sometimes a different difficulty tier). The tests
  seed `random` to stay deterministic.

## Testing

`tests/` covers the evaluator (including implication's vacuous truth and
counting nodes), three-valued short-circuiting, puzzle validation, the
solver's known results for both built-in puzzles, the pipeline's agreement
with brute force on seeded generated puzzles, the generator's uniqueness
guarantee and failure mode, and `play.py`'s input handling. `demo.py` also
keeps a runtime regression check that Puzzle 1 still produces its original
numbers (16 candidates, 8 passing the constraint, 1 fully valid). CI runs
the suite on every push and pull request.

## Development process

I designed Veridex one step at a time. For each step I wrote a spec first:
its goal, what is in scope, what is explicitly out of scope, and what
"done" means. Those specs are published in [docs/specs/](docs/specs/), with
an index and the shared [rules](docs/specs/RULES.md) that applied to every
step. The implementation was then done with [Claude Code](https://claude.com/claude-code),
following those specs. The specs set the direction and the limits; the
tests, the architecture and the decisions about what to change are reviewed
and owned by me.

The steps, each one a foundation for the next:

- Step 1: brute-force solver for one hard-coded puzzle.
- Step 2: generic expression AST and puzzle-agnostic solver.
- Step 3: three-valued evaluator and the hypothesize-and-check tactic.
- Step 4: backward propagation and case-split fallback, combined into a
  pipeline.
- Steps 5-6: natural-language explanations for every technique.
- Steps 7-10: puzzle generator with uniqueness verification, whodunit mode,
  N people, and a richer grammar with `Implies` and counting nodes.
- Step 11: structural difficulty classification.
- Step 12: split the original single-file implementation into modules.
- Steps 13-14: interactive play loop and `rich` terminal presentation.

Step 15 (generated puzzles in the game menu) is specified but not
implemented yet.

## Limitations and roadmap

- Backward propagation does not yet reason through `ExactlyN` / `AtLeastN` /
  `AtMostN` counting constraints (it skips them safely).
- Case-split has no ordering heuristics.
- The whodunit generator supports exactly two people, and does not use
  `Implies` or counting nodes; the knight-only generator is calibrated up to
  five people.
- The game only offers the two hand-written puzzles; generated puzzles are
  not on its menu yet.
- Generated puzzles are not deduplicated.
- The difficulty rating is not calibrated against real player data.
- Terminal only: there is no GUI or web interface.

A note on random output: on some runs `demo.py` prints a `WARNING` next to
one of its end-of-run difficulty expectations (for example the 4-person demo
landing on `MEDIUM` instead of `EASY`). That is intentional honesty about
unseeded generation, not a bug in the classifier.

## License

[MIT](LICENSE)

## Author

**Justin Williams** — Software Engineering student, Universidad Tecnológica de Panamá
[GitHub](https://github.com/JustinoLM) · [LinkedIn](https://www.linkedin.com/in/jugawike)
