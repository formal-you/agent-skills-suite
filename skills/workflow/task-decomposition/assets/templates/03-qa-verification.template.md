# QA Verification

> Owner: QA agent; read-only for Planner and Dev. Fill the matrix and evidence below while verifying
> the task declared in `01-contract.md`.
> Do not edit `01-contract.md`, `02-dev-workspace.md` or `04-process.md`.

## 1. Verification metadata

Fill a value only once it is known; empty cells are valid until then.

| Field | Value |
| :--- | :--- |
| QA agent |  |
| Reviewed commit |  |
| Environment |  |
| Attempt |  |
| Verdict time (UTC) |  |

## 2. Test matrix

Acceptance tests live under `tests/acceptance/` and are authored by QA only. Add one row per case;
do not read the implementation before writing the black-box assertions.

| Case ID | Category | Scenario / attack vector | Expected result | Status |
| :--- | :--- | :--- | :--- | :--- |
| TC-01 | Normal path |  |  |  |
| TC-02 | Boundary |  |  |  |
| TC-03 | Duplicate / replay |  |  |  |
| TC-04 | Authorization / security |  |  |  |

## 3. Execution evidence

| Field | Value |
| :--- | :--- |
| Command |  |
| Result |  |
| Tests (total / passed / failed) |  |
| Coverage |  |

## 4. Boundary and anti-cheat audit

- [ ] Every changed path is listed in `01-contract.md` → `touch_files`
- [ ] Dev did not modify `tests/acceptance/` or `01-contract.md`
- [ ] Implementation honors every decision in `adherence_adrs`

## 5. Verdict

Check exactly one box:

- [ ] QA_PASSED
- [ ] REWORK_REQUIRED

## 6. Verdict notes

<!-- Explain the verdict and include complete failure traces for REWORK_REQUIRED. -->

QA signature (only if the project requires one):
