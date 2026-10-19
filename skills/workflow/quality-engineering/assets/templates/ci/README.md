# CI Templates — Modern Quality Engineering Gates and RBAC Enforcement

This directory is bundled inside the `quality-engineering` skill (`assets/templates/ci/`), so the
templates and the five gate helpers under the skill's `scripts/` directory
(`complexity_check.py`, `verification_linter.py`, `rbac_audit.py`, `mutation_gate.py`,
`branch_guard.py`) travel together: a global skill install needs no repository checkout. The files
are production-ready, copy-paste GitHub Actions workflows that enforce the Agent Skills Suite and
Modern Quality Engineering standards on pull requests. Core linters and helpers are standard-library
only; the complexity checker optionally uses tree-sitter/lizard for multi-language analysis. The
workflows use the official `actions/checkout`, `actions/setup-python`, `actions/upload-artifact`
and `actions/download-artifact` actions. No third-party marketplace action is required.

The templates invoke the skill scripts by their project-relative path
(`.agents/skills/quality-engineering/scripts/...` and `.agents/skills/plan-linter/scripts/...`), so
the skill must be installed at the default `.agents/skills/` location in the adopting repository.
The suite's `quickstart.py --with-ci` installer does exactly that.

## Shipped Workflow Templates

| File | Primary Trigger | Core Commands | Fails When |
| :--- | :--- | :--- | :--- |
| `quality-gate.yml` | `pull_request` & `push` to `main` | `plan_linter.py`, `rbac_audit.py`, McCabe AST check + artifact, acceptance tests + JUnit, cross-validated `verification_linter.py` (AST + mutation reports), fail-closed `mutation_gate.py` | Any gate fails (BDD, RBAC, Complexity $V(G) > 15$, missing/failing acceptance tests, Gate 3 mismatch/MSI, missing mutation configuration or report, MSI $< 80\%$) |
| `plan-gate.yml` | `pull_request` touching `tasks/**` or `.specs/**` | `python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --spec .specs/02-tech-spec.md --json` | Gate 1 finds structural, BDD format, size, DAG, or spec anchor violations |
| `rbac-gate.yml` | every `pull_request` | `python .agents/skills/quality-engineering/scripts/rbac_audit.py --base <base.sha> --head <head.sha> --tasks-dir ./tasks --json` | A role touched files outside its authorized write scope (L1 audit) |

- **`quality-gate.yml`** is the recommended master pipeline: it orchestrates the quality
  engineering stages in a single unified workflow.
- **`plan-gate.yml`** and **`rbac-gate.yml`** are modular, dedicated workflows for repositories
  that prefer separate status checks or isolated trigger paths.

## Multi-language stack profiles and tool matrix

`quality-gate.yml` is a **Python-first reference implementation**, not a universal pipeline.
The `profiles/` directory ships per-stack reference fragments for the invariant gates. Four stacks
also ship a **ready-to-copy `*.config.json`** with real commands (no empty placeholders), so an
adopting project can copy one file to its repository root and pass it to
`mutation_gate.py run --config`:

| Stack | Profile | Ready-to-copy config | Acceptance/BDD (industry standard) | Mutation (industry standard) | One-line rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Python | `profiles/python.yml` | `profiles/python.config.json` | pytest-bdd / behave -> pytest JUnit XML | mutmut | Standard OSS pair for Python BDD acceptance and source-level mutation. |
| Node.js / TS | `profiles/node.yml` | `profiles/node.config.json` | Cucumber.js -> JUnit XML | Stryker | Cucumber.js is the reference JS/TS BDD runner; Stryker is the reference mutation framework. |
| Go | `profiles/go.yml` | `profiles/go.config.json` | Godog -> JUnit XML (gotestsum fallback) | go-mutesting | Godog is the Cucumber-compatible BDD runner for Go; go-mutesting is the standard OSS mutator. |
| Java / Kotlin | `profiles/java.yml` | `profiles/java.config.json` | Cucumber-JVM -> JUnit XML | PITest | Cucumber-JVM is the JVM BDD reference; PITest is the JVM mutation reference. |
| Rust | `profiles/rust.yml` | — | nextest + cargo2junit | cargo-mutants | Native runner plus the standard Rust mutation tool. |
| C# / .NET | `profiles/dotnet.yml` | — | JUnit logger / TRX adapter | Stryker.NET | The .NET port of the same mutation framework. |
| C / C++ | `profiles/cpp.yml` | — | CTest JUnit | Mull | CMake-native runner plus the LLVM mutation engine. |

- Complexity is always measured by the bundled `complexity_check.py` (Tree-sitter/Lizard engines,
  Python AST fallback) so Gate 3 can cross-check the artifact; each config also names a native
  second opinion in its notes (radon, gocyclo, ESLint complexity, PMD).
- Every ready-to-copy config records the **fail-closed mutation floor**: `min_msi: 80` and
  `core_min_msi: 90`. `mutation_gate.py --config` validates that `core_min_msi` is numeric, is
  `<= 100` and is `>= mutation.min_msi`; Gate 3 enforces the same floors via `risk_level: core`.
- `profiles/index.json` is the machine-readable catalog; entries for the four config-bearing stacks
  carry a `config` field pointing at the ready-to-copy file.
- Profiles are **reference fragments**: merge the toolchain/install/acceptance/mutation blocks
  into your adapted `quality-gate.yml`; they do not run standalone. Copying the Python workflow
  unchanged into a Node/Go/Rust/.NET/C++/Java repository is not adoption: replace the stack
  commands with the profile's real BDD runner and mutation tool, then keep every invariant job.
- `quality-gate.config.example.json` shows the profile/config shape.
- Profiles do not provision real middleware. Add GitHub Actions `services:` or testcontainers when
  acceptance tests need a real database/queue/cache.

### Config-driven mutation (replaces the empty `MUTATION_COMMAND` variable)

The shipped workflow no longer depends on a repository variable being pre-filled. Mutation
command resolution on `pull_request` and `push`:

1. a committed `quality-gate.config.json` (copy of `quality-gate.config.example.json` or the
   matching `profiles/<stack>.config.json`) passed to `mutation_gate.py run --config`; the config
   supplies `mutation.command`, `mutation.report`, `mutation.min_msi` and the optional
   `mutation.core_min_msi` floor;
2. otherwise the `MUTATION_COMMAND` repository variable;
3. otherwise the job fails with an actionable message.

PR-stage mutation is **mandatory and fail-closed**. A missing command, a non-zero command, a
missing/malformed normalized report, or MSI below 80% fails the pull request. The config file is
committed with the project, so the real per-stack command is reviewed like code; the repository
variable is only a fallback for projects that cannot commit it. `mutation.report` must be
`artifacts/mutation-report.json` so the artifact handoff to Gate 3 keeps working. `--config`
accepts `schema_version: 1` only, rejects a missing/invalid config or `mutation` object with exit
`2`, and validates `mutation.core_min_msi` (numeric, `<= 100`, `>= mutation.min_msi`) before the
command runs; the 90% core floor is enforced by Gate 3 through `risk_level: core`.

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
  --require-actual-complexity --actual-mutation ... --require-actual-mutation --strict --json`:
  cross-checks the `03` V(G) values against the real AST artifact, cross-checks aggregate and
  per-target mutation evidence against the real mutation report, and verifies basis path coverage
  and $\text{MSI} \ge 80\%$ (90% for core tasks).
- Runs the real mutation gate on every PR and on trunk pushes via `scripts/mutation_gate.py` with
  `--config quality-gate.config.json` (or the `MUTATION_COMMAND` fallback); a missing
  configuration, command failure, missing report, or low MSI fails the build. The gate is
  fail-closed and never skips.
- Gate 2 semantic audit remains a human/reviewer step (branch protection / CODEOWNERS); the shipped
  workflow template does not contain a Gate 2 job.

### Stage 4: Post-Merge & Staging / Release (Quality Engineering Automation)
- Executes full mainline regression test suites on push to trunk.
- `converge` (spec write-back and bundle archive) is a manual/optional workflow in the template;
  run the bundled `converge` skill's `converge.py apply --task tasks/<task-id>` after QA_PASSED.
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
- **Tool**: `python .agents/skills/quality-engineering/scripts/rbac_audit.py`
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

### 5. Gate 3 — Verification Linter Cross-Validated with Live AST and Mutation Reports
- **Tool**: `python .agents/skills/quality-engineering/scripts/verification_linter.py --actual-complexity artifacts/complexity-report.json --require-actual-complexity --actual-mutation artifacts/mutation-report.json --require-actual-mutation --strict --json`
- **Scope**: `tasks/<task-id>/03-qa-verification.md` signed off with `- [x] QA_PASSED`, plus the
  CI-uploaded complexity artifact and normalized mutation report.
- **Validation Rules**:
  - Cross-checks every `touch_files` function reported by the real AST scan against Section 3;
    omitted functions, phantom functions, and V(G) mismatches fail Gate 3.
  - Cross-checks Section 4 aggregate totals/MSI and per-target rows against the actual mutation
    report. A fabricated `MSI: 92%` no longer passes: aggregate or per-target discrepancies yield
    `MUTATION_MISMATCH_WITH_REPORT`, an invented target yields `MUTATION_PHANTOM_TARGET`, and a
    report target omitted from `03` yields `MUTATION_TARGET_MISSING_IN_03`.
  - Verifies basis path coverage $\text{Test Cases} \ge V(G)$ using the actual V(G) where available.
  - Audits Section 4: every populated table must be compliant (a compliant table cannot mask a
    non-compliant one); mutation engine, counts, and MSI $\ge 80\%$ ($\ge 90\%$ for `risk_level: core`).
  - With `--require-provenance`, requires Section 5 artifact path + SHA-256 and an equivalent-mutant
    justification when `Equivalent > 0`.
- **MSI Formula**:
  $$\text{MSI} = \frac{\text{Killed} + \text{TimedOut}}{\text{Total} - \text{Equivalent}} \times 100\% \ge 80\%$$

### 6. Mutation Gate — Active, Fail-Closed, PR-Stage
- **Tool**: `python .agents/skills/quality-engineering/scripts/mutation_gate.py run --config quality-gate.config.json --min-msi 80`
- **Scope**: every pull request and every push to `main`/`master`. The project supplies its real
  mutation command through a committed `quality-gate.config.json` (`mutation.command`,
  `mutation.report`, `mutation.min_msi`), or through the `MUTATION_COMMAND` repository variable as
  a fallback. The command must run the stack tool and write the normalized JSON report (schema in
  `quality-engineering/references/verification-protocol.md`).
- **Config precedence**: explicit CLI flags (`--command`, `--report`, `--min-msi`) override the
  config values, which override the defaults. `schema_version` must be `1`. `run` fails closed
  (usage exit 2) when neither `--command` nor `mutation.command` is configured; it never executes
  an empty command.
- **Fail-closed**: a missing mutation command/config, a non-zero mutation command, a
  missing/malformed report, or MSI below the threshold fails the job. Survived-mutant counts remain
  in the report for triage; the hard gate is MSI.
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
| **L0** | Prompt rules (the repository's `AGENTS.md` and role rules) | Local agent context | **Advisory**; guides generation but is bypassable |
| **L1** | Automated CI Gates (`quality-gate.yml`, `rbac-gate.yml`) | Pull requests | **Authoritative**; strictly blocks unauthorized diffs |
| **L2** | Branch protection & CODEOWNERS | GitHub repository settings | **Authoritative**; guarantees no merge without CI green |

**Key Principle**: Local prompt rules are advisory. They assist agents during code creation, but
they do not constitute physical or cryptographic enforcement. The absolute, authoritative gate is
GitHub Actions CI coupled with repository branch protection. No pull request may be merged without
passing CI quality gates.

---

## Installation and Adoption

### Option A — one command with quickstart

Run the suite's `quickstart.py` installer from the suite checkout with `--copy --with-ci`. It copies
the selected skills, the role rules and these three workflows into the adopting repository; the four
gate scripts travel inside the `quality-engineering` skill directory, so no separate copy is needed.
`--with-ci` reads `quality-gate.yml`, `plan-gate.yml` and `rbac-gate.yml` from this directory and
writes them to `<target>/.github/workflows/`. It guarantees that `quality-engineering` is selected,
because the workflows call its scripts. It does not create the project-specific
`quality-gate.config.json`: copy `quality-gate.config.example.json` to the repository root and fill
`mutation.command` for your stack (the mutation job fails closed until a command is configured).

### Option B — manual copy

With the skill already present at `.agents/skills/quality-engineering/`, copy the workflows from
this directory into `.github/workflows/`:

```bash
SKILL=.agents/skills/quality-engineering
mkdir -p .github/workflows
cp "$SKILL"/assets/templates/ci/quality-gate.yml .github/workflows/
cp "$SKILL"/assets/templates/ci/rbac-gate.yml .github/workflows/
cp "$SKILL"/assets/templates/ci/plan-gate.yml .github/workflows/
```

PowerShell:

```powershell
$Skill = ".agents\skills\quality-engineering"
New-Item -ItemType Directory -Force ".github\workflows" | Out-Null
Copy-Item "$Skill\assets\templates\ci\quality-gate.yml" ".github\workflows\quality-gate.yml"
Copy-Item "$Skill\assets\templates\ci\rbac-gate.yml" ".github\workflows\rbac-gate.yml"
Copy-Item "$Skill\assets\templates\ci\plan-gate.yml" ".github\workflows\plan-gate.yml"
Copy-Item "$Skill\assets\templates\ci\quality-gate.config.example.json" "quality-gate.config.json"
```

Then edit the committed `quality-gate.config.json` so `mutation.command` runs your stack's real
mutation tool and `mutation.report` stays `artifacts/mutation-report.json`. The mutation job prefers
this file on every pull request; `MUTATION_COMMAND` is only the fallback.

Commit the workflows together with the adopted skill directories and role rules so CI runs against
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
  - `Mutation - Active Kill Ratio Check`
  - `Gate 3 - Acceptance & MSI Audit`
- **Optional repository variable**: Set `RBAC_ROLE` to `dev`, `qa`, or `planner` in repository
  variables to pin one role for single-role branches. If unset, the audit reads the
  `Agent-Role: <role>` commit trailer.
- **Required for mutation gating**: commit a `quality-gate.config.json` (copy of
  `quality-gate.config.example.json`) whose `mutation.command` runs the stack's mutation tool and
  whose `mutation.report` is `artifacts/mutation-report.json`. The mutation job runs on pull
  requests and trunk pushes and fails closed when the config (or `mutation.command`) is missing;
  it is a required PR status check, not a post-merge-only job. `MUTATION_COMMAND` remains a
  fallback for repositories that cannot commit the config file; do not rely on it being set.

---

---

## Pinning the suite version

The workflows are plain repository files, so the version they enforce is the version you commit:

1. Adopt from a tagged release or a recorded commit SHA of the suite repository, not from a moving branch: check out the tag in the suite checkout, then run the quickstart installer with `--copy --with-ci`.
2. Commit the resulting skill directories and `.github/workflows/` files in one reviewable pull request.
3. Record the versions in that pull request: the installer `--version`, `python .agents/skills/quality-engineering/scripts/rbac_audit.py --version`, `python .agents/skills/quality-engineering/scripts/mutation_gate.py --version`, `python .agents/skills/plan-linter/scripts/plan_linter.py --version`, and the `metadata.version` values in each `SKILL.md`.
4. To upgrade, re-adopt from the new tag with `--force` and review the diff. The diff is the audit trail.
5. For a stricter supply chain, pin `actions/checkout` and `actions/setup-python` to a full commit SHA instead of `v4` / `v5`. Dependabot-style upgrades are then explicit.

Do not edit the copied workflows without recording why; they are the enforcement layer from the
"Authoritative Enforcement Hierarchy" section.

## Developer Commands: Local Verification Before Pushing

Run these commands locally to verify all gates pass before pushing:

```bash
# 1. Gate 1 Plan Linter (BDD scenarios & contract validation)
python .agents/skills/plan-linter/scripts/plan_linter.py \
  --tasks-dir ./tasks \
  --spec .specs/02-tech-spec.md \
  --json

# 2. RBAC Audit over the pull request range
git fetch origin main
python .agents/skills/quality-engineering/scripts/rbac_audit.py --base origin/main --head HEAD --role dev --json

# 3. Cyclomatic Complexity Check (McCabe V(G) <= 10)
python .agents/skills/quality-engineering/scripts/complexity_check.py \
  --src-dir src --json > artifacts/complexity-report.json

# 4. Acceptance Test Suite Execution
python -m pytest tests/acceptance -q --junitxml=artifacts/acceptance-junit.xml

# 5. Gate 3 Acceptance & MSI Audit (once QA_PASSED is checked; CI supplies the real artifacts)
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks \
  --actual-complexity artifacts/complexity-report.json \
  --require-actual-complexity \
  --actual-mutation artifacts/mutation-report.json \
  --require-actual-mutation \
  --strict --json

# 6. Real mutation gate (config-driven; writes artifacts/mutation-report.json)
python .agents/skills/quality-engineering/scripts/mutation_gate.py run \
  --config quality-gate.config.json --min-msi 80
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
| Gate 3 fails with `MUTATION_MISMATCH_WITH_REPORT` | Section 4 aggregate or per-target counts/MSI disagree with the uploaded mutation report | Re-run mutation, then re-fill Section 4 from the real normalized report; never edit the report to match the prose. |
| Gate 3 fails with `MUTATION_PHANTOM_TARGET` | Section 4 lists a target the mutation report does not contain | Remove the invented row or fix the report adapter; do not pad the table. |
| Gate 3 fails with `MUTATION_TARGET_MISSING_IN_03` | The mutation report contains a target with no Section 4 row | Add the missing target row using the report's counts. |
| Gate 3 fails with `MUTATION_REPORT_MISSING` | `--require-actual-mutation` was set but the mutation artifact is absent/unusable | Ensure the mutation job ran first and uploaded `artifacts/mutation-report.json`; check the Gate 3 `needs`/artifact name. |
| Gate 3 fails with `EVIDENCE_MISSING_ARTIFACT` / `EVIDENCE_HASH_INVALID` | Provenance is required but the artifact path/SHA-256 is missing or wrong | Point Section 5 at the real artifact and record its current SHA-256. |
| Mutation job fails with `MUTATION_REPORT_MISSING` | The configured command did not write the normalized report | Configure `mutation.report` (adapter output) in `quality-gate.config.json`; the gate is fail-closed. |
| Mutation job fails with "No mutation command configured" | Neither `quality-gate.config.json` nor `MUTATION_COMMAND` is available | Commit the config file with the real stack command (or set the repository variable); do not disable the job. |
| Mutation job fails with `MUTATION_THRESHOLD_FAILED` | Computed MSI is below 80% | Kill surviving mutants or remove dead code, then re-run. |
| Fork PR fails with `unknown revision` | Shallow checkout cannot find base commit | Ensure `fetch-depth: 0` is set on `actions/checkout` in the workflow. |
