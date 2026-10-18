# Gate Failure Triage & Routing

Use this table when a deterministic gate fails. Route the failure to the first owner, require the
listed action, and escalate when the same condition repeats. Never "fix" a gate by editing the
evidence, weakening the threshold, deleting a test, or wrapping the command in `|| true`.

| Code | Emitted by | Owner | First action | Escalate after | Never do |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `COMPLEXITY_MISSING_SECTION` | Gate 3 | `qa` | Fill Section 3 for every `touch_files` function | Second omission -> orchestrator | Leave the section blank while ticking `QA_PASSED` |
| `COMPLEXITY_EXCEEDS_MAX_THRESHOLD` | Gate 3 | `dev` | Refactor the function below `V(G) > 15` | Cannot split -> `planner` re-slices the task | Lower the threshold or omit the function |
| `COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD` (warning) | Gate 3 | `dev` | Justify in `02`; consider refactoring | Repeated warning -> `planner` | Ignore it silently |
| `COMPLEXITY_BASIS_PATH_INSUFFICIENT` | Gate 3 | `qa` | Add independent-path tests until `Test Cases >= V(G)` | Untestable path -> `dev`/`planner` | Count the same test ID twice |
| `COMPLEXITY_REPORT_MISSING` | Gate 3 | `quality-engineering` | Upload the AST artifact and pass `--actual-complexity` | CI config error -> orchestrator | Run Gate 3 without a report in CI |
| `COMPLEXITY_FUNCTION_MISSING_IN_03` | Gate 3 | `qa` | Add every AST function in `touch_files` to Section 3 | Second omission -> orchestrator | Delete the function from `touch_files` |
| `COMPLEXITY_MISMATCH_WITH_AST` | Gate 3 | `qa` | Re-read the AST report and correct Section 3 | Second mismatch -> orchestrator | "Adjust" the AST report to the prose |
| `COMPLEXITY_PHANTOM_FUNCTION` | Gate 3 | `qa` | Remove or correct the nonexistent function row | Fabricated row -> orchestrator | Invent a function to pad the table |
| `QA_MISSING_MUTATION_EVIDENCE` | Gate 3 | `qa` | Fill Section 4 with the real tool and counts | Tool unavailable -> `quality-engineering` | Use a synthetic claim without a tool |
| `QA_INVALID_MSI_SCORE` | Gate 3 | `qa` | Strengthen assertions or remove dead code until MSI passes | Still low -> `planner` | Inflate "Equivalent" without justification |
| `MUTATION_TABLE_INCONSISTENT` | Gate 3 | `qa` | Make every populated table agree on MSI and totals | Repeated -> orchestrator | Keep two conflicting summaries |
| `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING` | Gate 3 | `qa` | Explain why the mutant is semantically equivalent | Abuse -> orchestrator | Declare mutants equivalent without evidence |
| `EVIDENCE_MISSING_COMMAND` | Gate 3 | `qa` | Record the exact command that ran | — | Paste a paraphrase |
| `EVIDENCE_MISSING_RESULT` | Gate 3 | `qa` | Record the real result/counts | — | Claim success without output |
| `EVIDENCE_MISSING_ARTIFACT` | Gate 3 | `qa` | Point Section 5 at a real artifact under the repo root | CI artifact transfer bug -> `quality-engineering` | Use a placeholder path |
| `EVIDENCE_HASH_INVALID` | Gate 3 | `qa` | Recompute the SHA-256 of the artifact | Mismatch repeats -> orchestrator | Edit the hash to match a stale file |
| `TOUCH_FILES_UNREADABLE` (warning) | Gate 3 | `planner` | Make `touch_files` parseable in `01-contract.md` | Repeated -> orchestrator | Skip cross-validation silently |
| `MUTATION_REPORT_MISSING` | Mutation gate | `quality-engineering` | Configure `MUTATION_COMMAND` to write the normalized report | No tool for the stack -> lead decision | Set the job to `continue-on-error` |
| `MUTATION_REPORT_INVALID` | Mutation gate | `quality-engineering` | Fix the report adapter/schema | Repeated -> lead | Edit MSI by hand |
| `MUTATION_THRESHOLD_FAILED` | Mutation gate | `qa`/`dev` | Kill survivors or remove dead code | Still below threshold -> `planner` | Lower `--min-msi` in CI |
| `MUTATION_COMMAND_FAILED` | Mutation gate | `quality-engineering` | Fix the runner command/environment | Environment unavailable -> lead | Swallow the exit code |
| `DEV_EDITED_ACCEPTANCE_TESTS` | RBAC | `dev` | Revert the acceptance-test edits | Repeated -> orchestrator | Delete the failing test |
| `QA_EDITED_SOURCE` | RBAC | `qa` | Revert the source edits | Repeated -> orchestrator | "Fix" implementation to pass |
| `CONTRACT_EDITED_BY_NON_PLANNER` | RBAC | `planner` | Rewrite the contract under the planner role | Repeated -> orchestrator | Edit the contract from Dev/QA |
| `TEST_REPORT_MISMATCH` (future) | Gate 3 | `qa` | Reconcile the JUnit artifact with Section 5 | Repeated -> orchestrator | Fabricate test counts |

## Escalation Rules

1. The first failure returns to the owner in the table; do not reassign silently.
2. A second identical failure on the same task escalates to the orchestrator/lead with both failure
   reports and the attempted fixes.
3. A third rework round, or a second appeal on the same task, circuit-breaks to the planner/human.
4. `SPEC_AMBIGUITY` from an appeal goes to the planner; do not resolve it by changing tests to match
   the implementation.
