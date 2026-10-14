# Knights & Knaves Solver — Step 1 Spec

## Goal

Build a minimal, working brute-force solver for a single hardcoded Knights &
Knaves puzzle. This is the first step of a larger project, so keep scope
tight: no generator, no AST, no explainer engine yet. Just prove the core
logic works end to end.

## Project setup

- Use `uv` for dependency management (`pyproject.toml`, no `requirements.txt`).
- Python 3.11+.
- Project structure:

```
veridex/
├── pyproject.toml
├── README.md
└── solver.py
```

- The project should run with `uv run solver.py` with zero extra setup steps.

## The puzzle to hardcode

This is a "whodunit" variant: two co-defendants, Ada and Bo, are each either
a knight (always truthful) or a knave (always lies). They are also each
either guilty or innocent of a crime.

**Constraint:** If anyone is guilty, all co-defendants are guilty (i.e.
guilt is all-or-nothing between Ada and Bo).

**Statements:**
- Ada: "I am a knave, and none of us are innocent."
- Bo: "Ada and I are either both guilty or both innocent."

**Expected unique solution:** Ada = knave, innocent. Bo = knight, innocent.

## Functional requirements

1. Represent each person's two independent boolean attributes explicitly:
   - `is_knight: bool` (True = knight, False = knave)
   - `is_guilty: bool`
2. Encode each person's statement as a function that takes the full
   candidate assignment (for all people) and returns whether the statement
   is true under that assignment. Do not use a generic AST or expression
   parser yet — plain Python functions/lambdas over the assignment are
   correct for this step.
3. Brute-force all possible assignments (2^4 = 16 combinations for 2 people
   × 2 attributes each). For each candidate assignment:
   - Check the "all-or-nothing guilt" constraint holds.
   - Check that each person's statement truth value matches their knight/
     knave status (knights' statements must be true, knaves' statements
     must be false).
4. Collect all assignments that pass every check.
5. Print:
   - The full solution if exactly one valid assignment is found.
   - A clear warning if zero or more than one valid assignment is found
     (this would indicate a bug, since this puzzle is known to have a
     unique solution).

## Output requirements

The script's printed output must clearly explain what it's doing, not just
dump a final answer. At minimum, print:

- The puzzle statement (people, constraint, statements) at the start.
- How many total candidate assignments were checked.
- How many passed the constraint check vs. failed.
- How many passed the full check (constraint + statement consistency).
- The final solution, stated in plain language (e.g. "Ada is a knave and
  is innocent. Bo is a knight and is innocent.").

This output should read like a small, self-contained explanation — someone
with no context should be able to run the script and understand both the
puzzle and why the answer is correct.

## Code quality requirements

- Heavy inline comments. Every function needs a docstring explaining its
  purpose, parameters, and return value. Non-obvious lines (especially the
  brute-force loop and constraint checks) need comments explaining the
  reasoning, not just what the line does mechanically.
- All code, comments, docstrings, variable names, and printed output must
  be in English.
- Keep the implementation simple and readable over clever. This is a
  foundation to build on, not a final product.

## Execution approach

To keep context usage efficient, use subagents/background agents for
mechanical or exploratory work (e.g. scaffolding the project structure,
running/verifying `uv run` works, checking output formatting) rather than
doing everything in the main thread. Reserve the main thread for decisions
that actually require judgment (puzzle logic correctness, code structure).

Do not run shell commands directly (e.g. `uv run`, tests, greps for
verification) to save on token usage. Instead, state exactly which
command should be run and why, and let the user run it and report the
result back.

## Out of scope for this step

Do not build any of the following yet — they come later:
- Generic AST/expression representation for statements
- Puzzle generator
- Step-by-step natural-language explainer/deduction engine
- Difficulty rating
- Any UI beyond terminal output
- Support for more than this one hardcoded puzzle

## Definition of done

- `uv run solver.py` executes with no errors.
- Output correctly identifies the unique solution (Ada: knave/innocent,
  Bo: knight/innocent) with the explanatory output described above.
- Code is heavily commented and entirely in English.
