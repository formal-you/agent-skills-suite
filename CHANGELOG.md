# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Multi-language CI stack profiles**: `templates/ci/profiles/` ships reference fragments for
  Python, Node/TypeScript, Go, Java/Kotlin, Rust, C#/.NET and C/C++, plus `index.json` and
  `quality-gate.config.example.json`. `docs/ci-stack-profiles.zh-CN.md` records adoption,
  mutation-report adapter expectations and real-middleware guidance. `quality-gate.yml` remains the
  Python reference implementation.

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
