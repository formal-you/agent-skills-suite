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
- Stay inside the contract's `touch_files`; if a change outside them is required, stop and escalate.
- Run the contract's type check and lint, plus the project's existing tests; record the results in
  `02-dev-workspace.md`. The acceptance target (`dod.test_file`) is QA-owned: run it only if it
  already exists, never author or edit it.
- Check the `WAITING_FOR_QA` box only when every self-verification item passes.
- If the repository CI derives roles from commit trailers, include `Agent-Role: dev` in the commit
  that implements the task.

## Must not

- Edit `tests/acceptance/**` or any other role's document.
- Hand-edit `04-process.md`; it is derived output.

## Handoff

Check the handoff box, record the commit and notes for QA, then stop and hand off.
