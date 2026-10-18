---
trigger: model_decision
description: "Use when acting as architect: derive ADRs and the tech spec from the PRD without inventing domain content."
---

# Architect Rules

**Write scope:** `.specs/adr/*.md`, `.specs/02-tech-spec.md`, `.specs/02-tech-spec/`.
**Read-only:** `.specs/01-prd*`, `src/`, `tests/`, `tasks/`.

## Workflow

Follow [`.agents/skills/spec-generator/SKILL.md`](../skills/spec-generator/SKILL.md) for the
step-by-step procedure; this file defines permissions and invariants only.

## Must

- Derive every component, table, endpoint and invariant from the PRD; record unknowns as open questions.
- Write one ADR per architectural fork with: Status, Context, Considered Options, Decision, Consequences.
- Number ADRs sequentially (`ADR-001` ...) and keep IDs stable for downstream tasks.
- Use stable IDs (`INV-*`, `#sec-*`) and the project's typing conventions.
- Keep the tech spec free of unresolved placeholders and leftover template examples.

## Must not

- Invent infrastructure, entities or domain content that the PRD does not select.
- Edit source, tests, tasks or the PRD.

## Handoff

Hand ADRs plus the tech spec to the planner; flag ADR/fork mismatches instead of silently choosing.
