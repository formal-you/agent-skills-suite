# Plan Review (Gate 2) Checklist

Gate 2 answers: **is the task plan truthful to the upstream specification?** It runs only after
Gate 1 exits 0 and before implementation starts.

## Inputs

- PRD: `.specs/01-prd.md` and `.specs/01-prd/`.
- ADRs: `.specs/adr/*.md`.
- Tech spec: `.specs/02-tech-spec.md` and `.specs/02-tech-spec/`.
- Contracts: every `tasks/<task-id>/01-contract.md`.
- Gate 1 result.

## 1. Forward completeness

Extract every requirement, state transition, API contract, data entity and invariant from the
upstream documents. For each, confirm at least one task covers it (in `dod`, `touch_files` or the
readable contract). Report uncovered items as omissions. Check ordering: dependencies must exist and
precede the tasks that need them.

## 2. Reverse anti-hallucination / anti-contamination

For every entity, field, endpoint, error code and state in the contracts, find the upstream sentence
that authorizes it. Report anything that cannot be located, including:

- template examples copied into the plan (cart, order, payment, coupon, inventory, `tenant_id`, etc.);
- invented field names, error codes or numeric limits;
- infrastructure choices no ADR decided;
- requirements invented to fill a gap.

A single invented entity is a Gate 2 failure.

## 3. ADR compliance

Read every `adherence_adrs` entry and compare it with the contract/implementation hints. Report any
contradiction (for example, an ADR requiring a shared transactional store while a task proposes a
process-local map).

## 4. Contract quality

- `task_id` equals the directory name; IDs are unique.
- `touch_files` has 1–3 entries and avoids forbidden prefixes.
- `estimated_lines` is inside the configured range.
- `origin_spec_anchor` is a real `#sec-*`; `adherence_adrs` is non-empty.
- `dod` has type-check, lint, test file and at least two edge cases.
- The dependency graph is acyclic and has no dangling IDs.
- No unresolved placeholders in `01`/`02`/`03`.

## Output format

Pass:

```text
PASS — Gate 2 Passed: 0 omissions, 0 hallucinations, 0 ADR violations
```

Request changes:

```text
REQUEST CHANGES — Gate 2 Failed
- task-id: <omission | hallucination | adr-violation | contract-quality>
  severity: <blocker | major | minor | nit>
  field: <contract field or section>
  evidence: <upstream file/line, or "no upstream reference">
  action: <what the Planner must change>
```

Do not pass a principle you did not actually exercise. If the upstream documents are unavailable,
report Gate 2 as **BLOCKED**, not passed.
