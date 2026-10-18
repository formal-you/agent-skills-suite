# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Real-repository pilot report (`docs/v3-pilot.zh-CN.md`) with Gate 1/2, Dev, QA and convergence
  evidence.

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
