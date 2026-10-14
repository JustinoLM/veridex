See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 7 Spec

## Goal

Generate new, random Knights & Knaves puzzles (not hardcoded) and verify
each one has exactly one valid solution before accepting it, using the
existing two-valued solver from Step 2 (still correct — it's been
regression-checked every step so far). Then run the full deduction
pipeline (Steps 3-6) on a generated puzzle to confirm the whole system
works on puzzles it wasn't written specifically for.

**Deliberately narrow scope for this first version:**
- Exactly 2 people (same shape as Puzzle 1/2's `Ada`/`Bo` naming — reuse
  those names or generate simple placeholder names, either is fine).
- Only `is_knight` — no guilt axis, no global constraints. Adding those
  back is a natural extension for a later step, not this one.
- Statement grammar limited to `Not`, `And`, `Or`, `Iff` over
  `IsKnight`/`IsKnave` of either person. Do not include `Implies`,
  `ExactlyN`/`AtLeastN`/`AtMostN`, or guilt-referencing nodes in the
  generator yet — the retry-cap numbers below were calibrated
  specifically against this grammar and would need to be re-measured for
  a richer one.

## Statement generator

```python
def random_statement(people: list[str], max_depth: int) -> Expr
```

Recursive generation:
- At depth 0, or with some probability at any depth (to avoid every
  statement being maximally deep), produce a leaf: `IsKnight(person)` or
  `IsKnave(person)` for a randomly chosen person.
- Otherwise, pick one of `And`, `Or`, `Iff` at random and recurse into
  two sub-statements at `max_depth - 1`.

Use `max_depth = 2` as the default — this is the exact configuration
that was calibrated (see below). Make it a parameter, not a hardcoded
constant, but don't change the default without recalibrating.

## Puzzle generator + uniqueness check

```python
def generate_puzzle(max_attempts: int = 100) -> Puzzle
```

1. Generate a random statement for each of the 2 people.
2. Build a `Puzzle` with no constraints (empty list) and these
   statements.
3. Run it through the existing generic solver (from Step 2) and count
   how many assignments pass full validation.
4. If exactly 1, return this puzzle (include how many attempts it took).
5. If 0 or more than 1, discard and try again, up to `max_attempts`.
6. If `max_attempts` is exhausted without finding a unique-solution
   puzzle, raise a clear error rather than returning something broken or
   looping forever. This should not happen in practice — see calibration
   below — so hitting it would indicate something is actually wrong.

**Calibration (verified, not guessed):** with this exact grammar and
`max_depth = 2` over 2 people, roughly 1 in 3 randomly generated puzzles
has a unique solution. Across 2000 simulated trials, the average number
of attempts needed was 3, and the worst case observed was 20. A cap of
100 gives wide safety margin without risking a real infinite loop.

## Output requirements

Generate 3 puzzles. For each one:
- Print how many attempts it took to find a unique-solution puzzle.
- Print the puzzle in the same plain-language style used elsewhere in
  the project (people, statements — no constraint section needed here
  since this generator doesn't produce constraints).
- Run the FULL deduction pipeline from Steps 3-6 on it (tactic →
  propagation → case-split fallback, with natural-language rendering)
  and print the complete explanation, exactly as already happens for
  Puzzle 1 and Puzzle 2.

This should require no new pipeline code — the whole point is that a
generated `Puzzle` is not structurally different from a hardcoded one,
so everything built in Steps 2-6 should work on it unmodified. If it
doesn't work unmodified, that's a sign something in the pipeline was
accidentally puzzle-specific rather than fully generic — worth flagging
rather than special-casing around it.

## Out of scope for this step

- Guilt axis, global constraints, or richer statement grammar
  (`Implies`, counting nodes) in generated puzzles
- More than 2 people
- Difficulty rating or classification of generated puzzles
- Any deduplication (generating the "same" puzzle twice by chance is
  fine and not checked for)
- Persisting/saving generated puzzles anywhere

## Definition of done

- `generate_puzzle()` reliably returns a unique-solution puzzle within
  the attempt cap (expect ~3 attempts on average per the calibration
  above — if actual runs consistently need far more than that, treat it
  as a discrepancy worth investigating, not just accepting).
- All 3 generated puzzles run through the full Step 3-6 deduction
  pipeline without any code changes to that pipeline.
- Output for each generated puzzle includes the attempt count, the
  puzzle statement, and the complete natural-language explanation.
- Code follows every rule in RULES.md.
