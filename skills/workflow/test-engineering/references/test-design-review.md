# Test-Design Review — Independent Checklist

Review **how a task's tests are designed**, not whether the task passes. This is an independent,
read-only design review: it produces findings and a design-quality marker. It is not acceptance,
never issues `QA_PASSED` or `REWORK_REQUIRED`, and never replaces QA execution or a CI gate.

## Inputs

- The task contract: scope, acceptance criteria, edge cases, and traceability anchors.
- The upstream technical spec and decisions the behavior must honor.
- The proposed test design: test matrix, scenario list, technique rationale, data plan, and expected
  oracles.
- The existing test suites and their commands (read-only), for duplication and level fit.
- Defect history and the risk class assigned to this behavior.

## Independence rule

- You must not have authored the design, the implementation, or the acceptance tests under review.
- If you are not independent, stop and report that the review must be reassigned.
- Judge from the contract and evidence, not from a preference for a particular test style.

## 1. Contract traceability

- [ ] Every in-scope acceptance criterion maps to at least one planned test.
- [ ] Every declared edge case, boundary, replay/idempotency, and authorization case has a test.
- [ ] Tests are derived from the contract and spec, not reverse-engineered from the implementation.
- [ ] No test asserts behavior the contract does not define (invented requirements).
- [ ] Out-of-contract behavior is flagged as a gap or an explicit non-goal, not silently tested.

## 2. Risk coverage

- [ ] The design covers the assigned risk class at the expected depth.
- [ ] Critical risk has more than a happy-path test: negative, failure-path, and non-functional where
  relevant.
- [ ] High-risk interactions and data paths are exercised at the right level.
- [ ] Risk coverage is explicit (mapped risk to test), not implied by a test count.

## 3. Technique coverage

- [ ] Technique choice matches the input model: equivalence classes, boundaries, decision tables,
  state transitions, pairwise factors, or properties where appropriate.
- [ ] Each critical risk names the technique that covers it and the expected oracle.
- [ ] The design goes beyond example-based cases where the input space or state space is large.
- [ ] Property/invariant tests are present for algorithmic or data-integrity behavior when warranted.

## 4. Boundary and negative cases

- [ ] Empty, null, minimum, maximum, and just-outside-range inputs are planned.
- [ ] Invalid types, malformed payloads, and unsupported operations are covered.
- [ ] Authorization and security negatives are covered for protected behavior.
- [ ] Error paths assert observable outcomes, not just that an exception was raised.

## 5. State, replay, and idempotency

- [ ] Lifecycle and status transitions, including illegal transitions, are covered.
- [ ] Replay, duplicate, and retry behavior is covered when the contract declares it.
- [ ] Partial failure and recovery behavior is covered for multi-step operations.
- [ ] Tests restore shared state so order and repetition cannot change results.

## 6. Contract and property coverage

- [ ] External interfaces are covered by contract tests when consumers depend on them.
- [ ] Both success and error shapes of the contract are asserted.
- [ ] Compatibility across declared versions or platforms is addressed when promised.
- [ ] Fakes and doubles at boundaries are validated against the real contract.

## 7. Determinism and data control

- [ ] Time, timezone, randomness, locale, and generated identifiers are controlled or injected.
- [ ] Data is isolated per test; no dependence on execution order or leftovers.
- [ ] External network or services are faked or explicitly pinned; no accidental live calls.
- [ ] Data is synthetic or masked; no real personal, secret, or regulated data appears.

## 8. Test-double policy

- [ ] The code under test is not mocked; only true boundaries are doubled.
- [ ] Doubles are the simplest form that works; fakes are preferred to deep mock chains.
- [ ] Assertions target contract-observable behavior, not private calls or internals.
- [ ] Mocks do not assert implementation details that a safe refactor would break.

## 9. Oracle strength

- [ ] Assertions check the meaningful result, not merely that no exception occurred.
- [ ] Exact expected values or invariants are asserted, not just truthiness.
- [ ] Failure messages identify the input and the expected versus actual outcome.
- [ ] The oracle would fail if the behavior were subtly wrong (no tautological assertions).

## 10. Test independence and isolation

- [ ] Each test can run alone and in any order.
- [ ] Tests do not depend on another test's side effects or shared mutable fixtures.
- [ ] Setup failures are distinguishable from assertion failures.
- [ ] Duplicate or redundant tests are identified rather than multiplied.

## 11. Flakiness resistance

- [ ] No fixed sleeps or retry-based synchronization; use events, polling with bounds, or fakes.
- [ ] No reliance on wall-clock timing, scheduling order, or network latency.
- [ ] Resource cleanup and bounded waits prevent leaked processes, ports, or files.
- [ ] The design states how historical flakiness will be detected and quarantined.

## 12. Evidence and provenance

- [ ] Each planned test states its command, expected result, and where evidence will be recorded.
- [ ] The design uses the project's declared test command and layout.
- [ ] Planned evidence is reproducible from a clean checkout, not from a local-only state.
- [ ] Artifacts needed for later audit (report, seed, environment) are identified.

## 13. Out-of-scope and no scope creep

- [ ] The design does not add tests for unrelated behavior or unrelated refactoring.
- [ ] No source, contract, or other role artifact is modified by the design.
- [ ] No gate, threshold, or verification standard is weakened to make the design pass.
- [ ] Missing or contradictory contract content is reported, not invented.

## Severity model

| Severity | Meaning | Effect on the marker |
| :--- | :--- | :--- |
| `blocker` | The design cannot validate the contract or would produce false confidence | `DESIGN_GAPS` |
| `major` | A required risk, technique, determinism, or oracle element is missing | `DESIGN_GAPS` |
| `minor` | Improves clarity, duplication, or maintainability without invalidating the design | Optional fix |
| `observation` | Informational note, alternative approach, or follow-up | None |

## Output format

```
# Test-Design Review — <task id or feature>
Scope: <what was reviewed>
Independence: confirmed (author of design/implementation: no)

## Findings
| ID | Severity | Location | Evidence | Required action | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TD-01 | major | <file/section> | <concrete gap> | <action> | <role> |

## Design marker
DESIGN_READY | DESIGN_GAPS
Rationale: <one or two sentences tied to the findings above>
```

Rules for the marker:

- `DESIGN_READY` only when no `blocker` or `major` finding remains and the checklist was exercised.
- `DESIGN_GAPS` when at least one `blocker` or `major` is open; list every one with evidence.
- Issue exactly one marker. It is a **test-design quality opinion**, not task acceptance, and it never
  replaces `QA_PASSED` or `REWORK_REQUIRED`.

## Handoff

- Design findings go to the test designer (typically QA for acceptance design, Dev for unit/integration
  design) and to the design owner.
- `DESIGN_READY` means the design may proceed to execution; QA still decides acceptance independently.
- `DESIGN_GAPS` returns the design for rework; it does not block the task by itself.
- This review never edits the design, the contract, tests, source, or verification artifacts.
