---
name: plan-linter
description: "Run the Gate 1 deterministic static check on task bundles before development starts and follow the Gate 2 review checklist. Use when task contracts exist under tasks/ and you need to verify blast radius, diff budget, declared-file topology, traceability anchors, spec anchor coverage, inherited ADRs, machine-checkable acceptance criteria, and DAG acyclicity. Do not use for code execution, CI pipeline construction, AST/complexity checks, or test audits (owned by quality-engineering)."
license: MIT
compatibility: "Harness-agnostic. Python >= 3.9 optional; without Python follow the manual checklist in references/gate-2-review.md."
metadata:
  version: "3.0.0"
  category: spec-pipeline
---

# Plan Linter (Gate 1 Planning Validator)

This skill has a single, strictly bounded responsibility: **Gate 1 deterministic static validation of planned task contracts and bundles under `tasks/` before development starts**.

- **Gate 1** is a deterministic script in this skill: fast, offline, stdlib only.
- **Gate 2** is a prompt-only semantic review (`review` skill, with `references/gate-2-review.md` as fallback).
- **Non-goals**: plan-linter does NOT execute code, does NOT build or run CI pipelines, does NOT perform AST/code complexity analysis, and does NOT audit tests or the QA complexity/mutation evidence recorded in `03-qa-verification.md` (placeholder scanning and existence checks only). All CI pipelines and verification gates are owned by `quality-engineering`; local testing is owned by `qa`.

## Gate 1: deterministic checks

| Check | Default | Overridable |
| :--- | :--- | :--- |
| 01-contract.md exists and has valid metadata | required | no |
| task_id equals the directory name | required | no |
| task_id is unique across bundles | required | no |
| touch_files count | 1..3 | max_touch_files |
| estimated_lines | 50..250 | min_diff_lines, max_diff_lines |
| origin_spec_anchor matches #sec-[a-z0-9-]+ | required | require_anchor |
| adherence_adrs lists at least one ADR | required | require_adrs |
| dod.type_check, dod.lint, dod.test_file | required | no |
| dod.edge_cases count | at least 2 | min_edge_cases |
| 02-dev-workspace.md, 03-qa-verification.md, 04-process.md exist | required | require_docs |
| forbidden touch prefixes | tests/acceptance/ | forbidden_touch_prefixes |
| unresolved placeholders in 01/02/03 | blocked | scan_placeholders |
| 03-qa-verification.md content-level QA evidence | not audited (Gate 3) | no |
| reverse topology: modify paths exist, create paths do not | warning | check_topology, strict_topology, --repo-root |
| size_class micro: change_id present, 1 touch file, smaller budget | required when micro | micro_min_diff_lines, micro_max_touch_files |
| change_id has an open proposal under the change directory | required when --changes-dir is given | --changes-dir |
| spec anchor coverage matrix (uncovered sections) | report; error with --require-full-coverage | --spec, --coverage-out |
| contract anchors absent from the spec | warning; error with --strict-anchor | --spec |
| dependency graph | acyclic, no missing tasks | no |

Everything is checked; the order in the output is stable.

## Quick start

```bash
# Standard report or machine-readable JSON
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --json

# Custom configuration or legacy format
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --config plan-linter.json
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --legacy

# Gate 2 heuristics and blocking CI mode
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes --json
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --spec .specs/02-tech-spec.md --strict-topology --strict-anchor --require-full-coverage
```

The script is optional. If Python is unavailable, use `references/gate-2-review.md` as a
manual checklist and review the same fields by hand.

**Gate 2 is the separate `review` skill.** After Gate 1 exits 0, use the `review` skill
(plan-review mode) when it is installed for the independent semantic audit. This skill
keeps `references/gate-2-review.md` as a self-contained fallback when the review
skill is not installed; it never replaces Gate 1.

## Exit codes

| Code | Meaning |
| :--- | :--- |
| 0 | Gate 1 passed for every task bundle |
| 1 | Violations found (or a contract frontmatter cannot be parsed) |
| 2 | Usage or configuration error |
| 3 | Unexpected internal error |

## Contract format

The YAML frontmatter of 01-contract.md is authoritative. The human tables below
it are optional readability aids.

```yaml
---
task_id: task-001-auth
title: "User authentication"
module: auth
dependencies: [task-000-bootstrap]
estimated_lines: 120
touch_files:
  - action: create
    path: src/auth/service.py
  - action: modify
    path: src/auth/routes.py
origin_spec_anchor: "#sec-auth"
adherence_adrs: [ADR-001]
dod:
  type_check: "npm run type-check"
  lint: "npm run lint"
  test_file: "tests/acceptance/test_auth.ts"
  edge_cases:
    - "empty credentials return 400"
    - "expired token returns 401"
---
```

Rules:
- `task_id` must equal the task directory name; paths are repo-relative with forward slashes.
- `touch_files` may not point at forbidden prefixes (`tests/acceptance/` by default).
- Do not leave placeholders (`{{...}}`, `[TBD]`, `TODO`) in 01/02/03.

### Legacy fallback

Contracts without YAML frontmatter use a table fallback for pre-v2 layouts,
printing a `LEGACY_FORMAT` warning. Add `--legacy` to force the fallback.

## Configuration

```json
{
  "max_touch_files": 3,
  "min_diff_lines": 50,
  "max_diff_lines": 250,
  "require_anchor": true,
  "require_adrs": true,
  "min_edge_cases": 2,
  "require_docs": ["02-dev-workspace.md", "03-qa-verification.md", "04-process.md"],
  "forbidden_touch_prefixes": ["tests/acceptance/"],
  "scan_placeholders": true,
  "micro_min_diff_lines": 10,
  "micro_max_touch_files": 1,
  "check_topology": true,
  "strict_topology": false,
  "ignore_task_dirs": ["archive"]
}
```

The thresholds are repository conventions, not universal laws. Override them
per project; unknown keys produce a warning, while wrongly typed values exit 2.

## JSON output

```json
{
  "gate": "1",
  "passed": true,
  "tasks_scanned": 3,
  "errors": [],
  "warnings": [],
  "coverage": {
    "spec": ".specs/02-tech-spec.md",
    "spec_anchors": 3,
    "covered": ["#sec-alpha", "#sec-beta"],
    "uncovered": ["#sec-gamma"],
    "contract_anchors_missing_from_spec": [],
    "coverage_ratio": 0.6667
  }
}
```

`coverage` is present only when `--spec` is passed; `--coverage-out` writes it to a file.

Each error object has keys `task`, `code`, `message`, `file`, and `line`. Error codes
are stable English identifiers (e.g. `MISSING_DOC`, `TASK_ID_MISMATCH`, `DAG_CYCLE`,
`PLACEHOLDER`, `TOUCH_FILE_MISSING`, `FORBIDDEN_TOUCH_FILE`, `BDD_MISSING_PRECONDITION`,
`BDD_MISSING_ACTION`, `BDD_MISSING_OUTCOME`, `BDD_INVALID_SCENARIO`, `SPEC_SECTION_UNCOVERED`). Archived proposals
produce `CHANGE_ALREADY_ARCHIVED` instead of an error, and `ignore_task_dirs`
(`tasks/archive`) are never scanned as pending bundles. Full error reference: `references/gate-2-review.md`.

## Gate 2: semantic review (prompt only)

After Gate 1 passes, follow `references/gate-2-review.md` as an independent reviewer. Summarise as either:
- `Gate 2 Plan Review Passed: 0 omissions, 0 hallucinations`; or
- Finding list: task directory, contaminated fields, and violated ADR ids.

Gate 2 is manual: a script cannot judge semantic truthfulness. Do not pass unless reviewed.

## Portability, boundaries and non-goals
 
The script is stdlib-only, resolves relative to its own directory, and never writes files.
 
Strict boundaries and non-goals:
- **No code execution**: never runs DoD commands, application code, or test suites.
- **No CI orchestration**: does not build, manage, or run CI pipelines (owned by `quality-engineering`).
- **No AST or complexity analysis**: does not compute cyclomatic complexity $V(G)$ (owned by `quality-engineering`).
- **No test or verification audit**: does not audit 03 QA evidence. Only the
  four-document existence check and the unresolved-placeholder scan touch
  `03-qa-verification.md`; complexity, basis-path coverage and mutation MSI are
  audited by Gate 3 (`quality-engineering/verification_linter.py`).
- **No semantic judgment**: does not judge semantic truthfulness (Gate 2 is prompt review).
- **No RBAC enforcement**: does not replace the git-based RBAC audit.
