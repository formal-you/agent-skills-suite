# QA Role Boundaries (bundled)

The `qa` skill is self-contained: everything it needs lives in this skill directory. If the
adopting repository defines agent rules (`AGENTS.md`, a role-rules directory, or an equivalent
mechanism), read and follow them when present; they can add repository-specific requirements but
they are not required for this skill to work.

## Write scope

- `tests/acceptance/**`
- `tasks/<task-id>/03-qa-verification.md`

## Read-only

- `src/**`, `01-contract.md`, `02-dev-workspace.md`, `04-process.md`

## Invariants

- Derive tests from `01-contract.md` and the technical spec, never from the implementation.
- Cover the contract's edge cases plus at least one adversarial or security case.
- Record the command, evidence, pass/fail counts and complete failure traces.
- Tick exactly one verdict: `QA_PASSED` when everything passes, `REWORK_REQUIRED` otherwise.
- Never edit production code or another role's document; never hand-edit `04-process.md`.
- If the repository CI derives roles from commit trailers, include `Agent-Role: qa` in the commit
  that records the verdict.

## Enforcement honesty

Prompt rules are advisory. Where the repository has CI (for example a git-based role audit) or
branch protection, that is the authoritative layer; this skill cannot enforce role isolation.
