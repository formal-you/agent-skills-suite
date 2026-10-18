# Tech Spec Bundle: {{PROJECT_TITLE}} - Index

> Version: {{VERSION}} · Status: {{DOCUMENT_STATUS}} · Sources: {{SOURCE_PRD_PATH}}

This directory is the modular form of .specs/02-tech-spec.md. The aggregate file is
authoritative; keep this bundle consistent with it.

## Modules

| File | Contents |
| :--- | :--- |
| [01-topology.md](./01-topology.md) | System topology and component responsibilities |
| [02-database-schema.sql](./02-database-schema.sql) | Data model and illustrative DDL (only if the design persists data) |
| [03-api-contracts.ts](./03-api-contracts.ts) | API contract example (language and transport are project-specific) |
| [04-system-invariants.md](./04-system-invariants.md) | System invariants and enforcement |

## Traceability anchors

| Anchor | Module | Requirement | Component |
| :--- | :--- | :--- | :--- |
| #sec-{{MODULE_SLUG_1}} | {{MODULE_NAME_1}} | REQ-001 | {{COMPONENT_1}} |
| #sec-{{MODULE_SLUG_2}} | {{MODULE_NAME_2}} | REQ-002 | {{COMPONENT_2}} |

## Decisions

Each accepted architectural fork becomes one ADR under .specs/adr/. The ADR is the
authoritative record of the decision; this spec describes the resulting design.
