# Dev Protocol — Scope, DoD and Handoff

This reference expands the Dev workflow in `SKILL.md`. It assumes the task bundle format is
`tasks/<task-id>/` with `01-contract.md`, `02-dev-workspace.md`,
`03-qa-verification.md` and `04-process.md`.

## 1. Read the contract first

`01-contract.md` starts with YAML frontmatter, which is authoritative:

| Key | Dev use |
| :--- | :--- |
| `task_id` | Must equal the directory name. |
| `touch_files` | The complete blast radius; nothing else may be created or modified. |
| `estimated_lines` | A planning budget, not a target to pad. |
| `origin_spec_anchor`, `adherence_adrs` | Traceability; read the referenced spec/ADRs before coding. |
| `dod` | The exact commands and edge cases that must pass before handoff. |

If a required input is missing or contradictory, stop and report it. Do not fill gaps with
assumptions.

## 2. Verify the scope

Before editing, compare the contract with the working tree. A typical check:

```bash
git status --short
git diff --name-only <base>...HEAD
```

Every changed path must appear in `touch_files`. If the implementation needs another path:

- split the task and ask the Planner to add a contract, or
- escalate to the owner if the contract is wrong.

Never widen the scope silently. Acceptance tests under `tests/acceptance/` are QA-owned; Dev runs
them but does not create or edit them.

## 3. Implement and verify

1. Implement the smallest end-to-end vertical slice that satisfies the contract.
2. Run in this order: type check → lint → existing project tests → edge-case checks → cyclomatic
   complexity self-audit ($V(G) \le 10$). Use the exact `dod.type_check`/`dod.lint` commands, not
   equivalents you invented. `dod.test_file` is the QA-owned acceptance target: run it only if it
   already exists; never create or edit `tests/acceptance/**`.
3. Capture the command and result for `02-dev-workspace.md`. If the acceptance target is not
   authored yet, record that and leave acceptance execution to QA. If a command cannot run, report
   the command and error instead of omitting the check.
4. If a DoD command fails or any function violates complexity limits, fix or refactor the
   implementation and rerun. Do not tick the handoff box early.

## 4. Cyclomatic complexity control and refactoring patterns

Every function implemented or modified in `touch_files` must be evaluated for cyclomatic
complexity to guarantee maintainability, bounded blast radius, and testability.

### 4.1. Definition and calculation

McCabe Cyclomatic Complexity $V(G)$ quantifies the number of linearly independent execution paths
through a function's control flow graph:

$$V(G) = E - N + 2P$$

where:
- $E$ is the number of edges in the control flow graph.
- $N$ is the number of nodes (basic blocks).
- $P$ is the number of connected components ($P = 1$ for a single function: $V(G) = E - N + 2$).

In practice across modern programming languages, $V(G)$ equals the number of decision points
plus one:

$$V(G) = 1 + D$$

Decision points ($D$) include:
- Conditional branching statements: `if`, `elif` / `else if`.
- Conditional / ternary expressions: `x if cond else y`, `cond ? a : b`.
- Loop constructs: `for`, `while`, `async for`.
- Pattern matching / switch case statements: each `case` / `match` pattern arm.
- Exception handlers: `catch` / `except`.
- Short-circuiting boolean operators: `&&`, `||`, `and`, `or`.
- Explicit assertion statements: `assert`.

### 4.2. Strict thresholds

| Complexity Range | Classification | Action Required |
| :--- | :--- | :--- |
| $V(G) \le 10$ | **Standard** | Approved for production without exception. Represents modular, low-risk logic easily verified by independent paths. |
| $11 \le V(G) \le 15$ | **Warning** | Requires explicit architectural justification in `02-dev-workspace.md` Section 2 ("Implementation notes"). Dev must explain why further decomposition would harm cohesion or readability and confirm basis path coverage. |
| $V(G) > 15$ | **Critical** | Strictly prohibited. Dev must refactor the function into smaller, decoupled units before requesting QA. Handoff with $V(G) > 15$ triggers immediate rejection. |

### 4.3. Standard refactoring patterns

When a function approaches or exceeds the warning threshold, apply these standard patterns:

1. **Extract Method / Decomposition**:
   Split compound algorithms into discrete helper functions with single responsibilities. Each
   extracted helper has its own localized $V(G) \le 10$, reducing cognitive load and isolating
   independent execution paths.

2. **Strategy / Lookup Table Dispatch**:
   Replace deeply nested `if-elif-else` chains or expansive `switch/case` trees with a dictionary
   or map mapping dispatch keys to handler callables or strategy classes. This transforms an $O(N)$
   branching cascade into an $O(1)$ lookup with $V(G) \le 2$.

3. **Guard Clauses / Early Return**:
   Invert nested conditionals. Validate input preconditions, boundary constraints, and error
   states at the beginning of the function and return or raise immediately. This flattens deep
   indentation and eliminates pyramid code structures.

4. **Polymorphism / State Pattern**:
   When branching repeatedly on type tags, status enums, or lifecycle phases, encapsulate
   state-dependent behavior within polymorphic subclasses or state objects instead of cascading
   conditional checks.

### 4.4. Dev-QA handshake

Before handing off the task bundle:
1. **Dev self-audit**: Dev audits the cyclomatic complexity of every function in `touch_files`
   (using static analysis tooling or control flow graph inspection).
2. **Document in 02**: Any function in the warning range ($11 \le V(G) \le 15$) must be accompanied
   by an architectural justification in `02-dev-workspace.md` Section 2.
3. **QA verification contract**: QA calculates $V(G)$ for each modified function and verifies that
   the acceptance test suite contains at least $V(G)$ independent basis path test cases. Any
   function with $V(G) > 15$ or an unjustified $V(G) \ge 11$ results in `REWORK_REQUIRED`.

## 5. Fill `02-dev-workspace.md`

The template is a blank role form; fill these sections in place:

- **Execution metadata**: Dev agent, branch, base commit, handoff commit, handoff time (UTC).
- **Implementation notes**: design decisions, trade-offs, architectural justification for any
  functions with warning complexity ($11 \le V(G) \le 15$), and deviations from the plan.
- **Actual changes**: one row per changed file with action, path and approximate lines; net lines
  added/removed. Every path must be in `touch_files`.
- **Implementation deviations**: one row per place where the implementation differs from the
  contract or the spec. Frozen format: `| Deviation ID | Spec anchor | Operation | Confirmed
  behavior |` with IDs `DEV-001`, `DEV-002`, ...; operation `add` | `modify` | `remove`; and an
  existing or newly added `#sec-*` anchor. Write None in every cell when nothing deviated - a
  blank table blocks convergence.
- **Self-verification**: tick only items that actually passed, confirming that all touched
  functions satisfy cyclomatic complexity limits ($V(G) \le 10$, or $11 \le V(G) \le 15$ with
  justification).
- **Handoff to QA**: check `- [x] WAITING_FOR_QA` only after every item above passes.

Do not edit `01-contract.md`, `03-qa-verification.md` or `04-process.md`.

## 6. Handoff and rework

Handoff is a single checked box, not a prose message:

```markdown
- [x] WAITING_FOR_QA
```

On `REWORK_REQUIRED`, QA's traces in `03` are the input. Fix only inside the contract, rerun the
DoD, update `02` for the new attempt, and hand off again. Repeated failures are a planning or
scope signal: escalate rather than bypassing the contract.

## 7. Appeal instead of ping-pong

A `REWORK_REQUIRED` is not always a code defect. When the verdict and the contract/spec disagree,
raise a structured appeal in `02-dev-workspace.md` Section 6 instead of patching code to satisfy the
test.

### 7.1 When to appeal

- QA's assertion contradicts the contract, the referenced spec anchor or an inherited ADR.
- The required change falls outside `touch_files` (new file, another module, test-only change).
- The spec is self-contradictory or ambiguous, so the expected behavior cannot be derived.
- QA's evidence is wrong: the command failed for environmental reasons, or the case does not exercise
  the claimed behavior.

### 7.2 When not to appeal

- The implementation is hard, slow or inconvenient.
- You want to bypass a DoD check, a complexity limit or a mutation score threshold.
- The disagreement is a personal preference without a spec anchor.
- The appeal has no concrete evidence reference to a test, file or line.

An appeal is not a way to keep the task in Dev's hands: the orchestrator routes it to an independent
reviewer, never back to Dev. Fill only the Section 6 block in `02`; do not edit `03`, `01` or any
test to win the dispute.

### 7.3 Never special-case test values

Do not write production code that special-cases the exact values used by the acceptance tests
(hardcoded IDs, fixture strings, expected responses, test-only branches, environment sniffing). That
is reward hacking: it can pass the suite without implementing the contract. If a test insists on
behavior the contract does not specify, appeal with the spec anchor and evidence; do not neutralize
the test value.

## 8. After QA_PASSED: convergence owns the spec

Dev's responsibility ends with a truthful `02-dev-workspace.md`. Once QA checks `QA_PASSED`, the
`converge` skill owns the spec write-back:

- It appends the confirmed deviations to `.specs/02-tech-spec.md` (`Converged changes`), marks
  `04-process.md`, archives the bundle under `tasks/archive/<task-id>/` and closes the change
  proposal.
- Dev never edits `.specs/02-tech-spec.md` directly and never moves or deletes a task bundle.
- A structural deviation (new component, changed module boundary, new ADR-level decision) must be
  escalated to the Planner/`spec-generator`; the converge step refuses to fold it silently.
- On `REWORK_REQUIRED`, update the Implementation deviations table for the new attempt and hand
  off again; do not write spec prose to compensate for an unresolved rework.

## 9. `04-process.md`

`04` is derived output. Its initial state is `TODO` / `UNASSIGNED` / `None` / retry `0` with an
empty event table. When the handoff box is checked, optional repository tooling appends
`HANDOFF_QA_REQUESTED` and updates `macro_status` to `VERIFYING` and the lock holder to
`QAAgent`. If the tooling is absent, leave `04` as initialized and rely on git/CI; never write
event rows by hand.

## 10. Failure escalation checklist

- Missing/ambiguous contract → Planner/owner.
- Required file outside `touch_files` → split the task.
- DoD command unavailable → report exact command and error; do not claim a pass.
- High complexity cannot be decoupled without architectural/spec change → escalate to Planner/Architect.
- Repeated rework → escalate with evidence from `02`/`03`; if the verdict is disputed, appeal per
  Section 7 instead of coding around the test.
- Environment/tooling failure → report command and exit code; do not hand-edit derived files.
