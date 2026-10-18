---
name: review
description: "Perform an independent, read-only review of a plan/task bundle (Gate 2) or a code change, producing evidence-backed findings and one verdict without editing anything. Use when Gate 1 has passed and the plan needs semantic review, or when a change needs review. Do not use for implementation, planning, QA execution, or reviewing your own work."
license: MIT
compatibility: "Harness-agnostic prompt workflow. No scripts, no runtime dependency; use the host's file/diff tools."
metadata:
  version: "2.0.0"
  category: review
---

# Review — Independent, Read-Only Review

Review the work of another role, find what is wrong or missing, and issue a verdict. This skill
defines the **review process**; it never edits the artifact under review and never replaces Gate 1
or QA verification.

## Use when

- **Gate 2 (plan review)**: Gate 1 passed and the task bundles need a semantic check against the PRD,
  ADRs and tech spec before implementation.
- **Change review**: a Dev has implemented a task and the change needs a quality/contract review
  (optionally before or alongside QA verification).
- A reviewer is explicitly asked to audit traceability, scope or architecture compliance.

## Do not use when

- You wrote the artifact under review — independence is required; escalate to another reviewer.
- Gate 1 is failing or the plan is still being written — fix the plan first.
- You are asked to implement, plan or run acceptance verification — those belong to Dev, Planner
  and QA.
- The review would require editing the artifact to make it pass. Report findings instead.

## Review modes

| Mode | Review object | Primary question |
| :--- | :--- | :--- |
| **Plan / Gate 2** | `.specs/` + `tasks/<task-id>/01-contract.md` | Is the plan truthful, complete and ADR-compliant? |
| **Change / code** | diff/commit + contract + test evidence | Does the change satisfy the contract without scope, safety or quality regressions? |

Choose one mode per review; do not mix a plan review with code review in one verdict.

## Arbitration mode

Use this mode only when a Dev files an Appeal Request against a `REWORK_REQUIRED` verdict. Work as
the independent third layer, not as a second QA and not as the Dev's helper: arbitrate from the
contract, the spec anchor, QA failure evidence and the appeal, and return exactly one decision —
`CODE_BUG` (to Dev), `TEST_BUG` (to QA) or `SPEC_AMBIGUITY` (to the Planner/human) — with evidence
line numbers. Read [`references/arbitration.md`](references/arbitration.md) for inputs, independence
and the decision table. Arbitration never edits any file.

## Inputs

**Plan review**

- PRD (`.specs/01-prd.md` / `.specs/01-prd/`), ADRs (`.specs/adr/`), tech spec
  (`.specs/02-tech-spec.md` / `.specs/02-tech-spec/`).
- Every `tasks/<task-id>/01-contract.md` and the Gate 1 result.

**Change review**

- The contract (`01`), the diff/commit, `02-dev-workspace.md` evidence, and the acceptance/test
  result.
- The repository standards and ADRs the change must honor.

## Outputs

- A findings list with severity, evidence (file/line or diff hunk) and the required action.
- Exactly one verdict: `PASS`, `REQUEST CHANGES` or `BLOCKED`.
- No edits to any artifact. Review notes go in the review response, not in the task documents.

## Workflow

1. **Check independence.** Confirm you did not author the artifact. If you did, stop and hand the
   review to another reviewer.
2. **Pick the mode.** Plan review runs after Gate 1. Change review runs on a concrete diff and its
   evidence; do not review an unbuilt plan as code.
3. **Read upstream first.** For plan review, read PRD/ADR/spec before the contracts. For change
   review, read the contract and the diff before judging style.
4. **Apply the checklist.** Plan review: completeness, zero hallucination, ADR compliance, contract
   quality. Change review: contract alignment, scope, correctness, tests/edge cases, security,
   maintainability. Use [`references/plan-review.md`](references/plan-review.md) and
   [`references/code-review.md`](references/code-review.md).
5. **Classify findings.** `blocker` (cannot proceed), `major` (must fix before merge/handoff),
   `minor` (should fix), `nit` (optional). Every finding needs evidence and a concrete action.
6. **Issue one verdict.** `PASS` only when the checklist was actually exercised and no blocker/major
   remains. `REQUEST CHANGES` for fixable findings. `BLOCKED` when inputs are missing or the
   reviewer cannot be independent.
7. **Hand off.** Plan findings go to the Planner; change findings go to Dev (and QA if verification
   is affected). Do not edit on their behalf.

## Plan review essentials (Gate 2)

- **Completeness**: every requirement, state transition, API, entity and invariant maps to a task.
- **Zero hallucination**: every task entity/field/endpoint/error code traces to upstream text; no
  template examples (cart, order, payment, coupon, `tenant_id`, etc.) unless the PRD defines them.
- **ADR compliance**: no task contradicts an inherited ADR.
- **Contract quality**: `task_id` matches the directory, `touch_files` is 1–3, DoD commands and edge
  cases are concrete, dependencies are acyclic.
- Gate 1 must pass before Gate 2; never sign off a plan that Gate 1 rejected.

## Change review essentials

- **Contract alignment**: the diff implements what `01` declares; every changed path is in
  `touch_files`; no scope creep.
- **Correctness and edge cases**: behavior matches the contract; the declared edge cases are handled.
- **Tests/evidence**: tests exist and pass; the evidence in `02` is real (command + result), not a claim.
- **Security and safety**: no secrets, injection, unsafe deserialization, missing authorization or
  unintended data exposure.
- **Maintainability**: follows repository standards; avoid stylistic nits unless the repo enforces them.

## Must not

- Edit the artifact, the contract, tests, source or `04-process.md`.
- Weaken, skip or bypass Gate 1, or sign off while Gate 1 is failing.
- Rewrite a contract to make it pass, or accept "done" without evidence.
- Review your own work or issue a verdict after only skimming.

## Handoff

- Plan review: `PASS` allows implementation; `REQUEST CHANGES` returns the task set to the Planner.
- Change review: `PASS` allows merge/QA handoff; `REQUEST CHANGES` returns the diff to Dev.
- `BLOCKED` means missing inputs or independence; state exactly what is missing.

## References

- [`references/plan-review.md`](references/plan-review.md) — Gate 2 checklist and output format.
- [`references/code-review.md`](references/code-review.md) — change/code review checklist.
- [`references/arbitration.md`](references/arbitration.md) — appeal arbitration: inputs, independence
  rules and the `CODE_BUG | TEST_BUG | SPEC_AMBIGUITY` decision table.
- [`references/role-boundaries.md`](references/role-boundaries.md) — read-only invariants and the
  honest enforcement model (bundled; no external files needed).
- Planning gate: the `plan-linter` skill when installed; its Gate 2 fallback checklist is also
  bundled here as `references/plan-review.md`.
- Repository rules: read `AGENTS.md` and any role-rules files when the adopting project defines
  them; they may add requirements but are not required for this skill.

## Honest limits

Semantic review is prompt-driven, not automated. It can miss issues and cannot guarantee security.
Gate 1 remains the deterministic structural gate; QA remains the independent execution/verification
gate. This skill provides a third, read-only judgment layer.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
