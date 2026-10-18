# Change / Code Review Checklist

This review judges a concrete diff against the contract and repository standards. It is not a
substitute for QA's independent acceptance verification.

## Inputs

- `tasks/<task-id>/01-contract.md` (contract, DoD, touch_files, ADRs).
- The diff/commit under review.
- `02-dev-workspace.md` evidence (commands, results, edge-case notes).
- Test results and repository standards.

## Checklist

### Contract and scope

- [ ] The diff implements the contract; no undeclared feature.
- [ ] Every changed path is in `touch_files`; no scope creep.
- [ ] No edits to tests, contract, other role documents or `04-process.md`.

### Correctness and edge cases

- [ ] Behavior matches the contract and its state transitions.
- [ ] Every `dod.edge_cases` item is handled and covered by a test.
- [ ] Error paths return the documented error codes/behavior.
- [ ] Concurrency/idempotency/replay concerns from the contract are addressed.

### Tests and evidence

- [ ] Tests exist for the change and run green.
- [ ] The evidence in `02` is a real command + result, not a claim.
- [ ] No test weakening, skip or deletion to make the suite pass.

### Security and safety

- [ ] No secrets, credentials or tokens in the diff.
- [ ] Input validation/authorization is present where the contract requires it.
- [ ] No injection, unsafe deserialization, path traversal or unintended data exposure.
- [ ] Logging does not leak sensitive data.

### Maintainability

- [ ] Follows repository conventions; no dead code or debug artifacts.
- [ ] Public behavior is documented where the repo requires it.
- [ ] Dependencies/lockfile changes are justified by the contract.
- [ ] Style nits are reported as `nit`, not blockers, unless the repo enforces them.

## Verdict

- `PASS` — no blocker/major findings; can merge/hand off to QA.
- `REQUEST CHANGES` — fixable findings; list them with severity/evidence/action.
- `BLOCKED` — missing diff/evidence/contract, or reviewer cannot be independent.

## Rules

- Do not edit the code or tests; report findings.
- Do not review your own change.
- Do not approve on the basis of "tests pass" alone; check scope and edge cases.
