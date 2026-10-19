---
trigger: model_decision
description: "Use when coordinating multi-agent work or checking write boundaries: role matrix, 4-document task bundle, lifecycle markers and the honest L0-L3 enforcement model."
---

# Enforcement Model and Role Write Scopes

This repository uses a role-separated, 4-document task workflow. Host-agnostic rules live in
`AGENTS.md`; role-specific rules live in `.agents/rules/*.md`; this page explains the roles, write
scopes and the honest enforcement model. The shipped skills are self-contained: they treat this
rules layer as optional context and work without it.

## Role matrix

| Role | Rule file | Write scope | Read-only |
| :--- | :--- | :--- | :--- |
| Product manager | `pm.md` | `.specs/01-prd.md`, `.specs/01-prd/` | everything else under `.specs/`, `src/`, `tests/`, `tasks/` |
| Architect | `architect.md` | `.specs/adr/*.md`, `.specs/02-tech-spec.md`, `.specs/02-tech-spec/` | `.specs/01-prd*`, `src/`, `tests/`, `tasks/` |
| Planner | `planner.md` | `tasks/<task-id>/` while planning | `.specs/`, `src/`, `tests/` |
| Dev | `dev.md` | `src/**`, `tasks/<task-id>/02-dev-workspace.md` | `01-contract.md`, `03-qa-verification.md`, `04-process.md`, `tests/acceptance/**` |
| QA | `qa.md` | `tests/acceptance/**`, `tests/integration/**`, `tasks/<task-id>/03-qa-verification.md` | `src/**`, `01-contract.md`, `02-dev-workspace.md`, `04-process.md` |
| Quality Engineering | `quality-engineering` skill | CI workflows (`.github/workflows/*`, the skill's `assets/templates/ci/*`) | `tasks/`, `src/`, `tests/` (audited/executed in CI) |
| Test Engineering | `test-engineering.md` | the agreed test-strategy document and test-design review notes | `tasks/`, `src/`, `tests/` and CI artifacts (reviewed read-only) |
| Reviewer (Gate 2) | `reviewer.md` | none (read-only semantic audit) | `.specs/`, `tasks/`, `src/`, `tests/` |
| Orchestrator / Lead | `orchestrator.md` | coordination artifacts only (task board, status, routing notes) | all role documents, `.specs/`, `src/`, `tests/`, `tasks/` |

## Gate 2 reviewer

The reviewer is the read-only semantic gate between planning and implementation:

- builds a bidirectional traceability check (requirements/APIs ↔ task IDs);
- rejects invented entities or behaviors (zero hallucination);
- rejects tasks that contradict an inherited ADR;
- reports findings with task IDs and evidence, without editing any artifact.

It never replaces Gate 1: Gate 1 must pass first, and Gate 2 is prompt-driven, not automated.
The reviewer can also perform a change/code review (diff vs contract/tests). See
`reviewer.md`, the `review` skill, and the `plan-linter` skill's bundled `gate-2-review.md` fallback.

## Orchestrator

The orchestrator routes work and enforces the pipeline order; it does not author role artifacts:

1. PRD → spec → task bundles → Gate 1 → Gate 2 → Dev → QA;
2. one owner per task, dependencies for ordering;
3. evidence required for completion (gate report, test output, verdict);
4. escalate or split on blockers instead of bypassing a gate.

## The 4-document task bundle

Every task lives under `tasks/<task-id>/` and contains four documents:

| Document | Owner | Purpose |
| :--- | :--- | :--- |
| `01-contract.md` | Planner | YAML frontmatter contract (authoritative) plus readable sections; read-only for Dev/QA. |
| `02-dev-workspace.md` | Dev | Implementation notes, actual changes, self-verification and handoff. |
| `03-qa-verification.md` | QA | Independent test matrix, execution evidence and the verdict. |
| `04-process.md` | Tooling | Derived status card and append-only event log; agents never hand-edit it. |

The `task_id` in the contract frontmatter must equal the directory name. `01`, `02` and `03` must
not contain unresolved placeholders once their owner finishes.

## Goldilocks rule (configurable)

Default repository conventions: 1–3 touched files and 50–250 estimated diff lines per task. These are
defaults, not universal law: change them in the plan-linter configuration and keep the contract,
docs and templates consistent. A task below the minimum should be merged; a task above the maximum
should be split.

## Lifecycle markers

Only these checked-box lines drive the derived event log:

| Document | Checked marker | Meaning |
| :--- | :--- | :--- |
| `02-dev-workspace.md` | `- [x] WAITING_FOR_QA` | Dev finished and requests QA. |
| `03-qa-verification.md` | `- [x] QA_PASSED` | QA accepts the task. |
| `03-qa-verification.md` | `- [x] REWORK_REQUIRED` | QA rejects and returns the task to Dev. |

The templates ship these boxes unchecked and never contain a literal checked marker. Tooling reads
the box state; nothing else should be added. The derived mapping is:

| Checked marker | Event code | `macro_status` | `current_lock_holder` |
| :--- | :--- | :--- | :--- |
| `- [x] WAITING_FOR_QA` | `HANDOFF_QA_REQUESTED` | `VERIFYING` | `QAAgent` |
| `- [x] QA_PASSED` | `TASK_TERMINATED_DONE` | `DONE` | `None` |
| `- [x] REWORK_REQUIRED` | `REWORK_TRIGGERED` | `REWORKING` | `DevAgent` (+1 retry, capped) |

`04-process.md` starts at `TODO` / `UNASSIGNED` / `None` / retry `0` with an empty event table; the
first real event is written only after a role checks a lifecycle box. Dev/QA working steps and the
initial state are detailed in `task-decomposition/references/role-lifecycle.md`.

## Enforcement layers (honest model)

| Layer | Mechanism | Applies to | Guarantee |
| :--- | :--- | :--- | :--- |
| L0 | Prompt rules (this page, `AGENTS.md`, `.agents/rules/*.md`) | every agent/harness | advisory; depends on the agent following instructions |
| L1 | `quality-engineering` skill's `rbac_audit.py` in CI | every harness with git | authoritative for committed changes |
| L2 | Branch protection / CODEOWNERS | repository settings | authoritative |

Prompt rules are **not** physical enforcement and must not be described as such. The authoritative
protection for role isolation is L1 plus repository permissions. The audit trail is git history plus
the CI audit; `04-process.md` is derived output, not the source of truth. This package ships no
host-side hook adapter; adopters may add local hooks, but they are best-effort and bypassable.

## What each role must never do

- The **planner** never writes source, tests or `04`; it also never fills `02`/`03` for other roles.
- **Dev** never edits tests, the contract, QA's report or the process file.
- **QA** never edits source, Dev's workspace, the contract or the process file.
- **Test Engineering** never accepts an individual task, writes tests or `03-qa-verification.md`,
  edits source, or runs CI gates; it only writes the agreed test-strategy document and test-design
  review notes, and its `DESIGN_READY`/`DESIGN_GAPS` marker is not a task verdict.
- **Architect** never invents domain content and never edits source, tests, tasks or the PRD.
- **PM** never edits architecture, tasks, source or tests.
- **Reviewer** never edits artifacts, weakens Gate 1, or rewrites a contract to make it pass.
- **Orchestrator** never implements, writes tests/specs, fills role documents or bypasses a gate.

If an action is outside your write scope, escalate to the owner instead of editing; a scope conflict
is a planning signal, not a licence.

## References

- `AGENTS.md` — host-agnostic summary rules.
- `.agents/rules/*.md` — per-role permissions and invariants.
- `.agents/skills/README.md` — skill index, discovery and repository conventions.
- `.agents/skills/task-decomposition/SKILL.md` — how to produce a task bundle.
- `.agents/skills/plan-linter/SKILL.md` — deterministic Gate 1 and the Gate 2 fallback checklist.
- `.agents/skills/review/SKILL.md` — independent plan (Gate 2) and change/code review workflow.
- `.agents/skills/dev/SKILL.md` — Dev implementation, self-verification and handoff workflow.
- `.agents/skills/qa/SKILL.md` — QA black-box verification, evidence and verdict workflow.
- `.agents/skills/test-engineering/SKILL.md` — repository-wide test strategy, test-design standards
  and independent test-design review (design markers only, never a task verdict).

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
