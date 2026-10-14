See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 4 Spec

## Goal

Combine three techniques into one deduction pipeline that fully solves
both puzzles end to end (not partially, as in Step 3):

1. **The tactic from Step 3** (hypothesize each person's knight/knave
   status, check for contradiction) — unchanged.
2. **Backward propagation** (new): given an expression's required truth
   value, derive forced values for its sub-expressions where the logic
   allows exactly one consistent option.
3. **Case-split fallback** (new): once (1) and (2) reach a fixed point,
   if any `(person, attribute)` values are still unknown, brute-force
   only the *remaining* unknowns (not the whole puzzle) and check full
   consistency, same as Step 1/2's original brute force but scoped down
   to just what's left.

This was verified by simulation before writing this spec. Both puzzles
are fully solved by this combination — but propagation alone contributes
**zero new facts** in both puzzles (it's genuinely exercised by neither
puzzle's specific structure). That's expected and not a bug — see
"Validating propagation directly" below for why this still needs to be
tested on its own.

## Backward propagation

```python
def propagate(expr: Expr, required: bool, assignment: dict, facts: dict) -> None
```

Given that `expr` must evaluate to `required`, walk the tree and record
any `(person, attribute) -> bool` facts that are *forced* — i.e. where
there's exactly one consistent way to satisfy `required` given what's
already known. Mutates `facts` in place. Do not guess when there's
genuine ambiguity (see the `And`/`Or` cases below) — leaving something
unresolved is correct behavior, not a shortcoming.

Rules per connective:

- **`Var`**: if not already known, record `required` directly.
- **`Not(e)`**: recurse into `e` with `not required`.
- **`And(*es)`**, required `True`: every operand must be `True` —
  recurse into each with `True`.
- **`And(*es)`**, required `False`: only propagate if *exactly one*
  operand is still unknown AND every other operand is already known
  `True`. In that case the unknown one must be `False`. Otherwise, do
  nothing — with two or more unknowns you cannot tell which one is
  responsible for the conjunction being false.
- **`Or(*es)`**, required `False`: every operand must be `False` —
  recurse into each with `False`.
- **`Or(*es)`**, required `True`: only propagate if exactly one operand
  is unknown and every other operand is already known `False`. That one
  must be `True`. Otherwise do nothing (mirror of the `And` case).
- **`Implies(a, b)`**, required `False`: this pins both sides — `a` must
  be `True` and `b` must be `False`. Recurse into both.
- **`Implies(a, b)`**, required `True`: only partial propagation is
  possible — if `a` is already known `True`, recurse into `b` with
  `True`. If `b` is already known `False`, recurse into `a` with
  `False`. Otherwise do nothing.
- **`Iff(a, b)`**, either required value: if one side's current value is
  already known, the other side is forced (equal to it if `required` is
  `True`, opposite if `required` is `False`). If *both* sides are still
  unknown, nothing can be forced — this is the exact case that stalls
  propagation in Puzzle 1's constraint.

Do not implement backward propagation for `ExactlyN` / `AtLeastN` /
`AtMostN` in this step — neither puzzle's statements need it there
(only the case-split fallback touches those, and brute force doesn't
need propagation rules). Leave this out rather than building it
speculatively.

## Validating propagation directly

Because neither puzzle's real trace exercises every branch above, add a
small set of standalone checks — not full puzzles, just constructed
expressions — that directly confirm `propagate()` behaves correctly in
isolation. At minimum, cover:

- `And(Var(X), Var(Y))` required `True` → both `X` and `Y` forced `True`.
- `And(<known True>, Var(Z))` required `False` → `Z` forced `False`.
- `And(Var(X), Var(Y))` required `False` (both still unknown) → **no**
  facts forced (this must NOT produce a guess).
- `Iff(Var(A), Var(B))` required `True`, with `A` already known → `B`
  forced to match.
- `Iff(Var(A), Var(B))` required `True`, with both `A` and `B` unknown →
  no facts forced.
- `Implies(Var(P), Var(Q))` required `False` → both `P` forced `True`
  and `Q` forced `False`.

These are small, deliberately constructed checks of the propagation
function itself, independent of the two puzzles.

## Case-split fallback

After the tactic and propagation are run in a loop until neither makes
further progress (a "fixed point"):

```python
def case_split_fallback(puzzle, assignment) -> dict
```

1. Collect every `(person, attribute)` pair still unknown after the
   fixed point.
2. Enumerate every combination of `True`/`False` for just that
   remaining set (not the whole puzzle — reuse the existing known
   values as fixed).
3. For each combination, check full consistency: every constraint
   evaluates `True`, and every person's statement evaluates to their
   `is_knight` value (use the existing two-valued `evaluate()` from
   Step 2, since at this point every value is filled in).
4. If exactly one combination is fully consistent, that's the answer —
   merge it into `assignment`.
5. If zero or more than one combination survives, treat this the same
   way Step 1 treated an ambiguous/broken puzzle: report it clearly
   rather than silently picking one.

## Pipeline structure

```
loop (up to a small round cap, e.g. 10):
    changed = tactic_round() or propagate_round()
    if not changed: break

if any (person, attribute) still unknown:
    case_split_fallback(...)
```

`propagate_round()` should run propagation from every constraint
(always required `True`) and from every already-resolved person's
statement (required = their known `is_knight` value), merging any new
facts into the assignment.

## Output requirements

For each puzzle, print an explanatory trace that clearly separates the
three techniques (don't blur them into one undifferentiated log):

- Which facts the **tactic** resolved, and why (as in Step 3).
- Which facts **propagation** resolved, and why — or, if none, say so
  explicitly rather than omitting the section (e.g. "Propagation made no
  additional progress on this puzzle").
- How many unknowns remained for the **case-split fallback**, how many
  combinations were checked, and how many were fully consistent.
- The final, complete solution for every person and every attribute.

**Expected results (verified by simulation):**

- **Puzzle 1:** tactic resolves Ada. Propagation resolves nothing.
  3 unknowns remain (`Bo.is_knight`, `Ada.is_guilty`, `Bo.is_guilty`) →
  8 case-split combinations → exactly 1 valid completion. Final: Ada =
  knave/innocent, Bo = knight/innocent.
- **Puzzle 2:** tactic resolves nothing. Propagation resolves nothing.
  All 3 unknowns remain → 8 case-split combinations → exactly 1 valid
  completion. Final: Ada = knave, Bo = knave, Cal = knight.

Both puzzles should now be reported as **fully solved**, unlike Step 3's
explicitly partial output.

## Project structure

Add the propagation function and the case-split fallback to the same
module Step 3 created for the three-valued evaluator and tactic (or
create a new `deduction.py` if Step 3 didn't already establish one —
check what exists before creating a new file). Keep all deduction logic
(tactic, propagation, case-split) together rather than scattering it
across files.

## Out of scope for this step

- Backward propagation for `ExactlyN` / `AtLeastN` / `AtMostN`
- Smarter case-split ordering/heuristics (e.g. picking which variable to
  branch on first) — brute-forcing the full remaining set is fine at
  this scale
- Natural-language rendering of the full deduction trace into
  human-readable prose (this step's output is structured/explicit, not
  polished explanation text — that's a later step)
- Puzzle generator, difficulty rating

## Definition of done

- `propagate()` passes all the standalone checks listed above,
  independent of either puzzle.
- Puzzle 1 is fully solved (all 4 values resolved, matching the
  simulated result above).
- Puzzle 2 is fully solved (all 3 values resolved, matching the
  simulated result above).
- Output clearly separates tactic / propagation / case-split
  contributions, and honestly reports that propagation contributed
  nothing on these two puzzles specifically.
- Code follows every rule in RULES.md.
