# AGENTS.md — Global Rules for the Agent Skills Suite

> **Purpose.** Always-loaded contract for agents developing/validating this skill suite and running
> its per-task pipeline.
>
> **Precedence (highest first).** Host/user instruction and task contract; role rule for permissions;
> this file for conventions; skill docs for procedure. On conflict, stop and escalate.
>
> **Authority.** Prompt rules are advisory; CI gates, branch protection and CODEOWNERS are
> authoritative. Skills are self-contained; this file is never a runtime dependency.
>
> **Safety.** Never commit secrets/PII or run destructive commands without explicit confirmation;
> verify resolved paths before delete/move and never modify outside the declared write scope.

## 1. Repository map

| Path | Purpose |
| :--- | :--- |
| `.agents/skills/` | Canonical skills: `SKILL.md`, `references/`, `assets/` (incl. CI templates), `scripts/` |
| `skills/workflow/` | Installable mirror; byte-identical to `.agents/skills/` |
| `.agents/rules/` | Role permissions and enforcement model |
| `tests/unit/` | Black-box tests for skills, tools, templates and distribution |
| `tools/` | Maintainer helpers (`quickstart.py`, `install_skills.py`) |
| `docs/`, `tasks/` | Guides/strategy; per-task bundles used by the delivery pipeline |

## 2. Work types

### 2.1 Discovery and specification

`idea -> PRD (PM + prd-generator) -> ADRs/tech spec (Architect + spec-generator) -> task bundles (Planner + task-decomposition) -> Gate 1 -> Gate 2 -> Dev <-> QA -> Gate 3 -> converge`

- PM / `prd-generator` writes `.specs/01-prd.md` and `.specs/01-prd/`: stable `REQ-*/CON-*/NFR-*/FORK-*`
  IDs and `#sec-*` anchors, with open questions explicit.
- Architect / `spec-generator` writes `.specs/adr/*.md`, `.specs/02-tech-spec.md` and
  `.specs/02-tech-spec/`: one ADR per fork, `INV-*`/`#sec-*` IDs, no unresolved placeholders.
- Four-perspective review, subagents and chain-of-thought are brainstorming techniques; the
  deliverable is the traceable PRD/spec, not the deliberation itself.
- Handoff is PRD -> spec -> task bundles. `task-decomposition` authors bundles from spec anchors;
  `plan-linter` is the Gate 1 validator, not the author; Gate 2 `review` checks semantic alignment.
- Bounded brownfield changes use `change`: proposal -> one task bundle. They may skip a full PRD but
  must preserve spec anchors and record deviations; `converge` writes confirmed deviations back.

### 2.2 Per-task delivery

`task bundles -> Gate 1 -> Gate 2 -> Dev <-> QA -> Gate 3 -> converge`

- Planner writes `01-contract.md`; Dev writes `02-dev-workspace.md`; QA writes `03-qa-verification.md`;
  `04-process.md` is derived and never hand-edited.
- Do not start Dev without a contract, start QA without `WAITING_FOR_QA`, or merge with a red required
  gate. Completion = `QA_PASSED` + Gate 3 + clean role audit.

### 2.3 Skill-suite development

Changes to skills, rules, templates, tools, manifests, CI or docs follow §4. Use it when improving
the suite rather than delivering one task bundle.

## 3. Roles, gates and single sources of truth

- **Role matrix:** [`enforcement.md#role-matrix`](.agents/rules/enforcement.md#role-matrix) is the
  canonical list of owners, write scopes and read-only areas. Do not duplicate it here; each role
  follows its `.agents/rules/<role>.md`.
- **Gates:** Gate 1 `plan-linter` validates contracts/anchors/DAG; Gate 2 is independent `review`;
  Gate 3 `verification_linter.py` audits V(G)/basis paths/MSI/provenance; mutation runs on trunk via
  `mutation_gate.py`; RBAC uses `rbac_audit.py`. Gate scripts and CI templates live inside the
  `quality-engineering` skill; canonical details:
  [`.agents/skills/quality-engineering/assets/templates/ci/README.md`](.agents/skills/quality-engineering/assets/templates/ci/README.md).
- **Quality bar:** PRD/spec have no unresolved placeholders, stable IDs/anchors and every ADR fork
  resolved or explicitly open before decomposition. Code: `V(G) <= 10` per function (`11-15` waiver,
  `>15` rejected); `Test Cases >= V(G)`; `MSI >= 80%` (`>= 90%` for `risk_level: core`); no critical
  surviving mutant; no fabricated evidence.
- **Evidence and freshness:** current files, commands and tests are the evidence for current
  behavior. Archived notes explain history only and never establish a current gap; read before claiming.
- **Task bundles and Goldilocks:** `01` Planner contract, `02` Dev handoff, `03` QA evidence/verdict,
  `04` derived and tooling-owned; `task_id` in `01` equals the directory name. Default 1–3 touched
  files and 50–250 estimated diff lines; split larger work and merge smaller work.

## 4. Skill change workflow (authoring -> optimization -> tests -> git flow)

This section applies when changing the suite itself (`SKILL.md`, `references/`, assets, scripts,
rules, templates, manifests, CI or docs). It does not replace §2.2. Principles: small, reviewable,
reversible; evidence over claims; one writer per file; no bypassed gates.

1. **Intent and issue (user-triggered, batched).** Do not open an issue or PR for every change or
   conversation turn. Accumulate related fixes and open one issue/PR when the user asks or the work
   is release-worthy; that issue may cover several fixes from the same development effort. Behavior,
   security, gate or CI changes still need a problem statement, acceptance criteria, test plan and
   risk in that issue (or in the PR when the user skips the issue).
2. **Branch and write scope.** Branch from an up-to-date `main` using `feat/<topic>`, `fix/<topic>`,
   `docs/<topic>`, `chore/<topic>` or `security/<topic>`. Keep one coherent workstream per branch;
   related fixes may share it. Never commit directly to `main`. Parallel agents must use disjoint
   write scopes; the Lead integrates and reviews, and two agents must not edit the same file.
3. **Author or optimize.** Edit canonical `.agents/skills/<name>/` and the byte-identical mirror
   `skills/workflow/<name>/`; keep `SKILL.md` under 200 lines, canonical English, self-contained;
   put detail in `references/`/`assets/`; keep templates token-free where Gate 1 scans them. Compose
   with other skills by name, never by copying their scripts or a bare `scripts/...` path. Update
   the role rule, docs, `metadata.version`, `CHANGELOG.md`, `VERSION` and plugin manifests for
   behavior changes; document breaking changes and migration. Never weaken a gate, test or boundary.
4. **Test and evidence before commit.** Run targeted tests, then the full suite:
   `python -m unittest discover -s tests/unit -p "test_*.py"`. Verify dual-tree parity,
   self-containment, line limits, YAML/JSON parse, `git diff --check` and the CI matrix
   (Ubuntu/Windows, Python 3.9/3.12, plugin manifests). For distribution changes run an install smoke
   test; for manifest changes run `claude plugin validate .` when available. CI is authoritative:
   local tests are necessary but not sufficient. Never delete, skip or weaken a test, and never use
   `|| true` / `continue-on-error` to hide a failure.
5. **Commit.** Use conventional commits (`feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`,
   `security(scope): ...`). Keep commits atomic; stage only intended files; never commit secrets,
   credentials, generated caches or unrelated reformatting.
6. **Pull request and review (when triggered).** Push the branch and open a PR against `main` using
   the PR template: `Closes #<issue>`, summary, test evidence, risk/rollback, release/tag plan.
   Required checks must be green; behavior/security/gate/CI changes need an independent reviewer
   (CODEOWNERS/branch protection where configured). Docs-only changes may self-merge when permitted.
7. **Merge, sync and post-merge verification.** Merge only with required checks and review complete;
   do not force-push a reviewed branch; delete the branch and `git switch main && git pull --ff-only`.
   Watch post-merge CI; if `main` is red, fix forward with a new PR or revert with a PR.
8. **Tag and release (SemVer).** Release only from merged `main`. Breaking -> major, feature ->
   minor, fix -> patch; docs/chore only when user-visible or bundled with a release. Update
   `VERSION`, `CHANGELOG.md`, plugin manifests and skill metadata, create an annotated `vX.Y.Z` tag
   (sign it if required), push it, and verify the release workflow, assets, GitHub release and
   install smoke. Never move or delete a published tag; a bad release gets a new patch release.
9. **Definition of done.** Issue/PR linked when one was opened; tests and CI green; independent
   review where required; mirrors byte-identical; docs, version, changelog and manifests agree; PR
   merged; post-merge CI watched; tag/release verified when released; rollback path documented.
10. **Prohibited shortcuts.** Direct commits to `main`; force-pushing shared branches; bypassing
    required checks (`|| true`, `continue-on-error`, `[skip ci]` on required gates); deleting or
    skipping tests; editing only one tree; committing secrets; self-approving behavior/security/gate
    changes; tagging before merge; moving published tags; declaring done without evidence.

Only when the user says "standard open-source workflow", "git flow", "issue/PR", "commit/push/PR/tag"
or equivalent do you open the issue/PR and execute this section without asking again. Otherwise work
and commit locally; never create issues or PRs on your own initiative.

## 5. Commands

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
python -m compileall -q .agents tools
python tools/gen_manifest.py --check      # tracked-file SHA-256 manifest
claude plugin validate .                  # when manifests change; optional if unavailable
python tools/quickstart.py --target .tmp-smoke --dry-run   # distribution smoke
git diff --check
```

## 6. Maintaining this file
- Keep this always-loaded summary at most 155 lines; move detail to the source of truth linked above.
- Do not duplicate role permissions, gate details or pinned versions; changes need a docs PR, the
  workflow guard tests and §4 review. If this conflicts with a role rule, the role rule wins.

## References

- [`enforcement.md`](.agents/rules/enforcement.md) — canonical role matrix and enforcement model.
- [`skills/README.md`](.agents/skills/README.md) — skill index, discovery and per-skill contract.
- [`quality-engineering` CI guide](.agents/skills/quality-engineering/assets/templates/ci/README.md) — bundled gates, stack profiles and four-stage pipeline.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor setup, tests and PR conventions.
- [`docs/README.md`](docs/README.md) — user-facing docs index; `docs/archive/` — historical notes.
- [`docs/skills-guide.zh-CN.md`](docs/skills-guide.zh-CN.md) — usage walkthrough.
