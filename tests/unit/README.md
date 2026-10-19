# tests/unit — test taxonomy and evidence contract

This directory is the **suite-level regression net**: it proves that the skill scripts, templates,
rules, docs and distribution behave as this repository documents. It is **not** a per-task
acceptance mechanism. A green suite does not prove that a task contract under `tasks/<task-id>/`
was implemented; that evidence comes from Gate 1, Gate 2, Gate 3, the QA verdict and CI.

Every test belongs to one of the categories below. When adding a test, decide which category it is
and keep the category's evidence strength honest.

## Categories

| Category | Files | What it proves | Evidence strength |
| :--- | :--- | :--- | :--- |
| **Behavioral (black-box)** | `test_plan_linter.py`, `test_verification_linter.py`, `test_complexity_check.py`, `test_rbac_audit.py`, `test_mutation_gate.py`, `test_skill_scripts.py`, `test_distribution.py`, `test_manifest.py` | Runs the shipped helper as a subprocess (or imports it under test) and asserts exit codes, JSON, filesystem effects, temp git repositories and relocated installs | **Strong** — fails if the implementation regresses |
| **Mixed** | `test_change_skill.py`, `test_converge.py`, `test_task_templates.py`, `test_modern_quality_engineering.py` | Combines real script execution with template/structure assertions | **Medium** — depends on the test |
| **Policy and structure guards** | `test_agents_workflow.py`, `test_docs_consistency.py`, `test_error_code_consistency.py`, `test_test_strategy_wiring.py`, `test_test_engineering_skill.py`, `test_ci_profiles.py`, `test_execution_skills.py`, `test_review_skill.py` | Mirrors are byte-identical, links resolve, line budgets hold, required phrases/sections exist, error-code registries and versions agree | **Anti-regression only** — a passing test can be satisfied by editing text; it does not prove runtime behavior |

## Known weakness

`test_modern_quality_engineering.py` contains local reimplementations
(`BDDScenarioParser`, `CyclomaticComplexityAnalyzer`, `MutationScoreCalculator`,
`QualityGateLinterEngine`, `QualityEngineeringTriadAuditor`). Most of its tests exercise those local
models rather than the shipped `plan_linter.py` / `complexity_check.py` / `verification_linter.py`;
only the Tier 4 end-to-end tests invoke the real plan linter. Treat those model tests as
**specification examples**, not proof that the real gates behave that way.

Planned remediation: migrate the model tests to invoke the real scripts (or add a parity test) so the
suite cannot drift from the implementation.

## What proves a change is real

| Question | Evidence |
| :--- | :--- |
| Did this task implement its contract? | `tasks/<task-id>/01-contract.md` + Gate 1, Gate 2, Gate 3, `03-qa-verification.md` evidence and the single QA verdict |
| Does the suite still behave? | Behavioral tests in this directory |
| Are docs, mirrors, versions and manifests consistent? | Policy and structure guards in this directory |
| Is it safe to merge? | CI checks plus branch protection; local tests are necessary but not sufficient |

## Conventions

- Standard library only. No network access from tests.
- Prefer black-box tests: `subprocess`, `tempfile` directories, fixture task bundles, temporary git
  repositories. Do not mock the code under test when running it is cheap.
- Add a behavioral test for every new or changed helper. Add a policy guard only for rules that must
  not regress silently (mirror parity, links, line budgets, registries).
- Never delete, skip or weaken a test to make a change pass; never use `|| true` or
  `continue-on-error` to hide a failure.
- After adding or removing a tracked file, regenerate the distribution manifest and commit it:
  `python tools/gen_manifest.py`.
- Do not treat a green run as permission to skip the pipeline gates.

## Run

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
python -m unittest tests.unit.test_distribution tests.unit.test_manifest -v
```
