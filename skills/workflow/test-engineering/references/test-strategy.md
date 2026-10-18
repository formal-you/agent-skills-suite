# Test Strategy — Template and Checklist

A test strategy is a durable, versioned agreement about **what the project tests, at which level,
with which technique, using which data and environments, and how it knows the result is trustworthy**.
It is global: it does not accept a task or replace per-task acceptance. Fill it from
`assets/templates/test-strategy.template.md` and keep it under change control.

## 1. Scope and context

- System under test: services, libraries, interfaces, data stores, and user journeys in scope.
- Explicitly out of scope: components, platforms, or risk classes this strategy does not cover.
- Supported stacks, versions, and the commands that build and run each suite.
- Constraints: compliance, data residency, environment availability, and time budget.
- Consumers of the strategy: QA, CI owners, Dev, planners, and reviewers.

## 2. Quality attributes

Name the attributes that matter and state how each is verified. An attribute with no verification
method is a wish, not a requirement.

| Attribute | Question it answers | Verification approach |
| :--- | :--- | :--- |
| Correctness | Does behavior match the contract? | Example-based and property-based tests at unit, contract, and acceptance levels |
| Reliability | Does it keep working under repeat, retry, and failure? | State-transition, idempotency, fault-injection, and recovery tests |
| Performance | Does it meet latency/throughput targets? | Load, stress, soak, and benchmark tests with declared thresholds |
| Security | Is access controlled and input handled safely? | Authorization matrix, boundary/invalid input, injection, and token handling tests |
| Compatibility | Do supported versions and consumers work? | Matrix tests across versions, platforms, and contract versions |
| Observability | Can failure be diagnosed from evidence? | Assertions on logs, metrics, traces, and error codes |
| Maintainability | Can tests be changed safely and quickly? | Design review of testability, duplication, and fixture ownership |

## 3. Risk matrix

Classify each behavior, interface, or component by likelihood and impact. Risk drives test depth; do
not treat every behavior identically.

| Risk class | Likelihood x impact | Minimum test depth | Gate behavior |
| :--- | :--- | :--- | :--- |
| Critical | High x High | Contract + acceptance + negative + failure-path + non-functional | Blocking; owner sign-off |
| High | High x Medium, Medium x High | Acceptance + boundary + one technique beyond examples | Blocking |
| Medium | Medium x Medium | Acceptance + representative boundaries | Blocking for declared scope |
| Low | Low x Low | Smoke or targeted examples | Advisory |

Template register:

| Risk ID | Behavior / interface | Likelihood | Impact | Class | Levels | Techniques | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R-01 | {{BEHAVIOR}} | {{LIKELIHOOD}} | {{IMPACT}} | {{CLASS}} | {{LEVELS}} | {{TECHNIQUES}} | {{OWNER}} |

## 4. Test levels

Pick a deliberate level mix, not a default pyramid. Record the isolation model and exit criteria for
each level.

| Level | Purpose | Scope and isolation | Typical owner | Exit criteria |
| :--- | :--- | :--- | :--- | :--- |
| Unit | Pin down logic and edge cases fast | In-process, no network, deterministic | Dev | Fast, isolated, no real I/O |
| Integration | Verify module/data-store interactions | Real or fake boundary dependencies | Dev and QA | Interaction and state behavior verified |
| Contract | Protect consumer/provider interfaces | Both sides checked against one contract | Dev and QA | Contract compatibility verified both ways |
| Acceptance | Verify the task/feature behavior from the outside | Black box, derived from the contract | QA | Declared scenarios and edge cases pass |
| End-to-end | Protect critical user journeys | Full stack, minimal isolation | QA and CI owners | Critical journeys pass reliably |

Guidance: prefer the lowest level that can detect the defect; use higher levels for journey risk, not
for logic that unit tests can cover; keep every level deterministic enough to be trusted on repeat.

## 5. Technique selection

Choose techniques from the input model and risk, not from habit. Every risk class above should map
to at least one technique beyond happy-path examples.

| Technique | Use when | Input model | Strong signal |
| :--- | :--- | :--- | :--- |
| Equivalence partitioning | Inputs have classes with identical expected behavior | Class boundaries | One case per class, including invalid classes |
| Boundary value analysis | Valid ranges or limits exist | Range edges and just outside | Off-by-one and limit defects |
| Decision table | Behavior depends on combinations of conditions | Condition/action matrix | Missing rule combinations |
| State transition | Lifecycle, status, or workflow behavior | States, events, transitions | Illegal transitions and stuck states |
| Pairwise / combinatorial | Many independent configuration factors | Factor/level model | Interaction defects without full product |
| Property-based | Invariants and algebraic laws hold | Generators plus properties | Counterexamples beyond hand-picked examples |
| Mutation-aided design | Assertions may be weak | Mutants over changed code | Weak or missing oracles |
| Fault injection | Failure and recovery behavior matters | Failure modes | Error handling and resilience gaps |
| Example-based / BDD | Contract scenarios are given as Given-When-Then | Scenario list | Traceability to the contract |

Mapping rule: state, for every critical risk, the technique that covers it and the observable oracle.

## 6. Test data policy

- Classify data: generated synthetic, curated fixtures, masked or anonymized copies, and golden files.
- Never use real personal, secret, or regulated production data; never commit secrets into fixtures.
- Generate data with a fixed seed; record the seed in the test output so failures reproduce.
- Isolate data per test; clean up, reset, or use unique namespaces; never depend on execution order.
- Version fixtures alongside the tests and assign an owner; delete unused fixtures.
- For large or combinatorial data, use generators rather than checked-in blobs.

## 7. Environment policy

- Declare environments: local, ephemeral CI, and shared integration; state parity and differences.
- Pin toolchain and runtime versions; install dependencies from a lockfile or image, not implicitly.
- Declare required external services and how they are provided (container, fake, or real endpoint).
- Make time, timezone, locale, random seed, and generated identifiers controllable and explicit.
- Block or fake outbound network by default in automated runs; opt in per test with a declared target.
- Record environment provenance (image/tag, commit, tool versions) in run output.

## 8. Test-double policy

| Double | Use for | Rule |
| :--- | :--- | :--- |
| Stub | Canned responses from an unowned boundary | Keep minimal; assert on the system, not the stub |
| Fake | A lightweight working implementation of a boundary | Preferred for data stores and services; verify the fake itself |
| Spy | Observing calls without replacing behavior | Use sparingly; avoid asserting private interactions |
| Mock | Verifying an interaction contract is unavoidable | Only at true boundaries; never mock the code under test |

- Prefer fakes and contract tests at external boundaries over deep mock chains.
- Never mock the unit under test, and never assert on implementation details that the contract does
  not require. A test that breaks on a safe refactor is a design defect.
- Validate that fakes/doubles stay faithful to the real behavior via contract tests.

## 9. Flakiness policy

- Definition: a test that produces different results on unchanged code and environment.
- Detect: repeated runs, order randomization, and historical flake reports; track flake rate per suite.
- Root-cause categories: time/timezone, randomness, shared state, test-order coupling, async/timing,
  network/external dependency, resource limits, and environment drift.
- Quarantine, do not ignore: label the flaky test, assign an owner, set an expiry (for example 14
  days), and keep it out of the blocking tier until fixed or deleted.
- Retries are diagnostic only; automatic retries must never silently convert a real failure into a
  pass. Report retried outcomes explicitly.
- Fix by removing the cause (inject a clock, seed randomness, isolate state); raising timeouts is not
  a fix. Re-enable only after repeated clean runs.

## 10. Automation and CI handoff

- Define tiers (fast, standard, extended) with time budgets and which tier blocks a merge.
- Make every automated command explicit and runnable non-interactively from a clean checkout.
- Tag tests by risk or level so CI can select a tier without editing test code.
- Define the artifacts each run must produce: test report, coverage, mutation report, logs, and
  environment provenance.
- Hand metric definitions and tier expectations to the CI owner; this strategy does not build or
  operate pipelines or gates.

## 11. Metrics and thresholds

Metrics are diagnostic signals used to steer design; never optimize a single number in isolation.

| Metric | Definition | Typical target | Caution |
| :--- | :--- | :--- | :--- |
| Mutation score | Killed plus timed-out mutants over all non-equivalent mutants | At or above the project threshold | Needs a real mutation tool and runtime budget |
| Statement/branch coverage | Executed lines/branches over total | Track trend, not a universal target | High coverage can coexist with weak oracles |
| Flake rate | Flaky test runs over total runs per period | Near zero, trending down | Measure on unchanged code |
| Defect escape rate | Defects found after the gate over all defects | Trending down | Requires honest incident labels |
| Time to feedback | Wall-clock time from push to green signal | Declared per tier | Do not trade determinism for speed |
| Risk coverage | Critical risks with at least one independent test | All critical risks covered | Requires the register to stay current |
| Test runtime | Duration per test and per suite | Declared per tier | Slow suites get skipped, which hides risk |

Thresholds used for blocking decisions belong to the QA/CI owners and their gates; this strategy
defines and hands over the definitions, not the enforcement.

## 12. Roles and RACI

| Activity | Test engineering | QA | Quality engineering | Dev | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Test strategy and standards | A/R | C | C | C | I |
| Risk register | A/R | C | I | C | I |
| Per-task acceptance and verdict | C | A/R | I | I | I |
| CI pipeline and gates | C | C | A/R | I | I |
| Test design review | A/R | C | I | C | I |
| Flakiness triage | C | R | C | R | I |
| Metrics definitions | A/R | C | C | I | I |
| Semantic plan/code review | I | C | I | I | A/R |

A = accountable, R = responsible, C = consulted, I = informed.

## 13. Adoption roadmap

1. **Baseline**: inventory suites, commands, runtime, flake data, and existing coverage. Do not
   change behavior yet.
2. **Risk register**: agree critical journeys and interfaces; classify risk with owners.
3. **Pilot**: apply the level mix and technique policy to one stack or service; measure runtime and
   signal quality.
4. **Ratify**: publish the strategy; agree metric definitions and tier expectations with QA and CI
   owners.
5. **Encode**: add review checklists and templates; wire tier selection into automation with the CI
   owner.
6. **Operate**: review flake rate, defect escapes, and runtime on a fixed cadence; revise the strategy
   with evidence; retire stale or duplicate tests.

## 14. Strategy completion checklist

- [ ] Scope, constraints, and supported stacks are explicit.
- [ ] Every quality attribute has a verification approach.
- [ ] The risk register covers critical journeys, interfaces, and components with owners.
- [ ] Each risk class maps to required levels and at least one design technique.
- [ ] Test-level isolation models and exit criteria are stated.
- [ ] Test data, environment, and test-double policies are actionable and enforceable by review.
- [ ] Flakiness detection, quarantine, ownership, and expiry are defined.
- [ ] Automation commands, tiers, and required artifacts are declared.
- [ ] Metrics have definitions, owners, and cautions; blocking thresholds are owned elsewhere.
- [ ] RACI and an adoption roadmap with dates and owners are present.
