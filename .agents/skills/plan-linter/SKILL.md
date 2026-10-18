---
name: plan-linter
description: "Run the Gate 1 deterministic static check on task bundles and follow the Gate 2 review checklist before development starts. Use when task contracts exist under tasks/ and you need to verify blast radius, diff budget (standard and micro), declared-file topology, traceability anchors, the spec anchor coverage matrix, inherited ADRs, machine-checkable acceptance criteria, required documents, change proposals and dependency acyclicity. Do not use when the spec or task decomposition is still being written, or when you only need to review a single source change."
license: MIT
compatibility: "Harness-agnostic. Python >= 3.9 optional; without Python follow the manual checklist in references/gate-2-review.md."
metadata:
  version: "3.0.0"
  category: spec-pipeline
---

# Plan Linter

Two gates run before implementation:

- **Gate 1** is a deterministic script in this skill: fast, offline, stdlib only.
- **Gate 2** is a prompt-only semantic review. It is not automated. The script
  never claims to perform it.

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
| reverse topology: modify paths exist, create paths do not | warning | check_topology, strict_topology, --repo-root |
| size_class micro: change_id present, 1 touch file, smaller budget | required when micro | micro_min_diff_lines, micro_max_touch_files |
| change_id has an open proposal under the change directory | required when --changes-dir is given | --changes-dir |
| spec anchor coverage matrix (uncovered sections) | report; error with --require-full-coverage | --spec, --coverage-out |
| contract anchors absent from the spec | warning; error with --strict-anchor | --spec |
| dependency graph | acyclic, no missing tasks | no |

Everything is checked; the order in the output is stable.

## Quick start

```bash
# human-readable report, default tasks directory
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks

# machine-readable result for CI or another agent
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --json

# custom thresholds and extra forbidden prefixes
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --config plan-linter.json

# legacy contracts only
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --legacy

# skip the placeholder scan (rare; document why)
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --no-placeholder-scan

# Gate 2 heuristics: coverage matrix, real-file topology, brownfield proposals
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes \
  --coverage-out artifacts/coverage.json --json

# make the heuristics blocking in CI
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --spec .specs/02-tech-spec.md --strict-topology --strict-anchor --require-full-coverage
```

The script is optional. If Python is unavailable, use
references/gate-2-review.md as a manual checklist and review the same fields by
hand.

**Gate 2 is the separate `review` skill.** After Gate 1 exits 0, use
`review/SKILL.md` (plan-review mode) for the independent semantic audit. This skill
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

- task_id must equal the task directory name.
- Paths are repository-relative and use forward slashes.
- touch_files may not point at a forbidden prefix (tests/acceptance/ by default).
- Do not leave placeholders such as mustache variables, [TBD] or TODO in 01/02/03.

### Legacy fallback

Contracts without YAML frontmatter are parsed with a table fallback that
understands the pre-v2 Chinese and English layouts. A successful legacy run
prints a LEGACY_FORMAT warning so the migration debt stays visible. Both
formats are validated by the same checks. Add --legacy to force the fallback.

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

`coverage` is present only when `--spec` is passed. `--coverage-out` writes the same
object as a standalone file so a reviewer or CI job can diff it between runs.

Each error object has the keys task, code, message, file and line. Error codes
are stable English identifiers such as MISSING_LINT, MISSING_ADRS,
INVALID_ANCHOR, MISSING_DOC, TASK_ID_MISMATCH, DUPLICATE_TASK_ID,
DEPENDENCY_NOT_FOUND, DAG_CYCLE, FORBIDDEN_TOUCH_FILE, PLACEHOLDER,
TOUCH_FILE_MISSING, TOUCH_FILE_EXISTS, TOUCH_PATH_OUTSIDE_ROOT,
SPEC_SECTION_UNCOVERED, ANCHOR_NOT_IN_SPEC, CHANGE_PROPOSAL_MISSING,
CHANGE_NOT_OPEN, INVALID_SIZE_CLASS, INVALID_CHANGE_ID, MICRO_REQUIRES_CHANGE_ID,
MICRO_TOO_MANY_TOUCH_FILES, MICRO_DIFF_TOO_SMALL and MICRO_DIFF_TOO_LARGE.
Archived proposals produce the warning CHANGE_ALREADY_ARCHIVED instead of an error, and
the directories listed in ignore_task_dirs (default tasks/archive) are never scanned as
pending bundles.

## Gate 2: semantic review (prompt only)

After Gate 1 passes, read references/gate-2-review.md and perform the review as
an independent reviewer. Summarise the result as either:

- Gate 2 Plan Review Passed: 0 omissions, 0 hallucinations; or
- a list of task directories, contaminated fields and violated ADR ids.

Gate 2 is deliberately manual: a static script cannot judge whether a business
entity is invented. Do not report a Gate 2 pass unless the review actually ran.

## Portability and limits

The script uses only the Python standard library and resolves nothing outside
its own directory, so the skill directory can be copied elsewhere and still run
(for example, copy it to a temporary directory and run --help or --tasks-dir).
It never writes files.

It does not:

- execute the DoD commands (no type-check or test execution);
- judge whether a spec section is *semantically* covered: the coverage matrix is
  anchor-level bookkeeping, and a task can reference an anchor without implementing it;
- check the prose quality of a contract;
- replace the git-based RBAC audit in tools/rbac_audit.py.
