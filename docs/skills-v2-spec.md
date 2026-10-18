# Skills v2 — Universalization Design Contract

Status: implementation contract for branch `skills-universal-v2`.
Owner: Lead. Reviewers: script-forensics, content-consistency, generality-review.

## 1. Decisions (approved by the user: "execute these")

1. **Prompts travel, gates stay home.** Skills carry judgment + assets + small stdlib helpers. Deterministic enforcement lives in repo CI, not in a host-specific promise.
2. **Engines are optional.** `prd_generator/` and `spec_generator/` stay in the repo but skills never import them via `sys.path`. Bundled `engine.py` proxies exit 2 with install guidance.
3. **RBAC is layered.** L0 prompt rules (universal), L1 optional Antigravity hooks (best effort), L2 `tools/rbac_audit.py` git audit in CI (authoritative), L3 git protection (repo setting). Docs must say exactly this.
4. **English canonical.** SKILL.md, references, scripts and messages are English. Chinese stays as optional translations (`references/zh-CN.md`), never required at runtime. Generated product documents use the user's language.
5. **Templates are neutral.** Infrastructure/domain values are placeholders with `{{...}}`; any example value must be explicitly labelled illustrative. No embedded state markers, fake timestamps or domain entities.
6. **4-document + Goldilocks are repo conventions.** Skills support them by default; thresholds are configurable.
7. **Single source of truth.** Each file has exactly one canonical location under `.agents/skills/<name>/`. Root `spec-templates/`, `task-templates/` and duplicate scripts are removed.
8. **discovery paths.** `.agents/skills` is native for Codex, Antigravity and DSH; `tools/install_skills.py` adds `~/.agents/skills` / `.claude/skills` installs.

## 2. Canonical layout

```text
.agents/skills/<skill>/
  SKILL.md                   # <200 lines, English, frontmatter per agentskills.io
  references/                # optional deep docs, zh-CN translations, prompts
  assets/templates/          # optional, canonical templates (`assets`, not `resources`)
  scripts/                   # optional stdlib helpers
```

Pipeline skills: `prd-generator`, `spec-generator`, `task-decomposition` (planning),
`plan-linter` (Gate 1; all `category: spec-pipeline`), `review` (Gate 2 plan review plus change
review; `category: review`), and `dev`, `qa` (execution; `category: execution`).
`review`, `dev` and `qa` are prompt-only workflow skills: they consume plans/task bundles/diffs
and do not ship templates or scripts.

Frontmatter (all skills):

```yaml
---
name: <directory name>
description: "<what it does>. Use when <triggers>. Do not use when <non-triggers>."
license: MIT
compatibility: "Harness-agnostic. Python >=3.9 optional for scaffolding and linting; a manual fallback exists."
metadata:
  version: "2.0.0"
  category: spec-pipeline
---
```

## 3. Task contract (01-contract.md) — frontmatter first

The machine-readable block is authoritative; the human tables below it stay for readability.
`task_id` MUST equal the directory name. Paths are repo-relative with forward slashes.

```yaml
---
task_id: task-001-auth
title: "User authentication"
module: auth
dependencies: [task-000-bootstrap]     # [] when none
estimated_lines: 120
touch_files:
  - action: create                     # create | modify
    path: src/auth/service.py
  - action: modify
    path: src/auth/routes.py
origin_spec_anchor: "#sec-auth"        # required, #sec-[a-z0-9-]+
adherence_adrs: [ADR-001]              # required, at least one
dod:
  type_check: "npm run type-check"
  lint: "npm run lint"
  test_file: "tests/acceptance/test_auth.ts"
  edge_cases:
    - "empty credentials return 400"
    - "expired token returns 401"
---
```

Rules: touch_files 1..3; estimated_lines 50..250; no unresolved placeholders in 01/02/03 (02/03 ship as token-free blank forms, so a planned bundle passes Gate 1); 04 is intentionally not scanned; forbidden touch prefixes (default `tests/acceptance/`); dependency graph must be a DAG; duplicate task_id forbidden; 02/03/04 must exist.

## 4. plan-linter v2 CLI

```text
python .agents/skills/plan-linter/scripts/plan_linter.py \
  [--tasks-dir ./tasks] [--config ./plan-linter.json] [--json] [--legacy] [--no-placeholder-scan]
```

- Exit codes: 0 pass; 1 violations; 2 usage/config error.
- Placeholder scope: Gate 1 scans 01/02/03; 04 is never scanned. 02/03 are token-free blank forms at plan time, so a planned bundle passes after the Planner fills 01.
- `--json` prints one object: `{"gate":"1","passed":bool,"tasks_scanned":n,"errors":[{task,code,message,file,line}],"warnings":[...]}`.
- Config keys (defaults): `max_touch_files=3`, `min_diff_lines=50`, `max_diff_lines=250`, `require_anchor=true`, `require_adrs=true`, `min_edge_cases=2`, `require_docs=["02-dev-workspace.md","03-qa-verification.md","04-process.md"]`, `forbidden_touch_prefixes=["tests/acceptance/"]`, `scan_placeholders=true`.
- Parsing: YAML frontmatter first (small stdlib parser); if absent, legacy Chinese table parsing + `LEGACY_FORMAT` warning. English and Chinese contracts must both pass.
- Gate 2 (semantic anti-hallucination) is a prompt-only reference at `references/gate-2-review.md`; never claim it is automated.

## 5. Hook / audit scripts

### 5.1 `.agents/hooks.json` (Antigravity adapter only)
- Commands use `.agents/scripts/rbac_guard.py` / `event_bus_logger.py` (relative to workspace root, as Antigravity runs them).
- Matcher: `write_to_file|replace_file_content|multi_replace_file_content`.
- The file must be documented as optional; removing it must not break any skill or workflow.

### 5.2 `rbac_guard.py` (PreToolUse)
- Reads path from Antigravity (`toolCall.args.TargetFile|target_file`), Claude/DSH (`tool_input.file_path`), or `args.path`.
- Resolves relative paths against the workspace root; path matching is by path segments (`tests`,`acceptance`), never leading-slash substring.
- Role from `AGENT_ROLE` or `AGY_AGENT_ROLE` (lowercase; aliases dev/devagent, qa/qaagent, planner).
- Denies: any role writing `tasks/*/04-process.md`; dev writing `01-contract.md`, `03-qa-verification.md`, or `tests/acceptance/**`; qa writing `01-contract.md`, `02-dev-workspace.md`, or `src/**`; planner writing `04-process.md` only.
- Unknown role: deny only `04-process.md`; document that CI audit is the authoritative layer.
- Output Antigravity decision JSON; exit 0; parse failure → allow + stderr warning.

### 5.3 `event_bus_logger.py` (PostToolUse / optional manual)
- Tasks dir from `--tasks-dir`, else changed-file task dir, else `./tasks`.
- Trigger detection: an actually checked box line `^\s*-\s*\[x\]\s*(.*?)(WAITING_FOR_QA|QA_PASSED|REWORK_REQUIRED)\b` — never a bare substring.
- Event codes: `HANDOFF_QA_REQUESTED` (status VERIFYING / holder QAAgent), `TASK_TERMINATED_DONE` (DONE / None), `REWORK_TRIGGERED` (REWORKING / DevAgent, retry_count +1 capped at 3).
- Idempotent per (task, event code) by scanning existing event rows. Insert into section 2's table; atomic write; never mutate status if the section/table is absent. Print `{}` on success.
- Do not claim SHA-256; the audit chain is git + `tools/rbac_audit.py`.

### 5.4 `tools/rbac_audit.py` (CI, harness-neutral)
```text
python tools/rbac_audit.py --base <git-ref> [--head HEAD] [--role dev|qa|planner] [--tasks-dir tasks] [--json]
```
- Role from `--role` or commit trailer `Agent-Role: <role>`; missing role → usage error 2.
- dev touching `tests/acceptance/**` fails; qa touching `src/**` fails; non-planner touching `tasks/*/01-contract.md` fails; any role hand-editing `04-process.md` in a way that deletes event rows fails (warn otherwise).
- Exit 0/1/2; `--json` output.

## 6. Bundled script contract

- Paths resolved from `Path(__file__).resolve().parent`; never the repository root; never `sys.path.insert` of a repo root.
- Python >=3.9 syntax, standard library only, no network, no writes outside `--out`.
- `--help`, `--version`; `--json` where a machine-readable result exists.
- Exit codes: 0 success, 1 content/gate failure, 2 optional dependency or usage unavailable, 3 unexpected internal error.
- Scaffolders: idempotent; refuse to overwrite without `--force`; `--dry-run` lists actions; print created/skipped files.

## 7. Templates

- `assets/templates/` under the owning skill only. No root duplicates.
- Task templates: frontmatter contract; no literal `[x]` tokens in unchecked checkboxes; 04-process starts with initialized status values (`TODO` / `UNASSIGNED` / `None` / retry `0`) and an empty event table (header only); no fake timestamps or sample lifecycle rows; Dev/QA workflow and event/status mapping are defined in `references/role-lifecycle.md`; neutral wording, no domain examples.
- PRD/spec templates: illustrative values marked as such; no fixed infra stack (Postgres/Redis/Kafka/Envoy) as the default answer; no multi-tenant/TS-only assumptions presented as universal; placeholders use `{{UPPER_SNAKE}}`.
- Each template set has a `README.md` listing placeholders/variables and ownership.

## 8. Dedupe / deletion list

- Delete: `.agents/scripts/plan_linter.py`, `.agents/scripts/prd_generator.py`, `.agents/scripts/spec_generator.py`, root `scripts/`, root `spec-templates/`, root `task-templates/`, all `scripts/run.py` in skills, `.agents/skills/spec-generator/resources/templates/01-prd.template.md`, `.agents/rules/README.md` (move to `docs/agent-rules.md`).
- Move: `resources/templates` → `assets/templates` in prd/spec/task skills.
- Canonical entrypoints: skill scripts only; optional console scripts stay in `pyproject.toml`.

## 9. Docs / badge

- Rewrite `.agents/skills/README.md`: English index, discovery matrix, per-skill table, degradation, honest RBAC wording, badge at end.
- New `docs/skills-compatibility.md`: harness × discovery × rules × enforcement.
- Update root `README.md` sections that describe `.agents` (no false "self-contained"/"physical hook" claims); badge at end.
- Badge (exact): `[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)`.
- `.agents/rules/*.md` get `trigger: model_decision` + English descriptions (Antigravity requirement), concise English body.

## 10. Acceptance tests (must pass before commit)

1. Relocation: each skill copied outside the repo runs its documented `--help`/scaffold/lint or exits 2 with guidance; no `ModuleNotFoundError`.
2. English contract passes; Chinese legacy contract passes with warning; six invalid cases fail (no lint cmd, no ADR, placeholder anchor, missing 02/03/04, duplicate ID, ID/dir mismatch); a fresh scaffold with a filled 01 and blank 02/03 passes Gate 1.
3. Fresh task scaffold produces no false events; real checked handoff produces exactly one; rerun idempotent; QA pass and REWORK produce one event each.
4. RBAC: dev relative+absolute `tests/acceptance` denied; qa `src` denied; `04-process` denied; unknown role documented behavior.
5. `tools/rbac_audit.py` fails a simulated dev-edits-tests commit.
6. Duplicate scan clean (no root template copies, no duplicate linter); all internal links resolve.
7. Remove `prd-generator`/engine: prompt workflow still complete; scaffold/lint work with stdlib.
8. `dev`/`qa` skills validate: frontmatter/name match, <200 lines, relative links resolve, and each
   skill documents its owned artifacts, handoff markers and `04` update rules without granting access.
9. `review` skill validates: read-only scope, plan-review (Gate 2) and code-review modes, severity
   and verdict output, no edits, and no claim that semantic review is automated.
---

## 11. v3 addendum (2026-10-18)

v2 remains the baseline contract. v3 is additive: nothing in v2 is removed, and every v2 command
keeps its exit codes. The additions close the two gaps named in the benchmark: brownfield change
and spec convergence, plus machine-assisted Gate 2 heuristics and distribution.

### 11.1 New skills and layout

- `change` (planning, 3.0.0): proposal -> one task bundle -> archive. Ships `scripts/scaffold_change.py`,
  `scripts/standards_extract.py`, `scripts/lint_change.py`, `assets/templates/proposal.template.md`,
  `references/brownfield-protocol.md`.
- `converge` (execution, 1.0.0): after `QA_PASSED`, append confirmed deviations to
  `.specs/02-tech-spec.md`, set `04` to `CONVERGED`, archive the bundle and the proposal. Ships
  `scripts/converge.py` and `references/convergence-protocol.md`.
- New layout entries: `.specs/changes/<change-id>/{proposal.md,convergence.md}`,
  `.specs/change-context/standards.md` (generated), `tasks/archive/<task-id>/` (moved, never deleted).
- `task-decomposition/scripts/scaffold_task.py` gains optional `--change-id` and `--size-class`; the
  default output is byte-identical to v2.

### 11.2 Contract additions (01-contract.md)

- Optional `change_id` (string, same id as the proposal and of `tasks/<id>/`).
- Optional `size_class: standard|micro` (default `standard`). `micro` requires a `change_id`, at most
  one touch file, and the `micro_min_diff_lines..min_diff_lines-1` budget (default 10-49).
- Everything else is unchanged: `touch_files` 1..3, `estimated_lines` 50..250 for standard, one or
  more ADRs, `#sec-*` anchor, `dod` commands and >=2 edge cases, four documents present.

### 11.3 plan-linter 3.0

```text
python .agents/skills/plan-linter/scripts/plan_linter.py \
  [--tasks-dir ./tasks] [--config ./plan-linter.json] [--json] [--legacy] [--no-placeholder-scan] \
  [--repo-root .] [--no-topology] [--strict-topology] \
  [--spec .specs/02-tech-spec.md] [--require-full-coverage] [--strict-anchor] \
  [--changes-dir .specs/changes] [--coverage-out artifacts/coverage.json]
```

- Reverse topology: `modify` paths must exist and `create` paths must not, resolved under
  `--repo-root` (default cwd). Warning by default; error with `--strict-topology`.
- Coverage matrix: with `--spec`, JSON gains `coverage` with `spec_anchors`, `covered`,
  `uncovered`, `contract_anchors_missing_from_spec` and `coverage_ratio`. Uncovered anchors are
  reported only; `--require-full-coverage` turns them into errors. `--coverage-out` writes the object.
- Change proposals: with `--changes-dir`, a `change_id` must have an open proposal; a missing
  proposal is `CHANGE_PROPOSAL_MISSING` (error), an archived one is `CHANGE_ALREADY_ARCHIVED`
  (warning), any other status is `CHANGE_NOT_OPEN` (error).
- New config keys: `micro_min_diff_lines=10`, `micro_max_touch_files=1`, `check_topology=true`,
  `strict_topology=false`, `ignore_task_dirs=["archive"]`. Defaults keep v2 pass/fail semantics;
  topology findings are warnings, not failures.
- New error codes: `MICRO_DIFF_TOO_SMALL`, `MICRO_DIFF_TOO_LARGE`, `MICRO_REQUIRES_CHANGE_ID`,
  `MICRO_TOO_MANY_TOUCH_FILES`, `INVALID_SIZE_CLASS`, `INVALID_CHANGE_ID`,
  `CHANGE_PROPOSAL_MISSING`, `CHANGE_NOT_OPEN`, `SPEC_SECTION_UNCOVERED`, `ANCHOR_NOT_IN_SPEC`.
- Archived bundles under `tasks/archive/` are never scanned as pending plans.

### 11.4 02-dev-workspace.md deviation log (frozen)

Dev appends an `Implementation deviations` section: one row per deviation, columns
`Deviation ID | Spec anchor | Operation | Confirmed behavior`, ids `DEV-001`, operation
`add|modify|remove`. No deviation means one `None` row. This table is the only input `converge`
reads; Dev never edits the spec. The section is token-free so a planned bundle still passes Gate 1.

### 11.5 converge

```text
python .agents/skills/converge/scripts/converge.py check --tasks-dir tasks [--json] [--fail-on-pending] [--strict]
python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id> [--dry-run] [--json] [--force] [--strict]
python .agents/skills/converge/scripts/converge.py --spec .specs/02-tech-spec.md --spec-sha256
```

- `check` classifies converged / pending / blocked with reasons; exit 0 unless `--fail-on-pending`.
- `apply` appends a `## Converged changes` entry (append-only; existing prose untouched) with a marker
  `<!-- converged: <task-id> sha256:<hex> -->`, sets `04-process.md` to `CONVERGED` plus a
  `TASK_CONVERGED` / `ConvergeTool` event, moves the bundle to `tasks/archive/<task-id>/`, and for a
  change bundle writes `.specs/changes/<id>/convergence.md` and sets `status: archived`. Second run is
  idempotent (exit 0, no writes).
- Refusals (exit 1): QA not passed or rework active, blank/missing deviation table, spec drift under
  `--strict`, archive destination exists without `--force`, missing `04-process.md`.
- Structural deviations (new module, new boundary, ADR-level decision) escalate to `spec-generator`; they
  are never converged silently.

### 11.6 change

- `scaffold_change.py` requires `--change-id --title --anchor`; refuses a base spec that does not exist,
  a malformed or unknown anchor, path escape, and an existing change dir without `--force`; writes
  `base_spec_sha256`; delegates the bundle to `scaffold_task.py --change-id --size-class` (inline
  fallback with a warning when the sibling skill is absent).
- `standards_extract.py` writes a deterministic, timestamp-free report (config files, test layout,
  top-level source dirs, declared runtime versions, existing anchors, evidenced commands); `--check`
  exits 1 when the report is stale. Only evidenced commands may appear in a contract DoD.
- `lint_change.py` validates proposal frontmatter/status, anchor existence, `base_spec_sha256` drift
  (open proposals only; archived proposals are exempt), `[CHG-n]` block shape and the matching bundle.

### 11.7 Distribution and CI

- `tools/quickstart.py` (PEP 723, stdlib): `--target --dest --skills --copy --force --dry-run --json
  --with-ci --with-rules --with-audit --print-oneliner`. Installs skills, rules, scripts, hooks and
  `tools/rbac_audit.py`; `--with-ci` copies `templates/ci/*.yml` into `<target>/.github/workflows/`.
  Every destination is containment-checked; no overwrite without `--force`; exit 0/1/2/3.
- `templates/ci/rbac-gate.yml` runs the L2 audit on `pull_request` with event base/head SHAs and
  `fetch-depth: 0`; `templates/ci/plan-gate.yml` runs Gate 1 (with `--spec`) on `tasks/**` and
  `.specs/**` changes. Both use `permissions: contents: read` and write nothing but the step summary.

### 11.8 Compatibility rules

- v2 repositories need no migration: new frontmatter fields are optional, new CLI flags default to off,
  and `--json` consumers only gain keys (`coverage`) plus warnings.
- v2-era completed bundles have no deviation table. Either have Dev add an explicit `None` row before
  convergence, or perform the manual append described in the `converge` skill. Do not fabricate rows.
- Roles do not change: Planner plans, Dev implements, QA verifies, Reviewer reviews read-only, Orchestrator
  routes. `change` uses the Planner identity; `converge` is tooling plus the Planner/Lead who runs it.

### 11.9 Additional acceptance tests

10. `change` scaffolder: happy path (proposal + one bundle, `change_id`/`size_class` in the contract,
    token-free 02/03/04), missing spec exit 2, unknown anchor refused, `--dry-run` writes nothing,
    containment refused, `lint_change` detects `base_spec_sha256` drift.
11. `converge`: check classification, apply happy path (spec entry + marker + `CONVERGED` + archived
    bundle + archived proposal), refusals (QA not passed, blank table), idempotent second apply,
    `--dry-run` writes nothing, `--strict` drift refusal.
12. plan-linter v3: micro budget accepted/rejected, topology warning vs `--strict-topology` error,
    coverage JSON and `--require-full-coverage`, archived proposals warn, archive dirs ignored.
13. distribution: quickstart install/`--with-ci`/`--force`/`--dry-run`/containment/`--json`/
    `--print-oneliner`; both workflows structurally valid without PyYAML.
14. Every new skill: frontmatter `name` equals its directory, relative links resolve, `--help` exits 0,
    and the skill works when copied outside the repository.
