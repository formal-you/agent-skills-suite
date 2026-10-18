# Verification Protocol for Quality Engineering

## 1. Overview
This document defines the CI testing pipeline architecture and evidence-audit protocols maintained by the `quality-engineering` skill. The pipeline governs multi-stage quality assurance across test environments, pre-merge pull request gates, and post-merge verification.

---

## 2. Multi-Stage CI Testing Pipeline Architecture

The quality engineering pipeline decouples testing into four distinct stages:

### Stage 1: Local Testing (Agent Workspace)
- Executed locally by Dev and QA roles during task implementation.
- Dev validates single-function cyclomatic complexity ($V(G) \le 10$) and runs machine-checkable DoD commands.
- QA conducts local integration testing, BDD-driven E2E testing, mutation testing ($\text{MSI} \ge 80\%$), static linting, and optional code review.
- QA completes `03-qa-verification.md` and checks `- [x] QA_PASSED`.

### Stage 2: Test Environment Configuration & Validation
- The shipped CI template installs the project's declared dependencies and runs an acceptance-test
  collection probe before execution.
- Network isolation is `advisory` unless `pytest-socket` is installed (then `--disable-socket`);
  container/sandbox topology validation remains a project responsibility.
- Verify environment health before launching automated test suites to eliminate environmental false failures.

### Stage 3: Pre-Merge PR Automated Checks (Authoritative Quality Gates)
Orchestrates automated gates on every pull request:
1. **Gate 1 (Plan Linter)**: Validates task contracts, Given-When-Then BDD scenarios, task sizing, DAG acyclicity, and specification anchors. It does not audit `03` complexity/mutation evidence.
2. **RBAC Boundary Audit**: Analyzes PR diffs to enforce role write scopes (Dev cannot edit acceptance tests; QA cannot edit source; Planner owns contracts).
3. **Static Complexity Gate**: Runs AST-level complexity analysis, fails closed when no source scope is given, and uploads `complexity-report.json` for Gate 3.
4. **Acceptance Test Execution**: Installs dependencies, runs a collection probe, then executes the black-box acceptance suite (pytest with JUnit XML, or unittest fallback).
5. **Gate 3 (Verification Linter Audit)**: Cross-validates signed-off `03-qa-verification.md` against the real AST artifact, then audits basis-path coverage and mutation testing MSI thresholds.

### Stage 4: Post-Merge Automated Checks & Convergence
- Triggered automatically on mainline merge (`push` to main/master).
- Executes comprehensive regression suites across the entire codebase.
- Runs the fail-closed mutation gate (`mutation_gate.py`) against the project's `MUTATION_COMMAND`.
- Spec convergence (`converge.py apply`) is manual/optional in the template; tracks mutation score baselines and benchmark metrics.

---

## 3. Gate 3 Evidence-Audit Protocol

The deterministic Gate 3 auditor (`verification_linter.py`) evaluates every task bundle marked `QA_PASSED` in `03-qa-verification.md`. It enforces the required sections and, in CI, cross-validates Section 3 against the live AST artifact.

### 3.1 Complexity & Basis-Path Coverage (Section 3)
| Column | Required format | Meaning |
|---|---|---|
| **Function** | `function_name` | Identifier of the target function/module |
| **V(G)** | Integer (e.g. `8`) | McCabe cyclomatic complexity |
| **Test Cases** | Identifiers (`TC-1, TC-2`) or count (`3`) | Independent test cases that cover distinct paths |

#### Thresholds
- `V(G) <= 10` — **Standard** (approved without qualification).
- `11 <= V(G) <= 15` — **Warning** (requires architectural justification in Dev workspace).
- `V(G) > 15` — **Error** (untestable complexity; prohibited; blocks build).
- **Basis-Path Rule**: $\text{Test Cases} \ge \text{actual } V(G)$. Every independent execution path must map to at least one test case.

#### AST cross-validation (`--actual-complexity`)
The report schema is the JSON emitted by `complexity_check.py`:

```json
{
  "engine": "tree-sitter",
  "functions": [
    {"file": "src/auth/service.py", "line": 45, "function": "authenticate", "vg": 7}
  ],
  "violations": [],
  "warnings": [],
  "passed": true
}
```

With `--require-actual-complexity` (CI), or whenever `--actual-complexity` is supplied:
- A `touch_files` function present in the AST report but absent from Section 3 -> `COMPLEXITY_FUNCTION_MISSING_IN_03`.
- Section 3 reports a different V(G) than the AST report -> `COMPLEXITY_MISMATCH_WITH_AST`.
- Section 3 lists a function absent from the AST report -> `COMPLEXITY_PHANTOM_FUNCTION`.
- A missing/unreadable report -> `COMPLEXITY_REPORT_MISSING`.
- An unparseable `touch_files` block -> `TOUCH_FILES_UNREADABLE` warning (promoted under `--strict`).

### 3.2 Mutation Testing (Section 4)
Evidence must provide the mutation kill ratio in one of two formats:
1. **Explicit MSI**: `MSI: 85%` (or in the summary table).
2. **Killed / Total counts**: `killed 85 of 100 mutants` (linter derives MSI).

#### Thresholds
- Default `min_msi = 80%`. `risk_level: core` raises the floor to `90%`.
- MSI below threshold yields `QA_INVALID_MSI_SCORE`.
- Every populated mutation table must be compliant; when two recognized tables are present they must
  agree on MSI/total, otherwise `MUTATION_TABLE_INCONSISTENT` is emitted.
- With `--require-provenance`, `Equivalent > 0` requires a non-empty
  `| Equivalent mutant justification | ... |` row, otherwise
  `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING`.
- Zero *critical* business-logic mutants surviving remains the reviewer/QA policy; the deterministic
  Gate 3 check enforces the MSI threshold and table consistency.

### 3.3 Execution Evidence and Provenance (Section 5)
Provides execution proof in a markdown table:

| Command | Result |
|---|---|
| `python -m unittest discover` | `All 24 tests passed` |

Both cells must be non-empty. Empty `Command` yields `EVIDENCE_MISSING_COMMAND`; empty `Result` yields `EVIDENCE_MISSING_RESULT`.

With `--require-provenance`, Section 5 must also provide:
- `| Artifact path | artifacts/... |` — a path that exists under `--repo-root`.
- `| Artifact SHA-256 | <hex> |` — must match the file digest.
- Optional: `| Tool version | ... |`, `| Timestamp (UTC) | ... |`.

Missing path/file -> `EVIDENCE_MISSING_ARTIFACT`; bad digest -> `EVIDENCE_HASH_INVALID`.

### 3.4 Normalized Mutation Report for the Active Gate

`mutation_gate.py run` executes the project's `MUTATION_COMMAND` and then requires this report
at `--report` (adapt it from the stack tool's output):

```json
{
  "tool": "mutmut",
  "targets": [
    {"file": "src/auth/service.py", "total": 10, "killed": 8,
     "timed_out": 1, "equivalent": 1, "survived": 0}
  ]
}
```

MSI is computed as `(killed + timed_out) / (total - equivalent)`. A missing command or report,
a non-zero command exit, or MSI below `--min-msi` fails the gate. The gate is fail-closed by design;
do not wrap it in `|| true` or `continue-on-error`.

---

## 4. Maintenance
- Update thresholds in `verification_linter.py` if project policies evolve.
- Keep `references/triage-routing.md` aligned with the emitted error codes.
- The protocol file lives in `/.agents/skills/quality-engineering/references/`. Keep it in sync with script updates.
