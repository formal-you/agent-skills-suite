# Global Agent Rules for Autonomous Multi-Agent Development

These rules apply to every agent and every harness in this repository. This file is the
host-agnostic rules layer shipped with the Agent Skills Suite: keep it at the adopting repository
root so AGENTS-aware hosts load it automatically (Codex, DSH, Antigravity, generic agents). The
skills are self-contained and work without this file; when both are present, these conventions
apply.

The pipeline is: idea or bounded change -> PRD/spec -> task bundles -> Gate 1 -> Gate 2 ->
Dev <-> QA -> convergence. This file is the always-loaded summary; it must not contradict the
detailed rules in `.agents/rules/enforcement.md`, the skill index `.agents/skills/README.md` or the
guides under `docs/`.

## Task bundles

All work is sliced into task bundles under `tasks/<task-id>/` containing exactly four documents:

- `01-contract.md` — Planner-owned contract; authoritative YAML frontmatter, read-only for Dev/QA.
- `02-dev-workspace.md` — Dev-owned implementation notes, self-verification, handoff and the
  `Implementation deviations` table (`DEV-001` / `#sec-*` / `add|modify|remove`; `None` row when nothing deviated).
- `03-qa-verification.md` — QA-owned test matrix, evidence and verdict.
- `04-process.md` — derived status/audit output maintained by tooling; no agent hand-edits it.

The `task_id` in `01-contract.md` must equal the directory name.

## Goldilocks rule

Tasks are sized for one reviewable change: 1–3 touched files and 50–250 estimated diff lines by
default. The limits are configurable in the plan-linter configuration. Split tasks above the maximum;
merge tasks below the minimum.

## Role isolation and no cheating

Each role has a rule file under `.agents/rules/`; it defines the permissions that this summary cannot
override. If an action is outside your write scope, escalate to the owner instead of editing.

- Planner — `.agents/rules/planner.md`: creates task bundles; never writes source, tests or `04`.
- Dev — `.agents/rules/dev.md`: writes `src/**` plus `02-dev-workspace.md`; never edits tests, contracts or other roles' docs.
- QA — `.agents/rules/qa.md`: local development stage testing (integration, BDD E2E, mutation testing, static lint & complexity analysis, autonomous review invocation, local Gate 3 pre-check). Prompt-first execution skill with a bundled `scripts/verification_linter.py`; writes `tests/acceptance/**`, `tests/integration/**` plus `03-qa-verification.md`; never edits source or other roles' docs.
- Quality Engineering — `.agents/skills/quality-engineering/`: CI pipeline construction, test environment provisioning, pre-merge PR gates (Gate 1, RBAC, complexity check, acceptance tests, Gate 3 audit), post-merge automated verification, and ownership of CI workflow templates (`quality-gate.yml`), audit scripts (`complexity_check.py`, `verification_linter.py`) and the fail-closed mutation helper (`mutation_gate.py`).
- Test Engineering — `.agents/rules/test-engineering.md`: owns the repository-wide test system (test strategy, risk-based test-design methods, data/environment and flakiness policy, test metrics, independent test-design review); writes only the agreed test-strategy document and test-design review notes; never accepts an individual task, never writes tests or `03`, and never runs CI gates.
- Reviewer (Gate 2) — `.agents/rules/reviewer.md`: read-only semantic audit; never edits artifacts or weakens Gate 1.
- Orchestrator/Lead — `.agents/rules/orchestrator.md`: routes work and enforces gate order; never authors role artifacts or bypasses a gate.

## Gates and evidence

- **Gate 1 (deterministic):** `plan-linter` has strictly single responsibility for Gate 1 deterministic task contract and DAG validation before development starts; checks contract fields, BDD Given-When-Then scenarios, DAG, placeholders, anchor coverage and real-file topology. It does not audit the complexity/mutation evidence in `03-qa-verification.md` (Gate 3 owns that; placeholder and existence checks are allowed). Its JSON and exit codes are the evidence.
- **Gate 2 (semantic):** an independent, read-only reviewer audits traceability, invented content and ADR alignment; it never replaces Gate 1.
- **Modern Quality Engineering Triad & Execution:**
  - **Static Complexity Checker:** Multi-language AST McCabe Cyclomatic Complexity static checker (`complexity_check.py` v2.0.0) powered by Tree-sitter (https://github.com/tree-sitter/tree-sitter) with Lizard integration and Python AST fallback, covering Python, JS/TS, Go, Rust, Java, C/C++, C#. Dev enforces single-function cyclomatic complexity ($V(G) \le 10$) and hands off with evidence in `02`.
  - **BDD Living Documentation:** QA conducts local integration and BDD E2E testing with stack-native open-source frameworks (pytest-bdd, Cucumber.js, Godog, Cucumber-JVM, cucumber-rs, Reqnroll/SpecFlow).
  - **Mutation Testing:** Mandatory open-source mutation testing tools (mutmut, Stryker, go-mutesting, PITest, cargo-mutants, Mull) with $\text{MSI} \ge 80\%$ threshold. QA designs basis path tests ($\text{Test Cases} \ge V(G)$), records evidence in `03`, and issues exactly one verdict (`QA_PASSED` or `REWORK_REQUIRED`); `converge` folds confirmed deviations back into the spec after `QA_PASSED`.
- **Gate 3 (acceptance audit):** `verification_linter.py` (maintained by `quality-engineering`) deterministically audits signed-off `03` artifacts for basis path coverage and mutation MSI thresholds, and cross-checks Section 3 V(G) values against the CI-uploaded AST artifact (`--actual-complexity`); it is fail-closed on omitted/phantom/mismatched functions and on any non-compliant mutation table.
- **Mutation gate:** `tools/mutation_gate.py` runs the project's `MUTATION_COMMAND` on trunk pushes, validates the normalized report, and enforces the MSI threshold. A missing command/report is a failure, never a skip.
- **Enforcement honesty (L0-L2):** prompt rules are advisory and bypassable (L0). The authoritative layer is the CI Quality Gate (`templates/ci/quality-gate.yml`, `tools/rbac_audit.py`, `tools/mutation_gate.py`) (L1) coupled with branch protection and CODEOWNERS (L2); no local hook adapter is shipped.

## Skill change workflow (authoring -> optimization -> tests -> git flow)

This section applies when changing the **skill suite itself** (`SKILL.md`, `references/`, assets,
scripts, rules, templates, manifests, CI or docs). It does not replace the per-task Planner -> Dev ->
QA -> converge pipeline. Principles: small, reviewable, reversible; evidence over claims; one writer
per file; no bypassed gates.

1. **Intent and issue (risk-based).** Behavior, security, gate, CI, release or multi-file changes
   start with an issue containing problem, scope, acceptance criteria, test plan and risk. A trivial
   typo or docs-only PR may skip the issue only when the PR explains why; never use that exception
   for code, gates, CI or release changes.
2. **Branch and write scope.** Branch from an up-to-date `main` using `feat/<topic>`, `fix/<topic>`,
   `docs/<topic>`, `chore/<topic>` or `security/<topic>`. One logical change per branch; never commit
   directly to `main`. Parallel agents must use disjoint write scopes and the Lead integrates and
   reviews the final diff; two agents must not edit the same file.
3. **Author or optimize.**
   - Edit canonical `.agents/skills/<name>/` and the byte-identical mirror `skills/workflow/<name>/`.
   - Keep `SKILL.md` under 200 lines, canonical English, and self-contained (no runtime dependency on
     another skill or on repository-only `docs/`, `tools/` or CI files).
   - Put detail in `references/` or `assets/`; keep templates token-free where Gate 1 scans them.
   - Update the role rule, docs, skill `metadata.version`, `CHANGELOG.md`, `VERSION` and plugin
     manifests when behavior or interfaces change. Document breaking changes and migration.
   - Never weaken a gate, test or role boundary to make a change easier to land.
4. **Test and evidence before commit.**
   - Run targeted tests, then the full suite:
     `python -m unittest discover -s tests/unit -p "test_*.py"`.
   - Verify dual-tree parity, skill self-containment, `SKILL.md` line limits, YAML/JSON parse,
     `git diff --check`, and the CI matrix (Ubuntu/Windows, Python 3.9/3.12, plugin manifests).
   - For distribution changes, run an installation smoke test (`quickstart --dry-run` or a temp
     install); for manifest changes, run `claude plugin validate .` when available.
   - CI is authoritative: local tests are necessary but not sufficient. Never delete, skip or weaken
     a test, and never use `|| true` / `continue-on-error` to hide a failure.
5. **Commit.** Use conventional commit messages (`feat(scope): ...`, `fix(scope): ...`,
   `docs(scope): ...`, `security(scope): ...`). Keep commits atomic; stage only intended files; never
   commit secrets, credentials, generated caches or unrelated reformatting.
6. **Pull request and review.** Push the branch and open a PR against `main` using the PR template:
   `Closes #<issue>`, summary, test evidence, risk/rollback, release/tag plan. Keep it small enough
   to review; open a draft PR early for long work. Required checks must be green, and
   behavior/security/gate/CI changes require approval from an independent reviewer who is not the
   author (use CODEOWNERS/branch protection where configured). Docs-only changes may self-merge only
   if branch protection permits it.
7. **Merge, sync and post-merge verification.** Merge only with required checks and review complete;
   use the repository's configured merge method; do not force-push a reviewed branch; delete the
   branch and `git switch main && git pull --ff-only`. Watch the post-merge CI run; if `main` is red,
   fix forward with a new PR or revert with a PR — never rewrite `main`.
8. **Tag and release (SemVer).** Release only from merged `main`. Breaking change -> major,
   feature -> minor, fix -> patch; docs/chore changes are released only when user-visible or bundled
   with a release. Update `VERSION`, `CHANGELOG.md`, plugin manifests and skill metadata, create an
   annotated `vX.Y.Z` tag (sign it if the repository requires signed tags), push it, and verify the
   release workflow, release assets, GitHub release and install smoke. Never move or delete a
   published tag; a bad release gets a new patch release.
9. **Definition of done.** Issue linked; tests and CI green; independent review where required;
   mirrors byte-identical; docs, version, changelog and manifests agree; PR merged; post-merge CI
   watched; tag/release verified when released; rollback path documented.
10. **Prohibited shortcuts.** Direct commits to `main`; force-pushing shared branches; bypassing
    required checks (`|| true`, `continue-on-error`, `[skip ci]` on required gates); deleting or
    skipping tests; editing only one tree; committing secrets; self-approving behavior/security/gate
    changes; tagging before merge; moving published tags; declaring done without evidence.

When the user says "standard open-source workflow", "git flow", "issue/PR", "commit/push/PR/tag" or
equivalent, execute this section without asking for a separate process description.

## References

- `.agents/rules/enforcement.md` — role matrix, lifecycle markers and the honest enforcement model.
- `.agents/skills/README.md` — skill index, discovery and the per-skill contract.
- `templates/ci/README.md` — CI quality engineering gates, RBAC audit and 4-stage testing pipeline.
- `skills/<category>/<name>/` — installable layout for plugins and `npx skills`; `.agents/skills/`
  is the AGENTS mirror.
- `docs/skills-guide.zh-CN.md`, `docs/brownfield-convergence.zh-CN.md`,
  `docs/skills-compatibility.md` — usage walkthrough, change/convergence and the harness matrix.
- `docs/skills-remediation.zh-CN.md` — hardening work packages, critique adjudication and evidence
  pointers for the truthful-gate changes.
- Review skill: `review` (Gate 2 plan review plus change/code review); execution skills: `dev`
  (implement + handoff) and `qa` (independent verification + verdict); quality engineering: `quality-engineering`
  (CI gates + pipeline automation); test engineering: `test-engineering` (repository-wide test
  strategy and independent test-design review; never a per-task verdict); brownfield entry: `change`
  (proposal -> one task bundle -> archive) and convergence: `converge` (after `QA_PASSED`, append
  deviations to `.specs/02-tech-spec.md`, move the bundle to `tasks/archive/`).
