---
name: quality-engineering
description: "Build CI pipelines and manage multi-stage testing gates: configure test environments, enforce pre-merge PR automated checks (Gate 1, RBAC, complexity, acceptance tests, Gate 3 audit) and post-merge automated verification. Use when configuring CI pipelines, provisioning test environments, or running automated pre-merge/post-merge quality gates. Do not use for local task implementation or black-box test authoring."
license: MIT
compatibility: "Harness-agnostic. Standard library only. Python >= 3.9."
metadata:
  version: "2.0.0"
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
4. **Authoritative CI templates & tooling**:
   - Maintain production-ready CI workflows (`quality-gate.yml`, `plan-gate.yml`, `rbac-gate.yml`).
   - Maintain the Tree-sitter powered multi-language cyclomatic complexity checker (`complexity_check.py`).
   - Maintain the deterministic Gate 3 verification auditor (`verification_linter.py`).

## Use when

- Setting up or updating CI pipelines and automated workflows for a repository.
- Configuring and validating test environments, runner matrices, or test container dependencies.
- Running or debugging automated pre-merge quality gates on pull requests.
- Running post-merge regression, spec convergence, or mutation baseline tracking on trunk.
- Auditing QA verification artifacts (`03-qa-verification.md`) via Gate 3 (`verification_linter.py`).

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

## Outputs

- CI pipeline definitions, workflow execution logs, and step summaries.
- Machine-readable Gate 3 audit report (`--json`) and pass/fail exit codes.
- Pre-merge check statuses (Gate 1, RBAC, Complexity, Acceptance, Gate 3).
- Post-merge regression and convergence triggers.

## CLI & Tooling

```bash
# Gate 3 verification linter (human-readable)
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks

# Cyclomatic complexity check (AST McCabe V(G) <= 10)
python .agents/skills/quality-engineering/scripts/complexity_check.py --json

# Machine-readable JSON for CI gating
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks --json --min-msi 80

# Relax mutation threshold (e.g. for legacy codebases)
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks --json --min-msi 60

# Skip mutation check (when tool is not yet integrated)
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks --no-mutation
```

## Exit codes

| Code | Meaning |
| :--- | :--- |
| `0` | All audited checks and task bundles pass |
| `1` | One or more gate violations (fails CI build) |
| `2` | Usage or configuration error |
| `3` | Unexpected internal error |

## Error codes (Gate 3 `errors[].code`)

| Code | Trigger |
| :--- | :--- |
| `COMPLEXITY_MISSING_SECTION` | Section 3 absent or has no data rows when QA_PASSED |
| `COMPLEXITY_EXCEEDS_MAX_THRESHOLD` | V(G) > 15 (absolute prohibition) |
| `BASIS_PATH_INSUFFICIENT` | Test Cases < V(G) |
| `MUTATION_MISSING_SECTION` | Section 4 absent when QA_PASSED |
| `MUTATION_NO_SCORE` | No MSI or killed/total counts found in Section 4 |
| `MUTATION_SCORE_BELOW_THRESHOLD` | MSI < min_msi (default 80%) |
| `EVIDENCE_MISSING_COMMAND` | Execution evidence Command field is blank |
| `EVIDENCE_MISSING_RESULT` | Execution evidence Result field is blank |

## Warning codes (Gate 3 `warnings[].code`)

| Code | Trigger |
| :--- | :--- |
| `COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD` | V(G) 11–15; passes but requires justification in `02` |
| `MUTATION_SCORE_MARGINAL` | MSI passes but is below 90% |

## Multi-Stage CI Pipeline Architecture

| Stage | Responsibility | Enforcement Tool | Scope |
| :--- | :--- | :--- | :--- |
| **Stage 1: Local Test** | Integration, BDD E2E, Mutation, Lint, Complexity | Dev & QA local tools | Pre-commit |
| **Stage 2: Test Env** | Environment readiness, isolation, mock validation | Docker, runner setup | PR setup |
| **Stage 3: Pre-merge PR** | Gate 1, RBAC, Complexity, Acceptance, Gate 3 | `quality-gate.yml` | Pull Request |
| **Stage 4: Post-merge** | Trunk regression, spec convergence, MSI baseline | Mainline CI workflows | Post-merge |

## References

- [`references/verification-protocol.md`](references/verification-protocol.md) — multi-stage CI
  testing pipeline architecture, test environment protocol, and Gate 3 evidence audit rules.
- Complexity checker: [`scripts/complexity_check.py`](scripts/complexity_check.py) — deterministic
  AST cyclomatic complexity check tool (standard library only, Python >= 3.9).
- Gate 3 auditor: [`scripts/verification_linter.py`](scripts/verification_linter.py) — deterministic
  audit tool (standard library only, Python >= 3.9).
- CI workflow template: `quality-gate.yml` — unified multi-stage CI quality gate.
- Sister skill: `qa` — local development stage testing and verification evidence generation.

## Honest limits

CI gates and verification linters audit submitted code, PR diffs, and evidence in `03-qa-verification.md`.
While Gate 1, RBAC, Complexity, and Acceptance tests run live code and diffs, Gate 3 relies on
recorded test and mutation metrics. True quality assurance requires combining local QA execution with
authoritative CI enforcement and branch protection.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
