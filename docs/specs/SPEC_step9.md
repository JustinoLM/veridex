See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 9 Spec

## Goal

Generalize the `is_knight`-only generator (Step 7) to work with more
than 2 people, and demonstrate it with a puzzle larger than anything
generated so far. The whodunit-style generator (Step 8) stays at 2
people for now — see "Why whodunit stays at 2 people" below, a real
finding from calibration, not an oversight.

## What actually needs to change

`random_statement` (Step 7) and `generate_puzzle` were already written
with a `people: list[str]` parameter rather than hardcoded names — check
whether the underlying generation logic is already people-count-agnostic
before writing new code. If it is, the work here is mostly: (a) generate
a list of N person names instead of always using `["Ada", "Bo"]`, and
(b) confirm via calibration that generation still performs well at this
N (see below) rather than assuming it does.

If anything turns out to be silently hardcoded to exactly 2 people
(e.g. in `Puzzle` construction, rendering, or the pipeline), fix that
specifically and note it — that would be a real bug worth flagging, not
just patching around.

```python
def generate_puzzle(people: list[str], max_attempts: int = 100) -> Puzzle
```

Use simple generated names for people beyond the existing `Ada`/`Bo`
(e.g. `Cal`, `Dee`, ... — reuse Puzzle 2's `Cal` naming convention where
convenient).

## Calibration (verified, not guessed)

`is_knight`-only puzzle generation stays stable as people are added —
this was checked directly, not assumed:

| People | Acceptance rate | Avg. attempts | Worst case (1500 trials) |
|---|---|---|---|
| 2 | 33.8% | 3.0 | 15 |
| 3 | 30.3% | 3.3 | 23 |
| 4 | 28.5% | 3.5 | 18 |
| 5 | 26.3% | 3.8 | 18 |

A cap of 100 (same as Step 7) still gives wide safety margin at these
sizes. Generate a demonstration puzzle with **4 people** for this step —
large enough to be a meaningfully bigger example than anything so far,
small enough that `2^4 = 16` combinations keeps brute-force verification
instant.

## Why whodunit stays at 2 people

Extending Step 8's whodunit generator (guilt axis + random constraint)
to more people was tested by simulation before writing this spec, and it
does not hold up:

| People | Acceptance rate | Avg. attempts | Worst case (1500 trials) |
|---|---|---|---|
| 2 | 11.7% | 8.6 | 58 |
| 3 | 2.9% | 33.3 | 100 |
| 4 | 0.3% | 365.5 | 830 |

The search space grows as `2^(2N)` (two attributes per person) while a
single randomly generated constraint doesn't get proportionally more
constraining as people are added — so larger whodunit puzzles become
extremely rare to land on by chance. Scaling this properly needs either
multiple constraints, deeper/more targeted constraint generation, or a
fundamentally different generation strategy — that's real design work
for a future step, not something to force into this one. **Do not
attempt to generalize the whodunit generator's people count in this
step.** Keep it at exactly 2, as already built.

## Output requirements

- Generate 1 demonstration puzzle with 4 people using the generalized
  `is_knight`-only generator. Print the attempt count (compare against
  the ~3.5-average calibration above).
- Print the puzzle in plain language and run it through the full Steps
  3-6 deduction pipeline, same as every generated puzzle so far.
- Keep Step 7's original 2-person demonstration puzzles and Step 8's
  whodunit puzzles unchanged in the output (regression check — nothing
  about them should look different after this step's changes).

## Out of scope for this step

- Generalizing the whodunit generator beyond 2 people (see above —
  deferred pending a real design change, not just a parameter tweak)
- People counts beyond 5 (not calibrated; don't assume it holds)
- Difficulty rating
- `Implies` or counting nodes in the grammar

## Definition of done

- The 4-person `is_knight`-only demonstration puzzle is generated within
  a small number of attempts (consistent with the ~3.5 average — if it
  needs dramatically more, that's worth investigating before accepting).
- It runs through the full Steps 3-6 pipeline correctly.
- Step 7 and Step 8's existing output is unchanged (regression check).
- The whodunit generator's people count was NOT changed in this step.
- Code follows every rule in RULES.md.
