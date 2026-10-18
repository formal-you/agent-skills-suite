# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.1] - 2026-10-19

### Fixed

- **QA self-contained Gate 3 pre-check**: `qa` now ships `scripts/verification_linter.py`, a
  stdlib-only vendored copy of the quality-engineering auditor, so a standalone `qa` install can
  audit `03` evidence without depending on another skill. The QA copy is byte-parity tested against
  the canonical quality-engineering copies.
- `qa/SKILL.md` no longer instructs `python -m verification_linter` (not an installed module).
  It now runs the bundled script and supports optional `--actual-complexity` /
  `--require-actual-complexity` cross-validation.

### Changed

- `qa` (`2.2.0`) compatibility notes an optional stdlib Python Gate 3 pre-check; the local check is
  explicitly advisory and CI Gate 3 remains authoritative. `qa-protocol.md` adds the local
  pre-check procedure.
- `VERSION`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are bumped to
  `3.4.1`.

## [3.4.0] - 2026-10-19

### Added

- **Repository test strategy**: `docs/testing-strategy.md` seeds the suite's own test strategy
  (purpose/scope, quality attributes, risk matrix, test levels and responsibilities, design
  techniques, data/environment, flakiness, contract/property/non-functional guidance, metrics,
  RACI, review cadence). Adopters replace its content with their project's strategy.
- **Strategy-to-CI mapping**: `quality-engineering/references/verification-protocol.md` gains a
  `Strategy-to-CI mapping` table that turns risk classes, test levels, data/environment policy,
  flakiness rules and metrics into required CI jobs, commands, environment services, rerun/quarantine
  rules and evidence artifacts. `quality-engineering` implements the strategy; `test-engineering`
  defines it.
- **Test design summary**: `qa/references/qa-protocol.md` records strategy reference, risk level,
  techniques, environment/data and out-of-scope, and the `03-qa-verification.md` template gains
  `### 2.1 Test design summary` before the existing matrix.
- **Wiring tests**: `tests/unit/test_test_strategy_wiring.py` asserts the strategy document, the
  role-rule default path/override, the QA strategy consumption, the template summary, the
  quality-engineering mapping table, the review boundary and skill self-containment.

### Changed

- `qa` (`2.1.0`) reads the repository test strategy before test design, records a test-design
  summary and marks `strategy: baseline` when the project has no strategy yet.
- `test-engineering` (`1.1.0`) names the strategy document's default location via the repository role
  rule (which adopters may override) instead of leaving the output path undefined.
- `quality-engineering` (`2.1.0`) declares the repository test strategy as a read-only input and
  gains one responsibility: map the approved strategy to CI profiles, job selection, thresholds and
  environment services; do not invent test standards.
- `review` now explicitly defers test-design quality review to the independent `test-engineering`
  review mode and stays semantic plan/change review.
- `VERSION`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are bumped to
  `3.4.0`; the plugin and marketplace descriptions keep counting eleven skills. `README.md`,
  `docs/skills-guide.zh-CN.md` and `docs/skills-compatibility.md` link the strategy artifact.

### Fixed

- The test-engineering role rule now names a concrete project-relative default strategy output
  (`docs/testing-strategy.md`) plus the adopter override rule, so the strategy no longer depends on
  an undefined "agreed path".
- Standalone installs no longer imply a suite-level strategy file: the skill ships the strategy
  template, the role rule says to create the project strategy from it when absent, and
  `docs/testing-strategy.md` is documented as the suite's own example rather than an install
  dependency.
- Test-design quality review no longer risks being absorbed into semantic Gate 2/change review; the
  boundary is stated in the `review` skill.
- CI configuration no longer lacks a documented translation from strategy to jobs/thresholds: the
  mapping table makes the handoff explicit and forbids hiding failures behind reruns.

## [3.3.0] - 2026-10-19

### Added

- **Multi-language CI stack profiles**: `templates/ci/profiles/` ships reference fragments for
  Python, Node/TypeScript, Go, Java/Kotlin, Rust, C#/.NET and C/C++, plus `index.json` and
  `quality-gate.config.example.json`. `docs/ci-stack-profiles.zh-CN.md` records adoption,
  mutation-report adapter expectations and real-middleware guidance. `quality-gate.yml` remains the
  Python reference implementation.
- **New `test-engineering` skill** (`skills/workflow/test-engineering/`, AGENTS mirror in
  `.agents/skills/test-engineering/`): prompt-only global test methodology covering test strategy,
  risk-based test design methods (equivalence, boundary, decision table, state transition, pairwise),
  test data/environment and test-double policy, flakiness policy, contract/property and
  non-functional guidance, test metrics and independent test-design review. It writes only the agreed
  test-strategy document and test-design review notes (`DESIGN_READY` / `DESIGN_GAPS`); it never
  accepts or signs off an individual task, never issues `QA_PASSED` / `REWORK_REQUIRED`, never writes
  tests or `03-qa-verification.md`, and never runs CI gates.
- **`test-engineering` role rule and bundled references**: `.agents/rules/test-engineering.md` plus
  `references/test-strategy.md`, `references/test-design-review.md`,
  `references/role-boundaries.md` and `assets/templates/test-strategy.template.md`.

### Changed

- **Testing role boundaries aligned for eleven skills**: `qa` owns per-task acceptance testing,
  evidence and the single `QA_PASSED` / `REWORK_REQUIRED` verdict; `quality-engineering` owns CI
  pipelines, gates and the authoritative audit scripts; `test-engineering` owns the repository-wide
  test system and an independent test-design opinion (a design marker, not a verdict). `AGENTS.md`,
  `.agents/rules/enforcement.md`, the skill index, `README.md`, `docs/skills-guide.zh-CN.md`,
  `docs/skills-compatibility.md` and the benchmark/remediation notes now describe eleven skills.
- `VERSION`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are bumped to
  `3.3.0`; the plugin and marketplace descriptions count eleven skills.

## [3.2.0] - 2026-10-19

### Added

- **Modern Quality Engineering Triad**:
  - Multi-language AST McCabe Cyclomatic Complexity static checker (`complexity_check.py` v2.0.0) powered by Tree-sitter (https://github.com/tree-sitter/tree-sitter) with Lizard integration and Python AST fallback, covering Python, JS/TS, Go, Rust, Java, C/C++, C#.
  - BDD executable living documentation with stack-native open-source frameworks (pytest-bdd, Cucumber.js, Godog, Cucumber-JVM, cucumber-rs, Reqnroll/SpecFlow).
  - Mandatory open-source mutation testing tools (mutmut, Stryker, go-mutesting, PITest, cargo-mutants, Mull) with MSI >= 80% threshold and basis path coverage (Test Cases >= V(G)).
- **New `quality-engineering` skill**: CI pipeline construction, test environment provisioning, pre-merge PR quality gates (Gate 1 contract lint, RBAC audit, complexity check, acceptance tests, Gate 3 audit), post-merge automated verification, and ownership of CI workflow templates (`quality-gate.yml`) and audit scripts (`complexity_check.py`, `verification_linter.py`).
- **Gate 3 Acceptance Audit**: `verification_linter.py` deterministically audits signed-off `03-qa-verification.md` artifacts for basis path coverage and mutation MSI thresholds before merge.
- **Fail-closed mutation gate**: `tools/mutation_gate.py` runs a project's `MUTATION_COMMAND`,
  validates the normalized report, enforces MSI, and fails closed on missing command/report or low
  score. `quickstart.py --with-ci` now installs it alongside `rbac_audit.py`.
- **Gate 3 cross-validation**: `verification_linter.py` accepts `--actual-complexity`,
  `--require-actual-complexity`, `--repo-root`, and `--require-provenance`; it cross-checks Section 3
  V(G) against the live AST artifact and rejects omitted/phantom/mismatched functions.
- **Evidence provenance and core profile**: `03-qa-verification.md` gains artifact path/SHA-256,
  tool version, timestamp and equivalent-mutant justification rows; `01-contract.md` gains optional
  `risk_level: standard|core` (core floors MSI at 90%).
- **Appeal and arbitration**: `02-dev-workspace.md` gains a structured Appeal Request; `review`
  gains an arbitration mode (`CODE_BUG` / `TEST_BUG` / `SPEC_AMBIGUITY`); orchestrator routing and
  circuit-break rules are documented.
- **Failure triage registry**: `quality-engineering/references/triage-routing.md` maps error codes to
  owners, first actions, escalation triggers and forbidden shortcuts.
- **Hardening handbook**: `docs/skills-remediation.zh-CN.md` records the critique adjudication,
  defect ledger and ordered work packages.

### Changed

- **Clear division of responsibilities**:
  - `qa`: Dedicated to local development stage testing (integration, BDD E2E, mutation testing, static lint & complexity analysis, autonomous review invocation). Refactored into a prompt-only execution skill.
  - `quality-engineering`: CI pipeline construction, test environment provisioning, pre-merge PR gates (Gate 1, RBAC, complexity check, acceptance tests, Gate 3 audit), post-merge automated verification, and ownership of CI workflow templates (`quality-gate.yml`) and audit scripts (`complexity_check.py`, `verification_linter.py`).
  - `plan-linter`: Strictly single responsibility for Gate 1 deterministic task contract and DAG validation before development starts.
- Skills are now self-contained for plugin distribution: every `SKILL.md` references only files
  inside its own directory, and each role skill bundles `references/role-boundaries.md`. Repository
  agent rules (`AGENTS.md`, `.agents/rules/`) are followed when present but are no longer a runtime
  dependency. This makes Claude Code/Codex/Copilot plugin installs and `npx skills` single-skill
  installs work without the rest of the repository.
- `docs/agent-rules.md` moved into the rules layer as `.agents/rules/enforcement.md`; `AGENTS.md`,
  the skills guide and the skill index now point there.
- `tools/package_skills.py` is maintainer-only and no longer shipped; it stays in the upstream
  development repository and `RELEASING.md` documents the build. The shipped tools are
  `quickstart.py`, `install_skills.py`, `rbac_audit.py` and `mutation_gate.py`.
- The upstream packaging build ships only user-facing docs and self-contained skills; the audit archive,
  the pilot report, the v2 design contract and the old `docs/agent-rules.md` are not copied.
- Benchmark report updated for v3.1.0 (nine skills plus the platform helper, plugin distribution,
  self-contained skills and the shipped test baseline); it stays in the release.
- The optional Antigravity hook layer was removed: `.agents/scripts/` (`rbac_guard.py`,
  `event_bus_logger.py`), `.agents/hooks.json` and their tests. The honest enforcement model is now
  prompt rules (L0, advisory), the CI RBAC audit (L1, authoritative) and branch protection (L2).
  No local hook adapter is shipped; adopters may add host-side hooks, but they stay bypassable.

### Fixed

- Gate 3 is no longer skipped on trunk pushes when `rbac-audit` is skipped; it uses
  `if: always()` and explicit needs results.
- `verification_linter.py` no longer passes when any one mutation table is compliant; all populated
  tables must comply and agree, otherwise `MUTATION_TABLE_INCONSISTENT`.
- `complexity_check.py` is fail-closed: it no longer scans `.` implicitly, supports
  `--changed-files`, emits a full `functions` array, and reports unsupported/engine-unavailable files
  instead of silently passing.
- `plan_linter.py` no longer audits Gate 3 evidence; Gate 1 remains single-responsibility.
- Error-code documentation and code now agree (`COMPLEXITY_BASIS_PATH_INSUFFICIENT`,
  `QA_INVALID_MSI_SCORE`, `FORBIDDEN_TOUCH_FILE`, `QA_EDITED_SOURCE`, etc.).
- CI acceptance installs dependencies, runs a collection probe, emits JUnit XML and uploads artifacts;
  the stdlib-only compatibility claim now explicitly excludes the optional complexity engines.

### Removed

- Development-process documents that are unrelated to using the skills:
  `docs/audit/` (skill-suite audit archive and evidence), `docs/v3-pilot.zh-CN.md`
  (internal pilot report) and `docs/skills-v2-spec.md` (v2 implementation contract). They remain in
  the upstream development repository.
- `.agents/scripts/`, `.agents/hooks.json` and `tests/unit/test_hooks.py` (optional L1 hook adapter;
  skills never depended on it).

## [3.1.0] - 2026-10-18

### Added

- Standalone distribution: nine prompt-first skills, role rules, hook adapters, helper tools,
  CI templates, skill docs and skill unit tests.
- `change` skill: brownfield proposal -> one 4-document task bundle -> archive, with a
  deterministic repository standards extractor.
- `converge` skill: append-only spec write-back after `QA_PASSED`, idempotent convergence
  markers, task-bundle and proposal archive.
- `plan-linter` 3.x: anchor coverage matrix (`--spec`, `--coverage-out`), reverse path
  topology (`--repo-root`, `--strict-topology`), change-proposal checks and the `micro` tier.
- `tools/quickstart.py`: one-command adoption into another repository, including CI templates.
- Claude Code plugin and marketplace manifests, so the suite can be installed as a plugin.

### Changed

- `standards_extract.py` 3.1 scans every package manifest (workspace packages included) and
  ignores generated `tasks/` and `.specs/changes/` directories, so `--check` is stable mid-change.
- Review/dev/qa skills updated for the deviation log and the Gate 2 heuristics.

### Fixed

- Gate 1 no longer treats `tasks/archive/**` as pending bundles and downgrades archived change
  proposals to a warning.
- Standards reports no longer invalidate themselves after scaffolding a change.

## [3.0.0] - 2026-10-18

### Added

- Brownfield `change` entry, `converge` loop, Gate 2 heuristics and distribution layer.
- Nine-skill pipeline: prd-generator, spec-generator, task-decomposition, change, plan-linter,
  review, dev, qa, converge.
