See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 12 Spec

## Goal

Split `main.py` (currently ~1006 lines, accumulated across 11 steps)
into cohesive modules. This is a pure reorganization — **no logic
changes, no behavior changes, no new features.** Everything that works
today must work identically after this step.

## Process

1. **Inventory first.** Before planning the exact split, use read-only
   inspection (view the file, grep for `class`/`def`) to see what's
   actually in `main.py` — don't assume the module boundaries below are
   exactly right without checking against the real file. Adjust as
   needed to match what's actually there.

2. **Propose module boundaries**, roughly along these lines (adjust
   naming/grouping to fit what's actually in the file — this is a
   starting template, not a rigid requirement):

   - `expressions.py` — AST node classes and both evaluators
     (`evaluate` two-valued, `evaluate_partial` three-valued).
   - `puzzles.py` — the `Puzzle` dataclass and the two hardcoded
     instances (the whodunit puzzle and the three-knave conditional).
   - `solver.py` — the generic brute-force solver.
   - `deduction.py` — `TacticStep`, `PropagationStep`,
     `RejectedCombination`, `CaseSplitResult`, the tactic function,
     `propagate()`, and the case-split fallback.
   - `rendering.py` — `render_tactic_step`, `render_propagation_step`,
     `render_case_split`, `_describe_fact`, and the propagation unit
     checks.
   - `generator.py` — `NAME_POOL`, `random_statement`,
     `random_constraint`, `generate_puzzle`,
     `generate_whodunit_puzzle`, `describe_generated_puzzle`.
   - `difficulty.py` — `Difficulty` and `classify_difficulty`.
   - `main.py` — orchestration only: imports from the modules above,
     calls the pipeline for each puzzle (hardcoded and generated), and
     prints. This file should end up dramatically smaller than 1006
     lines.

3. **Move code verbatim.** Function and class bodies should not change
   — only their location and the imports needed to wire modules
   together. If you notice something that looks like an actual bug
   while moving code, do NOT fix it as part of this step — note it
   separately and ask before touching it. This step is reorganization
   only.

## Regression verification — two different standards for two kinds of output

**Deterministic content must match exactly, byte for byte:**
- Puzzle 1 (whodunit regression check) output
- Puzzle 2 (three-knave conditional) output
- The propagation unit checks section (all 7 checks + their
  natural-language renderings)

Capture this output before refactoring and compare it character-for-
character against the same output after refactoring. Any difference
here is a real regression, not acceptable variance.

**Generated content cannot be compared this way** — there is no fixed
random seed anywhere in this project (confirmed back in Step 11, where
the same call produced different puzzles across runs). Comparing
generated puzzle text before/after refactoring would be meaningless;
different output there is expected and NOT a sign of a problem. For
this content, confirm instead that:
- Every generated-puzzle section (Steps 7, 8, 9, 10) still runs without
  errors or warnings after the refactor.
- Difficulty classification still runs and produces a sane tally at the
  end.

## Out of scope for this step

- Fixing the `NAME_POOL` 5-name limit (noted in the README already —
  separate future work if you decide to extend past 5 people)
- Any new functionality — interactivity, hiding explanations, difficulty
  selection, etc. This step only reorganizes existing code.
- Fixing any bugs noticed along the way (flag them, don't fix them here)

## Definition of done

- `main.py` contains only orchestration and printing — no AST
  definitions, no deduction logic, no generation logic.
- The proposed module split (or an adjusted version, if the real file
  structure warranted changes) is in place with clean imports and no
  circular dependencies.
- Puzzle 1, Puzzle 2, and the propagation unit checks produce byte-for-
  byte identical output to before the refactor.
- All generated-puzzle sections (Steps 7-10) still run cleanly with no
  errors or warnings.
- Difficulty classification (Step 11) still runs and tallies correctly.
- Any bugs noticed during the refactor are reported, not silently fixed.
- Code follows every rule in RULES.md.
