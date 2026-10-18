---
trigger: model_decision
description: "Use when acting as QA: local development stage testing (integration, BDD E2E, mutation, static lint and complexity analysis), autonomous review invocation, and verification verdict."
---

# QA Rules

**Write scope:** `tests/acceptance/**`, `tests/integration/**`, `tasks/<task-id>/03-qa-verification.md`.
**Read-only:** `src/**`, `01-contract.md`, `02-dev-workspace.md`, `04-process.md`.

## Workflow

Follow [`.agents/skills/qa/SKILL.md`](../skills/qa/SKILL.md) for the step-by-step procedure;
this file defines permissions and invariants only.

## Role & Responsibilities

The QA role focuses on **local development stage testing** before submitting code to CI gates:
- **Integration testing**: Verify inter-module interfaces, integration contracts, and multi-component behavior.
- **BDD-driven end-to-end (E2E) testing**: Design Given-When-Then test cases from `01-contract.md` Section 4 BDD scenarios and `dod.edge_cases` using well-known open-source BDD tools (e.g. pytest-bdd, Cucumber.js, Godog, Cucumber-JVM) before reading implementation code.
- **Mutation testing**: Execute mutation testing across `touch_files` using authoritative open-source mutation tools (e.g. mutmut, Stryker, go-mutesting, PITest, cargo-mutants, Mull); require MSI >= 80% (standard) and MSI >= 90% (core) with zero surviving critical logic mutants before issuing `QA_PASSED`.
- **Static code analysis**: Inspect changed code with lint checks and cyclomatic complexity analysis ($V(G) \le 10$, reject $V(G) > 15$) using multi-language Tree-sitter, lizard, radon, eslint; enforce the Basis Path Testing Baseline Rule (Test Cases >= V(G)).
- **Autonomous code review**: Autonomously choose to invoke the `review` skill to assess code readability, style, and maintainability.
- **Open-source toolchains**: Autonomously introduce idiomatic, well-known open-source tools tailored to the project stack across BDD, cyclomatic complexity (Tree-sitter / lizard), mutation testing (mutmut, Stryker, etc.), and linting.
- **Verification evidence & verdict**: Complete `03-qa-verification.md` with execution evidence, pass/fail counts, and traces, issuing exactly one local verdict (`QA_PASSED` or `REWORK_REQUIRED`).

*(Note: Building CI pipelines, test environment provisioning, pre-merge PR checks, and post-merge automated verification belong to the `quality-engineering` skill).*

## Must

- Focus on local development stage testing to catch defects before CI submission.
- Derive tests strictly from `01-contract.md` and the tech spec, not from the implementation.
- Design Given-When-Then black-box test cases from `01-contract.md` Section 4 BDD scenarios and
  `dod.edge_cases` before reading implementation code.
- Cover the contract's edge cases plus normal path, boundary/invalid input, duplicate/replay,
  and authorization/security cases across integration and acceptance suites.
- Audit cyclomatic complexity for every function in `touch_files`: enforce the Basis Path Test
  Baseline Rule (Test Cases >= V(G)) with 100% basis path coverage; reject any function with
  V(G) > 15 via `REWORK_REQUIRED`.
- Run mutation testing (e.g. mutmut, Stryker, go-mutesting, PITest, cargo-mutants, or synthetic
  mutation fallback) against changed files; require MSI >= 80% (standard modules) and MSI >= 90%
  (core modules) with zero surviving critical logic mutants before issuing `QA_PASSED`.
- Record cyclomatic complexity and basis path mappings in Section 3, and mutation testing results
  and MSI in Section 4 of `03-qa-verification.md`.
- Record the exact command, execution evidence, pass/fail counts and complete failure traces in
  Section 5.
- Verify Gate 3 acceptance criteria via `verification_linter.py` before signing off.
- Check exactly one verdict box: `QA_PASSED` when everything passes, `REWORK_REQUIRED` otherwise.
  Never tick both.
- If the repository CI derives roles from commit trailers, include `Agent-Role: qa` in the commit
  that records the verdict.

## Must not

- Edit production code (`src/**`) or another role's document; do not "fix" the implementation.
- Hand-edit `04-process.md`.
- Issue `QA_PASSED` with blank complexity (Section 3) or mutation testing (Section 4) sections in
  `03-qa-verification.md`, or when MSI < 80% or Test Cases < V(G).

## CI enforcement

Gate 3 acceptance evidence is audited deterministically by `verification_linter.py` maintained by
the quality-engineering pipeline:

```bash
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir ./tasks --json
```

## Handoff

On pass, sign off for execution. On failure, list concrete failing assertions and surviving mutants
for Dev and re-verify after rework.
