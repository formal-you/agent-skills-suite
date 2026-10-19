---
name: plan-linter
description: "Run the Gate 1 deterministic static check on task bundles before development starts and follow the Gate 2 review checklist. Use when task contracts exist under tasks/ and you need to verify blast radius, diff budget, declared-file topology, traceability anchors, spec anchor coverage, inherited ADRs, BDD Gherkin acceptance criteria, machine-checkable test targets, and DAG acyclicity. Do not use for code execution, CI pipeline construction, AST/complexity checks, or test audits (owned by quality-engineering)."
license: MIT
compatibility: "Harness-agnostic. Python >= 3.9 optional; without Python follow the manual checklist in references/gate-2-review.md."
metadata:
  version: "4.0.0"
  category: spec-pipeline
---

# Plan Linter (Gate 1 Planning Validator)

This skill has one bounded responsibility: **Gate 1 deterministic static validation of planned task
contracts and bundles under `tasks/` before development starts**.

- **Gate 1** is a deterministic, offline, stdlib-only script in this skill.
- **Gate 2** is a prompt-only semantic review (`review` skill; `references/gate-2-review.md` fallback).
- **Non-goals**: plan-linter never executes code, builds or runs CI pipelines, performs AST/complexity
  analysis, or audits QA complexity/mutation evidence in `03-qa-verification.md` (placeholder scan and
  document-existence checks only); those belong to `quality-engineering` and `qa`.

## Gate 1: deterministic checks

| Check | Default | Overridable |
| :--- | :--- | :--- |
| 01-contract.md exists and has valid metadata | required | no |
| task_id equals the directory name and is unique | required | no |
| touch_files count | 1..3 | max_touch_files |
| estimated_lines | 50..250 | min_diff_lines, max_diff_lines |
| origin_spec_anchor matches #sec-[a-z0-9-]+ | required | require_anchor |
| adherence_adrs lists at least one ADR | required | require_adrs |
| dod.type_check, dod.lint, dod.test_file | required | no |
| dod.feature_file is a `.feature` file under an acceptance prefix | required | require_feature_file, feature_allowed_prefixes |
| dod.step_definitions is non-empty glue code, never a `.feature` file | validated when present | no |
| Section 4 fenced `gherkin` block: one Feature + >=2 Scenarios with Given/When/Then | required | require_gherkin_block |
| dod.edge_cases count | at least 2 | min_edge_cases |
| 02-dev-workspace.md, 03-qa-verification.md, 04-process.md exist | required | require_docs |
| forbidden touch prefixes | tests/acceptance/ | forbidden_touch_prefixes |
| unresolved placeholders in 01/02/03 | blocked | scan_placeholders |
| 03-qa-verification.md content-level QA evidence | not audited (Gate 3) | no |
| reverse topology: modify paths exist, create paths do not | warning | check_topology, strict_topology, --repo-root |
| size_class micro: change_id, 1 touch file, smaller budget | required when micro | micro_min_diff_lines, micro_max_touch_files |
| change_id has an open proposal under the change directory | required when --changes-dir is given | --changes-dir |
| spec anchor coverage (uncovered anchors / contract anchors absent from spec) | report; error with --require-full-coverage or --strict-anchor | --spec, --coverage-out |
| dependency graph | acyclic, no missing tasks | no |

## Quick start

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --json
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --config plan-linter.json
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --legacy
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --repo-root . \
  --spec .specs/02-tech-spec.md --changes-dir .specs/changes \
  --strict-topology --strict-anchor --require-full-coverage --json
```

The script is optional: without Python, use `references/gate-2-review.md` as a manual checklist.
**Gate 2 is the separate `review` skill**; `references/gate-2-review.md` is the self-contained fallback
when it is not installed, and never replaces Gate 1.

## Exit codes

| Code | Meaning |
| :--- | :--- |
| 0 | Gate 1 passed for every task bundle |
| 1 | Violations found (or a contract frontmatter cannot be parsed) |
| 2 | Usage or configuration error |
| 3 | Unexpected internal error |

## Contract format

The YAML frontmatter of 01-contract.md is authoritative.

```yaml
---
task_id: task-001-auth
title: "User authentication"
estimated_lines: 120
touch_files:
  - action: create
    path: src/auth/service.py
origin_spec_anchor: "#sec-auth"
adherence_adrs: [ADR-001]
dod:
  type_check: "npm run type-check"
  lint: "npm run lint"
  test_file: "tests/acceptance/auth.spec.ts"
  feature_file: "tests/acceptance/auth.feature"
  step_definitions: "tests/acceptance/steps/auth.steps.ts"
  edge_cases:
    - "Given empty credentials, When login is attempted, Then return 400"
    - "Given an expired token, When authentication is checked, Then return 401"
---
```

Rules:
- `task_id` must equal the task directory name; paths are repo-relative with forward slashes.
- `touch_files` may not point at forbidden prefixes (`tests/acceptance/` by default).
- `dod.test_file` is the BDD runner/test target and must never end in `.feature`.
- `dod.feature_file` is required (v4): it must end in `.feature` and live under an allowed acceptance
  prefix (`tests/acceptance/` by default). `dod.step_definitions` is optional glue code; when present
  it must be non-empty and must not be the `.feature` file.
- Do not leave placeholders (`{{...}}`, `[TBD]`, `TODO`) in 01/02/03.

### BDD enforcement (v4)

Section 4 of a frontmatter contract must contain a fenced `gherkin` block shaped like:

```gherkin
Feature: <feature name>
  Scenario: <scenario title>
    Given <precondition>
    When <action>
    Then <observable outcome>
```

Gate 1 parses the first fenced block, requires one non-empty `Feature:` line and at least two
`Scenario:` blocks, and reports missing `Given`/`When`/`Then` clauses with the inherited
`BDD_MISSING_PRECONDITION` / `BDD_MISSING_ACTION` / `BDD_MISSING_OUTCOME` codes. With the default
config a missing block yields `BDD_GHERKIN_BLOCK_MISSING` and suppresses per-scenario findings;
malformed structure is `BDD_GHERKIN_INVALID`. Set `require_gherkin_block: false` only as a migration
escape hatch: the pre-v4 Markdown-bullet Scenario parser then keeps working.

### Legacy fallback

Contracts without YAML frontmatter use a table fallback for pre-v2 layouts, printing a
`LEGACY_FORMAT` warning (add `--legacy` to force it). BDD block/feature problems
(`MISSING_FEATURE_FILE`, `BDD_FEATURE_FILE_EXTENSION`, `FEATURE_FILE_OUTSIDE_ACCEPTANCE`,
`BDD_GHERKIN_BLOCK_MISSING`, `BDD_GHERKIN_INVALID`, `BDD_STEP_DEFINITIONS_INVALID`) are warnings for
legacy contracts, never hard findings, so historical Markdown-table bundles stay re-lintable.

## Configuration

```json
{
  "max_touch_files": 3,
  "min_diff_lines": 50,
  "max_diff_lines": 250,
  "require_anchor": true,
  "require_adrs": true,
  "min_edge_cases": 2,
  "require_feature_file": true,
  "feature_allowed_prefixes": ["tests/acceptance/"],
  "require_gherkin_block": true
}
```

Every other check in the table above has a same-named default (for example `require_docs`,
`forbidden_touch_prefixes`, `scan_placeholders`, `micro_min_diff_lines`,
`micro_max_touch_files`, `check_topology`, `strict_topology`, `ignore_task_dirs`). The thresholds
are repository conventions, not universal laws; unknown keys produce a warning, while wrongly typed
values exit 2. **Migration from v3**: add `dod.feature_file` and the fenced Gherkin block to every
pending contract, or opt out with `require_feature_file: false` / `require_gherkin_block: false`
while old bundles are migrated.

## JSON output

```json
{
  "gate": "1",
  "passed": true,
  "tasks_scanned": 3,
  "errors": [],
  "warnings": [],
  "coverage": {"spec_anchors": 3, "covered": ["#sec-alpha"], "uncovered": ["#sec-gamma"]}
}
```

`coverage` is present only when `--spec` is passed (it also carries
`contract_anchors_missing_from_spec` and `coverage_ratio`); `--coverage-out` writes it to a file.

Each error object has keys `task`, `code`, `message`, `file`, and `line`. Error codes are stable
English identifiers (e.g. `MISSING_DOC`, `TASK_ID_MISMATCH`, `DAG_CYCLE`, `PLACEHOLDER`,
`TOUCH_FILE_MISSING`, `FORBIDDEN_TOUCH_FILE`, `MISSING_FEATURE_FILE`, `BDD_FEATURE_FILE_EXTENSION`,
`FEATURE_FILE_OUTSIDE_ACCEPTANCE`, `BDD_GHERKIN_BLOCK_MISSING`, `BDD_GHERKIN_INVALID`,
`BDD_STEP_DEFINITIONS_INVALID`, `BDD_MISSING_PRECONDITION`, `BDD_MISSING_ACTION`,
`BDD_MISSING_OUTCOME`, `BDD_INVALID_SCENARIO`, `SPEC_SECTION_UNCOVERED`). Archived proposals produce
`CHANGE_ALREADY_ARCHIVED` instead of an error, and `ignore_task_dirs` (`tasks/archive`) are never
scanned as pending bundles. Full error reference: `references/gate-2-review.md`.

## Gate 2: semantic review (prompt only)

After Gate 1 passes, follow `references/gate-2-review.md` as an independent reviewer. Summarise as
either `Gate 2 Plan Review Passed: 0 omissions, 0 hallucinations`, or a finding list with task
directory, contaminated fields and violated ADR ids. Gate 2 is manual; do not pass unless reviewed.

## Portability, boundaries and non-goals

The script is stdlib-only, resolves relative to its own directory, and never writes files.
- **No code execution**: never runs DoD commands, application code, or test suites.
- **No CI orchestration / AST analysis**: does not build CI pipelines or compute $V(G)$ (owned by `quality-engineering`).
- **No test or verification audit**: does not audit 03 QA evidence. Only the four-document existence
  check and the unresolved-placeholder scan touch `03-qa-verification.md`; complexity, basis-path
  coverage and mutation MSI are audited by Gate 3 (`quality-engineering/verification_linter.py`).
  The linter checks that the BDD artifact and runner target are *declared*; it never executes them.
- **No semantic judgment**: does not judge semantic truthfulness (Gate 2 is prompt review).
- **No RBAC enforcement**: does not replace the git-based RBAC audit.
