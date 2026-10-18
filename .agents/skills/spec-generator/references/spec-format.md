# Tech Spec Artifact Contract

The spec has an aggregate document, a modular bundle, and one ADR per decision. The
aggregate is authoritative.

| Path | Authoritative | Contents |
| :--- | :--- | :--- |
| `.specs/02-tech-spec.md` | yes | Complete technical specification |
| `.specs/02-tech-spec/README.md` | no | Bundle index and anchor map |
| `.specs/02-tech-spec/01-topology.md` | no | Topology and component responsibilities |
| `.specs/02-tech-spec/02-database-schema.sql` | no | Data model and illustrative DDL |
| `.specs/02-tech-spec/03-api-contracts.ts` | no | Illustrative API contract |
| `.specs/02-tech-spec/04-system-invariants.md` | no | Invariants and enforcement |
| `.specs/adr/NNN-title.md` | yes | One ADR per accepted decision |

## Required content in the aggregate spec

- Architecture overview and non-functional targets (`NFR-###`, with verification).
- Topology (Mermaid) and a component responsibility table.
- At least one unique `#sec-*` anchor; reuse PRD anchors and do not invent new ones for
  existing modules.
- Invariants (`INV-###`) with an enforcement mechanism, not a wish.
- Traceability: every component, table, interface and invariant maps to a REQ or an ADR.
- Open technical questions, explicitly listed.

## ADR contract

Every ADR contains these sections in this order (the linter checks them):

1. `## Status`
2. `## Context and problem statement`
3. `## Considered options`
4. `## Decision`
5. `## Consequences`

Record rejected options and the accepted trade-offs. Do not write an ADR that hides its
cost.

## Mermaid rules

- Fence each diagram with ```mermaid ... ``` and make sure the closing fence exists.
- Keep brackets balanced; avoid parentheses inside unquoted node labels.
- Use only node types and syntax supported by the target Mermaid version.
- The topology must match the component table.

## Data model and API guidance

- Include a data model only if the design persists data; include API contracts only if it
  exposes an interface. Otherwise remove those sections and say why.
- The provided `.sql` and `.ts` files are illustrative shapes. The database engine,
  contract language and transport are project-specific; adapt them.
- Do not present a tenant/scope column, framework or protocol as a universal default.
  Add it only when the requirements call for it.

## Placeholders and links

- Replace every `{{UPPER_SNAKE}}` placeholder; no `[TBD]` or `TODO` remains.
- Every relative link resolves.
- The aggregate and the bundle stay consistent.

## Gate

- Manual: use the checklist in `SKILL.md`.
- Script: `python scripts/lint_spec.py .specs` and fix all errors.
