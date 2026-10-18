# Arbitration — Independent Appeal Review

This reference defines the arbitration mode of the `review` skill. It is used only after a Dev files
an Appeal Request against a `REWORK_REQUIRED` verdict. Arbitration is the third layer after Gate 1
(deterministic) and QA verification (execution); it never replaces either of them and it adds no
runtime or tooling requirement.

## When arbitration applies

- `02-dev-workspace.md` Section 6 contains a completed `appeal` block.
- `03-qa-verification.md` records the `REWORK_REQUIRED` verdict and the failure evidence under dispute.
- The orchestrator routed the task to an independent reviewer instead of back to Dev.

Do not arbitrate without a concrete appeal and concrete failure evidence. A request for more
implementation work is a rework instruction, not an appeal.

## Inputs

Read the inputs in this order and record the line numbers you rely on:

1. `01-contract.md` — frontmatter (`touch_files`, `dod`, `origin_spec_anchor`, `adherence_adrs`), the
   behavioral scenarios in Section 4 and the optional `risk_level`.
2. The spec anchor named by the appeal — the referenced `.specs/02-tech-spec.md` section and any
   inherited ADR it points to.
3. `03-qa-verification.md` — the failing case, the command output and the verdict text that the
   appeal disputes.
4. `02-dev-workspace.md` Section 6 — `appeal_id`, `target_case`, `spec_anchor`, `reason`, `evidence`
   and `requested_verdict`.

The acceptance tests under `tests/acceptance/` are evidence only when they are quoted by path and
line. Do not read them as the source of truth; the contract and the spec anchor are.

## Independence rule

- Do not arbitrate your own work: you must not have authored the contract, the implementation, the
  tests, the `03` verdict or the appeal.
- Arbitrate once per appeal; do not discuss the outcome with Dev or QA before the decision is
  recorded.
- Stay read-only. Arbitration never edits `01`, `02`, `03`, `04`, tests, source or spec; it returns a
  decision and evidence to the orchestrator, which routes the next action.

## Decision table

Exactly one decision per appeal. `requested_verdict` is a claim, not a decision: verify it against
the contract and the spec anchor before accepting it.

| Decision | Evidence pattern | Meaning | Next owner |
| :--- | :--- | :--- | :--- |
| `CODE_BUG` | The spec/contract requires the behavior QA asserted, and the implementation or its evidence does not deliver it. | The implementation is wrong; the test is legitimate. | Dev |
| `TEST_BUG` | The test asserts behavior the contract/spec does not require, or the failure evidence is environmental rather than behavioral. | The test is wrong or over-specified; the implementation is legitimate. | QA |
| `SPEC_AMBIGUITY` | The contract and spec do not determine the expected behavior, contradict each other, or the needed anchor does not exist. | Requirements must be clarified before code or tests change. | Planner/human |

Reject an appeal that has no spec anchor and no evidence line: it is a preference, not a defect. When
the inputs are incomplete, choose `SPEC_AMBIGUITY` and list the missing input instead of inventing a
requirement.

## Required output

```
Decision: CODE_BUG | TEST_BUG | SPEC_AMBIGUITY
Evidence:
- <path>:<line> — <what this line requires or proves>
- <path>:<line> — <supporting or contradicting evidence>
Action: <one sentence for the next owner>
```

Every decision needs at least two evidence references with line numbers: one for the asserted
behavior and one for the failure or the gap. Keep the reasoning short enough to audit; do not
paraphrase a line when the exact text matters.

## Circuit break

Arbitration is not an infinite loop. If this is the second appeal on the same task, or the third
`REWORK_REQUIRED`, the orchestrator breaks the cycle to the Planner/human instead of scheduling
another arbitration round. Record that escalation as the decision context; do not arbitrate a fourth
round.
