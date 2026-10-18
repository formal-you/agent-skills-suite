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

| Case ID | Category | Given (Precondition) | When (Trigger / Action) | Then (Expected Observable Outcome) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | Normal path |  |  |  |  |
| TC-02 | Boundary |  |  |  |  |
| TC-03 | Duplicate / replay |  |  |  |  |
| TC-04 | Authorization / security |  |  |  |  |

## 3. Complexity and basis path coverage

Verify that every function modified in `touch_files` satisfies cyclomatic complexity limits ($V(G) \le 10$)
and has at least $V(G)$ independent basis path test cases mapped.

| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |

## 4. Mutation testing and MSI audit

Record mutation testing results for every modified source file declared in `touch_files`.
Ensure the kill ratio satisfies $\text{MSI} \ge 80\%$ ($\ge 90\%$ for security-critical modules).
Every mutant classified as equivalent needs a semantic justification; an unjustified equivalent
mutant may not be excluded from the MSI denominator.

| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |  |  |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine |  |
| Total mutants generated |  |
| Killed mutants |  |
| Timed-out mutants |  |
| Equivalent mutants |  |
| Equivalent mutant justification |  |
| Survived mutants |  |
| Mutation Score Indicator (MSI) |  |

## 5. Execution evidence

Bind the evidence to real artifacts: record the artifact path (relative to the repository root), its
SHA-256 digest, the producing tool version and the UTC timestamp. Leave the provenance rows empty
only while the evidence is not collected yet.

| Field | Value |
| :--- | :--- |
| Command |  |
| Result |  |
| Tests (total / passed / failed) |  |
| Coverage |  |
| Artifact path |  |
| Artifact SHA-256 |  |
| Tool version |  |
| Timestamp (UTC) |  |

## 6. Boundary and anti-cheat audit

- [ ] Every changed path is listed in `01-contract.md` → `touch_files`
- [ ] Dev did not modify `tests/acceptance/` or `01-contract.md`
- [ ] Implementation honors every decision in `adherence_adrs`

## 7. Verdict

Check exactly one box:

- [ ] QA_PASSED
- [ ] REWORK_REQUIRED

## 8. Verdict notes

<!-- Explain the verdict and include complete failure traces for REWORK_REQUIRED. -->

QA signature (only if the project requires one):
