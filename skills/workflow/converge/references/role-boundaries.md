# Converge Role Boundaries (bundled)

The `converge` skill is self-contained: everything it needs lives in this skill directory. If the
adopting repository defines agent rules (`AGENTS.md`, a role-rules directory, or an equivalent
mechanism), read and follow them when present; they can add repository-specific requirements but
they are not required for this skill to work.

Converge is tooling plus the Planner/Lead who runs it after verification; it is not a free-form
editing role.

## Write scope

- `.specs/02-tech-spec.md` — append-only "Converged changes" entries.
- `.specs/changes/<change-id>/convergence.md` — convergence record for a change proposal.
- `tasks/<task-id>/04-process.md` — event/status updates written by the tool.
- `tasks/archive/<task-id>/` — archived task bundles (moves, never deletes).

## Read-only

`01-contract.md`, `02-dev-workspace.md`, `03-qa-verification.md`, source code and tests.

## Invariants

- Run only after `QA_PASSED`; refuse when the QA verdict is missing or rework is active.
- Refuse a blank or missing `Implementation deviations` table; never fabricate deviation rows.
- Never rewrite existing spec prose: append a new entry with a marker and spec fingerprint.
- Structural deviations (new module, new boundary, ADR-level decision) escalate to the
  `spec-generator` skill; never converge them silently.
- A second run on an already converged bundle is a no-op.

## Enforcement honesty

Dev writes the deviation table; converge reads it and writes the spec/archive. Prompt rules are
advisory. Where the repository has CI (for example a git-based role audit) or branch protection,
that is the authoritative layer; the bundled helper is an optional deterministic assistant, never a
permission grant.
