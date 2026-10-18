# Task Templates — Variables and Ownership

This directory is the single source for the four task-bundle documents. Copy them with
`scripts/scaffold_task.py` or by hand; do not maintain copies elsewhere.

## Ownership and edit rules

| Template | Instantiated file | Owner after planning | Edit rule |
| :--- | :--- | :--- | :--- |
| `01-contract.template.md` | `tasks/<task-id>/01-contract.md` | Planner | Read-only for Dev and QA |
| `02-dev-workspace.template.md` | `tasks/<task-id>/02-dev-workspace.md` | Dev | Read-only for Planner and QA |
| `03-qa-verification.template.md` | `tasks/<task-id>/03-qa-verification.md` | QA | Read-only for Planner and Dev |
| `04-process.template.md` | `tasks/<task-id>/04-process.md` | Repository tooling | Never hand-edited by agents |

## Rules

1. `01-contract.md` starts with YAML frontmatter; it is authoritative. `task_id` must equal the task
   directory name. `touch_files` has 1–3 entries; `estimated_lines` defaults to the 50–250 range;
   `origin_spec_anchor` matches `#sec-[a-z0-9-]+`; `adherence_adrs` has at least one ADR.
2. `01` must contain **no** unresolved placeholder tokens after planning. `02` and `03` are blank
   role forms: they contain no template tokens, so Gate 1 can pass before Dev/QA start. `04` is
   initialized with concrete status values by this template (only `{{TASK_ID}}` is substituted by the
   scaffolder) and is outside the Gate 1 placeholder scan.
3. `02` and `03` contain real Markdown checkboxes. The templates contain only unchecked boxes
   (`- [ ]`); they never contain a checked-box marker. Tooling detects a checked box, so do not add a
   second marker line.
4. `04` is derived output. It starts at `macro_status: TODO`, `micro_phase: UNASSIGNED`,
   `current_lock_holder: None`, `retry_count: 0`, empty heartbeat, and an event table with only the
   header and separator. Tooling appends rows. Never paste sample events, lifecycle rows or fake
   timestamps into it.
5. Wording stays domain-neutral. In `01`, infrastructure, entities, identifiers and thresholds
   are placeholders, never example values. `02` and `03` contain empty fields only. `04` contains
   only neutral lifecycle values and tooling-owned fields.

## Placeholder variables

Format: `{{UPPER_SNAKE}}`. Planner-filled tokens appear only in `01-contract.template.md`.
`04-process.template.md` contains only `{{TASK_ID}}` (substituted by the scaffolder) and is otherwise
initialized with concrete lifecycle values; it is not scanned by Gate 1. Replace values without
leaving the braces. The numeric `estimated_lines` field is unquoted in YAML; replace the token with
an integer. `retry_count` is not a placeholder: the template initialises it to `0` and tooling
increments it.

### 01-contract.template.md

| Variable | Meaning |
| :--- | :--- |
| `{{TASK_ID}}` | Directory/contract ID; must equal the task directory name (for example `task-001-auth`). |
| `{{TASK_TITLE}}` | Short human title of the task. |
| `{{MODULE_NAME}}` | Owning module or area. |
| `{{ESTIMATED_LINES}}` | Estimated net diff lines; integer within the configured range. |
| `{{TOUCH_FILE_1}}` / `{{TOUCH_FILE_2}}` | Allowed create/modify paths; 1–3 total. |
| `{{MODULE_SLUG}}` | Lowercase slug used in `#sec-<slug>`. |
| `{{ADR_ID_1}}` | Inherited ADR ID; add more `adherence_adrs` items when needed. |
| `{{TYPE_CHECK_COMMAND}}` | Type-check command that must exit 0. |
| `{{LINT_COMMAND}}` | Lint command that must exit 0. |
| `{{TEST_FILE_PATH}}` | Acceptance test file owned by QA. |
| `{{EDGE_CASE_1}}` / `{{EDGE_CASE_2}}` | At least two edge/negative assertions. |
| `{{GOAL_AND_SCOPE}}` | One-paragraph goal and scope. |
| `{{OUT_OF_SCOPE}}` | Explicit non-goals. |
| `{{INVARIANT_INPUT_VALIDATION}}` | Input-validation invariant. |
| `{{INVARIANT_STATE_TRANSITIONS}}` | State-transition invariant. |
| `{{INVARIANT_IDEMPOTENCY}}` | Idempotency/consistency invariant. |
| `{{INHERITED_ADR_SUMMARY}}` | One-line summary of inherited ADR decisions. |
| `{{NOTES}}` | Open questions or notes for the implementer. |

### 02-dev-workspace.template.md and 03-qa-verification.template.md

These two files are blank role workspaces, not placeholder forms: Dev and QA fill the empty table
cells and prose sections in place. They intentionally contain **no** template tokens (no double-brace
fields, no stub markers) so a freshly planned bundle can pass Gate 1 before implementation starts.

### 04-process.template.md

The template starts from a concrete planning state; the scaffolder only substitutes `{{TASK_ID}}`.

| Field | Initial value | Updated by |
| :--- | :--- | :--- |
| `macro_status` | `TODO` | event tooling (`VERIFYING` / `REWORKING` / `DONE`) |
| `micro_phase` | `UNASSIGNED` | tooling or a manual tooling job |
| `current_lock_holder` | `None` | event tooling (`QAAgent` / `DevAgent`) |
| `retry_count` | `0` | event tooling on rework, capped |
| `last_heartbeat` | `""` | tooling when available |

The event table starts with header + separator only. Event codes, status transitions and the
Dev/QA lifecycle are defined in [`references/role-lifecycle.md`](../../references/role-lifecycle.md).

## Placeholder conventions

- `{{UPPER_SNAKE}}` — planner-filled tokens only in `01-contract.template.md`; `04` contains only
  `{{TASK_ID}}`, substituted by the scaffolder. Replace values; never rename a token.
- `<angle-bracket>` — replace with a value in prose/examples where no YAML token is needed.
- `02` and `03` contain no tokens; fill their empty cells and rows directly.
- No value in this directory is domain-specific: infrastructure, entities and thresholds are the
  target repository's decision, not the template's.
