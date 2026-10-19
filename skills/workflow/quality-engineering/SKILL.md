---
name: quality-engineering
description: "Build CI pipelines and manage multi-stage testing gates: configure test environments, enforce pre-merge PR automated checks (Gate 1, RBAC, complexity, acceptance tests, Gate 3 audit) and post-merge automated verification. Use when configuring CI pipelines, provisioning test environments, or running automated pre-merge/post-merge quality gates. Do not use for local task implementation or black-box test authoring."
license: MIT
compatibility: "Harness-agnostic. Core linters standard library only; multi-language complexity uses optional tree-sitter/lizard with a Python AST fallback. Python >= 3.9."
metadata:
  version: "2.2.0"
  category: execution
---

# Quality Engineering — CI Pipelines & Multi-Stage Testing Gates

Build, configure, and maintain authoritative Continuous Integration (CI) pipelines and multi-stage
quality gates. This skill provides the automation and gating infrastructure that governs code
transitions from local development through pull request evaluation to post-merge verification:

```
Stage 1: Local Testing (Dev & QA)
    → Stage 2: Test Environment (Sandbox Isolation & Dependencies)
    → Stage 3: Pre-Merge PR Gate (Gate 1, RBAC, Complexity, Acceptance, Gate 3 Audit)
    → Stage 4: Post-Merge & Convergence (Mainline Regression, Spec Write-back)
```

## Core Responsibilities

1. **Test environment configuration and validation**:
   - Provision isolated, reproducible test environments (containers, sandboxes, matrix runners).
   - Verify toolchain dependencies, runtime versions, external services (DB, cache), and network mocks.
   - Validate environment readiness before running automated test suites.
2. **Pre-merge PR automated checks (Authoritative L1/L2 Quality Gates)**:
   - **Gate 1 (Plan Linter)**: Deterministically validate contract formatting, Given-When-Then BDD scenarios,
     task sizing (50–250 diff lines, 1–3 files), spec anchor coverage, and DAG acyclicity.
   - **RBAC boundary audit**: Diff PR commits to strictly prevent Dev from editing acceptance tests, QA
     from editing source, and non-planners from editing contracts.
   - **Static complexity check**: Enforce Tree-sitter / Lizard multi-language single-function cyclomatic
     complexity ($V(G) \le 10$, warning $11-15$, critical $> 15$ blocks build across Python, JS/TS, Go, Rust, Java, C/C++).
   - **Acceptance test suite execution**: Run black-box integration and acceptance test suites (BDD Given-When-Then
     runners: pytest-bdd, Cucumber.js, Godog, etc.) against clean source with 100% pass requirement.
   - **Gate 3 (Verification Linter audit)**: Deterministically audit `03-qa-verification.md` for basis
     path coverage ($\text{Test Cases} \ge V(G)$) and mutation testing kill ratios ($\text{MSI} \ge 80\%$).
3. **Post-merge automated checks and pipelines**:
   - Execute full trunk regression suites upon branch merge (`push` to main/master).
   - Automate spec convergence (`converge.py apply`) to fold confirmed deviations back into specs.
   - Maintain long-term mutation score baselines, test efficacy trends, and performance benchmarks.
4. **Self-contained CI toolbox (bundled, no external checkout)**:
   - Ship the four gate scripts under `scripts/`: `complexity_check.py` (Tree-sitter/Lizard/AST),
     `verification_linter.py` (Gate 3), `rbac_audit.py` (role boundaries), `mutation_gate.py`
     (fail-closed MSI).
   - Ship the production-ready workflows (`quality-gate.yml`, `plan-gate.yml`, `rbac-gate.yml`),
     stack profiles and config example under `assets/templates/ci/`. On adoption, read them from
     this skill directory and write them into the project's `.github/workflows/`.
5. **Test-strategy mapping (implementation, not definition)**:
   - Map the approved test strategy to CI profiles/job selection/thresholds/environment services; do not invent test standards.
   - The `test-engineering` skill defines risk classes, levels, data/environment, flakiness and metric definitions; this skill implements them in CI.

## Use when

- Setting up or updating CI pipelines and automated workflows for a repository.
- Configuring and validating test environments, runner matrices, or test container dependencies.
- Running or debugging automated pre-merge quality gates on pull requests.
- Running post-merge regression, spec convergence, or mutation baseline tracking on trunk.
- Auditing QA verification artifacts (`03-qa-verification.md`) via Gate 3 (`verification_linter.py`).
- Adopting the bundled CI templates: read them from `assets/templates/ci/` and write them into the
  project's `.github/workflows/`; other stacks start from the shipped profile fragments (Python,
  Node/TS, Go, Java, Rust, .NET, C/C++).

## Do not use when

- Local development stage testing or black-box test authoring — that belongs to `qa`.
- Implementing production features or refactoring code — that belongs to `dev`.
- Planning, task slicing, or contract authoring — that belongs to `task-decomposition` / `planner`.
- Semantic anti-hallucination review — that belongs to `review` (Gate 2).

## Inputs

- CI workflow definitions (`quality-gate.yml`, etc.) and runner environment configurations.
- Git PR commit range (`--base`, `--head`) and role context (`Agent-Role` trailer).
- `tasks/<task-id>/03-qa-verification.md` — QA-filled sections (Complexity, Mutation MSI, Evidence).
- Test environment requirements, container configs, and environment dependency manifests.
- Project test strategy (read-only; created in the adopting project): risk classes, test levels,
  data/environment policy, flakiness rules and metric definitions. When absent, keep the project's
  existing CI conventions.

## Outputs

- CI pipeline definitions, workflow execution logs, and step summaries.
- Machine-readable Gate 3 audit report (`--json`) and pass/fail exit codes.
- Pre-merge check statuses (Gate 1, RBAC, Complexity, Acceptance, Gate 3); post-merge triggers.

## CLI & Tooling

Every script is standard-library Python >= 3.9 and resolves data from the skill directory, so a
global install works without a repository checkout. Run them from the project root:

```bash
# Gate 3 audit (human-readable), then cross-validated with the live AST artifact
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks --actual-complexity artifacts/complexity-report.json --require-actual-complexity --strict --json

# Gate 3 audit requiring evidence provenance (artifact path + SHA-256)
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks --require-provenance --strict --json

# Complexity report (fail-closed; explicit source directory)
python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json > artifacts/complexity-report.json

# RBAC boundary audit across a git range (authoritative L1 in CI)
python .agents/skills/quality-engineering/scripts/rbac_audit.py --base origin/main --head HEAD --tasks-dir ./tasks --json

# Fail-closed mutation gate on trunk (runs the project's mutation command)
python .agents/skills/quality-engineering/scripts/mutation_gate.py run --command "$MUTATION_COMMAND" --report artifacts/mutation-report.json --min-msi 80
```

Local-only `verification_linter.py` escape hatches (`--min-msi`, `--no-mutation`) never belong in
authoritative CI.

## Bundled CI templates

Read the workflows from `assets/templates/ci/` and write them into the project's
`.github/workflows/`. The templates invoke `.agents/skills/quality-engineering/scripts/...`, so
install the skill at the default `.agents/skills/` location; `quickstart.py --with-ci` installs both.
Details, stack profiles and troubleshooting:
[`assets/templates/ci/README.md`](assets/templates/ci/README.md).

## Exit codes

`0` pass, `1` gate violation, `2` usage/configuration error, `3` unexpected internal error.

## Error codes (Gate 3 `errors[].code`)

| Code | Trigger |
| :--- | :--- |
| `COMPLEXITY_MISSING_SECTION` | Section 3 absent or has no data rows when QA_PASSED |
| `COMPLEXITY_EXCEEDS_MAX_THRESHOLD` | V(G) > 15 (absolute prohibition) |
| `COMPLEXITY_BASIS_PATH_INSUFFICIENT` | Test Cases < actual V(G) |
| `COMPLEXITY_REPORT_MISSING` | `--require-actual-complexity` without a usable AST report |
| `COMPLEXITY_FUNCTION_MISSING_IN_03` | A `touch_files` function in the AST report is absent from Section 3 |
| `COMPLEXITY_MISMATCH_WITH_AST` | Section 3 reports a different V(G) than the AST report |
| `COMPLEXITY_PHANTOM_FUNCTION` | Section 3 lists a function absent from the AST report |
| `QA_MISSING_MUTATION_EVIDENCE` | Section 4 absent or has no data rows when QA_PASSED |
| `QA_INVALID_MSI_SCORE` | Missing/non-numeric MSI, or MSI below the threshold (80%; 90% core) |
| `MUTATION_TABLE_INCONSISTENT` | Populated mutation tables disagree, or a populated table has a blank companion |
| `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING` | `Equivalent > 0` but no justification, with `--require-provenance` |
| `EVIDENCE_MISSING_COMMAND` | Execution evidence Command field is blank |
| `EVIDENCE_MISSING_RESULT` | Execution evidence Result field is blank |
| `EVIDENCE_MISSING_ARTIFACT` | Provenance is required but the artifact path is blank/missing |
| `EVIDENCE_HASH_INVALID` | Provenance SHA-256 is missing or does not match the artifact |

## Warning codes (Gate 3 `warnings[].code`)

| Code | Trigger |
| :--- | :--- |
| `COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD` | V(G) 11–15; passes but requires justification in `02` |
| `TOUCH_FILES_UNREADABLE` | `touch_files` could not be parsed from `01-contract.md`; cross-validation is incomplete |

## Multi-Stage CI Pipeline Architecture

The four stages (local test -> test environment -> pre-merge PR gate -> post-merge) and their
enforcement tools are defined in [`references/verification-protocol.md`](references/verification-protocol.md)
section 2; this skill owns the workflows and scripts that implement them.

## Failure Triage & Routing

Read [`references/triage-routing.md`](references/triage-routing.md) after a gate failure. It maps
each deterministic error code to its owner, first action, escalation trigger and forbidden shortcut.
The short rule is: complexity mismatch/missing function -> `qa` (re-fill Section 3 from the AST
artifact); low MSI -> `qa`/`dev` (strengthen assertions or remove dead code); missing artifact/hash ->
`qa` (record real provenance); CI wiring/artifact problems -> `quality-engineering`; repeated
fabrication or an unresolvable spec conflict -> escalate to the orchestrator.

## References

- [`references/verification-protocol.md`](references/verification-protocol.md) — multi-stage CI
  testing pipeline architecture, test environment protocol, Gate 3 evidence audit rules and the
  normalized mutation-report schema.
- [`references/triage-routing.md`](references/triage-routing.md) — error-code to owner/action
  routing, escalation rules and forbidden shortcuts.
- Complexity checker: [`scripts/complexity_check.py`](scripts/complexity_check.py) — deterministic
  AST cyclomatic complexity check tool. Standard-library Python AST fallback; optional
  tree-sitter/lizard engines for multi-language analysis (Python >= 3.9).
- Gate 3 auditor: [`scripts/verification_linter.py`](scripts/verification_linter.py) — deterministic
  audit tool (standard library only, Python >= 3.9).
- Gate helpers: [`scripts/rbac_audit.py`](scripts/rbac_audit.py) (git-diff role boundaries) and
  [`scripts/mutation_gate.py`](scripts/mutation_gate.py) (fail-closed MSI gate).
- CI workflows and stack profiles: [`assets/templates/ci/`](assets/templates/ci/README.md) — the
  `quality-gate.yml` reference pipeline plus `plan-gate.yml`, `rbac-gate.yml`, seven stack profile
  fragments and a config example. They are copy-and-adapt templates, not standalone workflows.
- Sister skill: `qa` — local development stage testing and verification evidence generation.

## Honest limits

Gate 3 now cross-checks Section 3 V(G) against the CI-uploaded AST artifact and fails on omitted,
phantom or mismatched functions. It still trusts the mutation evidence recorded in `03`; the
fail-closed `mutation_gate.py` run on trunk is what actually executes the mutation tool.
Local prompt rules and `--no-mutation`/relaxed thresholds are advisory escape hatches, not
enforcement. True quality assurance requires combining local QA execution with authoritative CI
enforcement plus branch protection. The suite no longer ships duplicate repo-level copies of the
gate scripts: install this skill, not a separate toolbox.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
