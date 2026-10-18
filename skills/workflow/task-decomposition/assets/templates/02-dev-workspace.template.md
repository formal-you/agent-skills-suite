# Dev Workspace

> Owner: Dev agent; read-only for Planner and QA. This is a blank working record: fill the tables
> and sections below while implementing the task declared in `01-contract.md`.
> Do not edit `01-contract.md`, `03-qa-verification.md` or `04-process.md`.

## 1. Execution metadata

Fill a value only once it is known; empty cells are valid until then.

| Field | Value |
| :--- | :--- |
| Dev agent |  |
| Branch |  |
| Base commit |  |
| Handoff commit |  |
| Handoff time (UTC) |  |

## 2. Implementation notes

<!-- Describe local design decisions, trade-offs and any deviation from the original plan. -->

## 3. Actual changes

Add one row per changed file. Every path must be listed in `01-contract.md` → `touch_files`.

| Action (create/modify) | Path | Approx. lines |
| :--- | :--- | :--- |

| Change summary | Value |
| :--- | :--- |
| Net lines added |  |
| Net lines removed |  |

## 4. Self-verification

Run the exact commands declared in `01-contract.md` → `dod` before handing off.

- [ ] Type check passes (`dod.type_check`)
- [ ] Lint passes (`dod.lint`)
- [ ] Existing project/unit tests pass (acceptance target `dod.test_file` is QA-owned and will be run by QA)
- [ ] Every edge case in `dod.edge_cases` is covered
- [ ] No changed path falls outside `touch_files`

## 5. Handoff to QA

Check the box below only after every self-verification item passes:

- [ ] WAITING_FOR_QA

The handoff event is derived from the checked box by repository tooling. Do not edit
`04-process.md` yourself.

## Implementation deviations

After implementation, list every place where the code ended up different from the contract or the
spec: one row per deviation, or write None in every cell when there are none. Deviation IDs are
DEV-001, DEV-002, ...; Operation is add | modify | remove; Spec anchor is an existing or newly
added #sec-* anchor. Leave this table blank only while the task is still being implemented.

| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |

## 6. Appeal Request

Optional. Complete this block only when raising a structured appeal against a `REWORK_REQUIRED`
verdict; otherwise leave it empty. Dev owns this block and no other role edits it. The
`requested_verdict` value must be exactly one of `CODE_BUG`, `TEST_BUG` or `SPEC_AMBIGUITY`.

```yaml
appeal:
  appeal_id: ""          # AP-001, AP-002, ...
  target_case: ""        # test case ID from 03, for example TC-02
  spec_anchor: ""        # existing or newly added #sec-* anchor the expectation comes from
  reason: ""             # why the QA verdict and the contract/spec disagree
  evidence: ""           # test or source reference with line numbers
  requested_verdict: ""  # CODE_BUG | TEST_BUG | SPEC_AMBIGUITY
```
