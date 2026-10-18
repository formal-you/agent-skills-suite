# Task Decomposition Rules

Detailed guidance for `task-decomposition`. The skill's `SKILL.md` is the entry point; this file
expands the rules that are easy to get wrong.

## 1. Goldilocks slicing

Defaults are configurable; the values below are the repository defaults, not universal constants.

| Dimension | Default | Override |
| :--- | :--- | :--- |
| Touched files (`touch_files`) | 1–3 | linter config `max_touch_files` |
| Estimated net diff lines (`estimated_lines`) | 50–250 | linter config `min_diff_lines` / `max_diff_lines` |
| Edge/negative assertions in `dod.edge_cases` | at least 2 structured Given-When-Then strings | linter config `min_edge_cases` |
| Required documents | `02`, `03`, `04` | linter config `require_docs` |
| Forbidden touch prefixes | `tests/acceptance/` | linter config `forbidden_touch_prefixes` |

If a slice exceeds the maximum, split it. If it falls below the minimum, merge it with a neighboring
slice. A repository may use different numbers; read the linter config before judging.

## 2. Vertical slices

Each task must deliver a complete, independently verifiable behavior: input, processing, output, and
the observable result QA can assert. Reject horizontal work such as "create DTOs", "create tables
only", or "add an empty endpoint". A vertical slice may still be small; size and completeness are
different axes. Each vertical slice should deliver testable BDD behavioral scenarios that can be
executed and asserted end-to-end.

## 3. Traceability

- `origin_spec_anchor` points at the `#sec-*` section of the tech spec / PRD that this task
  implements. It must match `#sec-[a-z0-9-]+` and must be a real anchor in the upstream document.
- `adherence_adrs` lists every ADR this task must honor, for example `["ADR-001", "ADR-003"]`. A task
  that knowingly violates an ADR is invalid; raise it with the architect instead.
- Do not invent anchors or ADR IDs. If the anchor does not exist, fix the upstream document first.

## 4. Contract frontmatter is authoritative

The human-readable sections are a convenience for reviewers. When they disagree with the frontmatter,
the frontmatter wins and the human section must be corrected. Required keys and types are listed in
`SKILL.md`. Additional project-specific keys may be added, but they must not contradict the required
ones.

Instantiation rules:

1. `task_id` equals the task directory name (for example `task-001-auth`).
2. Replace every placeholder token; an instantiated `01`/`02`/`03` contains none.
3. Keep `dependencies: []` for no dependencies; otherwise list existing task IDs only.
4. `touch_files` paths are repo-relative, forward slashes, 1–3 entries.
5. `dod` commands must be executable as written and must be the same commands recorded in `02`.
6. `dod.edge_cases` entries must be structured Given-When-Then strings: `"Given [precondition], When [action], Then [outcome]"`.

## 5. BDD executable specifications and Given-When-Then derivation

Tasks are defined as executable specifications (living documentation) using Behavior-Driven
Development (BDD) conventions. Planners must translate upstream requirements into unambiguous,
verifiable behaviors using the domain's ubiquitous language.

### Deriving Given-When-Then scenarios from PRD and Tech Spec

Derive concrete scenarios directly from upstream artifacts without inventing behavior:

1. **Happy path & core capabilities** (from PRD Functional Requirements `Acceptance criteria` and `Scope`):
   - **Given**: authorized actor and prerequisite system state (e.g., active account, initialized session).
   - **When**: the primary action, event, or input trigger occurs (e.g., login credentials submitted).
   - **Then**: the observable result, returned response, and persisted state change (e.g., session token issued, HTTP 200).
2. **Validation & boundary edge cases** (from PRD `Rules and validation` and Tech Spec `API contracts`):
   - **Given**: malformed, missing, boundary (min/max length or value), or unauthorized input data.
   - **When**: the request is processed.
   - **Then**: the request is rejected with specific domain error codes/status (e.g., HTTP 400 Bad Request, field error message) without persisting corrupted state.
3. **State transitions & lifecycle** (from PRD `State transitions` and Tech Spec `System invariants`):
   - **Given**: an entity in a specific lifecycle state (e.g., `PENDING_REVIEW`).
   - **When**: a lifecycle transition trigger occurs (e.g., `APPROVE` vs `REJECT`).
   - **Then**: the entity moves to the valid target state (`APPROVED`), audit logs/events are produced, and invalid transitions (e.g., editing after approval) are strictly blocked.
4. **Idempotency & consistency** (from Tech Spec `Core system invariants` and ADRs):
   - **Given**: an already processed transaction or repeated request with the same idempotency key.
   - **When**: the identical operation is retried.
   - **Then**: the original result is returned with zero duplicated side-effects, charges, or database records.

### Structuring `dod.edge_cases` in `01-contract.md`

Frontmatter `dod.edge_cases` mandates at least two concrete edge/negative scenarios.
Each entry must be a single structured string adhering to the format:

`"Given [precondition], When [action/trigger], Then [observable outcome]"`

Examples of valid edge-case specifications:
- `"Given an expired session token, When accessing a protected endpoint, Then return 401 Unauthorized"`
- `"Given an input payload exceeding the 10KB size limit, When submitted to ingest endpoint, Then reject with 413 Payload Too Large"`
- `"Given a duplicate transaction reference, When payment is submitted, Then return existing transaction without re-charging"`

Reject vague, unstructured assertions such as `"handles errors"`, `"invalid inputs fail"`, or
`"test edge cases"`.

### Authoring Section 4: Behavioral Contract and Invariants

Section 4 of `01-contract.md` formalizes the contract into executable Gherkin feature scenarios:
- **Scenario 1 (Input validation)**: Given-When-Then specifying boundary limits and payload rejection.
- **Scenario 2 (State transitions)**: Given-When-Then defining valid transitions and terminal state locks.
- **Scenario 3 (Idempotency and consistency)**: Given-When-Then defining concurrency and replay protection.

These scenarios define the exact contract implemented by Dev and asserted independently by QA in
`03-qa-verification.md` and `tests/acceptance/`.

## 6. Anti-hallucination and template neutrality

Templates are structural skeletons, not domain answers. Never copy example entities, infrastructure
choices or thresholds from a template into a task unless the upstream spec explicitly selects them.
If a field is unknown at planning time, record an open question in the contract's notes; do not fill
it with a plausible-sounding guess. Reject any task that introduces a requirement, table, endpoint or
invariant that is absent from the PRD / ADR / tech spec.

## 7. Handoff and audit trail

- Leave `02` and `03` as blank scaffolds; Dev and QA own them after planning.
- `04-process.md` is derived output. Repository tooling may append event rows from checked handoff
  boxes; agents never edit the file. The authoritative audit is git history plus CI.
- If a task must be reworked, update `01-contract.md` only when the scope itself changes; a purely
  implementation-level fix belongs to Dev/QA and does not require a new contract.

## 8. Validation checklist (manual fallback)

Run this when the optional `plan-linter` Gate 1 is unavailable:

1. Every task directory contains all four documents with the expected names.
2. Every `01-contract.md` has parseable YAML frontmatter with all required keys.
3. `task_id` equals the directory name and appears once across the task set.
4. Each `touch_files` list has 1–3 entries and avoids the configured forbidden prefixes.
5. `estimated_lines` is inside the configured range.
6. `origin_spec_anchor` is a real `#sec-*` anchor; `adherence_adrs` is non-empty.
7. `dod` has type-check, lint, test-file and at least two concrete edge cases in Given-When-Then format.
8. The dependency graph is acyclic: no cycles and no dependency on a missing task ID.
9. No unresolved placeholder tokens remain in `01`/`02`/`03`.

Gate 2 (semantic anti-hallucination review) is a prompt-only reviewer pass, not an automated gate.
