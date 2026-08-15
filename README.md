# Veridex

A brute-force solver for Knights & Knaves logic puzzles.

In a Knights & Knaves puzzle, each person is either a knight (always tells
the truth) or a knave (always lies). Given a set of statements made by each
person, the goal is to figure out who is which. Statements are expressed as
an expression tree (see `expressions.py`), and puzzles (see `puzzles.py`)
declare their people, attributes, statements, and constraints as data - the
solver itself (`solver.py`) contains no knowledge of any specific puzzle.

The solver works by enumerating every possible combination of attributes for
everyone involved, then discarding any combination that isn't logically
consistent with the puzzle's constraints and statements. What's left is the
solution.

## Running it

This project uses [uv](https://docs.astral.sh/uv/) for dependency
management. There are no external dependencies, so you can run it directly:

```sh
uv run main.py
```

That's it — no install step, no virtual environment setup required. The
script prints each puzzle, walks through how many candidate assignments were
checked and how many survived each filtering step, prints the final
brute-force solution in plain language, then runs a small set of standalone
checks on the propagation function (including natural-language renderings of
a few of them), and finally runs the full deduction pipeline against each
puzzle - printing a natural-language explanation for every resolved value,
regardless of which of the three techniques actually resolved it.

## Scope

This is the seventh step of a larger project. The solver still brute-forces
every puzzle as in Step 2. Step 3 added a three-valued evaluator (True /
False / Unknown) and one deduction tactic on top of it - hypothesize each
person's knight/knave status and check whether either hypothesis leads to a
contradiction. Step 4 combined that tactic with two more techniques into a
pipeline that fully solves both puzzles end to end:

- The Step 3 tactic, unchanged.
- Backward propagation: given an expression's required truth value, derive
  forced values for its sub-expressions wherever there is exactly one
  consistent option.
- Case-split fallback: once the tactic and propagation stop making
  progress, brute-force only whatever (person, attribute) values are still
  unknown and check full consistency on each possible completion.

Propagation happens to contribute zero new facts on both of this project's
puzzles - that was verified before writing the pipeline, and the printed
output says so explicitly rather than hiding it. It is still exercised
directly by a set of standalone checks, independent of either puzzle.

Steps 5 and 6 added natural-language rendering on top of all three
techniques, so every resolved value in both puzzles now comes with a plain-
language explanation instead of a raw structured summary:

- The tactic's hypothesize-and-check contradiction (Step 5).
- Propagation's "this was the only way left to satisfy that requirement"
  reasoning (Step 6) - validated against the standalone propagation checks,
  since neither puzzle's real trace happens to force anything this way.
- Case-split's exhaustive-checking fallback (Step 6), explained honestly as
  what it is - not a clever deduction, but a systematic check of every
  remaining combination - along with the winning combination, a per-person
  consistency confirmation, and one concrete rejected combination as a
  counterexample.

Step 7 adds a puzzle generator (`generator.py`), so new puzzles no longer
have to be hand-written. It builds random two-person statements out of the
same And/Or/Iff/IsKnight/IsKnave building blocks the hand-written puzzles
use, then discards and retries candidates until the Step 2 brute-force
solver confirms one has exactly one valid solution. The full Step 3-6
deduction pipeline then runs against each generated puzzle completely
unmodified - confirming that pipeline was always genuinely generic, rather
than something that happened to work only because it was tuned against
Puzzle 1 and Puzzle 2's specific shape.

Not included yet (planned for later steps):

- Backward propagation for "exactly N" / "at least N" / "at most N"
  counting constraints
- Smarter case-split ordering/heuristics
- A unified "explain the whole puzzle as one flowing narrative" mode,
  rather than one explanation per resolved value printed in sequence
- A guilt axis, global constraints, or a richer statement grammar
  (`Implies`, counting nodes) in generated puzzles
- Generated puzzles with more than two people
- Difficulty rating or deduplication for generated puzzles
- Any interface beyond terminal output
