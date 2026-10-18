---
name: converge
description: "Fold confirmed implementation deviations back into the technical spec after a task reaches QA_PASSED, archive the task bundle and close the change proposal. Use when a task bundle records a checked QA_PASSED verdict and its 02-dev-workspace.md deviation log is ready to be written back. Do not use while implementation or QA is still running, and do not use to invent spec content."
license: MIT
compatibility: "Harness-agnostic prompt workflow. Python >=3.9 optional for the bundled converge helper; a manual fallback exists."
metadata:
  version: "1.0.0"
  category: execution
---

# Converge - Spec Write-Back After QA

Close the execution loop: a task that passed QA becomes part of the living specification. This
skill represents the **ConvergeTool** role in the lifecycle. It defines the process; repository
agent rules still own permissions, and this skill never grants extra access.

Pipeline position: `dev` -> `qa` -> **converge** -> archived bundle + updated spec.

## Use when

- A task bundle's `03-qa-verification.md` records a checked `QA_PASSED` verdict.
- `02-dev-workspace.md` contains the frozen Implementation deviations table (rows or an
  explicit None row).
- The task's confirmed behavior must be folded into `.specs/02-tech-spec.md`, the bundle
  archived and the originating change proposal closed.

## Do not use when

- Implementation or QA is still running, the handoff marker is unchecked, or
  `REWORK_REQUIRED` is active - wait for a stable `QA_PASSED` verdict.
- The deviation log is blank or missing - send the task back to Dev instead of guessing.
- You would have to invent spec content or rewrite existing spec prose; that is a planning change,
  not a convergence.

## Inputs

- `tasks/<task-id>/01-contract.md` - title, traceability anchors, optional `change_id`.
- `tasks/<task-id>/02-dev-workspace.md` - the Implementation deviations table (frozen format).
- `tasks/<task-id>/03-qa-verification.md` - the checked `QA_PASSED` verdict and evidence.
- `tasks/<task-id>/04-process.md` - derived status card and event log.
- `.specs/02-tech-spec.md` - the living technical specification.
- `.specs/changes/<change-id>/proposal.md` - the originating change proposal, when one exists.

## Outputs

- One dated, attributed entry per task inside the spec's **Converged changes** section.
- A convergence marker per task: `<!-- converged: <task-id> sha256:<hash> -->`.
- `04-process.md` with `macro_status: "CONVERGED"` and one `TASK_CONVERGED` event row
  (actor `ConvergeTool`).
- The task bundle moved (never deleted) to `tasks/archive/<task-id>/`.
- `.specs/changes/<change-id>/convergence.md` plus proposal status `archived`, when a proposal
  exists.

## Check -> apply -> verify

1. **Check.** Classify bundles before writing anything:
   `python .agents/skills/converge/scripts/converge.py check --tasks-dir ./tasks --json`
   A bundle is converge-ready only when QA passed, no rework is active, the deviation table has at
   least one row or an explicit None row, and the spec does not already carry its marker.
2. **Apply.** Converge one bundle:
   `python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id>`
   Use `--dry-run` first to inspect the planned writes. The helper refuses with exit 1 when the
   bundle is not converge-ready, and refuses an existing archive destination unless `--force`.
3. **Verify.** Re-run `check`, confirm the marker is present, `04-process.md` says `CONVERGED`, the
   bundle is archived, and `--spec-sha256` matches the expected CI value:
   `python .agents/skills/converge/scripts/converge.py --spec .specs/02-tech-spec.md --spec-sha256`

## Manual fallback (no Python)

When the helper is unavailable, perform the same steps by hand and keep the markers exact:

1. Confirm `QA_PASSED` is checked in `03` and no `REWORK_REQUIRED` is active.
2. Read the deviation rows from `02`; reject a blank log.
3. Append (do not edit) one entry to the spec's **Converged changes** section: a `### <task-id>`
   heading, the deviation table, and the `<!-- converged: <task-id> sha256:<hash> -->` marker.
   Compute the hash with any SHA-256 tool over the normalized task ID and rows.
4. Set `macro_status` to `CONVERGED` in `04` and append the `TASK_CONVERGED` / `ConvergeTool` row.
5. Move, never delete, the bundle to `tasks/archive/<task-id>/`; archive the proposal and write
   `convergence.md` when a change proposal exists.
6. Re-run the verify step and record the evidence.

## Refusal conditions

Stop and report instead of converging when any of these is true:

- **QA not passed** - `03` has no checked `QA_PASSED`, or `REWORK_REQUIRED` is still active.
- **Unresolved rework** - retry evidence shows the task is mid-rework; wait for a new verdict.
- **Blank deviation log** - the Implementation deviations table is missing or has no DEV row and
  no explicit None row.
- **Spec drift** - a `modify`/`remove` deviation points at a `#sec-*` anchor the spec does not
  contain; the spec and the deviation log disagree. Run `check`/`apply` with `--strict` in CI to
  turn this warning into a refusal.
- **Archive collision** - `tasks/archive/<task-id>/` already exists and `--force` was not given.

Structural deviations (new modules, changed boundaries, new ADR-level decisions) must escalate to
`spec-generator`; they are never converged silently.

## History and attribution

Convergence never rewrites history: it appends a dated, attributed section instead of editing
existing spec prose. Existing entries stay byte-for-byte stable, and every entry names the source
task, the QA verdict and the ConvergeTool actor. Never edit an old convergence entry to make a new
task fit; add a new entry and record the conflict.

## References

- [`references/convergence-protocol.md`](references/convergence-protocol.md) - state machine, who
  writes what, archive layout, idempotency markers, conflict rules and structural escalation.
- Role boundaries: [`references/role-boundaries.md`](references/role-boundaries.md) — write scope,
  invariants and the honest enforcement model (bundled; no external files needed).
- Task bundle format and role lifecycle: `task-decomposition` skill (when installed).
- Handoff input: `dev` skill; verdict input: `qa` skill.
- Repository rules: read `AGENTS.md` and any role-rules files when the adopting project defines
  them; they may add requirements but are not required for this skill.

## Honest limits

This skill does not grant write access and cannot enforce role isolation. Where the repository has
CI (for example a git-based role audit) or branch protection, that is the authoritative layer. The
bundled helper is an optional deterministic assistant; the markers and the written evidence are the
contract.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
