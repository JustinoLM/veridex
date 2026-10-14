# Step specs

Veridex was designed one step at a time. Before each step was implemented,
a short spec defined its goal, its scope, what was explicitly out of scope,
and what "done" meant. [RULES.md](RULES.md) holds the conventions shared by
every step.

These are the specs as they were written at each step, not rewritten
afterwards, so some details (the file tree, module and function names)
reflect the project at that moment rather than its current layout. For the
current structure, see the [main README](../../README.md).

Subagent usage is described in SPEC_step1.md (Execution approach), not in RULES.md.

| Step | Spec | What it adds |
|---|---|---|
| 1 | [SPEC_step1.md](SPEC_step1.md) | Brute-force solver for a single hard-coded puzzle |
| 2 | [SPEC_step2.md](SPEC_step2.md) | Expression tree (AST) and a puzzle-agnostic solver, with a regression check against Step 1 |
| 3 | [SPEC_step3.md](SPEC_step3.md) | Three-valued (True / False / Unknown) evaluator and the hypothesize-and-check tactic |
| 4 | [SPEC_step4.md](SPEC_step4.md) | Backward propagation and case-split fallback, combined into a pipeline that fully solves both puzzles |
| 5 | [SPEC_step5.md](SPEC_step5.md) | Natural-language explanations for the tactic's steps |
| 6 | [SPEC_step6.md](SPEC_step6.md) | Natural-language explanations for propagation and case-split |
| 7 | [SPEC_step7.md](SPEC_step7.md) | Random puzzle generator that verifies each puzzle has exactly one solution |
| 8 | [SPEC_step8.md](SPEC_step8.md) | Whodunit-style generator (guilt axis plus a random global constraint) |
| 9 | [SPEC_step9.md](SPEC_step9.md) | Knight-only generator extended to more than two people |
| 10 | [SPEC_step10.md](SPEC_step10.md) | Generator grammar extended with `Implies` and counting nodes |
| 11 | [SPEC_step11.md](SPEC_step11.md) | Structural difficulty classification (EASY / MEDIUM / HARD) |
| 12 | [SPEC_step12.md](SPEC_step12.md) | Split the monolithic `main.py` into cohesive modules, with no behavior change |
| 13 | [SPEC_step13.md](SPEC_step13.md) | Interactive play loop: guess first, then see the explanation |
| 14 | [SPEC_step14.md](SPEC_step14.md) | Terminal presentation with `rich` (panels, colors, styled prompts) |
| 15 | [SPEC_step15.md](SPEC_step15.md) | Generated puzzles in the game menu (specified, not implemented yet) |
