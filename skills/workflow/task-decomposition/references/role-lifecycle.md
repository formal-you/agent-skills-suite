# Task Role Lifecycle: Planner → Dev → QA

This reference defines how the four documents of a task bundle are produced, handed off and audited.
The short version: **the Planner authors the contract, Dev implements and self-tests, QA verifies
independently, and tooling derives `04-process.md`.** This skill owns the bundle format; it does not
replace the adopting repository's role rules.

## 1. Ownership at a glance

| Document | Author / owner | Read-only for | Written during |
| :--- | :--- | :--- | :--- |
| `01-contract.md` | Planner | Dev, QA | planning |
| `02-dev-workspace.md` | Dev | Planner, QA | implementation |
| `03-qa-verification.md` | QA | Planner, Dev | verification |
| `04-process.md` | Repository tooling | all agents | continuously, derived |

`task_id` in `01-contract.md` must equal the task directory name. A role never edits another role's
document; a needed change outside the contract's `touch_files` is a planning signal, not a licence.

## 2. Initial state after planning

The Planner creates the bundle (for example with `scripts/scaffold_task.py`) and fills `01`. The
other three documents are intentionally not "completed" at planning time:

- `02-dev-workspace.md` — blank role form: empty metadata/changes tables, unchecked self-verification
  items, unchecked `WAITING_FOR_QA`. It contains no template tokens.
- `03-qa-verification.md` — blank role form: empty metadata/evidence tables, `TC-01`…`TC-04` rows,
  no verdict selected. It contains no template tokens.
- `04-process.md` — initialized derived file:

  ```yaml
  task_id: "task-001-auth"
  macro_status: "TODO"
  micro_phase: "UNASSIGNED"
  current_lock_holder: "None"
  retry_count: 0
  last_heartbeat: ""
  ```

  Its event table contains only the header and separator. **No initialization event, sample row or
  fake timestamp is written.** The first real event appears when a role checks a lifecycle box and
  the optional tooling runs. The authoritative audit trail is git history plus the CI audit; `04` is
  a derived convenience view.

Gate 1 can therefore pass immediately after the Planner fills `01`: `02`/`03` are token-free blank
forms and `04` is initialized, not half-written.

## 3. Dev workflow

1. **Read the contract.** Read `01-contract.md` (frontmatter is authoritative), its inherited ADRs
   and the relevant spec anchors. Do not edit `01`.
2. **Implement inside the blast radius.** Create/modify only paths listed in `touch_files`. If the
   change needs a file outside that list, stop and escalate; split the task if necessary.
3. **Run the declared DoD.** Execute `dod.type_check`, `dod.lint` and the project's existing tests;
   consider every `dod.edge_cases` item. `dod.test_file` is QA-owned: run it only if it already
   exists, never create or edit `tests/acceptance/**`. If the acceptance target does not exist yet,
   record that in `02` and let QA run it during verification.
4. **Fill `02-dev-workspace.md`.** Record branch/base/handoff commit, implementation notes, one row
   per actual changed file with approximate lines, and net line counts. Do not write another role's
   document.
5. **Self-verify, then hand off.** Tick every self-verification item that is true. Only when all of
   them pass, change `- [ ] WAITING_FOR_QA` to `- [x] WAITING_FOR_QA`. That single checked box is the
   handoff trigger.
6. **Do not touch `03` or `04`.** QA owns the verdict; tooling owns the derived audit file.

## 4. QA workflow

1. **Read the contract and the handoff.** Read `01` for the DoD/ADRs and `02` for what Dev claims.
   Design black-box tests before/without reading the implementation, so the tests are independent.
2. **Write acceptance tests.** QA may create/change only `tests/acceptance/**` and `03-qa-verification.md`.
3. **Execute and record evidence.** Run the declared test command, fill the test matrix (normal,
   boundary, duplicate/replay, authorization/security), record command, totals, failures and coverage.
4. **Audit the blast radius.** Confirm every changed path is in `touch_files`, Dev did not edit tests
   or `01`, and the implementation honors `adherence_adrs`.
5. **Issue exactly one verdict.** Tick `- [x] QA_PASSED` only when tests and audits pass; otherwise
   tick `- [x] REWORK_REQUIRED` and include complete failure traces and the expected fix.
6. **Do not edit source, `02`, or `04`.** If QA finds a defect, the fix goes back through Dev.

## 5. Rework loop

On `REWORK_REQUIRED`:

1. QA leaves the verdict and traces in `03`; Dev reads them and fixes code only inside the contract.
2. Dev updates `02` and re-runs the DoD. The handoff box stays checked for the new attempt (or is
   re-checked after the previous state).
3. QA updates the attempt metadata and verdict in `03`; use a fresh attempt/round value rather than
   deleting previous evidence.
4. Tooling increments `retry_count` (capped by the configured limit). A task that keeps failing is a
   planning or scope problem: escalate instead of bypassing the contract.

## 6. `04-process.md` event contract

Only a **real checked checkbox line** is a trigger. A bare token in prose, an unchecked box or a
template instruction is not. Each event is appended once per task and code (idempotent).

| Checked marker | Event code | `macro_status` | `current_lock_holder` | Retry |
| :--- | :--- | :--- | :--- | :--- |
| `- [x] WAITING_FOR_QA` in `02` | `HANDOFF_QA_REQUESTED` | `VERIFYING` | `QAAgent` | unchanged |
| `- [x] QA_PASSED` in `03` | `TASK_TERMINATED_DONE` | `DONE` | `None` | unchanged |
| `- [x] REWORK_REQUIRED` in `03` | `REWORK_TRIGGERED` | `REWORKING` | `DevAgent` | +1, capped |

Event rows use the table columns: event ID (`EV-AUTO`), timestamp (UTC), event code, actor, payload
and duration. `micro_phase` and `last_heartbeat` are tooling-owned; they are never inferred from prose.

**When no tooling is available**, leave `04` as initialized and rely on git/CI. Do not hand-write
events, invent timestamps or paste lifecycle samples. The repository CI audit (when configured) and
git history remain the source of truth.

## 7. Field ownership in `04`

| Field | Initial value | Updated by |
| :--- | :--- | :--- |
| `task_id` | directory name | never (must match the directory) |
| `macro_status` | `TODO` | event tooling |
| `micro_phase` | `UNASSIGNED` | tooling or manual tooling job |
| `current_lock_holder` | `None` | event tooling |
| `retry_count` | `0` | event tooling on rework |
| `last_heartbeat` | empty string | tooling when available |

## 8. Failure handling

- **Missing upstream document**: stop and report it; do not reconstruct it from memory.
- **Ambiguity**: record an open question in `01` notes and ask the Planner/owner; do not invent.
- **Out-of-scope edit needed**: split the task or escalate; never edit outside `touch_files`.
- **No tooling/Python**: use the manual checklists in `SKILL.md` and this reference; the workflow must
  not depend on optional tooling.
- **Tool failure**: report the command and exit code; never hand-edit `04` to "fix" it.
