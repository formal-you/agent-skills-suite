---
name: task-decomposition
description: "Slice a PRD, ADRs and tech spec into small, independently verifiable task bundles that follow the repository's 4-document convention. Use when a reviewed spec must become executable tasks with clear blast radius, traceability anchors, inherited ADRs and machine-checkable acceptance criteria. Do not use when the spec is still being designed, when the request is a single-file change that fits one task, or when the task only needs review (use plan-linter instead)."
license: MIT
compatibility: "Harness-agnostic. Python >=3.9 optional for scaffolding and linting; a manual fallback exists."
metadata:
  version: "2.0.0"
  category: spec-pipeline
---

# Task Decomposition

Turn reviewed upstream documents into atomic task bundles that a Dev agent can implement and a QA
agent can verify without re-reading the whole spec. This skill is prompt-first: every step works
with no tooling, and the bundled scripts are optional helpers.

Pipeline position: `prd-generator` → `spec-generator` → **task-decomposition** → `plan-linter` → implementation.

## Use when

- A PRD, ADR set and tech spec are approved and need to become executable tasks.
- A large change must be split into vertical slices with an explicit dependency graph.
- Each task needs a contract with blast radius, traceability, inherited ADRs and a machine-checkable DoD.

## Do not use when

- The spec is incomplete or contested — finish `spec-generator` first.
- The work is smaller than the Goldilocks minimum (one small file): keep it as a single task instead.
- You only need to audit existing task bundles: use the `plan-linter` skill (Gate 1 + Gate 2).

## Inputs

- PRD: `.specs/01-prd.md` and/or `.specs/01-prd/`.
- ADRs: `.specs/adr/*.md`.
- Tech spec: `.specs/02-tech-spec.md` and/or `.specs/02-tech-spec/`.
- Repository conventions: test layout, commands, lint/type-check setup.

## Outputs

For each slice, one directory with four documents:

| File | Owner | Purpose |
| :--- | :--- | :--- |
| `tasks/<task-id>/01-contract.md` | Planner | Authoritative YAML frontmatter + readable contract |
| `tasks/<task-id>/02-dev-workspace.md` | Dev | Implementation notes, changes, self-verification, handoff |
| `tasks/<task-id>/03-qa-verification.md` | QA | Independent test matrix, evidence, verdict |
| `tasks/<task-id>/04-process.md` | Tooling | Initialized status card + append-only event log (derived) |

`task_id` in the frontmatter must equal the directory name. Paths in the contract are repo-relative
and use forward slashes.

## Role workflow (Planner → Dev → QA)

The bundle format is shared; the work is not. A short contract for the three roles:

- **Planner** fills `01-contract.md`. `02` and `03` stay blank token-free role forms. `04` starts at
  `macro_status: TODO`, `micro_phase: UNASSIGNED`, `current_lock_holder: None`, `retry_count: 0`
  with an empty event table. No initialization event is fabricated.
- **Dev** implements only the paths in `touch_files`, records design/changes/self-verification in
  `02`, runs the three DoD checks plus the edge cases, and checks `- [x] WAITING_FOR_QA` only when
  everything passes. Dev never edits `01`, `03` or `04`, and never edits `tests/acceptance/`.
- **QA** designs black-box acceptance tests under `tests/acceptance/`, records the matrix, evidence,
  blast-radius audit and exactly one verdict in `03` (`QA_PASSED` or `REWORK_REQUIRED`). On rework,
  the fix goes back to Dev; QA updates the next attempt rather than rewriting history. QA never
  edits source, `01`, `02` or `04`.

`04` event/status mapping (marker → event code → status/lock/retry) and the full rework loop are in
[`references/role-lifecycle.md`](references/role-lifecycle.md). When no tooling is available, leave
`04` as initialized and rely on git/CI; never hand-write events.

## Repository conventions (configurable)

- **4-document bundles** under `tasks/<task-id>/`; all four files must exist.
- **Goldilocks defaults**: 1–3 `touch_files` and 50–250 `estimated_lines`. The numbers are defaults;
  a repository may change them in the linter config.
- **Traceability**: `origin_spec_anchor` must match `#sec-[a-z0-9-]+` and `adherence_adrs` must name
  at least one inherited ADR.
- **Forbidden touch prefix** by default: `tests/acceptance/` (QA-owned).
- **Dependency graph** must be acyclic (DAG); duplicate `task_id` values are forbidden.
- **No unresolved placeholders** in `01`/`02`/`03` after instantiation.

## Workflow

1. **Intake.** Read the three upstream inputs and build a traceability matrix: every requirement and
   invariant must map to at least one planned task, and every planned task must point back to a spec
   anchor and at least one ADR. If a requirement has no owner yet, plan a task for it; if a task has
   no upstream requirement, delete it.
2. **Slice vertically.** Each slice must deliver an end-to-end, independently verifiable behavior —
   never "only data structures" or "only an empty endpoint". Estimate net diff lines and touched
   files as you slice. Order slices into a DAG; prefer fewer edges and no cycles.
3. **Scaffold.** From the workspace root, or with the absolute path of an installed copy:

   `bash
   python .agents/skills/task-decomposition/scripts/scaffold_task.py \
     --task-id task-001-auth \
     --title "User authentication" \
     --tasks-dir ./tasks
   `

   Useful flags: `--dry-run` lists the files it would create; `--force` overwrites an existing task
   directory; `--help` shows all flags. The scaffold replaces `{{TASK_ID}}` and `{{TASK_TITLE}}` in the
   contract and leaves the other contract/process placeholders for their owners. If Python is
   unavailable, copy the four templates from `assets/templates/` by hand into `tasks/<task-id>/` and
   rename the file suffix `.template` away.

   **Brownfield change mode:** the `change` skill scaffolds one bundle per change. Pass
   `--change-id <change-id> --size-class standard|micro` and the scaffolder adds those two keys to the
   contract frontmatter (without the flags the output is unchanged); the Planner then validates the
   proposal and contract against the existing spec anchor.

   `bash
   python .agents/skills/task-decomposition/scripts/scaffold_task.py \
     --task-id CHG-001-rate-limit --title "Rate limit login attempts" \
     --tasks-dir ./tasks --change-id CHG-001-rate-limit --size-class micro
   `
4. **Write the contract.** Fill every placeholder in `01-contract.md`. The YAML frontmatter is
   authoritative; the human sections below it explain the same decisions for readers. Do not invent
   entities, components or fields that are absent from the spec. If the spec is silent on a decision,
   record an open question instead of guessing. `02` and `03` are blank role forms with **no template
   tokens**: leave them untouched so a freshly planned bundle can pass Gate 1 before Dev/QA start.
   Never fill another role's workspace pre-emptively. Leave `04` alone: it is derived output that
   starts initialized (`TODO`/`UNASSIGNED`/`None`/retry 0) with an empty event table.
5. **Validate (optional but recommended).** If the `plan-linter` skill is installed, run its helper
   from the plan-linter skill directory:

   `bash
   python scripts/plan_linter.py --tasks-dir <tasks-dir> --json
   `

   Exit codes: `0` pass, `1` violations, `2` usage/config error, `3` unexpected error. Read the JSON
   errors, fix the contracts and rerun.

   **Manual fallback** if the linter is unavailable. Check every item and fix failures by hand:
   - each `01-contract.md` frontmatter has all required keys and no placeholder values;
   - `task_id` equals the directory name; IDs are unique;
   - `touch_files` has 1–3 entries and does not touch `tests/acceptance/`;
   - `estimated_lines` is inside the configured range;
   - `origin_spec_anchor` matches `#sec-[a-z0-9-]+`; `adherence_adrs` has at least one entry;
   - `dod` has type-check, lint, test-file and at least two edge cases;
   - `02`/`03`/`04` exist; the dependency graph has no cycles and no missing task IDs.

6. **Optional semantic review.** Gate 2 is a prompt-only, read-only review by a reviewer agent. It is
   never automated. Use the `plan-linter` skill's Gate 2 reference when that skill is available;
   otherwise perform the equivalent manual pass: re-read each contract against the PRD and tech spec
   and reject anything that the upstream documents do not support.

## Contract frontmatter

`01-contract.md` starts with YAML frontmatter (see `assets/templates/01-contract.template.md`):

| Key | Type | Rule |
| :--- | :--- | :--- |
| `task_id` | string | Required; equals the task directory name. |
| `title` | string | Required; short human title. |
| `module` | string | Owning module or area. |
| `dependencies` | list of strings | Defaults to `[]`; every referenced task must exist. |
| `estimated_lines` | integer | Inside the configured Goldilocks range. |
| `touch_files` | list of `{action, path}` | 1–3 entries; `action` is `create` or `modify`. |
| `origin_spec_anchor` | string | Required; `#sec-[a-z0-9-]+`. |
| `adherence_adrs` | list of strings | Required; at least one ADR. |
| `dod` | object | `type_check`, `lint`, `test_file`, and `edge_cases` with at least two entries. |

The human sections below the frontmatter are for readers; they must not contradict it. An
instantiated `01-contract.md` must contain no unresolved placeholder tokens.

## Templates, references and helper script

- `assets/templates/README.md` — placeholder variables, ownership and edit rules.
- `assets/templates/01-contract.template.md` — contract skeleton (frontmatter first).
- `assets/templates/02-dev-workspace.template.md`, `03-qa-verification.template.md`, `04-process.template.md` — role scaffolds.
- `references/decomposition-rules.md` — detailed slicing, traceability and anti-hallucination rules.
- `references/role-lifecycle.md` — Dev/QA workflow, handoff markers, `04` initial state, event/status mapping and field ownership.
- `scripts/scaffold_task.py` — optional stdlib scaffold helper (exit codes `0`/`1`/`2`/`3`).

## Failure handling

- **Missing input**: stop and report which upstream document is missing; do not reconstruct it.
- **Ambiguous requirement**: turn it into an explicit open question in `01-contract.md` `Notes`; do not invent behavior.
- **Scope conflict**: if a necessary edit falls outside `touch_files`, split the task or escalate to the Planner/owner.
- **Tooling unavailable**: use the manual fallback above; the workflow must not depend on Python or optional tooling.
- **Wrapper/tooling failure**: report the command and exit code; do not silently hand-edit `04-process.md`.

## Honest limits

- `04-process.md` is derived output. The authoritative audit trail is git history plus the repository
  CI audit; no local hook adapter is shipped, and any adopter-provided hook is best-effort and
  bypassable, never a security guarantee.
- The Goldilocks thresholds, forbidden prefixes and required documents are repository conventions;
  they are configurable in the linter config and must not be presented as universal law.
- Gate 2 is a prompt, not a script.
