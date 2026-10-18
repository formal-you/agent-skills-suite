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
2. Run in this order: type check → lint → existing project tests → edge-case checks. Use the exact
   `dod.type_check`/`dod.lint` commands, not equivalents you invented. `dod.test_file` is the
   QA-owned acceptance target: run it only if it already exists; never create or edit
   `tests/acceptance/**`.
3. Capture the command and result for `02-dev-workspace.md`. If the acceptance target is not
   authored yet, record that and leave acceptance execution to QA. If a command cannot run, report
   the command and error instead of omitting the check.
4. If a DoD command fails, fix the implementation and rerun. Do not tick the handoff box early.

## 4. Fill `02-dev-workspace.md`

The template is a blank role form; fill these sections in place:

- **Execution metadata**: Dev agent, branch, base commit, handoff commit, handoff time (UTC).
- **Implementation notes**: design decisions, trade-offs, deviations from the plan.
- **Actual changes**: one row per changed file with action, path and approximate lines; net lines
  added/removed. Every path must be in `touch_files`.
- **Implementation deviations**: one row per place where the implementation differs from the
  contract or the spec. Frozen format: `| Deviation ID | Spec anchor | Operation | Confirmed
  behavior |` with IDs `DEV-001`, `DEV-002`, ...; operation `add` | `modify` | `remove`; and an
  existing or newly added `#sec-*` anchor. Write None in every cell when nothing deviated - a
  blank table blocks convergence.
- **Self-verification**: tick only items that actually passed.
- **Handoff to QA**: check `- [x] WAITING_FOR_QA` only after every item above passes.

Do not edit `01-contract.md`, `03-qa-verification.md` or `04-process.md`.

## 5. Handoff and rework

Handoff is a single checked box, not a prose message:

```markdown
- [x] WAITING_FOR_QA
```

On `REWORK_REQUIRED`, QA's traces in `03` are the input. Fix only inside the contract, rerun the
DoD, update `02` for the new attempt, and hand off again. Repeated failures are a planning or
scope signal: escalate rather than bypassing the contract.

## 6. After QA_PASSED: convergence owns the spec

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

## 7. `04-process.md`

`04` is derived output. Its initial state is `TODO` / `UNASSIGNED` / `None` / retry `0` with an
empty event table. When the handoff box is checked, optional repository tooling appends
`HANDOFF_QA_REQUESTED` and updates `macro_status` to `VERIFYING` and the lock holder to
`QAAgent`. If the tooling is absent, leave `04` as initialized and rely on git/CI; never write
event rows by hand.

## 8. Failure escalation checklist

- Missing/ambiguous contract → Planner/owner.
- Required file outside `touch_files` → split the task.
- DoD command unavailable → report exact command and error; do not claim a pass.
- Repeated rework → escalate with evidence from `02`/`03`.
- Environment/tooling failure → report command and exit code; do not hand-edit derived files.
