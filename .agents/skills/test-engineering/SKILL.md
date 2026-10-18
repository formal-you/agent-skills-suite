---
name: test-engineering
description: "Define and govern the repository-wide test system: test strategy, risk-based test design methods, test data and environment policy, flakiness policy, contract/property and non-functional test guidance, test metrics, and independent test-design review. Use when establishing or evolving global testing standards, choosing test levels and design techniques for a risk, defining test data/environment/flakiness policy, or reviewing a task's test design for coverage and determinism before QA execution. Do not use for per-task acceptance testing or verdicts (qa), CI pipeline or gate construction (quality-engineering), semantic plan or code review (review), implementation, or planning."
license: MIT
compatibility: "Harness-agnostic prompt workflow. No scripts, no runtime dependency."
metadata:
  version: "1.1.0"
  category: execution
---

# Test Engineering — Global Test System

The `test-engineering` role owns the **repository-wide test system**: how the project decides what to
test, which levels and techniques to use, how test data and environments are governed, how flakiness
is contained, which objective metrics matter, and whether a proposed test design is sound.

This skill is **global-only**. It is a prompt-only standards-and-review workflow: it never accepts,
verifies, or signs off an individual task, never issues `QA_PASSED` or `REWORK_REQUIRED`, never
writes tests or `03-qa-verification.md`, never edits source, and never runs or replaces CI gates. It
defers per-task acceptance to `qa` and CI pipeline/gate construction to `quality-engineering`.

## Use when

- Establishing, revising, or ratifying the repository-wide test strategy and quality attributes.
- Choosing test levels (unit, integration, contract, acceptance, E2E) and design techniques for a
  stated risk, stack, or feature area.
- Defining shared policy for test data, environments, test doubles, flakiness, or test metrics.
- Reviewing a task's or feature's **test design** independently before QA execution (design review,
  not acceptance).
- Onboarding a stack or service into an existing risk-based test system.
- Deciding how test evidence and metrics are defined and handed to QA and CI owners.

## Do not use when

- You are executing per-task acceptance testing, recording evidence, or issuing a QA verdict — that
  belongs to `qa`.
- You are building or changing CI pipelines, workflow definitions, gates, or runner environments —
  that belongs to `quality-engineering`.
- You need a semantic plan review (Gate 2) or a change/code review — that belongs to `review`.
- You are implementing product code or authoring the acceptance test suite — that belongs to `dev`
  and `qa`.
- You are planning, slicing, or authoring task contracts — that belongs to the planning skills.

## Inputs

- Repository context: supported stacks, critical user journeys, existing suites and their commands,
  and the current CI topology (read-only).
- Upstream product and architecture artifacts (requirements, decisions, technical spec) and task
  contracts, when assessing risk or reviewing a design (read-only).
- Defect and incident history, production telemetry summaries, flaky-test reports and test-runtime
  data.
- A draft test strategy or a task's proposed test matrix / test-design note.
- The adopting project's quality attributes, compliance constraints, and stated thresholds.
- The project's agreed test-strategy location (a role rule may fix a default). The skill ships a
  strategy template; if no strategy exists, create it from the template instead of assuming a file is
  present.

## Outputs

- A shared, versioned test-strategy document: goals, quality attributes, risk matrix, test-level and
  technique policy, data/environment policy, flakiness policy, metrics, RACI, and adoption roadmap.
  Its default location is fixed by the repository role rule; adopters may override that default only
  through the same rule. When no strategy exists, create it from the bundled template. The skill never
  depends on a suite-level strategy file being installed; the template is the self-contained source.
- Independent test-design review notes with severity-classified findings and exactly one design
  marker: `DESIGN_READY` or `DESIGN_GAPS`.
- Reusable standards: technique-selection guidance, review checklists, metric definitions, and a
  filled strategy template for the stack.
- Handoff recommendations addressed to `qa`, `quality-engineering`, `dev`, and the planning role.
- No test code, no source changes, no CI files, no task-bundle artifacts, and no acceptance verdicts.

## Workflow

1. **Assess.** Read the current suites, defect history, stack constraints and incident data. Build or
   refresh the risk register: likelihood x impact per behavior, component, and interface. Identify
   quality attributes that are currently unverified or thinly verified.
2. **Formulate the strategy.** Write the test-strategy document from
   [`assets/templates/test-strategy.template.md`](assets/templates/test-strategy.template.md): scope,
   quality attributes, risk matrix, level mix, technique policy, data/environment policy, test-double
   policy, flakiness policy, metrics, RACI, and an adoption roadmap with owners and dates.
3. **Define design standards.** Convert the strategy into checkable design rules: which techniques
   are mandatory for which risk class, what "deterministic" means for this stack, acceptable test
   doubles, required negative/boundary/state coverage, and the evidence each test must carry.
4. **Optionally review a test design.** Use
   [`references/test-design-review.md`](references/test-design-review.md) to audit one task's
   proposed test design independently. Report findings with severity and issue exactly one marker:
   `DESIGN_READY` when no blocker/major remains, `DESIGN_GAPS` otherwise. This marker is a
   design-quality opinion; it is **not task acceptance** and never a QA verdict.
5. **Hand off and measure.** Give QA the design findings and the risk-based priorities; give
   quality-engineering the metric definitions and tiering expectations; publish the strategy and
   review notes in the agreed location. Revisit metrics and flake data on a fixed cadence and revise
   the strategy when evidence changes.

## Boundaries

| Concern | Owner | Relationship to this skill |
| :--- | :--- | :--- |
| Per-task acceptance, test execution, evidence, `QA_PASSED` / `REWORK_REQUIRED` | `qa` | Receives design standards and review findings; owns the verdict. This skill never issues it. |
| CI pipelines, workflow definitions, gates, runner environments, automated enforcement | `quality-engineering` | Receives metric definitions and tiering expectations; owns CI execution and gates. This skill never runs them. |
| Semantic plan review (Gate 2) and change/code review | `review` | Independent of test design; this skill does not review plans or diffs. |
| Implementation, unit tests, refactoring | `dev` | Receives design standards; this skill never edits source. |
| Task contracts, slicing, acceptance criteria | planning skills | Read-only here; this skill never authors or rewrites contracts. |
| Repository-wide test strategy, design methods, data/environment and flakiness policy, metrics, test-design review | **this skill** | Owns the standards and the design-quality marker only. |

## Design markers (not a verdict)

- `DESIGN_READY` — the reviewed test design is traceable, risk-appropriate, deterministic, and
  independently executable; no blocker or major finding remains.
- `DESIGN_GAPS` — at least one blocker or major finding is open; list each with evidence and the
  required action.
- Both markers describe test-design quality. They are **not** `QA_PASSED`/`REWORK_REQUIRED`, not task
  acceptance, and not a CI gate result.

## References

- [`references/test-strategy.md`](references/test-strategy.md) — strategy template and checklist:
  quality attributes, risk matrix, test levels, technique selection, data/environment and test-double
  policy, flakiness, automation handoff, metrics, RACI, adoption roadmap.
- [`references/test-design-review.md`](references/test-design-review.md) — independent checklist for
  reviewing a task's test design, severity model and `DESIGN_READY`/`DESIGN_GAPS` output.
- [`references/role-boundaries.md`](references/role-boundaries.md) — write scope, read-only scope,
  invariants, and the honest enforcement model (bundled; no external files needed).
- [`assets/templates/test-strategy.template.md`](assets/templates/test-strategy.template.md) —
  fillable strategy template with sections and placeholders.
- Repository rules: read the adopting project's agent rules and role rules when present; they may add
  requirements but are not a runtime dependency of this skill.

## Honest limits

This skill is prompt-driven and cannot enforce standards or isolation. Its outputs are only as good as
the evidence supplied to it, and a design review can miss gaps. Where the repository has CI and branch
protection, that is the authoritative layer for gates and roles. Per-task acceptance remains with
`qa`; this skill provides the global system and an independent design opinion, never a verdict.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
