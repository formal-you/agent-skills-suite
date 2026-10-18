# Global Agent Rules for Autonomous Multi-Agent Development

These rules apply to every agent and every harness in this repository. This repository uses a
4-document task specification and role-separated write scopes. They are repository conventions and
can be adjusted per project, but not silently broken.

## Task bundles

All work is sliced into task bundles under `tasks/<task-id>/` containing exactly four documents:

- `01-contract.md` — Planner-owned contract; authoritative YAML frontmatter, read-only for Dev/QA.
- `02-dev-workspace.md` — Dev-owned implementation notes, self-verification, handoff and the
  `Implementation deviations` table (`DEV-001` / `#sec-*` / `add|modify|remove`; `None` row when nothing deviated).
- `03-qa-verification.md` — QA-owned test matrix, evidence and verdict.
- `04-process.md` — derived status/audit output maintained by tooling; no agent hand-edits it.

The `task_id` in `01-contract.md` must equal the directory name.

## Goldilocks rule

Tasks are sized for one reviewable change: 1–3 touched files and 50–250 estimated diff lines by
default. The limits are configurable in the plan-linter configuration. Split tasks above the maximum;
merge tasks below the minimum.

## Role isolation and no cheating

- Planner: creates task bundles; never writes source, tests or `04`.
- Dev: writes `src/**` plus `02-dev-workspace.md`; never edits tests, contracts or other roles' docs.
- QA: writes `tests/acceptance/**` plus `03-qa-verification.md`; never edits source or other roles' docs.
- Reviewer (Gate 2): read-only semantic audit; never edits artifacts or weakens Gate 1.
- Orchestrator/Lead: routes work and enforces gate order; never authors role artifacts or bypasses a gate.

## References

- Detailed roles, write scopes and the honest enforcement model: `docs/agent-rules.md`.
- Skills (PRD → spec → tasks → Gate 1/2 review): `.agents/skills/README.md`.
- Review skill: `review` (Gate 2 plan review plus change/code review).
- Execution skills: `dev` (implement + handoff) and `qa` (independent verification + verdict).
- Brownfield entry: `change` (proposal -> one task bundle -> archive) and convergence: `converge`
  (after `QA_PASSED`, append deviations to `.specs/02-tech-spec.md`, move the bundle to `tasks/archive/`).
- Optional Antigravity hooks live in `.agents/hooks.json`; CI audit is the authoritative layer.
