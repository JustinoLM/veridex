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
regardless of which of the three techniques actually resolved it, and a
structural `Difficulty:` rating for the puzzle as a whole, ending with a
summary tallying every puzzle's difficulty across the whole run.

## Scope

This is the ninth step of a larger project. The solver still brute-forces
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

Step 8 extends the generator to a second mode: whodunit puzzles, matching
Puzzle 1's shape. Both people get `is_knight` and `is_guilty` attributes,
their statements can mix claims about either one, and a randomly generated
global constraint over guilt (also And/Or/Iff-built) is added on top.
Uniqueness is still checked the same way, via the Step 2 brute-force
solver, and the full Step 3-6 pipeline runs against each generated
whodunit puzzle completely unmodified, same as Step 7's puzzles. Step 7's
is_knight-only generator is unchanged and still runs alongside it.

Step 9 generalizes the `is_knight`-only generator to more than two people.
The random statement builder already worked for any number of people; the
generator function itself was the part actually fixed to exactly two, so
that was the one thing changed - it now takes the people list as a
parameter instead of hardcoding it. Acceptance rate for a well-posed
puzzle stays roughly stable as people are added (checked directly, not
assumed), so the demonstration puzzle for this step uses four people -
noticeably bigger than anything generated so far, while `2^4 = 16`
candidate assignments keeps brute-force verification instant. The
whodunit generator from Step 8 stays at exactly two people: extending it
was tested by simulation and found to scale very badly, since a single
random constraint doesn't get proportionally more constraining as more
people are added. That is left for a future step that can generate
constraints more deliberately, not forced into this one.

Step 10 extends the is_knight-only generator's grammar - and only that
generator, not the whodunit one - to include `Implies` and counting
nodes (`ExactlyN`/`AtLeastN`/`AtMostN`) alongside `And`/`Or`/`Iff`: the
exact connectives this whole project was originally motivated by (the
vacuous-truth-of-implication gap found in the competing app, and the
"exactly N knaves" style reasoning from Puzzle 2). A counting node is
generated as a terminal wrapping a random subset of people's `IsKnave`
claims, matching how Puzzle 2's hand-written statements already use
counting nodes, rather than nesting further sub-expressions inside one.
Calibration by simulation found the richer grammar performs slightly
better than the plain grammar, not worse - a vacuously-true `Implies`
doesn't hurt uniqueness. The richer grammar is opt-in, via an
`allow_rich_grammar` flag on `random_statement()` and `generate_puzzle()`
that defaults to False: only the new Step 10 demonstration puzzles pass
True, so the Step 7 and Step 9 demonstration puzzles keep generating
with the original And/Or/Iff-only grammar, unchanged from before this
step. This step also confirms `propagate()` (Step 4) never actually
crashes when it reaches a counting node mid-traversal: it was always
written to skip them safely, but neither hand-written puzzle's trace
had ever exercised that path, so an explicit check now covers it
directly (see `run_propagation_checks()` in `main.py`).

Step 11 adds a structural difficulty classification (`classify_difficulty()`
in `solver.py`) on top of every puzzle the program already runs - not a
message-based rating like Glicko-2, which would need real user play data
this project doesn't have, but a rating grounded purely in which of the
three deduction techniques a puzzle's own resolution actually needed:
`EASY` if the Step 3 tactic alone resolved everything, `MEDIUM` if
propagation was also needed but the case-split fallback never was, and
`HARD` if case-split was needed for at least one value, which overrides
the other two tiers regardless of how much the tactic or propagation
contributed first. Every puzzle's output now prints its own
`Difficulty:` line, and the program ends with a summary tallying every
tier across everything it ran, plus explicit PASS/WARNING checks against
three specific expectations from SPEC_step11.md.

Puzzle 1 and Puzzle 2, both hand-written and deterministic, reliably
classify as `HARD` on every run - both were already known to need
case-split, back in Step 4. The generated puzzles are not deterministic:
none of the generators fix a random seed, so the *specific* instance
produced for a given demo (e.g. Step 9's 4-person puzzle) varies from
run to run, and its difficulty can vary right along with it.
SPEC_step11.md expected Step 9's demo to classify as `EASY`, based on an
earlier observed run; a run performed while validating this step instead
produced a 4-person instance where propagation genuinely forced one
additional fact after the tactic resolved the rest - a real `MEDIUM`,
not a classifier bug, and the end-of-program summary's expectation check
flagged it with a `WARNING` rather than silently claiming a match that
wasn't there. That WARNING is expected to appear on some runs, not only
that one - it is exactly the "flag it rather than silently accepting a
number that doesn't match" honesty SPEC_step11.md asks for, applied to a
generator that was never seeded to be reproducible in the first place.

`MEDIUM` overall is not necessarily rare either: that same validation
run saw it 3 times out of 12 puzzles - a whodunit puzzle propagating
straight from its global constraint, the Step 9 puzzle above, and a
rich-grammar puzzle propagating through an `Implies` - genuine cases
where propagation contributed once puzzles started drawing from a
richer statement pool than the two original hand-written puzzles. On a
different run, with different randomly generated puzzles, that count
could just as easily come out at 0; the summary reports whatever
actually happened for that run rather than assuming either outcome.

## Known quirks

The random statement/constraint generator can occasionally produce a
redundant sub-clause - the same leaf appearing twice under a nested
And/Or - since at low depth there are only a handful of possible leaves
to choose from (e.g. just 4 for a guilt-only constraint), and two
independent recursive branches can land on the same one by chance. This
does not affect correctness: the solver evaluates the expression tree
itself, not the rendered English text, so a repeated clause has no
effect on the puzzle's solution.

Not included yet (planned for later steps):

- Backward propagation for "exactly N" / "at least N" / "at most N"
  counting constraints
- Smarter case-split ordering/heuristics
- A unified "explain the whole puzzle as one flowing narrative" mode,
  rather than one explanation per resolved value printed in sequence
- `Implies` or counting nodes in the whodunit generator's grammar or in
  generated global constraints - only the `is_knight`-only generator's
  per-person statements have them, as of Step 10
- Generated `is_knight`-only puzzles with more than five people (not
  calibrated)
- Generated whodunit puzzles with more than two people (see Step 9 above)
- Deduplication for generated puzzles (difficulty rating was added in
  Step 11)
- Sub-tiers within `HARD`, or any calibration of the difficulty
  classification against real user performance (see SPEC_step11.md for
  why that's explicitly out of scope)
- Any interface beyond terminal output
