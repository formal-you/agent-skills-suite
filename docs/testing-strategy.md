# Testing Strategy — Agent Skills Suite

> Status: seed strategy for this repository. It is written for the Agent Skills Suite itself and is
> the default strategy document consumed by the `qa`, `quality-engineering`, and `test-engineering`
> roles. Adopters replace this file with their own strategy; the role rule fixes the default location
> and may name an override path.

## 1. Purpose and scope

This strategy governs how the suite verifies **its own distributable assets**:

- skills under `.agents/skills/` and their byte-identical mirrors under `skills/workflow/`;
- task templates and task-bundle contracts under `.agents/skills/task-decomposition/assets/`;
- helper scripts bundled with skills and under `tools/`;
- unit and contract tests under `tests/`;
- documentation under `docs/` and the repository root;
- distribution metadata: `VERSION`, `CHANGELOG.md`, plugin and marketplace manifests.

The suite has **no product runtime**. It does not run a service, a database, or a user-facing
application, so acceptance and E2E levels apply to the assets above, not to product journeys. Where a
consumer repository runs the generated task bundles, per-task acceptance remains the `qa` role's job.

Out of scope: performance of adopting projects, the behavior of third-party CI runners, and the
correctness of skills after an adopter edits them.

## 2. Quality attributes

| Attribute | Question it answers | Verification approach |
| :--- | :--- | :--- |
| Correctness | Do scripts, gates, and templates do what their documents claim? | Unit tests plus fixture task bundles that must pass or fail exactly as specified |
| Verifiability | Can a claim be checked without trusting prose? | Deterministic scripts, JSON/exit-code evidence, hashes, and token scans |
| Determinism | Does the same input produce the same result on repeat? | Fixed seeds, temp directories, no network, stable ordering |
| Portability | Does the suite work across supported OSes and Python versions? | Path and encoding discipline plus a declared version matrix |
| Distribution integrity | Do the two skill trees and the manifests stay consistent? | Byte-level mirror checks and manifest-to-directory reconciliation |
| Documentation accuracy | Does documentation match shipped behavior? | Docs consistency tests that bind commands, counts, versions, and paths |
| Role isolation | Can one role change another role's artifacts undetected? | Path-based role audit and static checks in CI |
| Maintainability | Can tests be changed safely and cheaply? | Clear fixture helpers, no shared mutable state, bounded suite runtime |

## 3. Risk matrix

Risk classes follow the repository convention: Critical blocks; High and Medium block their declared
scope; Low is advisory.

| Risk ID | Risk | Likelihood | Impact | Class | Required verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R-01 | Gate 3 false pass: a forged or incomplete `03` is signed off | Medium | High | Critical | Negative gate tests with forged, missing, phantom, mismatched, and low-MSI evidence |
| R-02 | RBAC bypass: an agent edits outside its role scope and the gate stays green | Medium | High | Critical | Role-audit tests over synthetic diffs, including forbidden and allowed paths |
| R-03 | Mirror drift: `.agents/skills/` and `skills/workflow/` diverge | Medium | High | High | SHA-256 parity check over every mirrored file plus directory-set equality |
| R-04 | Plugin-manifest drift: manifests, skill directories, and counts disagree | Medium | Medium | High | Manifest parse plus reconciliation against skill directory names and versions |
| R-05 | Cross-platform and Python-version drift: path separators, encodings, and newer syntax break a supported runtime | Medium | Medium | High | Windows and POSIX path cases, UTF-8 fixtures, and a declared Python version matrix |
| R-06 | Docs drift: documentation promises behavior the code does not implement | High | Medium | High | Docs consistency tests for commands, error codes, counts, and links |
| R-07 | Unvalidated multi-language CI profiles: stack commands are asserted but never executed | Medium | High | High | Profile-shape tests plus at least one executable smoke fixture per shipped profile |

## 4. Test levels and responsibilities

| Level | Scope | Typical owner | Exit criteria |
| :--- | :--- | :--- | :--- |
| Unit | Individual scripts, linters, parsers, and templates | Dev | Fast, isolated, no network; assertions target outputs, exit codes, and messages |
| Distribution / contract | Plugin manifests, quickstart/install flow, skill-tree parity, JSON schemas, CLI contracts | Dev and QA | Manifests parse; declared files exist; mirrored trees are byte-identical; documented commands and exit codes match |
| Docs consistency | Headings, tokens, links, language rules, counts, and version references in documentation | Test engineering and QA | Every documented path resolves and every count matches the shipped inventory |
| CI smoke | Workflow template shape, Gate 1 and Gate 3 behavior on fixture bundles, mutation gate report handling | Quality engineering | Required jobs exist, fail-closed behavior is proven, and artifacts are declared |

Level selection rule: prefer the lowest level that can detect the defect; reserve CI smoke for wiring
and end-to-end gate behavior that unit tests cannot reach.

## 5. Test design techniques

| Technique | Use it for | Strong signal |
| :--- | :--- | :--- |
| Equivalence partitioning | Input classes with identical expected behavior (valid/invalid contracts, compliant/non-compliant tables) | One representative per class, including invalid classes |
| Boundary value analysis | Thresholds and limits (MSI at 79, 80, and 90; line counts at 199 and 200; path depth) | Off-by-one and threshold defects |
| Decision table | Combined conditions (verdict state x evidence shape x flags) | Missing rule combinations |
| State transition | Lifecycle and status markers (`WAITING_FOR_QA` to verdict) | Illegal transitions and stuck states |
| Pairwise / combinatorial | Independent configuration factors (OS x Python version x skill tree) | Interaction defects without a full product matrix |
| Property-based and mutation-aided | Parser and linter invariants; assertion strength | Counterexamples beyond hand-picked examples and weak oracles |

Every Critical risk must map to at least one technique beyond happy-path examples and to an observable
oracle.

## 6. Data and environment policy

- Use `tempfile` directories for every scaffolder, linter, and gate test; never write into the
  repository checkout during a test.
- Keep fixtures small, versioned under `tests/`, and owned by the test that uses them.
- Run with no network access; a test that needs network is a design defect unless it targets an
  explicitly declared external contract.
- Make randomness deterministic: seed generators and record the seed in failure output.
- Never commit secrets, tokens, personal data, or production data into fixtures.
- Clean up temporary state and assert that failed runs leave no artifacts behind.
- Pin the Python version floor in the test matrix and prefer standard-library APIs only.

## 7. Flakiness policy

- Definition: a test that yields different results on unchanged code and environment.
- Do not retry to green. A blind retry converts a real failure into a false pass.
- Diagnose by repeating the test (for example 20 runs), randomizing order, and checking time,
  timezone, locale, randomness, shared state, and filesystem ordering.
- If the cause is not fixed immediately, quarantine: label the test, name an owner, set an expiry
  (default 14 days), and keep it out of the blocking tier until it is repaired or deleted.
- Fix the cause, not the timeout. Re-enable only after repeated clean runs, and record the evidence.

## 8. Contract, property, and non-functional guidance

- Contract tests bind the JSON shape and exit codes of `plan_linter.py`, `verification_linter.py`,
  `complexity_check.py`, `mutation_gate.py`, and the distribution manifests. A schema change is a
  contract change and must update its test.
- Property tests cover invariants such as "unresolved placeholder tokens never appear in a shipped
  template", "every mirrored file has an identical digest", and "a compliant table is not failed by an
  unrelated empty table".
- Non-functional expectations: the unit suite stays under the declared runtime budget, tests run
  offline, output is deterministic, and failures identify the artifact path and the violated rule.
- Security expectations for the suite: role boundaries are enforced by path audits, and no test may
  weaken a gate to make itself pass.

## 9. Metrics and thresholds

| Metric | Definition | Use |
| :--- | :--- | :--- |
| Mirror parity | Fraction of mirrored files with matching SHA-256 | Must be 100%; any mismatch fails |
| Self-containment | Count of forbidden external path tokens in skill documents | Must be zero |
| Manifest parse success | Whether plugin, marketplace, and distribution manifests parse and reconcile | Must be 100% |
| Pass rate | Passed tests over executed tests on a clean checkout | Must be 100% in the blocking tier |
| Flake rate | Flaky runs over total runs per period | Target near zero and trending down |
| Escaped defect count | Defects found after a gate | Trending down; each one gets a regression test |

Coverage is a diagnostic signal, not a target. No threshold may be raised by lowering a gate, deleting
an assertion, or excluding a test from the blocking tier.

## 10. RACI

| Activity | Test engineering | QA | Quality engineering | Dev | Review | Planner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Test strategy and standards | A/R | C | C | C | I | C |
| Risk register and risk classes | A/R | C | I | C | I | C |
| Per-task acceptance and verdict | C | A/R | I | I | I | I |
| CI pipelines, gates, and environments | C | C | A/R | I | I | I |
| Unit and integration test implementation | C | C | I | A/R | I | I |
| Independent test-design review | A/R | C | I | C | I | I |
| Semantic plan and change review | I | I | I | C | A/R | I |
| Task slicing and acceptance criteria | I | C | I | I | I | A/R |

A = accountable, R = responsible, C = consulted, I = informed.

## 11. Review cadence, exceptions, and out of scope

- Review this strategy at least every quarter and whenever a skill, gate, supported stack, or
  distribution channel changes.
- The `test-engineering` role proposes revisions; QA and quality-engineering ratify changes that
  affect evidence or thresholds before they take effect.
- Exceptions are explicit, time-boxed waivers recorded with a risk owner, a rationale, an expiry, and
  the compensating check; an expired waiver fails review.
- Out of scope for this strategy: product runtime behavior of adopting repositories, third-party
  runner availability, and the internal design of skills after an adopter modifies them.
