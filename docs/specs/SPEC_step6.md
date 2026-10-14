See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 6 Spec

## Goal

Extend Step 5's natural-language rendering to the two remaining
techniques: backward propagation and the case-split fallback. After this
step, every resolved value in both puzzles has a plain-language
explanation attached, not just the tactic-resolved ones.

**Known limitation, stated up front:** propagation resolves zero facts
in both existing puzzles (verified in Step 4). This means propagation's
natural-language renderer can only be validated against the standalone
constructed examples from Step 4's Part "Validating propagation
directly" — there is no real puzzle output to check it against yet.
That's expected, not a gap to fix in this step.

## Part 1 — structured records (do this first, only if needed)

Same pattern as Step 5. Check whether propagation and the case-split
fallback already produce structured records. If not, add:

```python
@dataclass
class PropagationStep:
    person: str
    attribute: str
    resolved_value: bool
    source_expr_description: str  # plain identifier of which statement/constraint forced this
    required_value: bool          # what that source expression was required to equal

@dataclass
class RejectedCombination:
    values: dict            # the (person, attribute) -> bool values tried
    failed_check: str        # which statement or constraint failed, e.g. "Bo's statement"
    expected_value: bool     # what was required (True for constraints, or the hypothesized is_knight for statements)
    actual_value: bool       # what it actually evaluated to

@dataclass
class CaseSplitResult:
    remaining_unknowns: list       # the (person, attribute) pairs that were unknown going in
    total_combinations: int
    winning_combination: dict
    example_rejected: RejectedCombination  # the FIRST rejected combination encountered, for illustration
```

For `example_rejected`: capture the first combination the case-split
loop rejects (in whatever enumeration order the code already uses — no
need to pick a "best" one), along with which specific statement or
constraint it failed and why. This requires the case-split loop to check
combinations one at a time and record the failure reason rather than
just filtering silently.

**Regression check:** this refactor must not change final answers.
Confirm both puzzles still resolve to the exact values verified in
Step 4.

## Part 2 — rendering propagation

```python
def render_propagation_step(step: PropagationStep) -> str
```

Explain, in 1-3 sentences: which expression's required truth value
triggered this, and why that forces this specific conclusion. Name the
connective in plain terms (e.g. "since the conjunction must be true,
each part of it must be true" rather than printing `And(...)`).

Validate this against Step 4's standalone propagation examples, rendered
into English — for instance, the check where `And(<known True>, Var(Z))`
required `False` forces `Z` to `False` should render as something like:
"One part of this statement is already known to be true. Since the
whole statement must be false, the other part — [Z] — must be false."
(Illustrative target, not literal required text — generate from the
data, don't hardcode this sentence.)

## Part 3 — rendering the case-split fallback

```python
def render_case_split(result: CaseSplitResult) -> str
```

This is the harder writing problem flagged in Step 5. Structure the
explanation around these required elements, in order:

1. **Frame it honestly**: state how many values were still unknown after
   direct deduction, and that every combination was checked systematically
   — don't dress this up as if it were a clever insight; it's exhaustive
   checking, and saying so is more trustworthy than hiding it.
2. **State the winning combination** in plain language (reuse the same
   per-person "knight/knave, guilty/innocent" phrasing used elsewhere).
3. **Confirm consistency**: briefly state, per person, that their
   statement's truth value matches their resolved type.
4. **Give one concrete counterexample** using `example_rejected`: name
   the specific combination that was tried and rejected, and state
   plainly which statement or constraint it violated and how (e.g. "if
   Bo were guilty instead, [constraint] would require Ada to also be
   guilty, but then Ada's statement would evaluate to a different value
   than her knave status requires").

Keep the whole explanation readable — aim for a short paragraph, not a
transcript of all 8 combinations.

## Output requirements

For each puzzle, every resolved value should now have an accompanying
natural-language explanation using the technique that actually resolved
it (tactic → Step 5's renderer, propagation → Part 2, case-split →
Part 3). Print all of them together as the puzzle's full explanation.

**Expected behavior:**
- **Puzzle 1**: Ada's explanation via the tactic renderer (unchanged
  from Step 5). Bo, Ada's guilt, and Bo's guilt all resolved via
  case-split (verified in Step 4) — these now get Part 3's
  natural-language treatment instead of Step 4's raw structured summary.
- **Puzzle 2**: all three people resolved via case-split — same
  treatment.
- Since propagation resolves nothing in either puzzle, no
  propagation-rendered explanation appears in either puzzle's output.
  State this plainly in the output, same as Step 5 did for the tactic
  in Puzzle 2.

## Out of scope for this step

- Improving case-split's underlying algorithm (still brute force over
  the remaining unknowns — that's fine at this scale)
- Puzzle generator, difficulty rating
- Any UI beyond terminal output
- A unified "explain the whole puzzle as one flowing narrative" mode —
  printing each resolved value's explanation in sequence is sufficient
  for this step

## Definition of done

- Structured records for propagation and case-split exist, with a
  regression check confirming both puzzles' final answers are unchanged
  from Step 4.
- `render_propagation_step` correctly renders Step 4's standalone
  propagation examples into readable English.
- `render_case_split` includes all four required elements (honest
  framing, winning combination, per-person consistency, one concrete
  counterexample) for Bo's resolution in Puzzle 1 and for all three
  people in Puzzle 2.
- Puzzle 1's full output has one tactic explanation (Ada) and case-split
  explanations for the remaining three values.
- Puzzle 2's full output has case-split explanations for all three
  people, and explicitly states that propagation and the tactic each
  contributed nothing.
- Code follows every rule in RULES.md.
