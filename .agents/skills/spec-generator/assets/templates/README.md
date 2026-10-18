# Template Set: Spec Generator

These templates are the canonical shapes for the spec-generator skill. They are
assets, not output: scaffold.py copies every file whose name contains
``.template.``, strips that segment, and writes the result under `--out`.
`README.md` (this file) is a guide and is never copied.

## Files and destinations

| Template | Output | Notes |
| :--- | :--- | :--- |
| 02-tech-spec.template.md | 02-tech-spec.md | Aggregate spec |
| 02-tech-spec/README.template.md | 02-tech-spec/README.md | Bundle index |
| 02-tech-spec/01-topology.template.md | 02-tech-spec/01-topology.md | Topology + components |
| 02-tech-spec/02-database-schema.template.sql | 02-tech-spec/02-database-schema.sql | Illustrative DDL |
| 02-tech-spec/03-api-contracts.template.ts | 02-tech-spec/03-api-contracts.ts | Illustrative contract |
| 02-tech-spec/04-system-invariants.template.md | 02-tech-spec/04-system-invariants.md | Invariants |
| adr.template.md | (not copied) | ADRs are created per decision; the scaffold creates `adr/` only |

## Conventions

- Placeholders use `{{UPPER_SNAKE}}`; every placeholder must be replaced before the
  lint gate passes.
- Identifiers: `NFR-###`, `INV-###`, `#sec-<module-slug>`; anchors must be unique.
- Infrastructure values are placeholders, not recommendations. Do not keep a component,
  table or contract that the PRD/ADR does not require.
- Output paths follow the repository convention: `.specs/02-tech-spec.md`,
  `.specs/02-tech-spec/`, `.specs/adr/`.

## Ownership

Owned by the spec-generator skill. Do not duplicate these files elsewhere; the skill
directory is the single source of truth.
