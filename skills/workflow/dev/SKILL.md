---
name: dev
description: "Implement one planned task bundle as the Dev role: read the contract, change only touch_files, run the machine-checkable DoD, fill 02-dev-workspace.md and hand off to QA. Use when a task contract exists and you are assigned implementation. Do not use for planning, task slicing, architecture, or QA verification."
license: MIT
compatibility: "Harness-agnostic prompt workflow. Optional Python for the repository's scaffold/lint helpers; a manual fallback exists."
metadata:
  version: "2.0.0"
  category: execution
---

# Dev — Task Implementation

Implement one task bundle and hand it to QA. This skill defines the **process** and carries its own
role boundaries in [`references/role-boundaries.md`](references/role-boundaries.md). If the adopting
repository defines agent rules (`AGENTS.md`, a role-rules directory or equivalent), read and follow
them when present; the skill never grants extra access.

## Use when

- A task under `tasks/<task-id>/` has a completed `01-contract.md` and you are the Dev role.
- You need to implement a vertical slice, run its DoD commands, record evidence and hand off.
- You are reworking a task after QA issued `REWORK_REQUIRED`.

## Do not use when

- The contract is missing, incomplete or contested — return it to the Planner.
- You are asked to plan, slice or review tasks, or to verify another agent's work.
- The requested change is outside the contract's `touch_files` — escalate or split the task.

## Inputs

- `tasks/<task-id>/01-contract.md` — authoritative YAML frontmatter, `touch_files`, `dod`, Section 4
  BDD behavioral scenarios (Given-When-Then invariants), and inherited ADRs.
- Spec anchors referenced by the contract.
- Project commands for type check and lint, the existing test suite, and the QA-owned acceptance
  target declared in `dod.test_file`.
- `tasks/<task-id>/02-dev-workspace.md` — the blank form you fill.

## Outputs

- Code changes **only** for paths listed in `touch_files`.
- Code adhering to BDD invariants and cyclomatic complexity limits ($V(G) \le 10$ standard, warning
  $11-15$ justified in `02`, critical $> 15$ prohibited).
- A completed `02-dev-workspace.md` with metadata, actual changes, self-verification, and the
  **Implementation deviations** table (rows `DEV-001`, `DEV-002`, ... or an explicit None row).
- Exactly one handoff marker: `- [x] WAITING_FOR_QA`, checked only when every DoD item passes.
- No edits to `01-contract.md`, `03-qa-verification.md`, `04-process.md` or
  `tests/acceptance/**`.

## Workflow

1. **Confirm scope and BDD contract.** Read `01-contract.md` frontmatter and Section 4 BDD scenarios.
   Check that `task_id` equals the directory name, and that `touch_files`, `dod`, `adherence_adrs`
   and Given-When-Then invariants are defined. Report missing or contradictory items to the Planner.
2. **Prepare the work.** Note the base commit and adhere to project branch/commit conventions. Do not
   reopen an already accepted task unless a reviewer reopens it.
3. **Implement vertical slice under BDD and complexity limits.** Change only files in `touch_files`.
   Implement logic fulfilling the Given-When-Then invariants declared in Section 4 and `dod.edge_cases`.
   Control single-function cyclomatic complexity ($V(G) \le 10$ standard). If complexity approaches
   the warning limit ($11-15$), apply refactoring patterns (Extract Method, Strategy / Lookup Table,
   Guard Clauses). If $V(G) > 15$, refactor before proceeding. Do not edit or create `tests/acceptance/**`.
4. **Run machine-checkable DoD and self-verification.** Execute `dod.type_check` and `dod.lint`, then
   run the project's existing tests; consider every `dod.edge_cases` item. Self-audit cyclomatic
   complexity on all touched functions. The acceptance target (`dod.test_file`) is QA-owned: run it
   only if it already exists, never author or edit it. If it does not exist yet, record that in `02`
   and let QA run it during verification. Capture commands/results.
5. **Fill `02-dev-workspace.md`.** Record branch, base/handoff commit, design notes, one row per
   actually changed file, net line counts, and tick each self-verification item that is true.
   Include explicit architectural justification for any function with warning complexity
   ($11 \le V(G) \le 15$). Leave items unticked if they did not pass. Complete the
   **Implementation deviations** table: one row per place where the code differs from the contract
   or spec (`DEV-001`, `DEV-002`, ...; operation `add` | `modify` | `remove`; a `#sec-*` anchor),
   or write None in every cell when nothing deviated.
6. **Hand off to QA.** Only when every self-verification item passes and complexity limits are
   satisfied, change `- [ ] WAITING_FOR_QA` to `- [x] WAITING_FOR_QA`. That single checked box is
   the handoff trigger. Do not edit `03` or `04`.
7. **On rework.** Read QA's failure traces in `03-qa-verification.md`, fix only within the
   contract, re-run the DoD, update `02` for the new attempt and hand off again. Escalate repeated
   failures instead of bypassing the contract.

## Quality gate (before declaring done)

- [ ] Every changed path is listed in `01-contract.md` → `touch_files`.
- [ ] No file outside the blast radius was created or modified.
- [ ] Implementation honors all Given-When-Then BDD scenarios and behavioral invariants.
- [ ] Type check and lint exit successfully; the project's existing tests pass.
- [ ] Cyclomatic complexity self-audit passes: all functions meet $V(G) \le 10$ (or $11-15$ with
      justification in `02`); none exceed $V(G) > 15$.
- [ ] The QA-owned acceptance target (`dod.test_file`) is declared; if it is not authored yet, that
      is recorded for QA.
- [ ] Every `dod.edge_cases` item has an implementation/test rationale.
- [ ] `02-dev-workspace.md` is complete for this attempt, including the Implementation deviations
      table (explicit None row when nothing deviated).
- [ ] Only `WAITING_FOR_QA` is checked; `03` and `04` are untouched.

## Failure handling

- **Missing or contradictory contract**: stop; report the field and ask the Planner to fix it.
- **Out-of-scope change needed**: split the task or escalate; never edit outside `touch_files`.
- **DoD command missing or not runnable**: report it with the command and error; do not hand-wave
  the check.
- **DoD fails**: fix the implementation and rerun. Do not tick the handoff box while a check fails.
- **Complexity exceeds threshold ($V(G) > 15$)**: refactor using Extract Method, Strategy /
  Lookup Table, Guard Clauses, or State patterns before handoff; never hand off critical complexity.
- **Tooling unavailable**: use the project's manual commands and record evidence in `02`; the
  workflow must not depend on optional tooling.

## `04-process.md` and tooling

`04-process.md` is derived output. After the handoff checkbox is checked, optional repository
tooling appends `HANDOFF_QA_REQUESTED` and updates `macro_status`/`current_lock_holder`. Never
hand-edit `04`; without tooling, rely on git/CI and the checked box.

## After QA_PASSED: spec write-back ownership

The **Implementation deviations** table is Dev's last deliverable for the task. After QA records
`QA_PASSED`, the `converge` skill owns the spec write-back: it folds the confirmed deviations into
`.specs/02-tech-spec.md`, archives the task bundle and closes the change proposal.

- Dev never edits `.specs/02-tech-spec.md` and never archives the bundle.
- A structural deviation (new component, changed boundary, new ADR-level decision) is escalated to
  the Planner/`spec-generator` instead of being converged silently.
- If QA requests rework, update the deviation table for the new attempt; do not pre-write spec prose.

## References

- [`references/dev-protocol.md`](references/dev-protocol.md) — detailed checklists, scope
  verification, McCabe cyclomatic complexity limits, refactoring patterns, handoff and rework procedure.
- Role boundaries: [`references/role-boundaries.md`](references/role-boundaries.md) — write scope,
  read-only scope, invariants and the honest enforcement model (bundled; no external files needed).
- Repository rules: read `AGENTS.md` and any role-rules files when the adopting project defines
  them; they may add requirements but are not required for this skill to work.
- Task bundle format: `task-decomposition` skill (optional sibling; this skill only consumes its
  artifacts).

## Honest limits

This skill does not grant write access and cannot enforce role isolation. Where the repository has
CI (for example a git-based role audit) or branch protection, that is the authoritative layer. The
contract, not this document, defines the allowed blast radius.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
