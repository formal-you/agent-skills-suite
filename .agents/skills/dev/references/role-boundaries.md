# Dev Role Boundaries (bundled)

The `dev` skill is self-contained: everything it needs lives in this skill directory. If the
adopting repository defines agent rules (`AGENTS.md`, a role-rules directory, or an equivalent
mechanism), read and follow them when present; they can add repository-specific requirements but
they are not required for this skill to work.

## Write scope

- `src/**`
- `tasks/<task-id>/02-dev-workspace.md`

## Read-only

- `01-contract.md`, `03-qa-verification.md`, `04-process.md`, `tests/acceptance/**`

## Invariants

- Read `01-contract.md` first and implement only what it declares.
- Stay inside the contract's `touch_files`; if a change outside them is required, stop and escalate.
- Run the contract's type check and lint, plus the project's existing tests. The acceptance target
  (`dod.test_file`) is QA-owned: run it only if it already exists, never author or edit it.
- Check `WAITING_FOR_QA` only when every self-verification item passes.
- Never hand-edit `04-process.md`.
- If the repository CI derives roles from commit trailers, include `Agent-Role: dev` in the commit
  that implements the task.

## Enforcement honesty

Prompt rules are advisory. Where the repository has CI (for example a git-based role audit) or
branch protection, that is the authoritative layer; this skill cannot enforce role isolation.
