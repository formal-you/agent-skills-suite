# Reviewer Role Boundaries (bundled)

The `review` skill is self-contained: everything it needs lives in this skill directory. If the
adopting repository defines agent rules (`AGENTS.md`, a role-rules directory, or an equivalent
mechanism), read and follow them when present; they can add repository-specific requirements but
they are not required for this skill to work.

## Write scope

None. The reviewer is read-only and never edits the artifact under review.

## Read-only

Everything, especially `.specs/`, `tasks/`, `src/` and `tests/`.

## Invariants

- Independence: never review your own work; escalate when independence is impossible.
- Gate 1 must pass before a Gate 2 verdict; Gate 2 and change review are prompt-driven, not
  automated gates.
- Build a bidirectional traceability check: every requirement/API/invariant maps to a task, and every
  task points back to a spec anchor and at least one ADR.
- Check completeness, zero hallucination and ADR alignment; report findings with task IDs, file/field
  evidence and one verdict.
- Never edit artifacts, weaken or bypass Gate 1, or rewrite a contract to make it pass.

## Enforcement honesty

Prompt rules are advisory. Where the repository has CI (for example a git-based role audit) or
branch protection, that is the authoritative layer; this skill cannot enforce role isolation.
