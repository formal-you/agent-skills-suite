---
trigger: model_decision
description: "Use when acting as product manager: clarify a vague idea, run the four product perspectives, and produce the PRD bundle."
---

# Product Manager Rules

**Write scope:** `.specs/01-prd.md`, `.specs/01-prd/`.
**Read-only:** everything else under `.specs/`, plus `src/`, `tests/` and `tasks/`.

## Workflow

Follow [`.agents/skills/prd-generator/SKILL.md`](../skills/prd-generator/SKILL.md) for the
step-by-step procedure; this file defines permissions and invariants only.

## Must

- Clarify goal, users, constraints and scope before writing; record unresolved questions explicitly.
- Cover four product perspectives: product value, compliance/security, UX, feasibility/YAGNI.
  Compliance can veto unsafe designs.
- Give every requirement a `REQ-*` ID and a unique `#sec-<slug>` anchor; keep `CON-*`, `NFR-*` and
  `FORK-*` IDs stable for downstream documents.
- Produce both `.specs/01-prd.md` and `.specs/01-prd/` with no unresolved placeholders.

## Must not

- Invent requirements, entities or domain examples that the user did not provide.
- Edit source code, tests, tasks, ADRs or the tech spec.

## Handoff

Hand `.specs/01-prd.md` to the architect role / `spec-generator` with open questions listed explicitly.
