# Convergence Protocol - State Machine, Ownership and Conflicts

This reference expands the converge workflow in `SKILL.md`. It fixes the lifecycle transition, the
archive layout, the idempotency marker and the rules for conflicts and structural deviations.

## 1. State machine

~~~text
WAITING_FOR_QA --(qa: QA_PASSED)--> QA_PASSED --(converge: apply)--> CONVERGED
WAITING_FOR_QA --(qa: REWORK_REQUIRED)--> REWORKING --(dev + qa)--> WAITING_FOR_QA
~~~

| State | Meaning | Who moves it forward |
| :--- | :--- | :--- |
| `WAITING_FOR_QA` | Dev checked the handoff box in `02`; QA has not finished. | QA |
| `QA_PASSED` | QA wrote a checked `QA_PASSED` verdict in `03`; no active rework. | ConvergeTool |
| `CONVERGED` | The deviation log is folded into the spec, the bundle is archived. | nobody (terminal) |

`REWORKING` is not a convergence input: while a rework verdict is active the bundle is blocked.

## 2. Who writes what

| Artifact | Writer | Convergence rule |
| :--- | :--- | :--- |
| `01-contract.md` | Planner | Read-only; convergence never edits it. |
| `02-dev-workspace.md` | Dev | Read-only after `QA_PASSED`; the frozen deviation table is the input. |
| `03-qa-verification.md` | QA | Read-only; only the checked `QA_PASSED` verdict is consumed. |
| `04-process.md` | Tooling (ConvergeTool) | `macro_status: "CONVERGED"` plus one `TASK_CONVERGED` event. |
| `.specs/02-tech-spec.md` | ConvergeTool | Append-only: **Converged changes** entries and markers. |
| `.specs/changes/<change-id>/proposal.md` | ConvergeTool | Status becomes `archived`. |
| `.specs/changes/<change-id>/convergence.md` | ConvergeTool | Written once per converged task. |
| `tasks/archive/<task-id>/` | ConvergeTool | The moved bundle; contents are never rewritten. |

## 3. Idempotency marker

Every converged entry ends with the exact marker:

~~~text
<!-- converged: <task-id> sha256:<hash> -->
~~~

- The hash is SHA-256 over the normalized task ID and the deviation rows (ID, anchor, operation,
  confirmed behavior). It deliberately excludes the timestamp, paths and actor, so the same input
  always produces the same hash.
- The marker is the convergence commit point: when it is present, `check` reports `converged` and
  a second `apply` is a no-op (`no_changes`, exit 0).
- A `TASK_CONVERGED` event row is appended at most once per task/archive payload; re-running apply
  never duplicates it.

## 4. Archive layout

~~~text
tasks/
  <task-id>/                      # active bundle (before convergence)
  archive/
    <task-id>/                    # the moved bundle (after convergence)
      01-contract.md
      02-dev-workspace.md
      03-qa-verification.md
      04-process.md
.specs/
  changes/
    <change-id>/
      proposal.md                 # status: archived
      convergence.md              # convergence record for the change
~~~

Convergence **moves** the bundle; it never deletes it. If `tasks/archive/<task-id>/` already
exists, the run is refused (exit 1) unless `--force` is given, in which case the archived copy is
replaced by the current one.

## 5. Conflict rules when two tasks touch the same anchor

The spec is append-only, so conflicts are resolved by ordering, not by rewriting:

- Two tasks may reference the same `#sec-*` anchor; their entries are independent and both stay.
- Apply tasks in dependency/merge order. The entry order in **Converged changes** is the order of
  convergence, and it is the authoritative "later wins" signal for readers.
- If a new task contradicts an already-converged entry, do not edit the old block. Converge the
  new task as a new entry and note the contradiction in `convergence.md`; if the contradiction is
  structural, escalate (next section).
- A `modify`/`remove` deviation whose anchor is absent from the spec is **spec drift**: refuse the
  apply and escalate instead of inventing the missing anchor. The helper reports the miss as a
  warning by default and as a refusal under `--strict`, so CI can enforce it.

## 6. Structural deviations escalate

A deviation is structural when it changes module boundaries, introduces a new component,
contradicts an ADR, or needs a new top-level spec section. Structural deviations are **not**
converged silently:

1. Stop the convergence and mark the bundle blocked.
2. Hand the deviation to the `spec-generator` skill so the spec (and any ADR) is redesigned.
3. Re-plan/re-slice with `task-decomposition`, then let the new task reach `QA_PASSED`.
4. Converge the new task; the old bundle stays archived with its history intact.

## 7. Verification checklist after apply

- [ ] The spec's **Converged changes** section contains exactly one entry for the task.
- [ ] The marker regex matches `<!-- converged: <task-id> sha256:<64 hex> -->`.
- [ ] `04-process.md` shows `macro_status: "CONVERGED"` and the `TASK_CONVERGED` / `ConvergeTool`
      event row.
- [ ] `tasks/<task-id>/` is gone and `tasks/archive/<task-id>/` contains all four documents.
- [ ] The proposal is `archived` and `convergence.md` exists when a `change_id` was declared.
- [ ] `--spec-sha256` matches the value CI recorded for the run.
