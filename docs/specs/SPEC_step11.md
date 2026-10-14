See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 11 Spec

## Goal

Classify every puzzle's difficulty based on which deduction technique
tier was actually required to fully resolve it — not a message-based
rating like Glicko-2 (which needs real user play data this project
doesn't have), but a measure grounded in the puzzle's actual logical
structure, using data the pipeline already computes.

## Classification rule

```python
from enum import Enum

class Difficulty(Enum):
    EASY = "easy"      # tactic alone fully resolved it
    MEDIUM = "medium"  # needed propagation too, but never needed case-split
    HARD = "hard"       # needed the case-split fallback for at least one value
```

```python
def classify_difficulty(tactic_steps, propagation_steps, case_split_result) -> Difficulty
```

Logic, checked in this order:
1. If `case_split_result` is not `None` and it actually resolved at
   least one value (i.e. the fallback was needed at all) → `HARD`.
   This overrides everything else — needing to fall back to
   systematic checking at all is the qualitative jump in difficulty,
   regardless of how much the tactic or propagation contributed before
   that point.
2. Otherwise, if `propagation_steps` is non-empty → `MEDIUM`.
3. Otherwise (tactic alone resolved everything) → `EASY`.

## Known expected results — state these honestly when you run it

- **Puzzle 1 and Puzzle 2** (the original hardcoded puzzles) both
  required case-split for at least one value (verified back in Step 4)
  → both should classify as **HARD**.
- **`MEDIUM` may turn out to be rare or entirely unobserved** across
  every puzzle in this project so far. Propagation has not resolved a
  single fact on any real puzzle generated through Steps 7-10 — only in
  the standalone constructed checks from Step 4/10. If every puzzle in
  the program's output classifies as either `EASY` or `HARD` with none
  landing on `MEDIUM`, report that plainly. It would mean this
  particular combination of grammar and puzzle size doesn't naturally
  produce puzzles where propagation alone (without also needing
  case-split) closes out the remaining unknowns — a real, honest
  finding about this generator, not a bug in the classifier.
- Step 9's 4-person `is_knight`-only demo puzzle was reported as fully
  resolved by the tactic alone with no case-split needed — that one
  should classify as **EASY**, giving at least one non-`HARD` example
  in the existing output.

If actual results contradict any of these expectations, flag it rather
than silently accepting a number that doesn't match — same practice as
every step so far.

## Output requirements

Print a `Difficulty: EASY / MEDIUM / HARD` line for every puzzle the
program already runs — this is additive to existing output, not a
restructuring. That means:
- Puzzle 1 (whodunit regression check)
- Puzzle 2 (three-knave conditional)
- Step 7's generated `is_knight`-only puzzles
- Step 8's generated whodunit puzzles
- Step 9's 4-person generated puzzle
- Step 10's rich-grammar generated puzzles

At the very end of the program's output, print a short summary: how
many puzzles classified as each of EASY / MEDIUM / HARD, across
everything the program ran in that execution.

## Out of scope for this step

- Any attempt to calibrate against real user performance (Glicko-2 or
  otherwise) — this is a structural classification, not a
  performance-based rating, and the spec should not pretend otherwise
- Sub-tiers within HARD (e.g. based on how many values needed
  case-split) — a single HARD tier is enough for this step
- Changing the generator to deliberately target a difficulty tier —
  classification only, not generation-by-difficulty

## Definition of done

- `classify_difficulty` implements the three-tier rule above exactly.
- Puzzle 1 and Puzzle 2 both classify as HARD.
- Step 9's 4-person demo puzzle classifies as EASY.
- Every puzzle printed by the program (across every step's output)
  includes its difficulty classification.
- The end-of-program summary correctly counts each tier.
- If MEDIUM turns out to be empty across all puzzles run, this is
  reported explicitly as a finding, not silently omitted.
- Code follows every rule in RULES.md.
