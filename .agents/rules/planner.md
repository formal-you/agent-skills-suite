---
trigger: model_decision
description: "Use when acting as planner: slice the approved spec into 4-document task bundles with a DAG and Goldilocks sizing."
---

# Planner Rules

**Write scope:** `tasks/<task-id>/` (create all four documents; edit `01-contract.md` while planning).
**Read-only:** `.specs/`, `src/`, `tests/`.

## Workflow

Follow [`.agents/skills/task-decomposition/SKILL.md`](../skills/task-decomposition/SKILL.md) and its
`references/role-lifecycle.md`; this file defines permissions and invariants only.

## Must

- Create `01-contract.md`, `02-dev-workspace.md`, `03-qa-verification.md` and `04-process.md` per task.
- Put the YAML frontmatter contract at the top of `01-contract.md`; `task_id` equals the directory name.
- Keep Goldilocks defaults (configurable): 1–3 `touch_files` and 50–250 `estimated_lines`.
- Anchor each task with `origin_spec_anchor` (a `#sec-*` anchor) and at least one `adherence_adrs` entry.
- Keep the dependency graph acyclic and reference existing task IDs only.
- Validate with the optional plan-linter Gate 1, or the manual checklist in `task-decomposition`.
- Use the `task-decomposition` scaffold when available, then fill the remaining placeholders.
- Leave `02`/`03` as blank token-free role forms and `04` at its initialized values
  (`TODO`/`UNASSIGNED`/`None`/retry `0`); never fill another role's document.
- If the repository CI derives roles from commit trailers, include `Agent-Role: planner` in the
  commit that creates the task bundle.

## Must not

- Edit `src/`, `tests/acceptance/`, `.specs/` or any `04-process.md`.
- Fill `02`/`03` on behalf of Dev/QA, or leave unresolved placeholders in `01`/`02`/`03`.

## Handoff

Run the optional Gate 1, fix violations, then hand the task set to the plan-linter Gate 2 review and
then to Dev/QA.
