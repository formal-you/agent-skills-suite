# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Skills are now self-contained for plugin distribution: every `SKILL.md` references only files
  inside its own directory, and each role skill bundles `references/role-boundaries.md`. Repository
  agent rules (`AGENTS.md`, `.agents/rules/`) are followed when present but are no longer a runtime
  dependency. This makes Claude Code/Codex/Copilot plugin installs and `npx skills` single-skill
  installs work without the rest of the repository.
- `docs/agent-rules.md` moved into the rules layer as `.agents/rules/enforcement.md`; `AGENTS.md`,
  the skills guide and the skill index now point there.
- `tools/package_skills.py` ships only user-facing docs and self-contained skills; the audit archive,
  the pilot report, the v2 design contract and the old `docs/agent-rules.md` are not copied.
- Benchmark report updated for v3.1.0 (nine skills plus the platform helper, plugin distribution,
  self-contained skills and the shipped test baseline); it stays in the release.
- The optional Antigravity hook layer was removed: `.agents/scripts/` (`rbac_guard.py`,
  `event_bus_logger.py`), `.agents/hooks.json` and their tests. The honest enforcement model is now
  prompt rules (L0, advisory), the CI RBAC audit (L1, authoritative) and branch protection (L2).
  No local hook adapter is shipped; adopters may add host-side hooks, but they stay bypassable.

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
