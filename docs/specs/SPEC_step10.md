See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 10 Spec

## Goal

Extend the `is_knight`-only generator's grammar to include `Implies` and
counting nodes (`ExactlyN`/`AtLeastN`/`AtMostN`) — the connectives this
whole project was originally motivated by (the vacuous-truth-of-
implication gap found in the competing app, and the "exactly N knaves"
style reasoning from Puzzle 2). This closes the loop: generated puzzles
can now exercise the exact reasoning that started this project, not just
`And`/`Or`/`Iff`.

**Scope note:** apply this only to the `is_knight`-only generator (Step
9's path). Do not combine this with the whodunit generator (Step 8) in
this step — that generator already has its own documented scaling
problem (Step 9), and compounling richer grammar with more attributes
at once makes any issue harder to isolate. One variable at a time.

## Grammar extension

Add two new productions to `random_statement`:

- **`Implies(a, b)`**: alongside `And`/`Or`/`Iff`, recurse into two
  sub-statements at `max_depth - 1`, same as the existing connectives.
- **Counting node** (terminal, not recursive): pick a random subset of
  2 to N people (where N is the puzzle's total people count), build a
  list of `IsKnave(person)` terms for that subset, pick one of
  `ExactlyN`/`AtLeastN`/`AtMostN` at random, and pick a threshold `n`
  between 0 and the subset size. This mirrors how Puzzle 2's real
  statements use counting nodes — wrapping simple knave terms, not
  arbitrarily nested sub-expressions.

Give the counting-node production a modest probability (roughly 15% at
each non-leaf branch point) so it appears regularly without dominating
every generated statement.

## Required robustness fix: `propagate()` and counting nodes

This matters and must be verified, not assumed: `propagate()` from Step
4 was written to handle `Var`/`Not`/`And`/`Or`/`Implies`/`Iff`, and
explicitly left counting nodes unhandled — but it was never actually
*exercised* against a counting node mid-traversal, because in Puzzle 2
the tactic never resolved anyone, so `propagate_round()` never got far
enough to call `propagate()` on a statement containing one. That was
luck, not a guarantee.

With random generation, a person's statement can absolutely be resolved
by the tactic while a *different* part of that same statement (nested
under an `And`/`Or`/`Implies` it's mixed into) contains a counting node.
`propagate()` will be called on it. It must not crash.

**Requirement:** confirm (and fix if needed) that `propagate()` safely
does nothing when it reaches a counting node it doesn't know how to
propagate through — no exception, no forced facts, just skip that
branch and return. Add an explicit check for this: construct a small
expression like `Implies(AtLeastN(2, [...]), Var(...))` with a known
required value, run it through `propagate()`, and confirm it completes
without raising and without inventing incorrect facts.

Do not implement real propagation logic for counting nodes in this
step — the fix here is purely "don't crash," not "reason through them."
That remains out of scope, same as Step 4.

## Calibration (verified, not guessed)

The richer grammar was checked by simulation and actually performs
slightly *better* than the plain `And`/`Or`/`Iff` grammar — `Implies`
being vacuously true often enough doesn't hurt uniqueness:

| People | Acceptance rate | Avg. attempts | Worst case (1500 trials) |
|---|---|---|---|
| 2 | 37.3% | 2.7 | 13 |
| 3 | 34.6% | 2.9 | 13 |
| 4 | 32.7% | 3.0 | 17 |

Use the existing `max_attempts = 100` default — still comfortable
margin.

## Output requirements

Generate 3 puzzles using the richer grammar (3 people each, for a good
chance of hitting both `Implies` and a counting node across the set).
For each:
- Print the attempt count.
- Print the puzzle in plain language.
- Run the full Steps 3-6 pipeline and print the complete explanation.

If any generated puzzle's explanation involves the tactic resolving
someone via an `Implies` that's vacuously true (antecedent false), or a
case-split counterexample that references a counting node, that's worth
calling out explicitly in your summary when reporting back — it's a
direct callback to the original motivating example from early in this
project.

## Out of scope for this step

- Combining rich grammar with the whodunit generator
- Real backward-propagation rules for counting nodes (only the
  "don't crash" fix is required)
- People counts beyond what Step 9 already calibrated
- Difficulty rating

## Definition of done

- `random_statement` generates `Implies` and counting nodes at the
  specified rate.
- The explicit `propagate()`-with-a-counting-node check passes: no
  crash, no incorrect forced facts.
- 3 puzzles generated with the rich grammar, each running cleanly
  through the full Steps 3-6 pipeline.
- All previous steps' output (Step 7, 8, 9) remains unchanged
  (regression check).
- Code follows every rule in RULES.md.
