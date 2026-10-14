See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 8 Spec

## Goal

Extend Step 7's generator to also produce whodunit-style puzzles: 2
people, both `is_knight` and `is_guilty` attributes, statements that can
reference either (like Puzzle 1's Ada), and a randomly generated global
constraint over guilt (like Puzzle 1's all-or-nothing guilt rule). Same
integration goal as Step 7: confirm generated puzzles run cleanly through
the unmodified Steps 3-6 pipeline.

**Still narrow for this step:**
- Still exactly 2 people. Still `Not`/`And`/`Or`/`Iff` only in the
  grammar (no `Implies`, no counting nodes). N-person and richer grammar
  remain future steps.

## Statement generator — extend for two attributes

Modify (or add a parameter to) `random_statement` from Step 7 so it can
generate leaves referencing either `is_knight` or `is_guilty`:

```python
def random_statement(people: list[str], max_depth: int, allowed_attrs: list[str]) -> Expr
```

For a whodunit puzzle's per-person statements, call this with
`allowed_attrs=["is_knight", "is_guilty"]` — a leaf can be
`IsKnight`/`IsKnave` OR `IsGuilty`/`IsInnocent` for a randomly chosen
person, matching how Ada's real statement mixes both ("I am a knave,
and none of us are innocent").

Step 7's puzzles (only `is_knight`) should still work by calling this
with `allowed_attrs=["is_knight"]` — this is a generalization of the
existing function, not a separate one.

## Constraint generator

```python
def random_constraint(people: list[str], max_depth: int) -> Expr
```

Same generation logic, but restricted to `allowed_attrs=["is_guilty"]`
only — constraints in this project describe facts about guilt, not
knight/knave status (matching Puzzle 1's constraint).

## Puzzle generator + uniqueness check

```python
def generate_whodunit_puzzle(max_attempts: int = 300) -> Puzzle
```

1. Generate a statement per person with `allowed_attrs=["is_knight",
   "is_guilty"]`.
2. Generate one constraint with `random_constraint`.
3. Build a `Puzzle` with both attributes (`["is_knight", "is_guilty"]`)
   and this constraint.
4. Run the existing generic solver (already handles guilt + constraints
   — this is exactly Puzzle 1's structure) and count valid assignments.
5. Accept if exactly 1; otherwise discard and retry, up to
   `max_attempts`.
6. If the cap is exhausted, raise a clear error (same as Step 7).

**Calibration (verified, not guessed):** with both attributes and a
random constraint in play, the search space is 16 combinations per
attempt instead of 4, and correspondingly fewer random puzzles land on
a unique solution: about **1 in 8** (12.7% in a 2000-trial simulation).
Average attempts needed: **~8**. Worst case observed: **43**. A cap of
300 gives comfortable safety margin (7x the observed worst case)
without risking a real infinite loop.

## Output requirements

Generate 3 whodunit puzzles. For each:
- Print how many attempts it took (compare mentally against the ~8
  average / 43 worst-case calibration — if a run needs dramatically
  more than that consistently, treat it as worth investigating, same
  spirit as Step 7).
- Print the puzzle in plain language, including the constraint this
  time (Step 7's puzzles had none).
- Run the full Steps 3-6 deduction pipeline and print the complete
  explanation, exactly as for Puzzle 1.

Keep Step 7's `is_knight`-only generator and output intact — this step
adds a second generation mode, it doesn't replace the first.

## Out of scope for this step

- More than 2 people
- `Implies` or counting nodes in generated statements/constraints
- Difficulty rating
- Anything not already covered by the existing Steps 2-6 pipeline (if a
  generated puzzle needs something the pipeline doesn't already handle,
  that's worth flagging rather than working around)

## Definition of done

- `random_statement` correctly generates leaves over both attributes
  when `allowed_attrs` includes both, and still works with
  `allowed_attrs=["is_knight"]` for Step 7's puzzles (regression check —
  Step 7's output should be unchanged).
- `generate_whodunit_puzzle` reliably finds a unique-solution puzzle
  within the attempt cap, consistent with the ~8-average calibration
  above.
- All 3 generated whodunit puzzles run through the full Step 3-6
  pipeline (tactic, propagation, case-split, natural-language
  rendering) without modification to that pipeline.
- Code follows every rule in RULES.md.
