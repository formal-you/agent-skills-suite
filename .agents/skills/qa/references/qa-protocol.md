# QA Protocol — Independent Verification

This reference expands the QA workflow in `SKILL.md`. It assumes the task bundle format
`tasks/<task-id>/` and QA-owned acceptance tests.

## 1. Handoff gate

QA starts only when `02-dev-workspace.md` contains:

```markdown
- [x] WAITING_FOR_QA
```

Also confirm the handoff commit in `02` exists, and `01-contract.md` is unchanged since planning
(spot-check the contract/diff). If the marker or commit is missing, return the task with the exact
gap rather than signing off.

## 2. Test design (before reading the implementation)

QA focuses on **local development stage testing**, authoring independent tests before PR submission:

### 2.1 Integration Testing
Verify interactions across internal module boundaries, shared services, and interface contracts. Integration tests ensure modules collaborate correctly when combined:
- Focus on inter-module contracts, state transitions, and boundary data flow.
- Place integration test suites under `tests/integration/` (or the project's declared integration test directory).
- Execute with real or stubbed dependencies as appropriate for local execution.

### 2.2 BDD-Driven End-to-End (E2E) Testing
Read the contract's DoD, `edge_cases`, `touch_files` and Section 4 BDD behavioral scenarios. Then design independent black-box acceptance and E2E tests before inspecting the implementation code:

| Case | Purpose | Example |
| :--- | :--- | :--- |
| Normal path | Required behavior works | valid input returns the documented result |
| Boundary / invalid | Bad input is rejected correctly | empty, null, oversized, wrong type |
| Duplicate / replay | Idempotency/consistency | repeated request does not create duplicates |
| Authorization / security | Access control | unauthorized actor is denied, no leakage |

Each case gets a stable ID (`TC-01`…), a Gherkin Given-When-Then scenario, an expected observable result, and status. Author acceptance tests under `tests/acceptance/`.

#### Open-Source BDD Frameworks per Stack
QA must author and execute acceptance tests using well-known, idiomatic open-source BDD tools tailored to the repository ecosystem:
- **Python**: `pytest-bdd` (`pytest tests/acceptance/`), `behave` (`behave tests/acceptance/features/`)
- **JavaScript / TypeScript**: `Cucumber.js` (`npx cucumber-js tests/acceptance/features/*.feature`), `playwright-bdd`, `jest-cucumber`
- **Go**: `Godog` (`godog run tests/acceptance/features/`)
- **Java**: `Cucumber-JVM` (`mvn test -Dcucumber.filter.tags="@acceptance"`), `JBehave`
- **Rust**: `cucumber-rs` (`cargo test --test cucumber`)
- **C# / .NET**: `Reqnroll`, `SpecFlow` (`dotnet test --filter Category=Acceptance`)

## 3. Complexity, static code analysis, and basis path testing

### 3.1 Static Code Analysis & Linting
QA inspects changed files using stack-appropriate static analysis and linting tools to catch style violations, syntax errors, and potential bugs:
- **Python**: `flake8`, `ruff`, or `pylint`
- **JavaScript / TypeScript**: `eslint`, `biome`
- **Go**: `golangci-lint`
- **Java**: `checkstyle`, `spotbugs`
- **Rust**: `cargo clippy`

Flag any syntax or lint violations. Code with unaddressed lint errors must not be approved.

### 3.2 McCabe Cyclomatic Complexity V(G)

Basis path testing is a structured verification technique based on the control flow graph (CFG) of the code under test. For every function modified in `touch_files`, QA must audit cyclomatic complexity and ensure basis path test coverage.

Cyclomatic complexity measures the number of linearly independent paths through a program module:

- **Graph definition**: $V(G) = E - N + 2P$, where $E$ is the number of edges, $N$ is the number of nodes, and $P$ is the number of connected components ($P = 1$ for a single function, yielding $V(G) = E - N + 2$).
- **Decision predicate definition**: $V(G) = D + 1$, where $D$ is the count of binary decision/predicate nodes (e.g., `if`, `while`, `for`, `case`/`switch`, `except`, `&&`, `||`, conditional ternary operators).

Thresholds for modified functions:
- **Standard ($V(G) \le 10$, V(G) <= 10)**: Target complexity; straightforward control flow with standard testability.
- **Warning ($11 \le V(G) \le 15$, 11 <= V(G) <= 15)**: High complexity; acceptable only if Dev documents architectural justification in `02-dev-workspace.md` and QA maps test cases for all independent paths.
- **Critical ($V(G) > 15$, V(G) > 15)**: Prohibited; untestable complexity. QA must reject with `REWORK_REQUIRED` requiring Dev to refactor (e.g. Extract Method, Strategy Pattern, Guard Clauses).

Open-source complexity tools per stack:
- **Universal Multi-Language Engine**: `tree-sitter` (https://github.com/tree-sitter/tree-sitter) via CST decision point node analysis; `lizard` (multi-language McCabe analyzer supporting 15+ languages)
- **Python**: `tree-sitter`, `lizard`, `radon cc`
- **JavaScript / TypeScript**: `tree-sitter`, `eslint` (complexity rule), `lizard`
- **Go**: `tree-sitter`, `gocyclo`, `gocognit`, `lizard`
- **Java**: `tree-sitter`, `pmd` (CyclomaticComplexity rule), `lizard`
- **Rust**: `tree-sitter`, `cargo clippy -- -D clippy::cognitive_complexity`, `lizard`
- **C / C++**: `tree-sitter`, `lizard`

### 3.3 Independent Path Definition

An **independent path** is defined as:
> A path through the control flow graph that introduces at least one new edge that has not been traversed by any prior test path.

In a program with cyclomatic complexity $V(G)$, a set of $V(G)$ independent paths forms a basis set. Any conceivable execution path through the module can be represented as a linear combination of paths in this basis set.

### 3.4 Basis Path Testing Baseline Rule

For every function modified in `touch_files`, QA must design at least $V(G)$ independent basis path test cases:

$$\text{Test Cases} \ge V(G)$$

- **Basis Path Testing Baseline Rule**: For every function modified in `touch_files`, QA must design at least $V(G)$ independent basis path test cases: Test Cases >= V(G).
- **100% Basis Path Coverage Requirement**: 100% basis path coverage across all functions modified in `touch_files` is mandatory before issuing a `QA_PASSED` verdict. Every independent path in the basis set must map to at least one test case ID in Section 3 of `03-qa-verification.md`.
- **Deficit Handling**: If test cases $< V(G)$ or an independent path is omitted, QA must design additional test cases. If a path is untestable due to unreachable code or hidden coupling, QA must reject with `REWORK_REQUIRED`.

### 3.5 Autonomous Code Review Invocation
QA may autonomously decide to invoke the `review` skill to assess code readability, maintainability, formatting, and adherence to clean code standards before issuing a final verdict. If the review identifies readability blockers or maintainability regressions, QA includes these findings in `03-qa-verification.md` and requests rework.

## 4. Mutation testing and test efficacy audit

Mutation testing evaluates the fault-detection efficacy of acceptance test suites by introducing deliberate syntactic modifications (mutants) into the production code under test (`touch_files`) and verifying whether the test suite detects and fails on (kills) each modification. While basis path testing ensures structural control-flow coverage, mutation testing ensures assertion quality, eliminating weak assertions and false-positive test passes.

### 4.1 Mutation Score Indicator (MSI) Formula and Thresholds

The Mutation Score Indicator (MSI) quantifies the percentage of non-equivalent mutants killed by the test suite:

$$\text{MSI} = \frac{\text{Killed} + \text{TimedOut}}{\text{Total} - \text{Equivalent}} \times 100\%$$

Plain-text representation:
```text
MSI = ((Killed + Timeout) / (Total - Equivalent)) * 100%
```

Where:
- **Total**: Total count of syntactically valid mutants generated for `touch_files`.
- **Killed**: Mutants detected by failing tests (assertion failures, exceptions, or non-zero exit codes).
- **TimedOut**: Mutants causing test execution timeouts (e.g. infinite loops or deadlocks induced by the mutation; counted as killed because altered behavior was caught).
- **Equivalent**: Mutants that are syntactically distinct but semantically identical to original code (cannot be killed by any test suite; excluded from effective denominator).
- **Survived**: Mutants that ran to completion with all tests passing (green), exposing assertion voids or missing test scenarios. Note invariant: $\text{Total} = \text{Killed} + \text{TimedOut} + \text{Equivalent} + \text{Survived}$.
- **Boundary Handling**: If $\text{Total} - \text{Equivalent} \le 0$, MSI is defined as 100.0% if Survived == 0, else 0.0%.

#### Strict Gating Thresholds
- **Standard modules**: $\text{MSI} \ge 80\%$. An MSI below 80% indicates unacceptably weak test assertions and blocks approval.
- **Core modules** (authentication, authorization, payment, cryptography, data consistency/financial state): $\text{MSI} \ge 90\%$. In addition, zero critical business logic mutants may survive regardless of overall score.
- **Gating rule**: If $\text{MSI} < 80\%$ (or $< 90\%$ for core modules) or any critical mutant survives, QA must NOT issue a `QA_PASSED` verdict; QA must issue `REWORK_REQUIRED` and document the surviving mutants.

### 4.2 6-Step Mutation Testing Standard Process

QA executes mutation testing following a structured 6-step cycle:

1. **Step 1: Baseline Pass (Baseline Verification)**:
   Run the acceptance test suite against untouched source code. Verify all tests pass cleanly (green, exit code 0). Never introduce mutations against a broken or flaky test baseline. If baseline fails, resolve test environment failures or escalate to Dev before mutating.

2. **Step 2: Mutation Generation**:
   Generate mutants across all files listed in `01-contract.md` -> `touch_files`. Systematically apply five core mutation operator categories:
   - *Conditional / Relational Boundaries*: Replace `>=` with `>`, `<=` with `<`, `>` with `>=`, `<` with `<=`.
   - *Condition Negation / Boolean Inversion*: Invert boolean predicates (`if cond` -> `if not cond`, `and` -> `or`, `True` -> `False`, `==` -> `!=`).
   - *Arithmetic / Mathematical Operators*: Alter math expressions (`+` to `-`, `*` to `/`, `a + b` to `a - b`).
   - *Return Value Substitution*: Mutate return values (replace valid returns with `None`, `null`, `0`, empty collections `[]`/`{}`, or inverted boolean values).
   - *Void / Side-Effect Call Omission*: Omit critical non-returning calls (e.g., omit authorization checks, audit logging, state cache invalidation, or database commit).

3. **Step 3: Mutation Execution**:
   Execute the test suite against each generated mutant in isolation (separate test process or sandbox). Record the execution status, output, and duration for each mutant. Enforce a per-mutant timeout (typically $2\times$ baseline test duration) to intercept infinite loops.

4. **Step 4: Classification (Kill Efficacy Analysis)**:
   Classify each executed mutant into one of four states:
   - **Killed**: At least one test assertion failed or raised an unexpected exception.
   - **Survived**: All tests passed without error. The mutant escaped detection.
   - **Timed Out**: Execution exceeded time threshold. Mutated control flow trapped.
   - **Incompetent / Equivalent**: Mutant failed to compile/load, or verified as semantically equivalent to original source.

5. **Step 5: Weak Assertion Elimination**:
   Deeply investigate all survived mutants. Identify weak assertions, missing boundary checks, or false positives:
   - *Status-Only Checks*: Tests verifying HTTP 200 or return codes without inspecting payload fields, response schema, or data integrity.
   - *Loose Existence Checks*: Tests using `assert "key" in res` instead of asserting exact expected key values and types.
   - *Missing Mock Verifications*: Tests asserting mock return values without verifying that expected methods were called with proper arguments.
   - *Omitted Negative / Exception Branches*: Tests not asserting specific error types or exception messages when invalid inputs are provided.
   Strengthen existing assertions and author targeted black-box test cases until every non-equivalent survived mutant is killed.

6. **Step 6: MSI Evidence Signoff (Audit Report & Threshold Gating)**:
   Compute the final MSI score using the standard formula. Document the mutation tool, mutant counts (Total, Killed, Survived, Timeout, Equivalent), and computed MSI in Section 4 of `03-qa-verification.md`. Verify MSI meets the applicable threshold ($\ge 80\%$ standard, $\ge 90\%$ core).

### 4.3 Weak Assertion and False Positive Elimination Patterns

Survived mutants indicate test blindness. QA must reinforce test assertions using these patterns:

| Weak Assertion Anti-Pattern | Blindness Mechanism | Reinforced Strong Assertion Pattern |
| :--- | :--- | :--- |
| **Status Code Only** (`assert res.status_code == 200`) | Ignores payload corruption, missing fields, or unauthorized data leakage | Validate payload schema, expected IDs, state transitions, and business values: `assert res.status_code == 200 and res.json()["role"] == expected_role` |
| **Loose Containment** (`assert "user" in res`) | Passes even if user object is empty, null, or wrong account | Assert field values and sub-structures: `assert res["user"]["id"] == expected_id and res["user"]["is_active"] is True` |
| **Unchecked Mock Invocations** (`mock_fn.return_value = ...`) | Succeeded without verifying if critical downstream call occurred | Verify exact call count and arguments: `mock_fn.assert_called_once_with(expected_arg)` |
| **Unbounded Exception Catching** (`except Exception: pass`) | Catches unexpected crash mutants without verifying error classification | Assert exact exception class and message: `pytest.raises(AuthExpiredError, match="Token expired")` |
| **Tautological / Shallow Checks** (`assert res is not None`) | Passes on corrupt or dummy objects | Validate functional invariants and business constraints |

### 4.4 Multi-Stack Open-Source Mutation Tool Integration Patterns

QA must execute mutation testing using well-known, authoritative open-source mutation frameworks across `touch_files`. Open-source tools provide deterministic mutant operators and reproducible kill metrics:

- **Python**: `mutmut` (`mutmut run --paths-to-mutate <touch_files> && mutmut results`), `cosmic-ray`
- **JavaScript / TypeScript**: `Stryker` (`npx stryker run --mutate '<touch_files>'`)
- **Go**: `go-mutesting` (`go-mutesting <touch_files>`)
- **Java**: `PITest` (`mvn org.pitest:pitest-maven:mutationCoverage -DtargetClasses=...`)
- **Rust**: `cargo-mutants` (`cargo mutants -f <touch_files>`)
- **C / C++**: `Mull` (`mull-runner`)
- **C# / .NET**: `Stryker.NET` (`dotnet stryker --mutate '<touch_files>'`)

### 4.5 Synthetic Mutation Disaster Fallback Procedure

The synthetic mutation procedure is strictly an exceptional disaster fallback reserved exclusively for niche, legacy, or unmaintained stacks where no viable open-source mutation framework exists. For all standard ecosystems, open-source mutation tooling is mandatory. When fallback is invoked:

1. Select at least five distinct, representative mutation injection sites across the CFG of functions modified in `touch_files`.
2. Apply the five core mutation operators manually in sandbox branches:
   - Relational operator inversion (`>` to `<=`, `==` to `!=`).
   - Boundary shift (`+1` to `+0`, `0` to `1`).
   - Logical condition inversion (`and` to `or`, boolean flip).
   - Return value corruption (`return result` to `return None` / `return {}`).
   - Statement deletion (omitting authorization check or state mutation call).
3. Execute the acceptance test suite against each synthetic mutant.
4. Verify that each mutant causes at least one test failure (killed). If any mutant survives, reinforce assertions until killed.
5. Record the synthetic mutant locations, operators, results, and calculated MSI in `03-qa-verification.md`.

## 5. Evidence

For every run record:

- exact command;
- environment/commit;
- total / passed / failed counts;
- failure output or traces (complete, not paraphrased);
- coverage if the project reports it;
- mutation testing tool / engine, mutant counts (Total, Killed, Survived, Timeout, Equivalent), and computed MSI (%).

A verdict without a command and result is not evidence. If a test cannot run, say why and do not
treat it as passed.

## 6. Anti-cheat / blast-radius audit

- Every changed path is in `01` → `touch_files` (use `git diff --name-only <base>...HEAD`).
- Dev did not modify `tests/acceptance/` or `01-contract.md`.
- The implementation honors `adherence_adrs`; note any deviation as a finding.
- No out-of-scope generated files, lockfile churn or dependency changes beyond the contract.
- Every modified function satisfies cyclomatic complexity limits ($V(G) \le 10$, or documented warning waiver for $11-15$; $V(G) > 15$ rejected).
- Basis path test baseline rule ($\text{Test Cases} \ge V(G)$) is satisfied with 100% basis path coverage.
- Mutation testing audit is complete with $\text{MSI} \ge 80\%$ ($\ge 90\%$ for core modules), and zero critical business logic mutants surviving.

## 7. Verdict

Exactly one marker:

- `- [x] QA_PASSED` — every test passes, 100% basis path coverage ($\text{Test Cases} \ge V(G)$) is achieved for all modified functions in `touch_files`, Mutation Score Indicator satisfies threshold ($\text{MSI} \ge 80\%$, $\ge 90\%$ for core modules), evidence is recorded, audit is clean.
- `- [x] REWORK_REQUIRED` — at least one failure, basis path coverage deficit ($\text{Test Cases} < V(G)$), cyclomatic complexity violation ($V(G) > 15$), mutation score deficit ($\text{MSI} < 80\%$, or $< 90\%$ for core modules), survived critical logic mutants, or audit violation; include complete traces and the expected fix.

Never tick both, never leave both empty. Record the attempt/round and timestamp so the history is
reproducible.

## 8. Rework loop

Keep prior attempts and evidence. On the next handoff:

1. update attempt metadata;
2. re-run the full matrix (not only the previously failing case);
3. re-audit complexity, basis path coverage, and mutation score (MSI);
4. issue a fresh verdict.

Repeated rework is a planning/scope signal. Escalate with evidence instead of lowering the bar or
editing source to make tests pass.

## 9. `04-process.md`

Derived output only. Optional tooling reacts to the checked verdict:

| Checked marker | Event code | Status | Lock holder | Retry |
| :--- | :--- | :--- | :--- | :--- |
| `WAITING_FOR_QA` (02) | `HANDOFF_QA_REQUESTED` | `VERIFYING` | `QAAgent` | unchanged |
| `QA_PASSED` | `TASK_TERMINATED_DONE` | `DONE` | `None` | unchanged |
| `REWORK_REQUIRED` | `REWORK_TRIGGERED` | `REWORKING` | `DevAgent` | +1, capped |

Never hand-edit `04`. Without tooling, rely on git/CI and the checked box.
