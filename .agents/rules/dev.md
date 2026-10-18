---
trigger: model_decision
description: "Use when acting as developer: implement exactly one task contract inside its declared blast radius and hand it off."
---

# Dev Rules

**Write scope:** `src/**`, `tasks/<task-id>/02-dev-workspace.md`.
**Read-only:** `01-contract.md`, `03-qa-verification.md`, `04-process.md`, `tests/acceptance/**`.

## Workflow

Follow [`.agents/skills/dev/SKILL.md`](../skills/dev/SKILL.md) for the step-by-step procedure;
this file defines permissions and invariants only.

## Must

- Read `01-contract.md` first and implement only what it declares.
- Adhere strictly to the BDD behavioral scenarios in `01-contract.md` Section 4 and `dod.edge_cases`
  (Given-When-Then invariants).
- Stay inside the contract's `touch_files`; if a change outside them is required, stop and escalate.
- Control single-function cyclomatic complexity for every function modified in `touch_files`:
  V(G) <= 10 (McCabe) is the standard; V(G) 11-15 requires explicit architectural justification in
  `02-dev-workspace.md`; V(G) > 15 is strictly prohibited — refactor using standard patterns
  (Extract Method, Strategy / Lookup Table, Guard Clauses) before requesting handoff (see
  dev-protocol Section 4 for patterns).
- Perform complete self-verification in `02-dev-workspace.md`: run `dod.type_check` and `dod.lint`,
  plus the project's existing tests; self-audit complexity limits; verify all BDD invariants;
  record all results and complete the Implementation deviations table (rows `DEV-001`, `DEV-002`,
  ... or an explicit `None` row). The acceptance target (`dod.test_file`) is QA-owned: run it only
  if it already exists, never author or edit it.
- Check the `WAITING_FOR_QA` box only when every self-verification item passes.
- If the repository CI derives roles from commit trailers, include `Agent-Role: dev` in the commit
  that implements the task.

## Must not

- Edit `tests/acceptance/**` or any other role's document.
- Hand-edit `04-process.md`; it is derived output.
- Hand off code exceeding cyclomatic complexity limits (V(G) > 15) or with unverified BDD invariants.

## Handoff

Check the handoff box, record the commit and notes for QA in `02-dev-workspace.md`, then stop and hand off.
