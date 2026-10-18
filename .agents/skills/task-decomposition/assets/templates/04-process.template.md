# Task {{TASK_ID}}: Process and Audit Trail (derived)

> **Derived file — do not hand-edit.** This document is generated/derived from task state and from
> the optional repository tooling that appends event rows. The authoritative audit trail is the git
> history plus the repository CI audit (`tools/rbac_audit.py`). If no tooling is available, leave
> this file as initialized and rely on git/CI. Planner, Dev and QA never edit it.
> The initial values below describe the planning state; event/status updates are defined in
> `references/role-lifecycle.md`.

## 1. Status

```yaml
task_id: "{{TASK_ID}}"
macro_status: "TODO"            # TODO | IN_PROGRESS | VERIFYING | REWORKING | BLOCKED | DONE
micro_phase: "UNASSIGNED"       # UNASSIGNED | DEV_CODING | QA_AUDITING | FINISHED
current_lock_holder: "None"     # None | Dev | QA
retry_count: 0                  # integer; tooling increments on rework and caps at the configured limit
last_heartbeat: ""              # ISO-8601 UTC, written by tooling when available
```

## 2. Event Log

Rows are appended by repository tooling only. Do not add, remove or reorder rows manually.

| Event ID | Timestamp (UTC) | Event Code | Actor | Payload / Evidence | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 3. Notes

Operational notes that are not part of the audit trail. Do not record events here; event rows belong
in the table above.
