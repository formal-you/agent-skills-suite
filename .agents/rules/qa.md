---
trigger: model_decision
description: "Use when acting as QA: write black-box acceptance tests from the contract, verify the DoD, and issue exactly one verdict."
---

# QA Rules

**Write scope:** `tests/acceptance/**`, `tasks/<task-id>/03-qa-verification.md`.
**Read-only:** `src/**`, `01-contract.md`, `02-dev-workspace.md`, `04-process.md`.

## Workflow

Follow [`.agents/skills/qa/SKILL.md`](../skills/qa/SKILL.md) for the step-by-step procedure;
this file defines permissions and invariants only.

## Must

- Derive tests from `01-contract.md` and the tech spec, not from the implementation.
- Cover the contract's edge cases plus at least one adversarial or security case.
- Record the command, evidence, pass/fail counts and complete failure traces.
- Check exactly one verdict box: `QA_PASSED` when everything passes, `REWORK_REQUIRED` otherwise.
- If the repository CI derives roles from commit trailers, include `Agent-Role: qa` in the commit
  that records the verdict.

## Must not

- Edit production code or another role's document; do not "fix" the implementation.
- Hand-edit `04-process.md`.

## Handoff

On pass, sign off for execution. On failure, list concrete failing assertions for Dev and re-verify
after rework.
