# AGENTS.md — Global Rules for the Agent Skills Suite

> **Purpose.** Always-loaded contract for agents developing/validating this skill suite and running
> its per-task pipeline.
>
> **Precedence (highest first).** Host/user instruction and task contract; role rule for permissions;
> this file for conventions; skill docs for procedure. On conflict, stop and escalate.
>
> **Authority.** Prompt rules are advisory; CI gates, branch protection and CODEOWNERS are
> authoritative. Skills are self-contained; this file is never a runtime dependency.

## 1. Repository map

| Path | Purpose |
| :--- | :--- |
| `.agents/skills/` | Canonical skill sources: `SKILL.md`, `references/`, `assets/`, `scripts/` |
| `skills/workflow/` | Installable mirror; byte-identical to `.agents/skills/` |
| `.agents/rules/` | Role permissions and enforcement model |
| `tests/unit/` | Black-box tests for skills, tools, templates and distribution |
| `templates/ci/` | Copy-paste CI gates and stack profiles |
| `tools/` | Maintainer helpers (`quickstart.py`, audit tools) |
| `docs/`, `tasks/` | Guides/strategy; per-task bundles used by the delivery pipeline |

## 2. How to work
### 2.1 Discovery and specification
`idea/change -> PRD (PM + prd-generator) -> ADRs/tech spec (Architect + spec-generator) -> task bundles (Planner + task-decomposition) -> Gate 1 -> Gate 2 -> Dev <-> QA -> Gate 3 -> converge`

- PM / `prd-generator` writes `.specs/01-prd.md` and `.specs/01-prd/`: stable `REQ-*/CON-*/NFR-*/FORK-*`
  IDs and `#sec-*` anchors, with open questions explicit.
- Architect / `spec-generator` writes `.specs/adr/*.md`, `.specs/02-tech-spec.md` and
  `.specs/02-tech-spec/`: one ADR per fork, `INV-*`/`#sec-*` IDs, no unresolved placeholders.
- Four-perspective review, subagents and chain-of-thought are brainstorming techniques; the
  deliverable is the traceable PRD/spec, not the deliberation itself.
- Handoff is PRD -> spec -> task bundles. `task-decomposition` authors bundles from spec anchors;
  `plan-linter` is the Gate 1 validator, not the author; Gate 2 `review` checks semantic alignment;
  `change` handles bounded brownfield deviations and `converge` writes confirmed deviations back.

### 2.2 Per-task delivery
`task bundles -> Gate 1 -> Gate 2 -> Dev <-> QA -> Gate 3 -> converge`

- Planner writes `01-contract.md`; Dev writes `02-dev-workspace.md`; QA writes `03-qa-verification.md`;
  `04-process.md` is derived and never hand-edited.
- Do not start Dev without a contract, start QA without `WAITING_FOR_QA`, or merge with a red required
  gate. Completion = `QA_PASSED` + Gate 3 + clean role audit.

### 2.3 Skill-suite development

Changes to skills, rules, templates, tools, manifests, CI or docs follow §6. Use it when improving
the suite rather than delivering one task bundle.
## 3. Task bundles and sizing

- `01` Planner-owned contract; `02` Dev handoff; `03` QA evidence/verdict; `04` derived and
  tooling-owned; `task_id` in `01` equals the directory name.
- Goldilocks default: 1–3 touched files and 50–250 estimated diff lines. Split larger work; merge
  smaller work. Limits are configurable.

## 4. Roles and write scopes

| Role | Rule | Owns | Never |
| :--- | :--- | :--- | :--- |
| PM | `.agents/rules/pm.md` | `.specs/01-prd.md`, `.specs/01-prd/` | Spec/ADRs, tasks, source, tests |
| Architect | `.agents/rules/architect.md` | `.specs/adr/*.md`, `.specs/02-tech-spec.md`, `.specs/02-tech-spec/` | PRD content, tasks, source, tests |
| Planner | `.agents/rules/planner.md` | Task bundles, contracts, DAG | Source, tests, `04` |
| Dev | `.agents/rules/dev.md` | `src/**`, `02-dev-workspace.md` | Tests, contracts, other roles' docs |
| QA | `.agents/rules/qa.md` | `tests/acceptance/**`, `tests/integration/**`, `03` | Source, `01`, `02`, `04`; uses bundled Gate 3 pre-check |
| Quality Engineering | `.agents/skills/quality-engineering/` | CI workflows, environment, gate scripts | Local task implementation, black-box test authoring |
| Test Engineering | `.agents/rules/test-engineering.md` | Agreed test strategy, design-review notes | Task acceptance, tests, `03`, running CI gates |
| Reviewer | `.agents/rules/reviewer.md` | Read-only semantic Gate 2 review | Editing artifacts or weakening gates |
| Orchestrator/Lead | `.agents/rules/orchestrator.md` | Routing, gate order, integration | Authoring role artifacts or bypassing gates |

## 5. Gates and quality bar

| Gate | Owner | Checks | Evidence |
| :--- | :--- | :--- | :--- |
| Gate 1 | `plan-linter` | Contract fields, BDD G/W/T, DAG, placeholders, anchors, topology | JSON + exit code |
| Gate 2 | Independent reviewer | Traceability, invented content, ADR alignment | Review findings |
| Gate 3 | `verification_linter.py` | Section 3 V(G), basis paths, Section 4 MSI, Section 5 provenance | JSON + exit code |
| Mutation | `tools/mutation_gate.py` | `MUTATION_COMMAND` report on trunk; fail-closed | Normalized report |
| Role audit | `tools/rbac_audit.py` | Changed paths vs role scope | CI status |

Quality bar: PRD/spec have no unresolved placeholders, stable IDs/anchors and every ADR fork resolved
or explicitly open before decomposition. Code: `V(G) <= 10` per function (`11-15` waiver, `>15`
rejected); `Test Cases >= V(G)`; `MSI >= 80%` (`>= 90%` for `risk_level: core`); no critical surviving
mutant; no fabricated evidence. CI plus branch protection (L1/L2) is authoritative; prompt rules are
L0 only.

## 6. Skill change workflow (authoring -> optimization -> tests -> git flow)

This section applies when changing the suite itself (`SKILL.md`, `references/`, assets, scripts,
rules, templates, manifests, CI or docs). It does not replace §2.2. Principles: small, reviewable,
reversible; evidence over claims; one writer per file; no bypassed gates.

1. **Intent and issue (risk-based).** Behavior, security, gate, CI, release or multi-file changes
   start with an issue containing problem, scope, acceptance criteria, test plan and risk. A trivial
   typo or docs-only PR may skip the issue only when the PR explains why; never use that exception
   for code, gates, CI or release changes.
2. **Branch and write scope.** Branch from an up-to-date `main` using `feat/<topic>`, `fix/<topic>`,
   `docs/<topic>`, `chore/<topic>` or `security/<topic>`. One logical change per branch; never commit
   directly to `main`. Parallel agents must use disjoint write scopes and the Lead integrates and
   reviews the final diff; two agents must not edit the same file.
3. **Author or optimize.** Edit canonical `.agents/skills/<name>/` and the byte-identical mirror
   `skills/workflow/<name>/`; keep `SKILL.md` under 200 lines, canonical English, self-contained;
   put detail in `references/`/`assets/`; keep templates token-free where Gate 1 scans them. Update
   the role rule, docs, skill `metadata.version`, `CHANGELOG.md`, `VERSION` and plugin manifests for
   behavior changes; document breaking changes and migration. Never weaken a gate, test or role
   boundary.
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
6. **Pull request and review.** Push the branch and open a PR against `main` using the PR template:
   `Closes #<issue>`, summary, test evidence, risk/rollback, release/tag plan. Keep it reviewable;
   open a draft PR early for long work. Required checks must be green, and behavior/security/gate/CI
   changes need approval from an independent reviewer who is not the author (CODEOWNERS/branch
   protection where configured). Docs-only changes may self-merge only if branch protection permits.
7. **Merge, sync and post-merge verification.** Merge only with required checks and review complete;
   use the configured merge method; do not force-push a reviewed branch; delete the branch and
   `git switch main && git pull --ff-only`. Watch post-merge CI; if `main` is red, fix forward with a
   new PR or revert with a PR — never rewrite `main`.
8. **Tag and release (SemVer).** Release only from merged `main`. Breaking -> major, feature ->
   minor, fix -> patch; docs/chore only when user-visible or bundled with a release. Update
   `VERSION`, `CHANGELOG.md`, plugin manifests and skill metadata, create an annotated `vX.Y.Z` tag
   (sign it if required), push it, and verify the release workflow, assets, GitHub release and
   install smoke. Never move or delete a published tag; a bad release gets a new patch release.
9. **Definition of done.** Issue linked; tests and CI green; independent review where required;
   mirrors byte-identical; docs, version, changelog and manifests agree; PR merged; post-merge CI
   watched; tag/release verified when released; rollback path documented.
10. **Prohibited shortcuts.** Direct commits to `main`; force-pushing shared branches; bypassing
    required checks (`|| true`, `continue-on-error`, `[skip ci]` on required gates); deleting or
    skipping tests; editing only one tree; committing secrets; self-approving behavior/security/gate
    changes; tagging before merge; moving published tags; declaring done without evidence.

When the user says "standard open-source workflow", "git flow", "issue/PR", "commit/push/PR/tag" or
equivalent, execute this section without asking for a separate process description.

## 7. Commands
```bash
python -m unittest discover -s tests/unit -p "test_*.py"
python -m compileall -q .agents tools templates
claude plugin validate .                  # when manifests change; optional if unavailable
python tools/quickstart.py --target .tmp-smoke --dry-run   # distribution smoke
git diff --check
```

## 8. Maintaining this file
- Keep this always-loaded summary at most 165 lines; move detail to role rules/skill docs/guides and
  do not duplicate role permissions, gate internals or pinned tool versions here.
- Changes need a docs PR, the workflow guard tests and the same review rules as §6. If this file
  conflicts with a role rule, the role rule wins for permissions; fix the stale source in the PR.

## References

- `.agents/rules/enforcement.md` — role matrix, lifecycle markers, enforcement model.
- `.agents/skills/README.md` — skill index, discovery and per-skill contract.
- `templates/ci/README.md` — CI gates, RBAC audit and the four-stage pipeline.
- `CONTRIBUTING.md` — contributor setup, tests and PR conventions.
- `docs/skills-guide.zh-CN.md`, `docs/brownfield-convergence.zh-CN.md`,
  `docs/skills-compatibility.md` — usage, convergence and harness compatibility.
- `docs/README.md` — user-facing docs index; `docs/archive/` — historical notes (not current rules).
