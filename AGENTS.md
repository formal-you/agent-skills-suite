# Global Agent Rules for Autonomous Multi-Agent Development

These rules apply to every agent and every harness in this repository. This file is the
host-agnostic rules layer shipped with the Agent Skills Suite: keep it at the adopting repository
root so AGENTS-aware hosts load it automatically (Codex, DSH, Antigravity, generic agents). The
skills are self-contained and work without this file; when both are present, these conventions
apply.

The pipeline is: idea or bounded change -> PRD/spec -> task bundles -> Gate 1 -> Gate 2 ->
Dev <-> QA -> convergence. This file is the always-loaded summary; it must not contradict the
detailed rules in `.agents/rules/enforcement.md`, the skill index `.agents/skills/README.md` or the
guides under `docs/`.

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

Each role has a rule file under `.agents/rules/`; it defines the permissions that this summary cannot
override. If an action is outside your write scope, escalate to the owner instead of editing.

- Planner — `.agents/rules/planner.md`: creates task bundles; never writes source, tests or `04`.
- Dev — `.agents/rules/dev.md`: writes `src/**` plus `02-dev-workspace.md`; never edits tests, contracts or other roles' docs.
- QA — `.agents/rules/qa.md`: writes `tests/acceptance/**` plus `03-qa-verification.md`; never edits source or other roles' docs.
- Reviewer (Gate 2) — `.agents/rules/reviewer.md`: read-only semantic audit; never edits artifacts or weakens Gate 1.
- Orchestrator/Lead — `.agents/rules/orchestrator.md`: routes work and enforces gate order; never authors role artifacts or bypasses a gate.

## Gates and evidence

- **Gate 1 (deterministic):** `plan-linter` checks contract fields, DAG, placeholders, anchor
  coverage and real-file topology; its JSON and exit codes are the evidence.
- **Gate 2 (semantic):** an independent, read-only reviewer audits traceability, invented content
  and ADR alignment; it never replaces Gate 1.
- **Execution:** Dev hands off with evidence in `02`; QA records commands, results and exactly one
  verdict in `03`; `converge` folds confirmed deviations back into the spec after `QA_PASSED`.
- **Enforcement honesty:** prompt rules are advisory and bypassable. The authoritative layer is the
  CI RBAC audit (`tools/rbac_audit.py`) plus branch protection; no local hook adapter is shipped.

## References

- `.agents/rules/enforcement.md` — role matrix, lifecycle markers and the honest enforcement model.
- `.agents/skills/README.md` — skill index, discovery and the per-skill contract.
- `skills/<category>/<name>/` — installable layout for plugins and `npx skills`; `.agents/skills/`
  is the AGENTS mirror.
- `docs/skills-guide.zh-CN.md`, `docs/brownfield-convergence.zh-CN.md`,
  `docs/skills-compatibility.md` — usage walkthrough, change/convergence and the harness matrix.
- Review skill: `review` (Gate 2 plan review plus change/code review); execution skills: `dev`
  (implement + handoff) and `qa` (independent verification + verdict); brownfield entry: `change`
  (proposal -> one task bundle -> archive) and convergence: `converge` (after `QA_PASSED`, append
  deviations to `.specs/02-tech-spec.md`, move the bundle to `tasks/archive/`).
