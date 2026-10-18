# CI Templates — Modern Quality Engineering Gates and RBAC Enforcement

This directory provides production-ready, copy-paste GitHub Actions workflows that enforce
the Agent Skills Suite and Modern Quality Engineering standards on pull requests. Core linters and
helpers are standard-library only; the complexity checker optionally uses tree-sitter/lizard for
multi-language analysis. The workflows use the official `actions/checkout`,
`actions/setup-python`, `actions/upload-artifact` and `actions/download-artifact` actions. No
third-party marketplace action is required.

## Shipped Workflow Templates

| File | Primary Trigger | Core Commands | Fails When |
| :--- | :--- | :--- | :--- |
| `quality-gate.yml` | `pull_request` & `push` to `main` | `plan_linter.py`, `rbac_audit.py`, McCabe AST check + artifact, acceptance tests + JUnit, cross-validated `verification_linter.py`, `mutation_gate.py` | Any gate fails (BDD, RBAC, Complexity $V(G) > 15$, missing/failing acceptance tests, Gate 3 mismatch/MSI, missing mutation report or MSI $< 80\%$) |
| `plan-gate.yml` | `pull_request` touching `tasks/**` or `.specs/**` | `python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --spec .specs/02-tech-spec.md --json` | Gate 1 finds structural, BDD format, size, DAG, or spec anchor violations |
| `rbac-gate.yml` | every `pull_request` | `python tools/rbac_audit.py --base <base.sha> --head <head.sha> --tasks-dir tasks --json` | A role touched files outside its authorized write scope (L1 audit) |

- **`quality-gate.yml`** is the recommended master pipeline: it orchestrates the quality
  engineering stages in a single unified workflow.
- **`plan-gate.yml`** and **`rbac-gate.yml`** are modular, dedicated workflows for repositories
  that prefer separate status checks or isolated trigger paths.

---

## The 4-Stage Layered Testing Pipeline

To balance agent iteration speed with strict quality guarantees, adoption follows a
standardized 4-stage layered testing pipeline:

```text
+-------------------+      +-------------------+      +-------------------+      +-------------------+
|  1. Local Test    | ---> | 2. Test Env /     | ---> | 3. Pre-Merge PR   | ---> | 4. Post-Merge /   |
|     (Dev & QA)    |      |    Sandbox        |      |    (Authoritative)|      |    Staging        |
+-------------------+      +-------------------+      +-------------------+      +-------------------+
  * Dev self-check:          * Ephemeral sandbox        * L1/L2 CI Gates:          * Full regression
    dod checks,                containers                 - RBAC role audit          suite execution
    McCabe V(G) <= 10        * ADR architecture           - Gate 1 BDD lint        * converge updates
  * QA black-box:              contract validation        - McCabe complexity        spec in repo
    Given-When-Then          * Real topology              - Acceptance tests       * Mutation score
    acceptance tests           interoperability           - Gate 3 MSI >= 80%        baseline tracked
  * Local Gate 1             * External service         * Gate 2 Reviewer          * Performance
    plan-linter dry-run        mocking/emulation          semantic signoff           benchmarks
```

### Stage 1: Local Testing (Agent Workspace — Dev & QA)
- **Dev**: Runs machine-checkable DoD commands (`dod.type_check`, `dod.lint`, `dod.test_file`),
  verifies single-function cyclomatic complexity ($V(G) \le 10$), and records evidence in
  `02-dev-workspace.md` before checking `- [x] WAITING_FOR_QA`.
- **QA**: Focuses on local development stage testing before PR submission:
  - Integration testing across internal module boundaries and services.
  - BDD-driven end-to-end (E2E) testing (`tests/acceptance/`, Given-When-Then scenarios).
  - Mutation testing across `touch_files`, enforcing $\text{MSI} \ge 80\%$ ($\ge 90\%$ core).
  - Static code analysis: lint checks and cyclomatic complexity analysis ($V(G) \le 10$), enforcing
    the Basis Path Testing Baseline Rule ($\text{Test Cases} \ge V(G)$).
  - Autonomously choosing to invoke the `review` skill to assess code readability, style, and maintainability.
  - Autonomously introducing well-known open-source tools tailored to the stack.
  - Completing `03-qa-verification.md` with local execution evidence and issuing the local verdict.
- **Local Pre-check**: Runs Gate 1 and Gate 3 linters locally to verify contract frontmatter, BDD syntax,
  and verification evidence before submitting pull requests.

### Stage 2: Test Environment (Managed by Quality Engineering)
- The `quality-engineering` skill provisions and validates isolated, reproducible test environments
  (containers, virtualized runners, or sandboxes).
- The shipped template installs the project's declared dependencies and runs an acceptance-test
  collection probe before execution. Network isolation is `advisory` in the template unless the
  project installs `pytest-socket` (then `--disable-socket` is used); it is not claimed as a hard
  sandbox guarantee.

### Stage 3: Pre-Merge PR Gate (Authoritative L1/L2 Enforcement — Quality Engineering)
- Serves as the authoritative barrier before code reaches trunk, orchestrated by `quality-engineering`:
- Enforces role separation via `rbac_audit.py` (Dev cannot touch acceptance tests; QA cannot touch
  source code).
- Enforces Gate 1 BDD scenarios and contract completeness via `plan_linter.py --json`.
- Enforces cyclomatic complexity control flow ($V(G) \le 10$, warning $11-15$, hard block $> 15$).
- Executes the black-box acceptance and integration test suites, requiring a 100% green baseline.
- Enforces Gate 3 verification evidence via `verification_linter.py --actual-complexity ... \
  --require-actual-complexity --strict --json`: cross-checks the `03` V(G) values against the real
  AST artifact and verifies basis path coverage and $\text{MSI} \ge 80\%$ (90% for core tasks).
- Runs a fail-closed mutation gate on trunk pushes via `tools/mutation_gate.py`; a missing
  `MUTATION_COMMAND`, missing report, or low MSI fails the build.
- Gate 2 semantic audit remains a human/reviewer step (branch protection / CODEOWNERS); the shipped
  workflow template does not contain a Gate 2 job.

### Stage 4: Post-Merge & Staging / Release (Quality Engineering Automation)
- Executes full mainline regression test suites on push to trunk.
- `converge` (spec write-back and bundle archive) is a manual/optional workflow in the template;
  run `python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id>` after QA_PASSED.
- Updates repository mutation testing baselines and performance benchmarks.

---

## The 6 CI Quality Gates Explained

### 1. Gate 1 — BDD Scenarios & Task Contract Validation
- **Tool**: `python .agents/skills/plan-linter/scripts/plan_linter.py`
- **Scope**: `tasks/<task-id>/01-contract.md` and `.specs/02-tech-spec.md` (it never audits the
  complexity/mutation evidence in `03-qa-verification.md`; that is Gate 3).
- **Validation Rules**:
  - Validates YAML frontmatter fields (`task_id`, `touch_files`, `dod`, `adrs`, etc.).
  - Enforces structured Given-When-Then scenarios in `dod.edge_cases` and Section 4 invariants.
  - Enforces Goldilocks task sizing (1–3 touch files, 50–250 estimated diff lines).
  - Verifies DAG acyclicity and validates specification anchor coverage (`#sec-*`).
  - Scans for unresolved placeholders and unrendered template tokens.
- **Exit Codes**: `0` Pass, `1` Contract/BDD violations, `2` Configuration/CLI error.

### 2. RBAC Audit — Role Boundary Enforcement
- **Tool**: `python tools/rbac_audit.py`
- **Scope**: Git range diff between PR base and head commit.
- **Validation Rules**:
  - Diffs changed files against the declared role from the `Agent-Role: dev|qa|planner` commit
    trailer or repository variable `RBAC_ROLE`.
  - Rejects Dev modifying `tests/acceptance/**` or `01-contract.md`.
  - Rejects QA modifying `src/**` or `02-dev-workspace.md`.
  - Rejects Planner modifying source code or test directories.
- **Exit Codes**: `0` Pass, `1` Boundary violation, `2` Git/environment error.

### 3. Cyclomatic Complexity Gate (McCabe $V(G) \le 10$)
- **Tool**: `python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json`
  - Multi-language static analyzer powered by **Tree-sitter** (https://github.com/tree-sitter/tree-sitter) with open-source multi-language support (Lizard) and standard library AST fallback.
  - Automatically parses Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, and C# when the
    optional engines are installed; the Python AST engine is the dependency-free fallback.
  - Fails closed (exit 2) when no source directory is available; it never silently scans `.`.
  - Emits a `functions` array so Gate 3 can cross-check `03` values against real AST results.
- **Thresholds**:
  - $V(G) \le 10$: **Standard** — Approved for production.
  - $11 \le V(G) \le 15$: **Warning** — Requires architectural justification in Dev notes.
  - $V(G) > 15$: **Critical** — Prohibited; build is blocked until refactored.
- **Refactoring Patterns**: Extract Method, Strategy Pattern, Guard Clauses / Early Return,
  Lookup Tables.
- **Multi-Stack Open-Source Analyzers**:
  - **Universal Engine (Bundled)**: `python .agents/skills/quality-engineering/scripts/complexity_check.py --json` (Tree-sitter + Lizard)
  - **Python**: `tree-sitter`, `lizard`, `radon cc src/ -s -n B`, `ruff check`
  - **TypeScript/JavaScript**: `tree-sitter`, `npx eslint --rule 'complexity: ["error", 10]' src/`, `lizard`
  - **Go**: `tree-sitter`, `gocyclo -over 10 src/`, `gocognit`
  - **Rust**: `tree-sitter`, `cargo clippy -- -D clippy::cognitive_complexity`, `lizard`
  - **Java**: `tree-sitter`, `pmd check -d src/ -R rulesets/java/codesize.xml/CyclomaticComplexity`, `lizard`
  - **C / C++**: `tree-sitter`, `lizard`

### 4. Acceptance Test Suite Execution (BDD Given-When-Then)
- **Scope**: Black-box acceptance tests in `tests/acceptance/` mapping to BDD Given-When-Then
  scenarios.
- **Execution**: Installs the project's declared dependencies, runs a collection probe, then
  executes the suite. When pytest is available it uses `pytest --junitxml`; otherwise it falls back
  to `unittest discover`. A missing `tests/acceptance/` directory, a collection error, or a failing
  test fails the job.
- **Network isolation**: `advisory` unless `pytest-socket` is installed (then `--disable-socket`).
- **Local BDD tools** (QA runs these locally; CI executes whatever the project's command collects):
  - **Python**: `pytest-bdd` (`pytest tests/acceptance/`), `behave tests/acceptance/features/`
  - **TypeScript/JavaScript**: `Cucumber.js` (`npx cucumber-js tests/acceptance/features/*.feature`), `playwright-bdd`
  - **Go**: `Godog` (`godog run tests/acceptance/features/`)
  - **Rust**: `cucumber-rs` (`cargo test --test cucumber`)
  - **Java**: `Cucumber-JVM` (`mvn test -Dcucumber.filter.tags="@acceptance"`), `JBehave`
  - **C# / .NET**: `Reqnroll`, `SpecFlow` (`dotnet test --filter Category=Acceptance`)

### 5. Gate 3 — Verification Linter Cross-Validated with Live AST
- **Tool**: `python .agents/skills/quality-engineering/scripts/verification_linter.py --actual-complexity artifacts/complexity-report.json --require-actual-complexity --strict --json`
- **Scope**: `tasks/<task-id>/03-qa-verification.md` signed off with `- [x] QA_PASSED`, plus the
  CI-uploaded complexity artifact.
- **Validation Rules**:
  - Cross-checks every `touch_files` function reported by the real AST scan against Section 3;
    omitted functions, phantom functions, and V(G) mismatches fail Gate 3.
  - Verifies basis path coverage $\text{Test Cases} \ge V(G)$ using the actual V(G) where available.
  - Audits Section 4: every populated table must be compliant (a compliant table cannot mask a
    non-compliant one); mutation engine, counts, and MSI $\ge 80\%$ ($\ge 90\%$ for `risk_level: core`).
  - With `--require-provenance`, requires Section 5 artifact path + SHA-256 and an equivalent-mutant
    justification when `Equivalent > 0`.
- **MSI Formula**:
  $$\text{MSI} = \frac{\text{Killed} + \text{TimedOut}}{\text{Total} - \text{Equivalent}} \times 100\% \ge 80\%$$

### 6. Mutation Gate — Active, Fail-Closed
- **Tool**: `python tools/mutation_gate.py run --command "$MUTATION_COMMAND" --report artifacts/mutation-report.json --min-msi 80`
- **Scope**: trunk pushes (`main`/`master`). The project exposes a `MUTATION_COMMAND` repository
  variable that runs its stack tool and writes the normalized JSON report (schema in
  `quality-engineering/references/verification-protocol.md`).
- **Fail-closed**: a missing `MUTATION_COMMAND`, a non-zero mutation command, a missing/malformed
  report, or MSI below the threshold fails the job. Survived-mutant counts remain in the report for
  triage; the hard gate is MSI.
- **Active mutation command examples** (wrapped by the project's report adapter):
  - **Python**: `mutmut run --paths-to-mutate src/ && mutmut results`
  - **TypeScript/JavaScript**: `npx stryker run`
  - **Go**: `go-mutesting ./...`
  - **Rust**: `cargo mutants`
  - **Java**: `mvn org.pitest:pitest-maven:mutationCoverage`

---

## Why CI is Authoritative (Enforcement Architecture)

The repository follows an honest, multi-tiered enforcement model:

| Layer | Mechanism | Scope | Guarantee |
| :--- | :--- | :--- | :--- |
| **L0** | Prompt rules (`AGENTS.md`, `.agents/rules/*.md`) | Local agent context | **Advisory**; guides generation but is bypassable |
| **L1** | Automated CI Gates (`quality-gate.yml`, `rbac-gate.yml`) | Pull requests | **Authoritative**; strictly blocks unauthorized diffs |
| **L2** | Branch protection & CODEOWNERS | GitHub repository settings | **Authoritative**; guarantees no merge without CI green |

**Key Principle**: Local prompt rules are advisory. They assist agents during code creation, but
they do not constitute physical or cryptographic enforcement. The absolute, authoritative gate is
GitHub Actions CI coupled with repository branch protection. No pull request may be merged without
passing CI quality gates.

---

## Installation and Adoption

### Option A — One command with quickstart

```bash
# Symlink adoption (default, POSIX)
python tools/quickstart.py --target /path/to/your-repo --with-ci

# Real files copy (recommended for Windows or standalone repositories)
python tools/quickstart.py --target /path/to/your-repo --copy --with-ci
```

`--with-ci` copies workflow templates from `templates/ci/` into `<target>/.github/workflows/`
alongside the skills, rules, `tools/rbac_audit.py`, and `tools/mutation_gate.py`.

### Option B — Manual copy

Run from the suite checkout, with `TARGET` pointing at the adopting repository:

```bash
TARGET=/path/to/your-repo
mkdir -p "$TARGET/.github/workflows" "$TARGET/tools"
cp templates/ci/quality-gate.yml "$TARGET/.github/workflows/quality-gate.yml"
cp templates/ci/rbac-gate.yml "$TARGET/.github/workflows/rbac-gate.yml"
cp templates/ci/plan-gate.yml "$TARGET/.github/workflows/plan-gate.yml"
cp tools/rbac_audit.py "$TARGET/tools/rbac_audit.py"
cp tools/mutation_gate.py "$TARGET/tools/mutation_gate.py"
```

PowerShell:

```powershell
$Target = "C:\path\to\your-repo"
New-Item -ItemType Directory -Force "$Target\.github\workflows", "$Target\tools" | Out-Null
Copy-Item templates/ci/quality-gate.yml "$Target\.github\workflows\quality-gate.yml"
Copy-Item templates/ci/rbac-gate.yml "$Target\.github\workflows\rbac-gate.yml"
Copy-Item templates/ci/plan-gate.yml "$Target\.github\workflows\plan-gate.yml"
Copy-Item tools/rbac_audit.py "$Target\tools\rbac_audit.py"
Copy-Item tools/mutation_gate.py "$Target\tools\mutation_gate.py"
```

Commit the workflows alongside `.agents/skills/`, `.agents/rules/`, and `tools/` so CI runs against
the exact reviewed suite version.

---

## Required Permissions and Repository Settings

- **Workflow token permissions**: Workflows declare `permissions: contents: read` at the top level.
  No write access and no repository secrets are required.
- **Fork pull requests**: Workflows run safely on fork pull requests with read-only tokens.
- **Checkout depth**: `fetch-depth: 0` is specified for `rbac-audit` because git diff requires the
  full commit history between base and head SHAs.
- **Branch protection status checks**: In GitHub repository settings (`Branches -> Branch protection rules`),
  require the following status check job names before enabling auto-merge:
  - `Gate 1 - BDD & Plan Linter`
  - `RBAC - Role Boundary Audit`
  - `Complexity - McCabe V(G) Static Check`
  - `Acceptance - Test Suite Execution`
  - `Gate 3 - Acceptance & MSI Audit`
- **Optional repository variable**: Set `RBAC_ROLE` to `dev`, `qa`, or `planner` in repository
  variables to pin one role for single-role branches. If unset, the audit reads the
  `Agent-Role: <role>` commit trailer.
- **Required for mutation gating**: Set `MUTATION_COMMAND` as a repository variable to the command
  that runs the stack's mutation tool and writes `artifacts/mutation-report.json`. The mutation job
  runs on trunk pushes and fails closed when the variable is absent; it is not a PR status check.

---

---

## Pinning the suite version

The workflows are plain repository files, so the version they enforce is the version you commit:

1. Adopt from a tagged release or a recorded commit SHA of the suite repository, not from a moving branch: `git checkout <release-tag-or-sha>` in the suite checkout, then run `quickstart.py --copy --with-ci`.
2. Commit the resulting `.agents/skills/`, `.agents/rules/`, `tools/rbac_audit.py`, `tools/mutation_gate.py` and `.github/workflows/` files in one reviewable pull request.
3. Record the versions in that pull request: `python tools/quickstart.py --version`, `python tools/rbac_audit.py --version`, `python tools/mutation_gate.py --version`, `python .agents/skills/plan-linter/scripts/plan_linter.py --version`, and the `metadata.version` values in each `SKILL.md`.
4. To upgrade, re-adopt from the new tag with `--force` (`quickstart.py --target . --copy --force --with-ci`) and review the diff. The diff is the audit trail.
5. For a stricter supply chain, pin `actions/checkout` and `actions/setup-python` to a full commit SHA instead of `v4` / `v5`. Dependabot-style upgrades are then explicit.

Do not edit the copied workflows without recording why; they are the enforcement layer from Section "Authoritative Enforcement Hierarchy".

## Developer Commands: Local Verification Before Pushing

Run these commands locally to verify all gates pass before pushing:

```bash
# 1. Gate 1 Plan Linter (BDD scenarios & contract validation)
python .agents/skills/plan-linter/scripts/plan_linter.py \
  --tasks-dir tasks \
  --spec .specs/02-tech-spec.md \
  --json

# 2. RBAC Audit over the pull request range
git fetch origin main
python tools/rbac_audit.py --base origin/main --head HEAD --role dev --json

# 3. Cyclomatic Complexity Check (McCabe V(G) <= 10)
python .agents/skills/quality-engineering/scripts/complexity_check.py \
  --src-dir src --json > artifacts/complexity-report.json

# 4. Acceptance Test Suite Execution
python -m pytest tests/acceptance -q --junitxml=artifacts/acceptance-junit.xml

# 5. Gate 3 Acceptance & MSI Audit (once QA_PASSED is checked)
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir tasks \
  --actual-complexity artifacts/complexity-report.json \
  --require-actual-complexity \
  --strict --json
```

---

## Troubleshooting CI Failures

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| Gate 1 fails with `BDD_MISSING_PRECONDITION` or syntax error | Edge cases or Section 4 do not conform to `Given ..., When ..., Then ...` | Update scenarios in `01-contract.md` to follow standard Given-When-Then clauses. |
| Gate 1 fails with `DIFF_TOO_LARGE` | Task exceeds 250 diff lines | Split the task into multiple smaller bundles following the Goldilocks rule. |
| RBAC audit fails with `DEV_EDITED_ACCEPTANCE_TESTS` | Dev role modified files in `tests/acceptance/**` | Dev must revert changes to acceptance tests; escalate test requirements to QA. |
| RBAC audit fails with `QA_EDITED_SOURCE` | QA role modified files in `src/**` | QA must revert changes to `src/**`; write acceptance tests only. |
| RBAC audit reports `no role available` | Head commit lacks `Agent-Role:` trailer and `RBAC_ROLE` is unset | Add `Agent-Role: dev` (or `qa`/`planner`) to commit message body or set `vars.RBAC_ROLE`. |
| Complexity check fails with $V(G) > 15$ | Single function contains too many branch points | Refactor using Extract Method, Strategy Pattern, or Guard Clauses until $V(G) \le 10$. |
| Complexity check exits 2 | No `src/` and no `--src-dir` provided | Pass `--src-dir <path>`; the checker is fail-closed and no longer scans `.`. |
| Gate 3 fails with `COMPLEXITY_BASIS_PATH_INSUFFICIENT` | Test count in Section 3 is less than $V(G)$ | Design additional black-box test cases until $\text{Test Cases} \ge V(G)$. |
| Gate 3 fails with `COMPLEXITY_MISMATCH_WITH_AST` | `03` reports a different V(G) than the live AST artifact | Re-run complexity_check and correct Section 3 from the artifact. |
| Gate 3 fails with `COMPLEXITY_FUNCTION_MISSING_IN_03` | A `touch_files` function is missing from Section 3 | Add every scanned function in the blast radius. |
| Gate 3 fails with `QA_INVALID_MSI_SCORE` | MSI score in Section 4 is below 80% (90% core) | Strengthen assertions until MSI meets the threshold. |
| Gate 3 fails with `EVIDENCE_MISSING_ARTIFACT` / `EVIDENCE_HASH_INVALID` | Provenance is required but the artifact path/SHA-256 is missing or wrong | Point Section 5 at the real artifact and record its current SHA-256. |
| Mutation job fails with `MUTATION_REPORT_MISSING` | `MUTATION_COMMAND` did not write the normalized report | Configure the adapter report path; the gate is fail-closed. |
| Mutation job fails with `MUTATION_THRESHOLD_FAILED` | Computed MSI is below 80% | Kill surviving mutants or remove dead code, then re-run. |
| Fork PR fails with `unknown revision` | Shallow checkout cannot find base commit | Ensure `fetch-depth: 0` is set on `actions/checkout` in the workflow. |
