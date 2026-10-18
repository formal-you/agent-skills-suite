# Gate 2 plan review (prompt only)

Gate 2 is a semantic review performed by a reviewer that did not write the plan.
It is **not automated** and there is no script for it. Gate 1 (plan_linter.py)
answers "is the bundle structurally valid?"; Gate 2 answers "is the bundle
truthful to the upstream specification?".

Run Gate 2 after Gate 1 exits 0 and before implementation starts.

## Machine-assisted pre-checks (optional)

When a spec and a git repository are available, ask Gate 1 for the heuristics that do
not require judgement. They narrow the manual review; they do not replace it.

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes \
  --coverage-out artifacts/coverage.json --json
```

- `coverage.uncovered` lists spec anchors no contract references: the starting point
  for forward completeness. A section may legitimately be covered by an existing
  implementation, so confirm before reporting an omission.
- `ANCHOR_NOT_IN_SPEC` and `TOUCH_FILE_MISSING` warnings list anchors and paths the
  contract claims but the repository does not have: the starting point for reverse
  anti-hallucination. A missing `create` target is expected before implementation; a
  missing `modify` target usually means the planner invented the path.
- `--strict-topology`, `--strict-anchor` and `--require-full-coverage` turn these into
  Gate 1 failures for CI. Do not enable them on repositories where the coverage
  matrix is not maintained.

Record in the Gate 2 report which heuristics were available. "Not run" is an honest
result; claiming a heuristic pass that never executed is not.

## Inputs

- the reviewed PRD (.specs/01-prd.md and .specs/01-prd/)
- the reviewed tech spec (.specs/02-tech-spec.md and .specs/02-tech-spec/)
- the ADRs (.specs/adr/)
- every tasks/<task-id>/01-contract.md

## Review principles

### 1. Forward completeness

Extract every requirement, state transition, API contract, data entity and
invariant from the upstream documents. For each one, confirm that some task
contract declares it in dod, touch scope or prose. Report anything that no task
covers as an omission. Also check ordering: dependencies must exist and must run
before the task that needs them.

### 2. Reverse anti-hallucination and anti-contamination

For every entity, field, endpoint, error code and state machine in the task
contracts, locate the upstream sentence that authorises it. Report anything that
cannot be located, including:

- example entities copied from templates (a cart, payment, coupon, order or any
  domain object that the upstream documents never mention);
- made-up field names, error codes or numeric limits;
- infrastructure choices the ADRs did not decide;
- numbered requirements invented to fill a gap.

A single invented entity is a Gate 2 failure.

### 3. ADR compliance

Read every ADR listed under adherence_adrs and compare the contract with its
decision. Report any implementation hint that contradicts an ADR (for example,
an ADR that mandates a shared transactional store while the task proposes a
process-local in-memory map).

## Output

Pass:

```text
Gate 2 Plan Review Passed: 0 omissions, 0 hallucinations
```

Fail (list every finding):

```text
Gate 2 Plan Review Failed
- task-id: <omission | hallucination | adr-violation>
  field: <contract field or section>
  evidence: <upstream file and line, or "no upstream reference">
  action: <what the planner must change>
```

Do not write "passed" if any principle was not actually exercised. If the
upstream documents are unavailable, report Gate 2 as not run instead of passing
it.

## Offline fallback

When Python is unavailable, Gate 1 can be reviewed manually using the table in
SKILL.md: for every task bundle, check task_id vs directory name, touch_files
count and prefixes, estimated_lines, origin_spec_anchor, adherence_adrs, the
three dod commands, edge case count, required documents and the dependency graph.
The result is a manual review, not a script result; say so explicitly.
