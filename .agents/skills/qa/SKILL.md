---
name: qa
description: "Independently verify a handoff task bundle as the QA role: design black-box acceptance tests, execute them, record evidence, audit blast radius and issue exactly one verdict (QA_PASSED or REWORK_REQUIRED). Use when a task is handed off with WAITING_FOR_QA. Do not use for implementation, planning, or contract authoring."
license: MIT
compatibility: "Harness-agnostic prompt workflow. Uses the project's declared test command; no bundled runtime dependency."
metadata:
  version: "2.0.0"
  category: execution
---

# QA — Independent Verification

Verify one task bundle independently and issue one verdict. This skill defines the **process**;
write permissions and role boundaries come from the repository's agent rules (for example
`docs/agent-rules.md` and `.agents/rules/qa.md`). The skill never grants extra access.

## Use when

- A task under `tasks/<task-id>/` has `- [x] WAITING_FOR_QA` in `02-dev-workspace.md`.
- You need to design and run independent acceptance tests, record evidence, audit the blast radius
  and sign off or return the task for rework.
- You are re-verifying a task after a Dev rework.

## Do not use when

- The handoff marker is not checked — return the task to Dev instead of guessing.
- You are asked to implement, plan, slice or review the plan; those belong to Dev, Planner and
  plan-linter respectively.
- The contract or the upstream spec is missing or contradictory — report it; do not reconstruct it.

## Inputs

- `tasks/<task-id>/01-contract.md` — DoD, `touch_files`, traceability and inherited ADRs.
- `tasks/<task-id>/02-dev-workspace.md` — Dev's handoff claim and declared commit.
- Project test layout and the declared `dod.test_file` command.
- `tasks/<task-id>/03-qa-verification.md` — the blank form you fill.

## Outputs

- Acceptance tests under `tests/acceptance/` (configurable in the target repository).
- A completed `03-qa-verification.md` with test matrix, execution evidence, audit and verdict.
- Exactly one verdict marker: `- [x] QA_PASSED` or `- [x] REWORK_REQUIRED`.
- No edits to source, `01-contract.md`, `02-dev-workspace.md` or `04-process.md`.

## Workflow

1. **Verify the handoff.** Confirm `WAITING_FOR_QA` is checked, the declared handoff commit exists,
   and `01` is still valid. If not, stop and report the exact gap.
2. **Read the contract, not the implementation.** Extract the DoD, edge cases, `touch_files` and
   inherited ADRs. Design black-box tests before reading implementation code so the tests are
   independent.
3. **Write the test matrix.** Cover at least: normal path, boundary/invalid input, duplicate/replay
   or concurrency, and authorization/security. Use a stable case ID per test.
4. **Write only acceptance tests.** Put tests under `tests/acceptance/` (or the project's declared
   QA-owned path). Do not edit production source or Dev's workspace.
5. **Execute and record evidence.** Run the declared acceptance command, capture totals, failures,
   coverage and complete traces. A claim without a command/result is not evidence.
6. **Audit the implementation boundary.** Check every changed path is in `touch_files`, Dev did not
   edit `tests/acceptance/` or `01`, and the implementation honors `adherence_adrs`.
7. **Issue exactly one verdict.** Tick `QA_PASSED` only when tests and audits pass; otherwise tick
   `REWORK_REQUIRED` and include complete failure traces and the expected fix. Never tick both.
8. **Rework loop.** On the next attempt, keep prior evidence, update attempt metadata and re-run.
   Repeated failures escalate; they are not a reason to bypass the contract.

## Quality gate (before signing off)

- [ ] Handoff marker was checked and the reviewed commit matches `02`.
- [ ] Test matrix covers normal, boundary, replay/concurrency and security cases.
- [ ] Every test ran; totals and failures are recorded with traces.
- [ ] Every changed path is inside `01` → `touch_files`.
- [ ] Dev did not modify acceptance tests or `01`.
- [ ] Exactly one verdict is checked; `REWORK_REQUIRED` has actionable traces.

## Failure handling

- **Handoff missing or inconsistent**: reject with the specific gap; do not invent a commit.
- **Test environment unavailable**: report the command, error and environment; do not sign off.
- **Out-of-scope Dev change**: issue `REWORK_REQUIRED` with the violating path.
- **Repeated rework**: escalate with the failure history; do not lower the bar to close the task.
- **No tooling/hooks**: run the project's commands manually and record evidence in `03`; the
  workflow must not depend on them.

## `04-process.md` and tooling

`04` is derived output. Checking `QA_PASSED` lets optional tooling append
`TASK_TERMINATED_DONE` and set `macro_status: DONE`; checking `REWORK_REQUIRED` appends
`REWORK_TRIGGERED`, sets `REWORKING` and increments the retry counter (capped). Never hand-edit
`04`; without tooling, rely on git/CI and the checked box.

## References

- [`references/qa-protocol.md`](references/qa-protocol.md) — test matrix, evidence format,
  anti-cheat checks and verdict rules.
- Repository role rules: `docs/agent-rules.md` and the project's rule files (read them when
  present; this skill does not override them).
- Task bundle format: `task-decomposition` skill (optional sibling; this skill consumes its
  artifacts).

## Honest limits

This skill does not grant write access and cannot enforce role isolation. The authoritative
protection is repository CI (`tools/rbac_audit.py`) plus branch protection. Gate 1/2 review is a
separate planning concern; this skill verifies a task that already passed planning.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
