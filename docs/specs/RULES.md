# Project Rules

These rules apply across every step of this project, not just one spec.
Step-specific SPEC files reference this document instead of repeating
these rules.

## Language

All code, comments, docstrings, variable names, commit messages, and
printed output must be in English.

## Documentation & comments

- Heavy inline comments. Every function needs a docstring explaining its
  purpose, parameters, and return value.
- Non-obvious logic (especially anything involving search, backtracking,
  or constraint checking) needs comments explaining the *reasoning*, not
  just what the line mechanically does.

## Execution

- Do not run any command that executes project code (e.g. `uv run`,
  tests, or anything that runs the puzzle solver/generator/pipeline) to
  save on token usage. Instead, state exactly which command should be
  run and why, then wait for the user to run it and report the result
  back before proceeding.
- Read-only inspection commands (e.g. `grep`, `cat`, `ls`, viewing file
  contents) are fine to run directly when they help you verify or
  navigate the codebase — these don't execute project logic or consume
  meaningful resources. The line is: does this command run the
  project's own code, or does it just look at files?

## Code style

- Prefer simple, readable code over clever code. Each step is a
  foundation for the next one, not a final product — don't over-engineer
  ahead of what the current step actually needs.
