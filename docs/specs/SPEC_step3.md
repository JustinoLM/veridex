See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 3 Spec

## Goal

Add a three-valued evaluator (`True` / `False` / `Unknown`) and a single
deduction tactic on top of it: for each person whose knight/knave status
isn't known yet, hypothesize each possibility and check whether it leads
to a contradiction. This is the foundation the explainer will be built on
— not the explainer itself.

**This step is intentionally narrow.** It was verified by simulation
(not assumed) that this one tactic, run to a fixed point, resolves only
Ada's knight/knave status in Puzzle 1 — it does not resolve Bo, it does
not resolve either guilt value, and it resolves nothing at all in
Puzzle 2. Those gaps are expected and are explicitly out of scope for
this step. See "Known limitations" below.

## Three-valued evaluator

Add a new evaluator (do not modify the existing two-valued `evaluate()`
from Step 2 — that one is still used by the brute-force solver and should
keep working as-is):

```python
def evaluate_partial(expr: Expr, assignment: dict) -> bool | None
```

`assignment` maps `(person, attribute)` to `True`, `False`, or is simply
absent/`None` for attributes not yet known. Returns `True`, `False`, or
`None` (unknown).

Implement short-circuit logic per connective — this is the entire point
of the three-valued evaluator, since it's what lets a statement resolve
to a definite value even while some of its parts are still unknown:

- `And`: `False` if any operand is `False` (regardless of the others),
  `Unknown` if any remaining operand is `Unknown`, else `True`.
- `Or`: `True` if any operand is `True`, `Unknown` if any remaining
  operand is `Unknown`, else `False`.
- `Not`: `Unknown` stays `Unknown`, otherwise flip the value.
- `Implies`: `True` if the antecedent is `False` (regardless of the
  consequent — this is the "vacuously true" case), `True` if the
  consequent is `True`, `False` only if antecedent is `True` and
  consequent is `False`, otherwise `Unknown`.
- `Iff`: `Unknown` if either side is `Unknown`, otherwise `True` iff both
  sides match.
- `AtLeastN` / `ExactlyN` / `AtMostN`: count how many operands are
  definitely `True` and how many are still `Unknown`; resolve to `True`
  or `False` only if the answer is certain regardless of how the
  `Unknown` operands turn out, otherwise `Unknown`.

## The tactic

```python
def try_resolve_knight_status(puzzle, assignment) -> list[str]
```

For each person whose `is_knight` value is not yet in `assignment`:
1. For each hypothesis in `(True, False)`: build a trial assignment with
   that hypothesis plugged in for this person's `is_knight`, keeping
   everything else as currently known. Evaluate the person's statement
   with `evaluate_partial`.
2. A hypothesis survives if the result is `Unknown` or matches the
   hypothesis itself (a knight's statement must not evaluate to a
   definite `False`; a knave's statement must not evaluate to a definite
   `True`).
3. If exactly one hypothesis survives, resolve that person's `is_knight`
   to that value in `assignment` and record it (return which people were
   newly resolved this round).

Run this in a loop until a pass resolves nobody new (fixed point). Cap
the loop at a small number of rounds (e.g. 10) as a safety net — it
should always reach a fixed point well before that on puzzles this size.

## Output requirements

Add a new entry point (or extend `main.py`) that runs this tactic against
Puzzle 1 and prints, in plain language:
- Which round(s) resolved which person, and why (state the hypothesis
  that was tried, and that the other hypothesis led to a contradiction).
- The final state after the tactic reaches a fixed point: which people
  are resolved, which are not, and which attributes (e.g. guilt) remain
  entirely untouched.
- An explicit, plainly worded statement that this is a partial result,
  not the full puzzle solution — e.g. "This step resolves Ada only. Bo's
  status and both guilt values require deduction techniques not yet
  implemented."

Do not print anything implying the puzzle was fully solved — the whole
point of this step's output is to honestly show what one deduction
technique can and cannot do on its own.

## Known limitations (expected — do not try to fix these in this step)

- **Bo (Puzzle 1) is not resolved.** Bo's statement doesn't reference
  Bo's own knight/knave status, so hypothesizing Bo's status doesn't by
  itself create a contradiction from Bo's statement alone at this stage.
- **Guilt values (Puzzle 1) are not resolved.** This tactic only reasons
  about knight/knave status. Determining guilt requires reasoning
  backward from a statement's now-known truth value into its
  sub-expressions (e.g. "Ada is a knave, so her statement is false, so
  the guilt clause inside it must be false") — a different technique,
  planned for a later step.
- **Puzzle 2 is not resolved at all.** It requires reasoning about
  "exactly N" constraints in a way this tactic can't do through
  short-circuit evaluation alone — it needs case-split/branching
  (hypothesize a full scenario, follow it to a contradiction or a
  consistent result), which is planned for a later step.

## Out of scope for this step

- Backward propagation from a known statement truth value into its
  sub-expressions
- Case-split / branching reasoning
- Any rendering of this into natural-language "explanation" prose beyond
  the plain status output described above
- Fully solving either puzzle via this tactic — that is not the goal of
  this step

## Definition of done

- `evaluate_partial()` correctly implements three-valued short-circuit
  logic for every node type from Step 2.
- The tactic correctly resolves Ada's status in Puzzle 1 in round 1, and
  correctly reports that Bo and both guilt values remain unresolved.
- Running the tactic against Puzzle 2 correctly resolves nobody, and the
  output says so plainly rather than erroring or hanging.
- Code follows every rule in RULES.md.
