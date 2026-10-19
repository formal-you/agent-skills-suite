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
| `MUTATION_MISMATCH_WITH_REPORT` | Gate 3 | `qa` | Re-fill Section 4 aggregates and per-target rows from the real normalized mutation report | Second mismatch -> orchestrator | Edit the report or the prose so they "agree" |
| `MUTATION_PHANTOM_TARGET` | Gate 3 | `qa` | Remove or correct the target row that the real report does not contain | Fabricated target -> orchestrator | Invent a target to look thorough |
| `MUTATION_TARGET_MISSING_IN_03` | Gate 3 | `qa` | Add the missing report target row with its real counts/MSI | Second omission -> orchestrator | Drop the target from the mutation run |
| `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING` | Gate 3 | `qa` | Explain why the mutant is semantically equivalent | Abuse -> orchestrator | Declare mutants equivalent without evidence |
| `EVIDENCE_MISSING_COMMAND` | Gate 3 | `qa` | Record the exact command that ran | — | Paste a paraphrase |
| `EVIDENCE_MISSING_RESULT` | Gate 3 | `qa` | Record the real result/counts | — | Claim success without output |
| `EVIDENCE_MISSING_ARTIFACT` | Gate 3 | `qa` | Point Section 5 at a real artifact under the repo root | CI artifact transfer bug -> `quality-engineering` | Use a placeholder path |
| `EVIDENCE_HASH_INVALID` | Gate 3 | `qa` | Recompute the SHA-256 of the artifact | Mismatch repeats -> orchestrator | Edit the hash to match a stale file |
| `TOUCH_FILES_UNREADABLE` (warning) | Gate 3 | `planner` | Make `touch_files` parseable in `01-contract.md` | Repeated -> orchestrator | Skip cross-validation silently |
| `MUTATION_REPORT_MISSING` | Gate 3 / Mutation gate | `quality-engineering` | Ensure the mutation job wrote and uploaded `artifacts/mutation-report.json` and Gate 3 downloaded it; pass `--actual-mutation` / configure `quality-gate.config.json` (`mutation.command`, `mutation.report`) | CI wiring bug repeats -> orchestrator | Run Gate 3 without the report in CI or make the mutation job non-blocking |
| `MUTATION_REPORT_INVALID` | Mutation gate | `quality-engineering` | Fix the report adapter/schema | Repeated -> lead | Edit MSI by hand |
| `MUTATION_THRESHOLD_FAILED` | Mutation gate | `qa`/`dev` | Kill survivors or remove dead code | Still below threshold -> `planner` | Lower `--min-msi` in CI |
| `MUTATION_COMMAND_FAILED` | Mutation gate | `quality-engineering` | Fix the runner command/environment; commit the real stack command in `quality-gate.config.json` | Environment unavailable -> lead | Swallow the exit code or leave the command unset |
| `DEV_EDITED_ACCEPTANCE_TESTS` | RBAC | `dev` | Revert the acceptance-test edits | Repeated -> orchestrator | Delete the failing test |
| `QA_EDITED_SOURCE` | RBAC | `qa` | Revert the source edits | Repeated -> orchestrator | "Fix" implementation to pass |
| `CONTRACT_EDITED_BY_NON_PLANNER` | RBAC | `planner` | Rewrite the contract under the planner role | Repeated -> orchestrator | Edit the contract from Dev/QA |
| `TEST_REPORT_MISMATCH` (future) | Gate 3 | `qa` | Reconcile the JUnit artifact with Section 5 | Repeated -> orchestrator | Fabricate test counts |

## Config-driven mutation routing

Mutation is config-driven: `mutation_gate.py run --config quality-gate.config.json` resolves
`mutation.command`, `mutation.report` and `mutation.min_msi`, and validates `mutation.core_min_msi`
(numeric, `<= 100`, `>= mutation.min_msi`). Explicit CLI flags override config values, which override
defaults. A missing config, invalid JSON, `schema_version != 1`, an invalid `mutation` object or a
missing command exits `2` and is a **configuration** failure owned by `quality-engineering`: commit
the real per-stack config (`assets/templates/ci/profiles/<stack>.config.json`), never disable the
job, leave the command unset, or mark it non-blocking. Gate 3 enforces the 90% core floor through
`risk_level: core`; only the config records the matching `core_min_msi` floor.

## Branch guard routing (`branch_guard.py`)

Branch-isolation failures come from `scripts/branch_guard.py check --task-dir tasks/<task-id>
--require-declared --json`. Lifecycle, migration runbook and the full option list live in
[`branch-isolation.md`](branch-isolation.md).

| Code | Emitted by | Owner | First action | Escalate after | Never do |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BRANCH_PROTECTED` | Branch guard | `dev` | Create/recreate the task branch from an up-to-date base and re-apply the work | Second breach -> orchestrator | Keep committing on `main`/`master` |
| `BRANCH_PATTERN_INVALID` | Branch guard | `dev` | Rename to `feat/<task-id>` (or the declared convention) | Repeated -> orchestrator | Bypass the guard with `--branch` in CI |
| `BRANCH_DETACHED` | Branch guard | `dev` | Check out the task branch before any work or handoff | Repeated -> orchestrator | Sign off from a detached `HEAD` |
| `BRANCH_DECLARED_MISSING` | Branch guard | `dev` | Record the `Branch` row in `02-dev-workspace.md` | Repeated -> orchestrator | Leave the row blank while handing off |
| `BRANCH_MISMATCH` | Branch guard | `dev` | Re-run the work on the branch declared in `02`, or correct the declaration | Repeated -> orchestrator | Edit `02` to match an unrelated branch |
| `TASK_DOC_MISSING` | Branch guard | `dev`/`planner` | Ensure `02-dev-workspace.md` exists in `tasks/<task-id>` | Repeated -> orchestrator | Delete the record to make the guard pass |
| `BRANCH_NOT_DECLARED` (warning) | Branch guard | `dev` | Record the branch before merge | — | Ignore it silently |

## Escalation Rules

1. The first failure returns to the owner in the table; do not reassign silently.
2. A second identical failure on the same task escalates to the orchestrator/lead with both failure
   reports and the attempted fixes.
3. A third rework round, or a second appeal on the same task, circuit-breaks to the planner/human.
4. `SPEC_AMBIGUITY` from an appeal goes to the planner; do not resolve it by changing tests to match
   the implementation.
