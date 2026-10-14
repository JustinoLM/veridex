See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 15 Spec

## Goal

Add generated puzzles to `play.py`'s menu, reusing the existing
generators from Steps 7-10 (`generate_puzzle`, `generate_whodunit_puzzle`
— already built, already verified). Right now `play.py` only offers the
2 hardcoded puzzles; this step makes every generation mode already in
the project playable, not just visible in `main.py`'s demo output.

**Explicitly excluded from this step (kept separate on purpose):**
- Extending `NAME_POOL` past 5 names
- Redesigning whodunit generation to support more than 2 people

Neither of those is touched here. Whodunit stays exactly 2 people (as
it already is); the N-person generator stays capped at what
`NAME_POOL` currently supports (5).

## Menu changes

Extend the existing menu with new options for each generation mode
already built:

```
Choose a puzzle to play:
  1. Whodunit (regression check from Step 1)
  2. The three-knave conditional
  3. Random puzzle (2 people)
  4. Random whodunit puzzle (2 people, with guilt)
  5. Random puzzle (choose how many people, 2-5)
  6. Random puzzle (richer logic: if/then, counting)
  q. Quit
```

For option 5, ask the player to pick a number of people between 2 and 5
(reject anything outside that range with a re-prompt — this is a hard
cap because it's exactly what `NAME_POOL` supports right now, not an
arbitrary choice).

Each generated option calls the corresponding existing generator
function, then feeds the resulting `Puzzle` into the same play loop
already built in Step 13 — no new game logic, just new sources of
puzzles.

## Generalize input collection (verify, don't assume)

Step 13's guess-collection logic needs to work for ANY puzzle shape now,
not just the two hardcoded ones. Check the current implementation:

- It must ask for a knight/knave guess for every person in
  `puzzle.people` — whatever that list actually is (2, 3, 4, or 5
  people), not a hardcoded `Ada`/`Bo` pair.
- It must ask for a guilty/innocent guess only if `"is_guilty"` is in
  `puzzle.attributes` — driven by the actual `Puzzle` data, not by
  checking which specific puzzle this is (e.g. not an `if this is
  Puzzle 1` check).

If the current code already works this way, confirm it explicitly
rather than assuming. If it's hardcoded to the two specific existing
puzzles in any way, generalize it — this is the same kind of check done
back in Step 6 for `_describe_fact`'s attribute-genericity.

## Puzzle presentation for generated puzzles

Generated puzzles don't have a fixed title like "Whodunit" or "The
three-knave conditional." Reuse `describe_generated_puzzle` (already
built in `generator.py`, already used by `main.py`'s demo output) for
consistent phrasing in `play.py`'s puzzle panel — don't write a new
description generator.

## Output requirements

- Every menu option (1-6) must be playable end to end: present the
  puzzle, collect the guess, check it, reveal the explanation, loop back
  to the menu.
- Since options 3-6 involve randomness, note in your summary when
  reporting back which generation mode you exercised for each option
  you tested — the exact puzzle content will differ run to run, that's
  expected (same as every other generated-puzzle output in this
  project).

## Out of scope for this step

- Extending `NAME_POOL`
- Whodunit generation beyond 2 people
- Difficulty selection before generating (still a separate future step)
- Persistence / avoiding repeat puzzles (still needs this step's play
  events to exist first, but isn't part of this step either)
- Any change to `main.py`

## Definition of done

- All 6 menu options are playable through the existing Step 13 game
  loop, unmodified in its core logic.
- Guess collection is confirmed (or fixed) to be driven by
  `puzzle.people`/`puzzle.attributes`, not hardcoded per-puzzle checks.
- Puzzle presentation for generated puzzles uses
  `describe_generated_puzzle`, not a new/duplicated description
  function.
- `main.py`'s output is unaffected.
- Code follows every rule in RULES.md.
