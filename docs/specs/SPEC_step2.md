See RULES.md for project-wide conventions (language, commenting, execution
rules, attribution, subagent usage).

# Knights & Knaves Solver — Step 2 Spec

## Goal

Replace the hardcoded lambda-based statements from Step 1 with a proper
expression tree (AST), and generalize the solver so it works for any
number of people, any set of boolean attributes per person, and any
combination of logical connectives — not just the one puzzle from Step 1.

Prove this works by:
1. Re-implementing the Step 1 puzzle using the new AST and confirming it
   produces the exact same numbers as before (regression check).
2. Implementing a second, harder puzzle that Step 1's plain-function
   approach could not express cleanly (it needs a conditional and
   counting constraints), to prove the AST generalizes.

## Expression tree (AST) design

Define each node as its own class (dataclasses are fine, and enable
pattern matching in the evaluator — see below).

**Atomic nodes** (reference one person's attribute):
- `IsKnight(person)`
- `IsKnave(person)`
- `IsGuilty(person)`
- `IsInnocent(person)`

**Logical connectives:**
- `And(*exprs)` — variadic, true iff all are true
- `Or(*exprs)` — variadic, true iff at least one is true
- `Not(expr)`
- `Implies(antecedent, consequent)` — standard material implication
  (true whenever the antecedent is false, regardless of the consequent)
- `Iff(left, right)` — true iff both sides have the same truth value
  (used for "X and Y are the same type")

**Counting nodes** (used for statements like "exactly two of us are
knaves" or "at least one of them is a knave"):
- `ExactlyN(n, exprs)`
- `AtLeastN(n, exprs)`
- `AtMostN(n, exprs)`

Keep the node set exactly to what the two puzzles below require. Do not
add node types you don't have a concrete use for yet.

## Evaluator

Write a single recursive function:

```python
def evaluate(expr: Expr, assignment: dict) -> bool
```

`assignment` maps `(person, attribute)` pairs to booleans, same as Step 1
— this step does NOT need three-valued/partial evaluation, since the
solver still enumerates full candidate assignments via brute force. Keep
the evaluator two-valued for now.

Use structural pattern matching (`match expr: case IsKnight(person): ...`)
for dispatch — it's the readable, idiomatic choice for this kind of
recursive tree walk in Python 3.11+, and it's a natural fit if the node
classes are dataclasses.

## Generalized puzzle representation

Introduce a `Puzzle` data structure that holds everything the solver
needs, so `solver.py` no longer has any puzzle-specific code in it:

```python
@dataclass
class Puzzle:
    name: str
    people: list[str]
    attributes: list[str]        # e.g. ["is_knight"] or ["is_knight", "is_guilty"]
    statements: dict[str, Expr]  # person -> their statement as an Expr
    constraints: list[Expr]      # must ALL evaluate True for a valid assignment
```

The solver becomes a generic function that takes a `Puzzle` and:
1. Enumerates all `2^(len(people) * len(attributes))` candidate
   assignments.
2. Filters by constraints.
3. Filters by knight/knave statement consistency (a person's statement
   must evaluate to their `is_knight` value).
4. Returns the list of valid assignments (ideally exactly one).

## Puzzles to implement

### Puzzle 1 — regression check (from Step 1)

Same puzzle, same people (Ada, Bo), same attributes (`is_knight`,
`is_guilty`), same constraint and statements, now expressed as `Expr`
trees instead of lambdas.

**Expected output must exactly match Step 1's numbers:**
- 16 total candidate assignments
- 8 pass the constraint
- 1 passes full validation
- Solution: Ada = knave/innocent, Bo = knight/innocent

If these numbers don't match Step 1's original output, something is
wrong with the AST or evaluator — treat that as a bug, not an acceptable
discrepancy.

### Puzzle 2 — new case (proves the AST generalizes)

Three people: Ada, Bo, Cal. Only one attribute: `is_knight` (no guilt
axis in this puzzle).

**Constraint:** At least one of them is a knave.

**Statements:**
- Ada: "Cal is a knave, and Cal and Bo are the same type."
- Bo: "If at least two of us are knaves, then all of us are knaves."
- Cal: "None of us are knaves, or exactly two of us are knaves."

**Expected output:**
- 8 total candidate assignments
- 7 pass the constraint
- 1 passes full validation
- Solution: Ada = knave, Bo = knave, Cal = knight

## Project structure

```
veridex/
├── pyproject.toml
├── README.md
├── SPEC.md
├── RULES.md          (gitignored, not part of the repo)
├── expressions.py    (AST node classes + evaluate())
├── puzzles.py         (Puzzle dataclass + the two Puzzle instances)
├── solver.py           (generic brute-force solve(puzzle) function)
└── main.py              (runs both puzzles, prints results)
```

`solver.py` from Step 1 should no longer contain any puzzle-specific
logic — that all moves to `puzzles.py`. `main.py` becomes the new
entry point (`uv run main.py`).

## Output requirements

For each puzzle, print (same explanatory style as Step 1, generalized):
- Puzzle name, people, constraint(s), and statements in plain language
  at the start.
- Total candidates checked, how many passed constraints, how many passed
  full validation.
- The final solution stated in plain language.

Additionally, explicitly print a line confirming Puzzle 1's numbers match
Step 1's original output (e.g. "Regression check: matches Step 1 output ✓"),
since that's a specific goal of this step, not just an implicit hope.

## Out of scope for this step

- Three-valued/partial evaluation (needed later for the explainer, not
  for brute-force solving)
- The step-by-step natural-language explainer itself
- Puzzle generator
- Difficulty rating
- `WouldSay` / nested-statement node type (not needed by either puzzle
  in this step — add it later if a puzzle actually needs it)

## Definition of done

- `uv run main.py` executes with no errors.
- Puzzle 1 output numbers exactly match Step 1's original output.
- Puzzle 2 output matches the expected numbers and solution above.
- `solver.py` contains no puzzle-specific code — it works purely off the
  `Puzzle` data structure.
- Code follows every rule in RULES.md (language, comments, attribution,
  execution, subagent usage).
