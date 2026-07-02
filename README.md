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
checked and how many survived each filtering step, and ends with the final
solution in plain language.

## Scope

This is the second step of a larger project. The solver now handles any
number of people, any set of boolean attributes per person, and any
combination of logical connectives - not just one hardcoded puzzle.

Not included yet (planned for later steps):

- Three-valued/partial evaluation of statements
- A puzzle generator, so new puzzles don't have to be hand-written
- A step-by-step natural-language explainer/deduction engine
- Difficulty rating for generated puzzles
- Any interface beyond terminal output
