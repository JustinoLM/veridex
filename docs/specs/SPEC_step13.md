See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 13 Spec

## Goal

Add a real interactive play loop: present a puzzle without its solution,
let the player guess each person's type (and guilt, for whodunit
puzzles) via terminal input, check their guess against the real answer,
and only THEN reveal the full natural-language explanation already built
in Steps 3-6. Right now the program computes and prints everything for
every puzzle at once — this step is what actually makes it playable.

## New entry point, not a replacement

Add a new file, `play.py`, as a separate interactive entry point
(`uv run play.py`). **Do not modify `main.py`'s existing behavior** —
it stays exactly as it is (a full demonstration/regression run of every
puzzle and every generation mode). `play.py` imports from the existing
modules (`expressions.py`, `puzzles.py`, `solver.py`, `deduction.py`,
`rendering.py`) and reuses `run_deduction_pipeline` from `main.py` for
the reveal step — don't duplicate that logic.

## Scope: the two hardcoded puzzles only

Use the existing `Puzzle 1` (whodunit) and `Puzzle 2` (three-knave
conditional) instances from `puzzles.py`. **Do not wire in generated
puzzles in this step** — prove the play loop works on puzzles that are
already fully verified before connecting it to generation, which is its
own follow-up step.

## Play loop

1. **Menu**: ask the player to choose Puzzle 1, Puzzle 2, or quit.
2. **Present the puzzle**: print the people, their statements, and any
   constraint — the same plain-language description already used
   elsewhere in the project. Do NOT print the solution or run the
   deduction pipeline yet.
3. **Collect the guess**: for each person, ask via `input()` whether
   they're a knight or a knave (accept a couple of reasonable input
   forms, e.g. `knight`/`k` and `knave`/`n`, case-insensitive). For
   Puzzle 1 specifically (which has a guilt axis), also ask guilty/
   innocent for each person.
4. **Validate input defensively**: if the player types something
   unrecognized, re-prompt for that same question rather than crashing
   or silently guessing. This is now real interactive code — it must
   not raise an uncaught exception on unexpected input.

   **Scoped exception to RULES.md's execution rule, for this
   requirement only:** testing invalid-input handling by asking the
   user to manually type garbage input and report back is impractical
   here. As an exception, you may run `play.py` directly (e.g. with
   piped/scripted stdin — feeding a sequence like `asdf`, `knight`,
   `xyz`, `n`, etc. — via a command like
   `echo "..." | uv run play.py`) specifically to verify the re-prompt
   behavior on bad input for both the menu and the guess-collection
   steps. This exception is scoped narrowly to validating this one
   requirement in this step. It does not extend to running `play.py`
   or any other project code for any other purpose — go back to
   handing off commands for everything else, including the final
   full walkthrough of a normal (valid-input) play session.
5. **Check the guess**: compute the actual solution using the existing
   solver (already correct, already regression-tested), compare it
   against the player's answers person by person.
6. **Report the result**: state clearly, per person, whether their
   guess was right or wrong, and whether they got the whole puzzle
   fully correct.
7. **Reveal the explanation**: regardless of whether they got it right,
   call `run_deduction_pipeline` (or equivalent) to print the full
   tactic/propagation/case-split explanation now — this is the payoff,
   and it should look the same as it already does in `main.py`'s output
   for these two puzzles.
8. **Loop**: after finishing a puzzle, return to the menu (play another,
   or quit) rather than exiting immediately.

## Out of scope for this step

- Wiring generated puzzles into the play loop (a natural next step, not
  this one)
- Difficulty selection
- Persistence / not repeating solved puzzles (this needs solved-events
  to exist first, which is exactly what this step creates — the next
  logical step, not this one)
- Partial hints (revealing one deduction step at a time before the
  player finishes guessing) — this step reveals everything at once,
  after the full guess
- Any change to `main.py`'s existing behavior or output

## Definition of done

- `uv run play.py` presents a working menu, lets the player choose a
  puzzle, and never shows the solution or explanation before the player
  has answered.
- Invalid input is handled gracefully (re-prompt, no crash) for both
  the menu and the guess-collection steps.
- The player's guess is checked correctly against the real solution for
  both Puzzle 1 and Puzzle 2.
- After answering, the full natural-language explanation is printed
  using the existing `run_deduction_pipeline` logic — not reimplemented.
- The loop returns to the menu after each puzzle instead of exiting.
- `main.py`'s existing output is completely unaffected by this step.
- Code follows every rule in RULES.md.
