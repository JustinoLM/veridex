See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 5 Spec

## Goal

Render the tactic's deduction steps (from Steps 3-4) into natural-language
explanation sentences — the original motivation for this whole project.
This step covers ONLY the tactic (hypothesize-and-check-for-contradiction)
technique. Propagation and case-split explanations are out of scope here
and planned for a later step — rendering those well is a harder problem
and doesn't belong rushed into this one.

## Part 1 — structured records (do this first, only if needed)

Check the existing code from Steps 3-4. If the tactic already returns or
stores structured records of what it resolved (not just printed strings),
skip to Part 2.

If it currently only prints and doesn't retain structured data, add a
record type and have the tactic populate it as it runs:

```python
@dataclass
class TacticStep:
    person: str
    resolved_value: bool          # True = knight, False = knave
    surviving_hypothesis: bool    # should equal resolved_value
    contradicting_hypothesis: bool | None  # the hypothesis that was ruled out, if any
    contradiction_result: bool | None      # what that hypothesis evaluated to
```

This refactor must not change any final answers. **Regression check:**
after this change, Puzzle 1 and Puzzle 2 must still resolve to the exact
same final values verified in Step 4 (Ada = knave/innocent, Bo = knight/
innocent; Ada = knave, Bo = knave, Cal = knight).

## Part 2 — natural-language rendering

```python
def render_tactic_step(step: TacticStep) -> str
```

Turn one `TacticStep` into a short, plain-language paragraph. The
sentence needs to communicate the actual logical move, not just announce
the answer. Structure it around:

1. Name the hypothesis that was tried and ruled out.
2. State what that hypothesis would have implied.
3. Say why that's a contradiction.
4. State the conclusion.

**Concrete target** — this must produce something equivalent in
substance to the by-hand explanation this project started from:

> "Suppose Ada is a knight. Then her statement would have to be true.
> But her statement includes 'I am a knave' — which a knight could never
> truthfully say. This is a contradiction, so Ada cannot be a knight.
> Ada is a knave."

Do not hardcode this exact sentence — `render_tactic_step` must generate
it (or an equivalent) from the `TacticStep` data and the person's actual
statement, so it works for any person/puzzle, not just Ada specifically.

**Guidance on wording, not just structure:**
- Use the person's name, not a generic placeholder.
- State the hypothesis being tested explicitly ("Suppose X is a knight" /
  "Suppose X is a knave").
- When the contradiction comes from the statement directly asserting
  something about the speaker's own type (as with Ada), name that
  specifically — don't just say "the statement evaluates to False,"
  explain *why* it does.
- Keep each explanation to 2-4 sentences. This is meant to be read
  quickly, not to reproduce every internal evaluation step.

## Output requirements

For each puzzle, after running the full Step 4 pipeline, print the
natural-language explanation for every step the tactic resolved (using
`render_tactic_step`), followed by the existing structured summary from
Step 4 for propagation and case-split (unchanged — those still print
their Step 4-style output, not new prose, since rendering them is out of
scope here).

**Expected behavior on the two puzzles:**
- **Puzzle 1**: exactly one natural-language explanation is printed (for
  Ada). Bo's resolution came from case-split, not the tactic, so it does
  NOT get a natural-language explanation in this step — it still shows
  the Step 4-style case-split summary.
- **Puzzle 2**: zero natural-language explanations are printed, since the
  tactic resolved nobody in this puzzle (verified in Step 4). Confirm the
  output says this plainly rather than printing nothing with no
  explanation of why.

## Out of scope for this step

- Natural-language rendering of propagation steps
- Natural-language rendering of case-split reasoning (explaining "we
  tried the remaining possibilities and only one was consistent" well,
  without sounding like a raw dump, is a harder writing problem — leave
  it for a later step)
- Puzzle generator, difficulty rating
- Any UI beyond terminal output

## Definition of done

- Structured `TacticStep` records exist and are populated correctly
  (Part 1), with a regression check confirming final answers for both
  puzzles are unchanged from Step 4.
- `render_tactic_step` produces a natural-language explanation
  substantively equivalent to the target example above, generated from
  data — not hardcoded per-puzzle text.
- Puzzle 1 output includes exactly one natural-language explanation (for
  Ada) and still shows Step 4-style output for Bo and the guilt values.
- Puzzle 2 output includes zero natural-language explanations, with an
  explicit statement of why (the tactic resolved nobody there).
- Code follows every rule in RULES.md.
