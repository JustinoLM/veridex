See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 14 Spec

## Goal

Improve `play.py`'s terminal presentation using the `rich` library —
panels, color, and styled prompts instead of raw `print()`/`input()`.
Purely visual. No change to game logic, puzzle content, or the
underlying deduction pipeline.

**Why `rich` and not `textual`:** `textual` requires restructuring the
interaction model into an event-driven TUI app — a much bigger rewrite
than this step calls for. `rich` layers styling onto the existing
`input()`/`print()` flow from Step 13 without changing how the loop
works. Use `rich` only.

## Dependency

Add `rich` via `uv add rich` (state this command for the user to run —
per RULES.md, don't run it yourself).

## What to restyle in `play.py`

- **Menu**: render the puzzle choices in a `rich.panel.Panel` or styled
  table, not plain print lines.
- **Puzzle presentation**: put the puzzle description (people,
  statements, constraint) in a bordered `Panel` with a title. Style
  person names consistently (e.g. bold) so they stand out from
  surrounding text.
- **Guess collection**: use `rich.prompt.Prompt` (or `Confirm`) for
  input instead of raw `input()`, so invalid-input re-prompting (from
  Step 13) gets consistent, styled formatting rather than a bare
  re-print of the question.
- **Result feedback**: color-code correctness — green for a correct
  per-attribute guess, red for incorrect — matching the existing
  "CORRECT"/"INCORRECT" structure from Step 13, not replacing its
  logic.
- **Explanation reveal**: give the tactic / propagation / case-split
  sections distinct visual treatment (e.g. different panel titles or
  accent colors per technique) so a player can visually tell which
  technique explains which resolved value, reinforcing the distinction
  Step 6 already worked to make clear in the text itself.

## What NOT to change

- **`main.py` stays exactly as it is** — no `rich` import, no styling,
  no output changes. It remains the plain-text demonstration/regression
  suite. Do not let any refactor of shared logic accidentally change
  what `main.py` prints.
- **No change to game logic**: the menu options, guess validation
  rules, correctness checking, and which puzzles are playable are all
  unchanged from Step 13. This step only changes how things look.
- **No change to the deduction pipeline's actual content** — the
  natural-language explanations themselves (from `rendering.py`) stay
  exactly as written. This step wraps them in better presentation, it
  doesn't rewrite them.

## Output requirements

Since this is a visual change, describe (in your summary when reporting
back) what the improved output looks like structurally — which parts
are now panels, what's colored, how the menu renders — since a plain
text pass/fail check doesn't capture whether the presentation is
actually better. The user will run `play.py` themselves to see it.

## Out of scope for this step

- `textual` or any event-driven TUI rewrite
- Wiring generated puzzles into `play.py` (still a separate future step)
- Any change to the difficulty classifier or the human-perceived-
  difficulty question raised after Step 13's playtest
- Sound, animation, or anything beyond static terminal styling

## Definition of done

- `play.py` uses `rich` for the menu, puzzle presentation, guess
  collection, result feedback, and explanation reveal.
- `main.py`'s output is provably unchanged (confirm no `rich` usage
  leaked into it, and its plain-text output still matches prior runs).
- All of Step 13's game logic (validation, correctness checking, loop
  behavior) is unchanged — only presentation differs.
- Code follows every rule in RULES.md.
