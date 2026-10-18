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
- QA — `.agents/rules/qa.md`: local development stage testing (integration, BDD E2E, mutation testing, static lint & complexity analysis, autonomous review invocation). Prompt-only execution skill; writes `tests/acceptance/**`, `tests/integration/**` plus `03-qa-verification.md`; never edits source or other roles' docs.
- Quality Engineering — `.agents/skills/quality-engineering/`: CI pipeline construction, test environment provisioning, pre-merge PR gates (Gate 1, RBAC, complexity check, acceptance tests, Gate 3 audit), post-merge automated verification, and ownership of CI workflow templates (`quality-gate.yml`) and audit scripts (`complexity_check.py`, `verification_linter.py`).
- Reviewer (Gate 2) — `.agents/rules/reviewer.md`: read-only semantic audit; never edits artifacts or weakens Gate 1.
- Orchestrator/Lead — `.agents/rules/orchestrator.md`: routes work and enforces gate order; never authors role artifacts or bypasses a gate.

## Gates and evidence

- **Gate 1 (deterministic):** `plan-linter` has strictly single responsibility for Gate 1 deterministic task contract and DAG validation before development starts; checks contract fields, BDD Given-When-Then scenarios, DAG, placeholders, anchor coverage and real-file topology; its JSON and exit codes are the evidence.
- **Gate 2 (semantic):** an independent, read-only reviewer audits traceability, invented content and ADR alignment; it never replaces Gate 1.
- **Modern Quality Engineering Triad & Execution:**
  - **Static Complexity Checker:** Multi-language AST McCabe Cyclomatic Complexity static checker (`complexity_check.py` v2.0.0) powered by Tree-sitter (https://github.com/tree-sitter/tree-sitter) with Lizard integration and Python AST fallback, covering Python, JS/TS, Go, Rust, Java, C/C++, C#. Dev enforces single-function cyclomatic complexity ($V(G) \le 10$) and hands off with evidence in `02`.
  - **BDD Living Documentation:** QA conducts local integration and BDD E2E testing with stack-native open-source frameworks (pytest-bdd, Cucumber.js, Godog, Cucumber-JVM, cucumber-rs, Reqnroll/SpecFlow).
  - **Mutation Testing:** Mandatory open-source mutation testing tools (mutmut, Stryker, go-mutesting, PITest, cargo-mutants, Mull) with $\text{MSI} \ge 80\%$ threshold. QA designs basis path tests ($\text{Test Cases} \ge V(G)$), records evidence in `03`, and issues exactly one verdict (`QA_PASSED` or `REWORK_REQUIRED`); `converge` folds confirmed deviations back into the spec after `QA_PASSED`.
- **Gate 3 (acceptance audit):** `verification_linter.py` (maintained by `quality-engineering`) deterministically audits signed-off `03` artifacts for basis path coverage and mutation MSI thresholds upon QA signoff.
- **Enforcement honesty (L0-L2):** prompt rules are advisory and bypassable (L0). The authoritative layer is the CI Quality Gate (`templates/ci/quality-gate.yml`, `tools/rbac_audit.py`) (L1) coupled with branch protection and CODEOWNERS (L2); no local hook adapter is shipped.

## References

- `.agents/rules/enforcement.md` — role matrix, lifecycle markers and the honest enforcement model.
- `.agents/skills/README.md` — skill index, discovery and the per-skill contract.
- `templates/ci/README.md` — CI quality engineering gates, RBAC audit and 4-stage testing pipeline.
- `skills/<category>/<name>/` — installable layout for plugins and `npx skills`; `.agents/skills/`
  is the AGENTS mirror.
- `docs/skills-guide.zh-CN.md`, `docs/brownfield-convergence.zh-CN.md`,
  `docs/skills-compatibility.md` — usage walkthrough, change/convergence and the harness matrix.
- Review skill: `review` (Gate 2 plan review plus change/code review); execution skills: `dev`
  (implement + handoff) and `qa` (independent verification + verdict); quality engineering: `quality-engineering`
  (CI gates + pipeline automation); brownfield entry: `change`
  (proposal -> one task bundle -> archive) and convergence: `converge` (after `QA_PASSED`, append
  deviations to `.specs/02-tech-spec.md`, move the bundle to `tasks/archive/`).
