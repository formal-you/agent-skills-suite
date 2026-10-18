# QA Protocol — Independent Verification

This reference expands the QA workflow in `SKILL.md`. It assumes the task bundle format
`tasks/<task-id>/` and QA-owned acceptance tests.

## 1. Handoff gate

QA starts only when `02-dev-workspace.md` contains:

```markdown
- [x] WAITING_FOR_QA
```

Also confirm the handoff commit in `02` exists, and `01-contract.md` is unchanged since planning
(spot-check the contract/diff). If the marker or commit is missing, return the task with the exact
gap rather than signing off.

## 2. Test design (before reading the implementation)

Read the contract's DoD, `edge_cases`, `touch_files` and inherited ADRs. Then design independent
black-box tests. A reasonable minimum matrix:

| Case | Purpose | Example |
| :--- | :--- | :--- |
| Normal path | Required behavior works | valid input returns the documented result |
| Boundary / invalid | Bad input is rejected correctly | empty, null, oversized, wrong type |
| Duplicate / replay | Idempotency/consistency | repeated request does not create duplicates |
| Authorization / security | Access control | unauthorized actor is denied, no leakage |

Each case gets a stable ID (`TC-01`…), a scenario, an expected observable result and a status.

## 3. Evidence

For every run record:

- exact command;
- environment/commit;
- total / passed / failed counts;
- failure output or traces (complete, not paraphrased);
- coverage if the project reports it.

A verdict without a command and result is not evidence. If a test cannot run, say why and do not
treat it as passed.

## 4. Anti-cheat / blast-radius audit

- Every changed path is in `01` → `touch_files` (use `git diff --name-only <base>...HEAD`).
- Dev did not modify `tests/acceptance/` or `01-contract.md`.
- The implementation honors `adherence_adrs`; note any deviation as a finding.
- No out-of-scope generated files, lockfile churn or dependency changes beyond the contract.

## 5. Verdict

Exactly one marker:

- `- [x] QA_PASSED` — every test passes, evidence is recorded, audit is clean.
- `- [x] REWORK_REQUIRED` — at least one failure or audit violation; include complete traces and
  the expected fix.

Never tick both, never leave both empty. Record the attempt/round and timestamp so the history is
reproducible.

## 6. Rework loop

Keep prior attempts and evidence. On the next handoff:

1. update attempt metadata;
2. re-run the full matrix (not only the previously failing case);
3. issue a fresh verdict.

Repeated rework is a planning/scope signal. Escalate with evidence instead of lowering the bar or
editing source to make tests pass.

## 7. `04-process.md`

Derived output only. Optional tooling reacts to the checked verdict:

| Checked marker | Event code | Status | Lock holder | Retry |
| :--- | :--- | :--- | :--- | :--- |
| `WAITING_FOR_QA` (02) | `HANDOFF_QA_REQUESTED` | `VERIFYING` | `QAAgent` | unchanged |
| `QA_PASSED` | `TASK_TERMINATED_DONE` | `DONE` | `None` | unchanged |
| `REWORK_REQUIRED` | `REWORK_TRIGGERED` | `REWORKING` | `DevAgent` | +1, capped |

Never hand-edit `04`. Without tooling, rely on git/CI and the checked box.
