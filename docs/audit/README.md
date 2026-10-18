# Skill Suite v2 — Audit Archive

> **Date**: 2026-10-18  
> **Scope**: `.agents/skills` (prd-generator, spec-generator, task-decomposition, plan-linter, and the
> platform helper diagnose-windows-sandbox-acl), `.agents/rules`, `.agents/scripts`,
> `.agents/hooks.json`, and the optional `prd_generator` / `spec_generator` engines.  
> **Question**: can this suite be shipped as a general-purpose, reusable Agent Skill set?

## Verdict

The suite was a coherent **Antigravity/repository-bound pipeline**, not a portable skill set:
self-containment, physical RBAC, the event-bus audit trail, and several Gate 1 rules were claimed but
not true. The strongest asset was the design discipline (agent does judgment, scripts check structure);
that discipline was kept and the couplings were removed.

| Audit line | Findings | Archived report |
| :--- | :--- | :--- |
| Script forensics (24 linter cases, 27 RBAC payloads, 11 event-bus experiments) | 2 blockers / 7 high / 5 medium / 2 low | [01-script-forensics.md](01-script-forensics.md) |
| Content consistency (claims-vs-artifacts matrix) | 5 blockers / 12 high / 12 medium / 6 low | [02-content-consistency.md](02-content-consistency.md) |
| Generality & portability (public Agent Skills spec) | 11 ranked couplings; keep/split/vendor/delete verdicts | [03-generality-review.md](03-generality-review.md) |

Key confirmed blockers at audit time:

1. Hooks invoked non-existent paths and DSH does not load `hooks.json`; `AGY_AGENT_ROLE` was never set.
2. `04-process.template.md` pre-contained the logger's idempotency markers, so the audit trail never
   started; `[x]` tokens in unchecked boxes could fabricate handoff/DONE events.
3. "100% self-contained" was false: `run.py` imported repository packages through `parents[4]`.
4. Gate 1 ignored 6 of its documented rules, was language-bound to Chinese labels, and could be
   bypassed through dependency formatting.
5. Templates hard-coded infrastructure/domain choices (Postgres/Redis/Kafka/tenant/TS) and shipped
   fake event rows and timestamps.

## Remediation (shipped)

The v2 implementation merged as commits `67ad35b` (skill rewrite) and `951885a` (merge to
`develop`/`master`). Current behavior is defined by:

- [`docs/skills-v2-spec.md`](../skills-v2-spec.md) — layout, contract frontmatter, linter/hook/RBAC interfaces.
- [`docs/skills-compatibility.md`](../skills-compatibility.md) — harness discovery, installation, L0–L3 enforcement.
- [`docs/agent-rules.md`](../agent-rules.md) — role write scopes and the honest enforcement model.
- [`.agents/skills/README.md`](../../.agents/skills/README.md) — skill index and quality gates.

Verification after the rewrite: 416 unit tests, 109 E2E tests, 108 skill-specific tests, and 21/21
end-to-end acceptance checks (relocation, Gate 1, event bus, RBAC, dedupe, badge).

## Evidence

The audit runs were reproduced by temporary scripts and fixtures. The scripts are not committed;
the captured outputs that back the reports are archived here:

- [plan-linter-evidence.txt](evidence/plan-linter-evidence.txt) — 24 Gate 1 cases.
- [rbac-evidence.txt](evidence/rbac-evidence.txt) — 27 RBAC payloads and role combinations.
- [event-bus-evidence.txt](evidence/event-bus-evidence.txt) — 11 event-bus experiments.
- [portability-cli-evidence.txt](evidence/portability-cli-evidence.txt) — relocation and CLI matrix.

Each report also contains the exact command used for its key findings, so the probes can be recreated.

## Notes on the archive

- Reports are preserved verbatim from the audit phase (including their original `artifacts/skill-audit/...`
  path references); those probe directories were temporary and are not part of the repository.
- The fifth skill, `diagnose-windows-sandbox-acl`, is a Windows/DSH platform helper, not part of the
  PRD→spec→tasks pipeline; it remains a local, untracked skill unless separately adopted.
- The external references consulted during the generality audit (agentskills.io, Codex, Claude Code,
  Antigravity) are cited inside [03-generality-review.md](03-generality-review.md) and were not
  re-distributed here.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
