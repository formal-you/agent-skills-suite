---
name: quality-engineering
description: "Build CI pipelines and manage multi-stage testing gates: configure test environments, enforce pre-merge PR automated checks (Gate 1, RBAC, complexity, acceptance tests, real mutation, Gate 3 audit) and post-merge automated verification. Use when configuring CI pipelines, provisioning test environments, or running automated pre-merge/post-merge quality gates. Do not use for local task implementation or black-box test authoring."
license: MIT
compatibility: "Harness-agnostic. Core linters standard library only; multi-language complexity uses optional tree-sitter/lizard with a Python AST fallback. Python >= 3.9."
metadata:
  version: "3.0.0"
  category: execution
---

# Quality Engineering — CI Pipelines & Multi-Stage Testing Gates

Build, configure, and maintain authoritative Continuous Integration (CI) pipelines and multi-stage
quality gates: local testing (Dev/QA) -> test environment -> pre-merge PR gate (Gate 1, RBAC,
complexity, acceptance, real mutation, Gate 3 audit) -> post-merge regression and spec convergence.

## Core Responsibilities

1. **Test environment configuration and validation**: provision isolated, reproducible test
   environments (containers, sandboxes, matrix runners); verify toolchains, services and network
   mocks before running suites.
2. **Pre-merge PR automated checks (authoritative L1/L2 quality gates)**:
   - **Gate 1 (Plan Linter)**: validate contract formatting, Gherkin/BDD scenarios, task sizing
     (50–250 diff lines, 1–3 files), spec anchors and DAG acyclicity.
   - **RBAC boundary audit**: diff PR commits so Dev never edits acceptance tests, QA never edits
     source, and non-planners never edit contracts.
   - **Static complexity check**: tree-sitter/lizard multi-language V(G) (≤10 standard, 11–15
     warning, >15 blocks) across Python, JS/TS, Go, Rust, Java and C/C++.
   - **Acceptance test suite execution**: run the project's BDD/acceptance suite (pytest-bdd,
     Cucumber.js, Godog, Cucumber-JVM, ...) with a 100% pass requirement.
   - **Real mutation gate (fail-closed, PR-stage)**: `mutation_gate.py` runs the project's actual
     mutation tool on every pull request and trunk push, enforces MSI ≥ 80% (≥ 90% for
     `risk_level: core`) and fails on a missing command, command failure or missing report.
   - **Gate 3 (Verification Linter)**: audit basis-path coverage (Test Cases ≥ V(G)) and mutation
     evidence, cross-validating Section 3 against the AST artifact and Section 4 against the
     normalized mutation report.
3. **Post-merge automated checks**: full trunk regression on merge, spec convergence
   (`converge.py apply`) and long-term mutation/performance baselines.
4. **Self-contained CI toolbox**: ship the five gate helpers under `scripts/`
   (`complexity_check.py`, `verification_linter.py`, `rbac_audit.py`, `mutation_gate.py`,
   `branch_guard.py`) plus the workflows, stack profiles and config example under
   `assets/templates/ci/`; on adoption, write the workflows into `.github/workflows/`.
5. **Test-strategy mapping (implementation, not definition)**: Map the approved test strategy to CI
   profiles, job selection, thresholds and environment services; do not invent test standards. The
   `test-engineering` skill defines risk classes, levels, data/environment, flakiness and metrics;
   this skill implements them in CI.

## Use when

- Setting up or updating CI pipelines and automated workflows for a repository.
- Configuring test environments, runner matrices, or test container dependencies.
- Running or debugging automated pre-merge quality gates on pull requests.
- Running post-merge regression, spec convergence, or mutation baseline tracking on trunk.
- Auditing QA verification artifacts (`03-qa-verification.md`) via Gate 3 (`verification_linter.py`).
- Adopting the bundled CI templates from `assets/templates/ci/`: other stacks merge the shipped
  profile fragments (Python, Node/TS, Go, Java, Rust, .NET, C/C++) into the reference workflow.

## Do not use when

- Local development stage testing or black-box test authoring — that belongs to `qa`.
- Implementing production features or refactoring code — that belongs to `dev`.
- Planning, task slicing, or contract authoring — that belongs to `task-decomposition` / `planner`.
- Semantic anti-hallucination review — that belongs to `review` (Gate 2).

## Inputs and outputs

- Inputs: CI/runner configuration; the PR commit range (`--base`, `--head`) and `Agent-Role`
  trailer; `tasks/<task-id>/03-qa-verification.md`; the real AST complexity and normalized mutation
  reports; the project test strategy (read-only, defined by `test-engineering` — risk classes, test
  levels, data/environment, flakiness, metrics; keep existing CI conventions when absent).
- Outputs: CI pipeline definitions and step summaries; the machine-readable Gate 3 report (`--json`)
  with pass/fail exit codes; pre-merge check statuses (Gate 1, RBAC, Complexity, Acceptance,
  Mutation, Gate 3) and post-merge triggers.

## CLI & Tooling

Every script is standard-library Python >= 3.9 and resolves data from the skill directory, so a
global install works without a repository checkout. Run them from the project root:

```bash
# Gate 3 audit: cross-validate Section 3 (AST) and Section 4 (mutation report)
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks \
  --actual-complexity artifacts/complexity-report.json --require-actual-complexity \
  --actual-mutation artifacts/mutation-report.json --require-actual-mutation --strict --json

# Gate 3 audit requiring evidence provenance (artifact path + SHA-256)
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks --require-provenance --strict --json

# Complexity report (fail-closed; explicit source directory)
python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json > artifacts/complexity-report.json

# RBAC boundary audit across a git range (authoritative L1 in CI)
python .agents/skills/quality-engineering/scripts/rbac_audit.py --base origin/main --head HEAD --tasks-dir ./tasks --json

# Fail-closed mutation gate: config-driven (preferred) or the MUTATION_COMMAND fallback
python .agents/skills/quality-engineering/scripts/mutation_gate.py run --config quality-gate.config.json --min-msi 80
python .agents/skills/quality-engineering/scripts/mutation_gate.py run --command "$MUTATION_COMMAND" --report artifacts/mutation-report.json --min-msi 80

# Branch isolation guard: the declared task branch must not be a protected trunk
python .agents/skills/quality-engineering/scripts/branch_guard.py check --task-dir tasks/<task-id> --require-declared --json
```

Exit codes: `0` pass, `1` gate violation, `2` usage/configuration error, `3` internal error.
`--config PATH` (for `run` and `check`) reads a `quality-gate.config.json`-shaped object
(`schema_version` 1) and resolves `mutation.command`, `mutation.report`, `mutation.min_msi`, and
validates `mutation.core_min_msi` (numeric, `<= 100`, `>= mutation.min_msi`). Precedence: CLI flag >
config > default; `run` fails closed (exit 2) when no command is configured and never executes an
empty command. Branch guard exits `0`/`1`/`2`; see
[`references/branch-isolation.md`](references/branch-isolation.md). Local-only
`verification_linter.py` escape hatches (`--min-msi`, `--no-mutation`) never belong in CI.

## Bundled CI templates

Read the workflows from `assets/templates/ci/` and write them into `.github/workflows/`; they invoke
`.agents/skills/quality-engineering/scripts/...`, so install the skill at the default
`.agents/skills/` location (`quickstart.py --with-ci` installs both). The shipped `quality-gate.yml`
is the Python reference, not a universal pipeline: each project merges its stack profile's real BDD
and mutation commands and commits a `quality-gate.config.json` so PR-stage mutation is config-driven;
`rbac-gate.yml` runs `branch_guard.py` first. Details, profiles and troubleshooting:
[`assets/templates/ci/README.md`](assets/templates/ci/README.md).

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
| `MUTATION_REPORT_MISSING` | `--require-actual-mutation` without a usable normalized mutation report |
| `MUTATION_MISMATCH_WITH_REPORT` | Section 4 aggregate or per-target counts/MSI disagree with the real mutation report |
| `MUTATION_PHANTOM_TARGET` | Section 4 lists a mutation target absent from the real mutation report |
| `MUTATION_TARGET_MISSING_IN_03` | The real mutation report lists a target with no Section 4 row |
| `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING` | `Equivalent > 0` but no justification, with `--require-provenance` |
| `EVIDENCE_MISSING_COMMAND` | Execution evidence Command field is blank |
| `EVIDENCE_MISSING_RESULT` | Execution evidence Result field is blank |
| `EVIDENCE_MISSING_ARTIFACT` | Provenance is required but the artifact path is blank/missing |
| `EVIDENCE_HASH_INVALID` | Provenance SHA-256 is missing or does not match the artifact |

Warning codes: `COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD` (V(G) 11–15; passes but requires
justification in `02`), `TOUCH_FILES_UNREADABLE` (`touch_files` unparseable; cross-validation
incomplete), `BRANCH_NOT_DECLARED` (no declared branch without `--require-declared`). Mutation gate
codes: `MUTATION_REPORT_MISSING`, `MUTATION_REPORT_INVALID`, `MUTATION_THRESHOLD_FAILED`,
`MUTATION_COMMAND_FAILED`. Branch guard codes: `BRANCH_PROTECTED`, `BRANCH_PATTERN_INVALID`,
`BRANCH_DETACHED`, `BRANCH_DECLARED_MISSING`, `BRANCH_MISMATCH`, `TASK_DOC_MISSING`.

The four pipeline stages and their enforcement tools are defined in
[`references/verification-protocol.md`](references/verification-protocol.md) section 2; this skill
owns the workflows and scripts that implement them.

## Failure Triage & Routing

Read [`references/triage-routing.md`](references/triage-routing.md) after a gate failure: it maps each
deterministic code to its owner, first action, escalation trigger and forbidden shortcut. Short rule:
complexity mismatch/missing function -> `qa` (re-fill Section 3 from the AST artifact); mutation
mismatch/phantom/missing target -> `qa` (re-fill Section 4 from the real report); low MSI ->
`qa`/`dev`; missing artifact/report/hash -> `qa`/`quality-engineering`; missing mutation
configuration -> `quality-engineering` (commit `quality-gate.config.json`); unresolved conflict ->
orchestrator.

## References

- [`references/verification-protocol.md`](references/verification-protocol.md) — multi-stage CI
  pipeline, test environment protocol, Gate 3 evidence audit rules and the normalized
  mutation-report schema.
- [`references/triage-routing.md`](references/triage-routing.md) — error-code to owner/action
  routing, escalation rules and forbidden shortcuts.
- [`references/branch-isolation.md`](references/branch-isolation.md) — one task/one branch
  lifecycle, `branch_guard.py` usage and error codes, and the trunk-work migration runbook.
- Complexity checker [`scripts/complexity_check.py`](scripts/complexity_check.py): deterministic AST
  complexity with optional tree-sitter/lizard engines for multi-language analysis (Python >= 3.9).
- Gate 3 auditor [`scripts/verification_linter.py`](scripts/verification_linter.py): deterministic
  audit with AST and mutation-report cross-validation (standard library only).
- Gate helpers: [`scripts/rbac_audit.py`](scripts/rbac_audit.py) (git-diff role boundaries) and
  [`scripts/mutation_gate.py`](scripts/mutation_gate.py) (fail-closed, config-driven MSI gate).
- CI workflows and stack profiles: [`assets/templates/ci/`](assets/templates/ci/README.md) — the
  `quality-gate.yml` reference pipeline, `plan-gate.yml`, `rbac-gate.yml`, seven stack profile
  fragments and a config example; they are copy-and-adapt templates, not standalone workflows.
- Sister skill: `qa` — local stage testing and verification evidence generation.

## Honest limits

Gate 3 cross-checks Section 3 V(G) against the CI-uploaded AST artifact and, when the mutation
artifact is supplied (`--actual-mutation`, required in CI), cross-validates Section 4 aggregate
counts/MSI and per-target rows against the real normalized report, failing on mismatched, phantom or
omitted targets. Mutation runs pre-merge (config-driven, fail-closed), not only after merge. Local
Markdown evidence remains non-authoritative: it is checked against CI artifacts, never trusted alone;
local prompt rules and `--no-mutation`/relaxed thresholds are advisory escape hatches. True quality
assurance combines local QA execution, authoritative CI enforcement and branch protection. The suite
ships one canonical copy of the gate helpers inside this skill (mirrors included).

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
