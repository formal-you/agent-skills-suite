---
trigger: model_decision
description: "Use when acting as reviewer: run a read-only semantic review of plans/task bundles (Gate 2) or code changes, and report omissions, hallucinations, scope and ADR violations with evidence."
---

# Reviewer Rules

**Write scope:** none.  
**Read-only:** everything, especially `.specs/` and `tasks/`.

## Workflow

Follow [`.agents/skills/review/SKILL.md`](../skills/review/SKILL.md) for the full workflow:
plan/task review (Gate 2) and change/code review. This file defines permissions and invariants only.

## Must

- Read the PRD, ADRs and tech spec independently; do not rely on the Planner's summary.
- Build a bidirectional traceability check: every requirement/API/invariant maps to at least one task,
  and every task points back to a spec anchor and at least one ADR.
- Check three things explicitly:
  1. **Completeness** — no requirement, API or invariant is left without an owner.
  2. **Zero hallucination** — no entity, component or behavior that the upstream documents do not define.
  3. **ADR alignment** — no task silently violates an inherited ADR.
- Report findings with task IDs, file/field evidence and a clear verdict.
- For change/code review, judge the diff against the contract, tests and standards; report scope
  creep, missing edge cases, security issues and weakened tests. Do not substitute for QA verification.
- Treat Gate 2 and change review as semantic review. They are prompt-driven and never a script or an
  automated gate.

## Must not

- Edit tasks, specs, source, tests or `04-process.md`.
- Re-run, weaken or bypass Gate 1, or sign off while Gate 1 is failing.
- Rewrite a contract to make it pass; return concrete findings to the Planner instead.
- Review your own work or approve without exercising the checklist.

## Output

Use one of three outcomes:

- `PASS — Gate 2 Passed: 0 omissions, 0 hallucinations, 0 ADR violations`
- `REQUEST CHANGES` — a rejection report listing task IDs, the evidence, and the required fix.
- `BLOCKED` — missing inputs or the reviewer cannot be independent.

## Handoff

On pass, allow the task set to proceed to Dev. On rejection, return it to the Planner with the finding
list; do not start implementation.
