# Agent Skills — Modern Quality Engineering & Execution Pipeline

Ten reusable, harness-neutral workflow skills that turn a vague idea or an existing codebase into a reviewed,
implemented, independently verified and spec-converged change, underpinned by modern quality engineering:

```text
idea    → prd-generator → spec-generator → task-decomposition → Gate 1 (plan-linter) → Gate 2 (review) → dev ↔ qa → Gate 3 (quality-engineering) → converge → done
           (.specs/01-prd*)  (.specs/02-tech-spec*, .specs/adr/*)   (tasks/task-*)      (BDD & DAG)     (Semantic) (V(G)<=10 & MSI>=80%) (CI Verification)   (Spec write-back)
change  → change (brownfield proposal + one task bundle) → the same Gate 1/2 → dev ↔ qa → Gate 3 → converge
```

This directory is the runtime source of truth (mirrored byte-for-byte to
`skills/workflow/<name>/`). The skills are prompt-first: they work with any agent harness and degrade
to a manual checklist when no helper script or Python interpreter is available. Deterministic gates
are stdlib-only helpers; the multi-language complexity checker additionally uses optional
tree-sitter/lizard engines with a Python AST fallback. Repository CI is the authoritative enforcement
layer (see `.agents/rules` and `docs/skills-compatibility.md`).

Chinese Guide: [docs/skills-guide.zh-CN.md](../../docs/skills-guide.zh-CN.md).

---

## Skills

| Skill | Use it for | Inputs | Outputs | Bundled helpers |
| :--- | :--- | :--- | :--- | :--- |
| [`prd-generator`](prd-generator/SKILL.md) | Turn an ambiguous idea into a modular product requirements document | User idea / notes | `.specs/01-prd.md`, `.specs/01-prd/` | `scaffold.py`, `lint_prd.py`, optional `engine.py` |
| [`spec-generator`](spec-generator/SKILL.md) | Turn a PRD into architecture decisions and an engineering spec | `.specs/01-prd.md` | `.specs/adr/*.md`, `.specs/02-tech-spec.md`, `.specs/02-tech-spec/` | `scaffold.py`, `lint_spec.py`, optional `engine.py` |
| [`task-decomposition`](task-decomposition/SKILL.md) | Slice a spec into atomic, independently verifiable task bundles with BDD Gherkin scenarios | PRD + ADRs + tech spec | `tasks/task-*/01-contract.md` … `04-process.md` | `scaffold_task.py` |
| [`change`](change/SKILL.md) | Run a bounded brownfield change: proposal, one task bundle, archive | Existing `.specs/02-tech-spec.md` + repository | `.specs/changes/<change-id>/proposal.md`, one `tasks/<task-id>/` bundle, standards report | `scaffold_change.py`, `standards_extract.py`, `lint_change.py` |
| [`plan-linter`](plan-linter/SKILL.md) | Run deterministic Gate 1 on task bundles (validating size, DAG, BDD Given-When-Then, placeholders) | `tasks/` (+ optional spec, repo root, change dir) | Gate 1 report; JSON; coverage matrix | `plan_linter.py` |
| [`review`](review/SKILL.md) | Independently review a plan (Gate 2) or a code change | plans/tasks, or diff + evidence | Findings + `PASS`/`REQUEST CHANGES`/`BLOCKED` | none (prompt workflow) |
| [`dev`](dev/SKILL.md) | Implement one task bundle within its blast radius, maintaining cyclomatic complexity V(G) <= 10, and hand off to QA | `tasks/<task-id>/01-contract.md` + project commands | Code changes, filled `02`, `WAITING_FOR_QA` | none (prompt workflow) |
| [`qa`](qa/SKILL.md) | Local development stage testing: integration, BDD E2E, mutation testing (MSI >= 80%), static lint/complexity analysis, autonomous review | `01`, filled `02`, project test command | `tests/acceptance/**`, `tests/integration/**`, filled `03`, `QA_PASSED`/`REWORK_REQUIRED` | none (prompt workflow) |
| [`quality-engineering`](quality-engineering/SKILL.md) | Build CI pipelines, validate test environments, enforce pre-merge PR checks and post-merge automated verification | CI workflow configs, PR diff, `03-qa-verification.md` | CI workflow statuses, Gate 3 audit report | `complexity_check.py`, `verification_linter.py` |
| [`converge`](converge/SKILL.md) | Fold QA-confirmed deviations back into the spec and archive the bundle | `01`, filled `02` deviation log, checked `03` | Updated `.specs/02-tech-spec.md`, `CONVERGED` status, archived bundle | `converge.py` |

The first four skills produce the plan (`change` is the brownfield entry that reuses
`task-decomposition`), `plan-linter` validates its structure and Given-When-Then BDD scenarios,
`review` audits semantics and ADR compliance, `dev`/`qa` execute and verify locally under strict
complexity and mutation testing thresholds, `quality-engineering` builds CI pipelines and validates
signoff artifacts at Gate 3 (`verification_linter.py`), and `converge` closes the loop by writing confirmed behavior back into
the spec. Skills are self-contained: each one bundles the role boundaries it needs in its own
`references/` directory. Repository role rules (`.agents/rules/*.md`, including `enforcement.md`)
are an optional suite layer that skills follow when present, not a runtime dependency.

Platform-specific helpers may also live in this directory (for example a Windows sandbox
diagnostic skill when installed). They are not part of the specification pipeline and must declare a
`compatibility` field in their frontmatter.

---

## Modern Quality Engineering Triad

The specification and execution pipeline embeds three modern quality engineering pillars:

1. **BDD Executable Specifications & Living Documentation**:
   - `01-contract.md` formalizes acceptance criteria using structured Gherkin Given-When-Then strings
     in `dod.edge_cases` and Section 4 behavioral invariants.
   - `task-decomposition` derives executable scenarios directly from PRDs and architecture specifications.
   - `plan_linter.py` statically enforces complete 3-clause syntax (`BDD_MISSING_PRECONDITION`,
     `BDD_MISSING_ACTION`, `BDD_MISSING_OUTCOME`), preventing vague requirements.
   - QA implements executable acceptance suites using stack-native open-source BDD frameworks (pytest-bdd,
     Cucumber.js, Godog, Cucumber-JVM, cucumber-rs, Reqnroll/SpecFlow) in `tests/acceptance/`.

2. **McCabe Cyclomatic Complexity & Basis Path Testing Gate**:
   - Multi-language AST analysis powered by **Tree-sitter** (https://github.com/tree-sitter/tree-sitter)
     and open-source analyzers (Lizard, radon, eslint, gocyclo, pmd) across Python, JS/TS, Go, Rust, Java, C/C++.
   - Dev controls single-function complexity: $V(G) \le 10$ (STANDARD), $11-15$ (WARNING), $> 15$ (CRITICAL/BLOCKED).
   - Standard refactoring patterns: Extract Method, Strategy Pattern, Guard Clauses, Table-driven design.
   - QA Basis Path Test Baseline Rule: Black-box acceptance test count must satisfy $\text{Test Cases} \ge \sum V(G)$.
   - Validated deterministically at CI Gate 3 by `verification_linter.py` and pre-merge by `complexity_check.py`.

3. **Mutation Testing & Mutation Score Indicator (MSI) Audit**:
   - Mandatory open-source mutation testing tools across ecosystems: `mutmut` (Python), `Stryker` (JS/TS),
     `go-mutesting` (Go), `PITest` (Java), `cargo-mutants` (Rust), `Mull` (C/C++), `Stryker.NET` (C#).
   - Eliminates false positives and weak assertions by mutating modified code in `touch_files`.
   - Mutation Score Indicator formula:
     $$\text{MSI} = \frac{\text{Killed} + \text{TimedOut}}{\text{Total} - \text{Equivalent}} \times 100\% \ge 80\%$$
   - 6-step QA workflow: Target Scope -> Mutate -> Execute -> Classify -> Kill Weak Assertions -> Audit.
   - Synthetic mutation fallback is strictly reserved for niche environments without open-source tooling.

---

## Quality Gates & Verification Architecture

The lifecycle features a decoupled, multi-stage gate architecture:

1. **Gate 1 — Deterministic Plan Gate (`plan_linter.py`)**:
   Validates contract frontmatter, task sizing (1-3 touch files, 50-250 lines), spec anchors, ADR compliance,
   placeholder absence, DAG acyclicity, real-file topology, and Given-When-Then BDD scenarios.
   ```bash
   python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --json
   ```

2. **Gate 2 — Semantic Review Gate (`review`)**:
   A prompt-only anti-hallucination, forward coverage, and ADR compliance audit performed by an
   independent, read-only reviewer agent. It issues `PASS`, `REQUEST CHANGES`, or `BLOCKED`.

3. **Gate 3 — Deterministic QA Verification Gate (`verification_linter.py`)**:
   Audits `03-qa-verification.md` upon `QA_PASSED` signoff, cross-checks the Section 3 V(G) values
   against the real AST artifact (`--actual-complexity`), ensures Basis Path coverage satisfies
   $\text{Test Cases} \ge V(G)$, and Mutation Testing evidence is compliant with $\text{MSI} \ge 80\%$
   ($\ge 90\%$ for `risk_level: core` tasks).
   ```bash
   python .agents/skills/quality-engineering/scripts/verification_linter.py \
     --tasks-dir ./tasks --actual-complexity artifacts/complexity-report.json \
     --require-actual-complexity --strict --json
   ```

4. **Convergence — Spec Write-Back (`converge.py`)**:
   After `QA_PASSED` and Gate 3 pass, `converge` folds confirmed implementation deviations from `02`
   into `.specs/02-tech-spec.md` (append-only), marks `04` as `CONVERGED`, and archives the bundle.
   ```bash
   python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id>
   ```

Exit codes for all bundled helpers: `0` success, `1` content/gate failure, `2` optional dependency or
usage unavailable, `3` unexpected error.

---

## 4-Stage Layered Testing Pipeline

Quality enforcement spans four distinct stages:

1. **Stage 1: Local Testing (Dev & QA Self-Checks)**:
   - Dev runs `dod.type_check`, `dod.lint`, unit tests, verifies $V(G) \le 10$, and fills `02-dev-workspace.md`.
   - QA writes black-box acceptance tests in `tests/acceptance/` directly from `01` BDD scenarios.
   - Pre-check: Local runs of `plan_linter.py` (Gate 1) and `verification_linter.py` (Gate 3).

2. **Stage 2: Test Environment (Sandbox & Topology Verification)**:
   - Ephemeral container or sandbox environments isolate external dependencies (databases, messaging, APIs).
   - The CI template installs declared project dependencies and runs an acceptance-test collection
     probe; network isolation is advisory unless `pytest-socket` is installed.

3. **Stage 3: Pre-merge / PR Gate (L2 Authoritative Layer)**:
   - Mandatory CI gating triggered on every pull request:
     1. RBAC boundary audit: `python tools/rbac_audit.py --base <base> --head <head> --tasks-dir tasks --json`
     2. Gate 1 static plan & BDD check: `python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json`
     3. Cyclomatic complexity static check: Enforces single-function $V(G) \le 10$ across changed lines.
     4. Full acceptance test execution: Runs `tests/acceptance/**`.
     5. Mutation testing kill ratio audit: fail-closed on trunk via `tools/mutation_gate.py`
        (normalized report + $\text{MSI} \ge 80\%$); PR Gate 3 audits the recorded evidence.
     6. Gate 3 QA verification audit: `python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir tasks --actual-complexity artifacts/complexity-report.json --require-actual-complexity --strict --json`
     7. Gate 2 Reviewer signoff: independent reviewer approves PR semantics (human/branch-protection
        step; not a shipped CI job).

4. **Stage 4: Post-merge & Staging/Release (Regression & Convergence)**:
   - Full mainline test suite execution prevents cross-PR regressions.
   - Specification convergence is manual/optional in the shipped template:
     `python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id>` appends
     confirmed deviations to `.specs/02-tech-spec.md` and archives completed task bundles.
   - Mainline mutation baseline refresh and performance benchmark tracking.

---

## Authoritative CI Enforcement & Templates

Prompt rules are advisory (L0/L1); **CI is the authoritative enforcement layer (L2)**.

Ready-to-use GitHub Actions workflow templates live under `templates/ci/`:
- `quality-gate.yml`: Integrated end-to-end quality engineering pipeline (RBAC + Gate 1 + Tests + Gate 3).
- `rbac-gate.yml`: Standalone role permission and write-scope boundary audit.
- `plan-gate.yml`: Standalone Gate 1 plan linter workflow.

See [`templates/ci/README.md`](../../templates/ci/README.md) for full setup instructions and branch protection guidance.

---

## Discovery and Installation

| Harness | Native location | Notes |
| :--- | :--- | :--- |
| Codex | `.agents/skills/<name>/` | Discovered from the current directory up to the repo root, and from `~/.agents/skills`. |
| Antigravity | `.agents/skills/<name>/` | Workspace scope; global scope is `~/.gemini/config/skills/`. |
| DeepSeek Harness (DSH) | `.agents/skills/<name>/` | Workspace skills are loaded directly. |
| Claude Code | `.claude/skills/<name>/` | Does **not** read `.agents/skills/`; use `tools/install_skills.py` to link or copy the same directories, or install the plugin. |

```bash
# Adopt the whole suite into another repository (skills + rules + audit + CI templates)
python tools/quickstart.py --target ../another-repo --copy --with-ci
```

---

## Enforcement Layers (Honest Model)

| Layer | Mechanism | Scope | Guarantee |
| :--- | :--- | :--- | :--- |
| L0 | Prompt rules + role instructions | every harness | advisory |
| L1 | Local linter pre-checks (`plan_linter.py`, `verification_linter.py`) | local development | advisory / early feedback |
| L2 | `tools/rbac_audit.py` & Quality Gate in CI | every harness with git | authoritative for committed changes |
| L3 | Branch protection / required status checks | repository settings | authoritative repository barrier |

**Do not** describe prompt rules or local hooks as physical enforcement. The authoritative protection
for the specification and execution pipeline is CI plus repository branch protection.

---

## Versioning

- Skill versions are declared in each `SKILL.md` frontmatter (`metadata.version`).
- Layout and behavior changes are recorded in [`docs/skills-compatibility.md`](../../docs/skills-compatibility.md).
- Dual-tree mirroring: `skills/workflow/<name>/` and `.agents/skills/<name>/` maintain 100% byte-for-byte parity.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
