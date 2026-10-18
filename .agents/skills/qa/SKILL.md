---
name: qa
description: "Local development stage testing: execute integration, BDD-driven E2E, mutation testing (MSI >= 80%), and static lint/complexity analysis; autonomously invoke review skill; introduce stack open-source tools; complete 03-qa-verification.md with local evidence and issue exactly one verdict (QA_PASSED or REWORK_REQUIRED). Use when a task is handed off with WAITING_FOR_QA. Do not use for implementation, planning, or contract authoring."
license: MIT
compatibility: "Harness-agnostic prompt workflow plus an optional stdlib Python Gate 3 pre-check script; no external runtime dependency."
metadata:
  version: "2.2.0"
  category: execution
---

# QA — Local Testing & Independent Verification

Execute comprehensive local development stage testing and independently verify task bundles before
submitting for CI gating. This skill defines the **process** and carries its own role boundaries in
[`references/role-boundaries.md`](references/role-boundaries.md). If the adopting repository defines
agent rules (`AGENTS.md`, a role-rules directory or equivalent), read and follow them when present;
the skill never grants extra access.

## Core Responsibilities (Local Development Stage Testing)

- **Integration testing**: Author and run tests verifying cross-module, API, and multi-component behavior.
- **BDD-driven E2E testing**: Extract Given-When-Then scenarios from `01-contract.md` Section 4 and
  `dod.edge_cases` to construct black-box acceptance and end-to-end tests under `tests/acceptance/`
  using well-known open-source BDD tools (e.g. pytest-bdd, Cucumber.js, Godog, Cucumber-JVM).
- **Mutation testing**: Execute mutation analysis across `touch_files` using authoritative open-source
  tools (e.g. mutmut, Stryker, go-mutesting, PITest, cargo-mutants, Mull), eliminating weak assertions
  until $\text{MSI} \ge 80\%$ ($\ge 90\%$ core) and zero critical mutants survive.
- **Static code analysis**: Inspect changed code using linting and McCabe cyclomatic complexity (via
  Tree-sitter, lizard, radon, eslint; $V(G) \le 10$, reject $V(G) > 15$); enforce the Basis Path
  Testing Baseline Rule ($\text{Test Cases} \ge V(G)$).
- **Autonomous code review**: Autonomously choose to invoke the `review` skill to assess code readability,
  code style conventions, and maintainability.
- **Toolchain selection**: Autonomously introduce well-known open-source tools tailored to the stack.
- **Verification evidence & verdict**: Populate `03-qa-verification.md` with local execution evidence
  and record exactly one verdict: `QA_PASSED` or `REWORK_REQUIRED`.
*(CI pipeline creation and automated pre-merge/post-merge gates belong to the `quality-engineering` skill).*

## Use when

- A task under `tasks/<task-id>/` has `- [x] WAITING_FOR_QA` in `02-dev-workspace.md`.
- You need to run local integration, BDD E2E, mutation, and static analysis (lint & complexity) tests.
- You need to record evidence in `03-qa-verification.md` and sign off or return the task for rework.
- You are re-verifying a task after a Dev rework.

## Do not use when

- The handoff marker is not checked — return the task to Dev instead of guessing.
- You are asked to implement, plan, slice, or build CI pipelines; those belong to Dev, Planner, and
  quality-engineering respectively.
- The contract or upstream spec is missing or contradictory — report it; do not reconstruct it.

## Inputs

- `tasks/<task-id>/01-contract.md` — DoD, `touch_files`, traceability, inherited ADRs, and Section 4
  BDD behavioral scenarios (Given-When-Then invariants).
- `tasks/<task-id>/02-dev-workspace.md` — Dev's handoff claim, declared commit, and complexity notes.
- Project test layout and the declared `dod.test_file` command.
- Project test strategy document (read-only, if present; created in the adopting project): risk
  classes, test levels, design techniques, data/environment and flakiness policy. The repository role
  rule fixes its default location; when it is absent, record `strategy: baseline` and use the
  contract-derived minimum.
- `tasks/<task-id>/03-qa-verification.md` — the blank form you fill.

## Outputs

- Integration and acceptance tests under `tests/acceptance/` and `tests/integration/`.
- A completed `03-qa-verification.md` with the test design summary (Section 2.1), BDD test matrix
  (Section 2.2), complexity & basis path coverage table (Section 3), mutation testing and MSI audit
  table (Section 4), execution evidence (Section 5), boundary audit (Section 6), and verdict
  (Section 7).
- Exactly one verdict marker: `- [x] QA_PASSED` or `- [x] REWORK_REQUIRED`.
- No edits to source, `01-contract.md`, `02-dev-workspace.md` or `04-process.md`.

## Workflow

1. **Verify handoff.** Confirm `WAITING_FOR_QA` is checked in `02`, declared commit exists, and `01`
   is unchanged. If not, stop and report the gap.
2. **Design BDD E2E & integration tests.** Read the repository test strategy first when present and
   record its reference (or `strategy: baseline` when absent) in the test design summary (Section 2.1
   of `03`). Then extract Section 4 BDD scenarios, `dod.edge_cases`, `touch_files`, and ADRs. Author
   black-box tests under `tests/acceptance/` before inspecting code.
3. **Static code analysis (lint & complexity).** Run stack linters (ruff, eslint, etc.) and calculate
   cyclomatic complexity $V(G)$ for modified functions in `touch_files` (lizard, radon, etc.). Enforce
   $V(G) \le 10$ and the Basis Path Baseline Rule ($\text{Test Cases} \ge V(G)$). Reject $V(G) > 15$.
4. **Autonomous code review.** Autonomously invoke the `review` skill to assess code readability,
   formatting, naming clarity, and maintainability.
5. **Execute tests & mutation analysis.** Run integration and acceptance suites; record totals, passes,
   and traces. Run mutation testing (mutmut, Stryker, go-mutesting, PITest, cargo-mutants, or synthetic
   fallback). Eliminate weak assertions until $\text{MSI} \ge 80\%$ ($\ge 90\%$ core) and zero critical
   mutants survive. Record counts and MSI in Section 4 of `03-qa-verification.md`.
6. **Audit boundaries & Gate 3 compliance.** Verify all changed paths are inside `touch_files`, Dev did
   not edit `tests/acceptance/` or `01`, then run the bundled Gate 3 pre-check:
   `python .agents/skills/qa/scripts/verification_linter.py --tasks-dir ./tasks --json`.
   When a real complexity artifact is available, add
   `--actual-complexity <report> --require-actual-complexity` to cross-check Section 3 V(G).
   This local check is advisory; CI Gate 3 remains authoritative.
7. **Issue exactly one verdict.** Tick `QA_PASSED` only when tests pass, 100% basis path coverage is
   achieved ($\text{Test Cases} \ge V(G)$), complexity complies, mutation score meets threshold
   ($\text{MSI} \ge 80\%$), Gate 3 linter passes with zero errors, and audits pass; otherwise tick
   `REWORK_REQUIRED` and include complete failure traces and surviving mutants. Never tick both.
8. **Rework loop.** On next attempt, retain prior evidence, update attempt metadata, and re-verify.

## Quality gate (before signing off)

- [ ] Handoff marker was checked and reviewed commit matches `02`.
- [ ] Test matrix covers Given-When-Then BDD scenarios: normal, boundary, replay, and security cases.
- [ ] Test design summary recorded and strategy reference (or baseline) stated.
- [ ] Basis path baseline satisfied: black-box test cases $\ge V(G)$ for every modified function.
- [ ] Every modified function satisfies $V(G) \le 10$ (or documented waiver for $11-15$; $>15$ rejected).
- [ ] Static analysis & linting clean; `review` skill optionally consulted for readability.
- [ ] Mutation testing audit complete: $\text{MSI} \ge 80\%$ ($\ge 90\%$ core) and zero critical mutants.
- [ ] Section 3 (Complexity) and Section 4 (Mutation) of `03-qa-verification.md` are completely filled.
- [ ] Gate 3 pre-check (bundled `verification_linter.py`) passes with zero violations; otherwise mark the evidence gaps and return for rework.
- [ ] Execution evidence recorded with command, counts, and traces in Section 5.
- [ ] Every changed path is inside `01` → `touch_files`. Dev did not modify acceptance tests or `01`.
- [ ] Exactly one verdict is checked; `REWORK_REQUIRED` has actionable traces.

## Failure handling

- **Handoff missing/inconsistent**: reject with specific gap; do not invent commits.
- **Basis path deficit / Untestable paths**: issue `REWORK_REQUIRED` if test cases $< V(G)$.
- **Complexity limit exceeded ($V(G) > 15$)**: issue `REWORK_REQUIRED` requiring Dev modular refactoring.
- **Mutation deficit ($\text{MSI} < 80\%$) / Survived critical mutants**: issue `REWORK_REQUIRED`.
- **Lint / Readability defects**: flag defects or issue `REWORK_REQUIRED` when code violates conventions.
- **Out-of-scope Dev change**: issue `REWORK_REQUIRED` with the violating path.
- **Repeated rework**: escalate with failure history; do not lower the bar to close the task.

## `04-process.md` and tooling

`04` is derived output. Checking `QA_PASSED` lets optional tooling append `TASK_TERMINATED_DONE` and
set `macro_status: DONE`; checking `REWORK_REQUIRED` appends `REWORK_TRIGGERED`, sets `REWORKING`
and increments retry counter. Never hand-edit `04`; rely on git/CI and the checked box.

## References

- [`references/qa-protocol.md`](references/qa-protocol.md) — test design summary, test matrix,
  integration testing, basis path testing ($V(G)$ baseline), mutation testing (MSI formula and 6-step
  workflow), static analysis, evidence format and verdict rules.
- Gate 3 pre-check: [`scripts/verification_linter.py`](scripts/verification_linter.py) — a bundled,
  stdlib-only copy of the quality-engineering auditor for Section 3 complexity and Section 4 mutation
  evidence. The copy is parity-tested against the canonical script; CI Gate 3 remains authoritative.
- Role boundaries: [`references/role-boundaries.md`](references/role-boundaries.md) — write scope,
  read-only scope, invariants and the honest enforcement model (bundled; no external files needed).
- Repository rules: read `AGENTS.md` and role-rules files when defined by adopting project.

## Honest limits

This skill does not grant write access and cannot enforce role isolation. Where the repository has
CI (for example a git-based role audit) or branch protection, that is the authoritative layer.
The bundled Gate 3 pre-check is advisory: it audits the `03` evidence and can cross-check a supplied
complexity artifact, but it does not execute tests or replace authoritative CI Gate 3. Gate 1/2 review
is a separate planning concern; this skill verifies a task that already passed planning.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)

