# Veridex

A brute-force solver for Knights & Knaves logic puzzles.

In a Knights & Knaves puzzle, each person is either a knight (always tells
the truth) or a knave (always lies). Given a set of statements made by each
person, the goal is to figure out who is which. This step solves a single,
hardcoded "whodunit" variant: two co-defendants, Ada and Bo, are each also
either guilty or innocent of a crime, and the puzzle is to determine both
their knight/knave status and their guilt from what they say.

The solver works by enumerating every possible combination of attributes for
everyone involved, then discarding any combination that isn't logically
consistent with the puzzle's constraints and statements. What's left is the
solution.

## Running it

This project uses [uv](https://docs.astral.sh/uv/) for dependency
management. There are no external dependencies, so you can run the solver
directly:

```sh
uv run solver.py
```

That's it — no install step, no virtual environment setup required. The
script prints the puzzle, walks through how many candidate assignments were
checked and how many survived each filtering step, and ends with the final
solution in plain language.

## Scope

This is the first step of a larger project. Right now the solver only
handles one puzzle, hardcoded directly in `solver.py`, with statements
written as plain Python functions.

Not included yet (planned for later steps):

- A generic representation (e.g. an AST) for statements, instead of raw
  Python functions
- A puzzle generator, so new puzzles don't have to be hand-written
- A step-by-step natural-language explainer/deduction engine
- Difficulty rating for generated puzzles
- Any interface beyond terminal output
- Support for puzzles with more than two people
