# PRD Bundle: {{PROJECT_TITLE}} - Index

> Version: {{VERSION}} · Domain: {{DOMAIN}} · Status: {{DOCUMENT_STATUS}}

This directory is the modular form of .specs/01-prd.md. The aggregate file and this
bundle must stay consistent; when they differ, the aggregate file is authoritative.

## Modules

| File | Contents | Primary reader |
| :--- | :--- | :--- |
| [00-overview.md](./00-overview.md) | Problem, value, scope, milestones | Product owner |
| [01-features.md](./01-features.md) | Functional requirements (REQ-###, #sec-* anchors) | Architect / implementer |
| [02-constraints.md](./02-constraints.md) | Business constraints (CON-###) | Security / compliance |
| [03-nfr.md](./03-nfr.md) | Non-functional targets (NFR-###) | Performance / SRE |
| [04-forks.md](./04-forks.md) | Architectural unknowns (FORK-###) | spec-generator (ADR input) |

## Downstream

The spec-generator skill consumes the aggregate PRD (or this directory) and produces
.specs/adr/*.md plus .specs/02-tech-spec.md and .specs/02-tech-spec/. It treats every
#sec-* anchor and every FORK-* item as a contract.
