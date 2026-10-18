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
- Provision isolated, reproducible test environments (containers, virtualized runners, or sandboxes).
- Validate environment prerequisites: correct runtime versions, system packages, database/cache services, and network mock configurations.
- Verify environment health before launching automated test suites to eliminate environmental false failures.

### Stage 3: Pre-Merge PR Automated Checks (Authoritative Quality Gates)
Orchestrates automated gates on every pull request:
1. **Gate 1 (Plan Linter)**: Validates task contracts, Given-When-Then BDD scenarios, task sizing, DAG acyclicity, and specification anchors.
2. **RBAC Boundary Audit**: Analyzes PR diffs to enforce role write scopes (Dev cannot edit acceptance tests; QA cannot edit source; Planner owns contracts).
3. **Static Complexity Gate**: Runs AST-level complexity analysis across changed files; rejects any function with $V(G) > 15$.
4. **Acceptance Test Execution**: Executes full black-box acceptance and integration test suites against clean code with 100% pass requirement.
5. **Gate 3 (Verification Linter Audit)**: Statically audits signed-off `03-qa-verification.md` files for basis path coverage and mutation testing MSI thresholds.

### Stage 4: Post-Merge Automated Checks & Convergence
- Triggered automatically on mainline merge (`push` to main/master).
- Executes comprehensive regression suites across the entire codebase.
- Triggers specification convergence to fold confirmed implementation deviations back into technical specs and archive completed bundles.
- Tracks long-term mutation score baselines and benchmark metrics.

---

## 3. Gate 3 Evidence-Audit Protocol

The deterministic Gate 3 auditor (`verification_linter.py`) evaluates every task bundle marked `QA_PASSED` in `03-qa-verification.md`. It enforces three mandatory sections:

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
- **Basis-Path Rule**: $\text{Test Cases} \ge V(G)$. Every independent execution path must map to at least one test case.

### 3.2 Mutation Testing (Section 4)
Evidence must provide the mutation kill ratio in one of two formats:
1. **Explicit MSI**: `MSI: 85%` (or in the summary table).
2. **Killed / Total counts**: `killed 85 of 100 mutants` (linter derives MSI).

#### Thresholds
- Default `min_msi = 80%`. Core/security modules require $\ge 90\%$.
- MSI below threshold yields error (`MUTATION_SCORE_BELOW_THRESHOLD`).
- $80\% \le \text{MSI} < 90\%$ yields warning (`MUTATION_SCORE_MARGINAL`).
- Zero critical business logic mutants surviving.

### 3.3 Execution Evidence (Section 5)
Provides execution proof in markdown table:
| Command | Result |
|---|---|
| `python -m unittest discover` | `All 24 tests passed` |

Both cells must be non-empty. Empty `Command` yields `EVIDENCE_MISSING_COMMAND`; empty `Result` yields `EVIDENCE_MISSING_RESULT`.

---

## 4. Maintenance
- Update thresholds in `verification_linter.py` if project policies evolve.
- The protocol file lives in `/.agents/skills/quality-engineering/references/`. Keep it in sync with script updates.
