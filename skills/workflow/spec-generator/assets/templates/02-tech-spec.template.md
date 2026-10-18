# Tech Spec: {{PROJECT_TITLE}}

> Status: {{DOCUMENT_STATUS}} · Version: {{VERSION}} · Sources: {{SOURCE_PRD_PATH}}

<!--
TECH SPEC CONTRACT (replace this comment after authoring)
- Derive every component, table, contract and invariant from the PRD and the accepted
  ADRs. This file is a shape, not content: do not import examples from other domains.
- The infrastructure shown below is illustrative placeholder structure only. It is not
  a recommended stack; choose components only if the PRD/ADR requires them, and remove
  the rest.
- Keep the modular copy in .specs/02-tech-spec/ consistent with this aggregate file.
- Reuse the PRD #sec-* anchors exactly; do not invent new anchors for existing modules.
- Every component, table and contract must trace to a REQ-### or an ADR-###.
-->

## 1. Architecture overview

{{ARCHITECTURE_SUMMARY}}

### Non-functional targets

| ID | Dimension | Target | Verification |
| :--- | :--- | :--- | :--- |
| NFR-001 | Throughput / scale | {{NFR_THROUGHPUT_TARGET}} | {{NFR_THROUGHPUT_VERIFICATION}} |
| NFR-002 | Latency | {{NFR_LATENCY_TARGET}} | {{NFR_LATENCY_VERIFICATION}} |
| NFR-003 | Availability | {{NFR_AVAILABILITY_TARGET}} | {{NFR_AVAILABILITY_VERIFICATION}} |
| NFR-004 | Durability / recovery | {{NFR_DURABILITY_TARGET}} | {{NFR_DURABILITY_VERIFICATION}} |

## 2. System topology

@`@@mermaid
flowchart TD
    User["{{ACTOR_NAME}}"]
    Entry["{{ENTRY_COMPONENT}}"]
    ServiceA["{{SERVICE_A_NAME}}"]
    ServiceB["{{SERVICE_B_NAME}}"]
    Store["{{DATA_STORE_NAME}}"]
    User --> Entry
    Entry --> ServiceA
    Entry --> ServiceB
    ServiceA --> Store
    ServiceB --> Store
@`@@

<!-- Delete components that do not exist in this design; rename placeholders to real
     component names from the architecture review. -->

## 3. Components and responsibilities

| Component | Runtime (if relevant) | Responsibility | Trust boundary | Dependencies | Anchor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| {{COMPONENT_1_NAME}} | {{COMPONENT_1_RUNTIME}} | {{COMPONENT_1_RESPONSIBILITY}} | {{COMPONENT_1_TRUST_BOUNDARY}} | {{COMPONENT_1_DEPENDENCIES}} | #sec-{{MODULE_SLUG_1}} |
| {{COMPONENT_2_NAME}} | {{COMPONENT_2_RUNTIME}} | {{COMPONENT_2_RESPONSIBILITY}} | {{COMPONENT_2_TRUST_BOUNDARY}} | {{COMPONENT_2_DEPENDENCIES}} | #sec-{{MODULE_SLUG_2}} |

## 4. Data model

<!-- Include this section only if the design persists data. The DDL in the modular
     file is illustrative: adapt column types and syntax to {{DATABASE_ENGINE}}. -->

- **Persistence choice and rationale**: {{PERSISTENCE_DECISION}}
- **Entities**: {{DATA_ENTITIES}}
- **Consistency and retention requirements**: {{DATA_CONSISTENCY_REQUIREMENTS}}

See [02-tech-spec/02-database-schema.sql](02-tech-spec/02-database-schema.sql).

## 5. API contracts

<!-- Include this section only if the design exposes an interface. The modular file is
     illustrative; the contract language and transport are project-specific. -->

- **Transport / protocol**: {{API_TRANSPORT}}
- **Authentication and authorization**: {{API_AUTH_MODEL}}
- **Error model**: {{API_ERROR_MODEL}}

See [02-tech-spec/03-api-contracts.ts](02-tech-spec/03-api-contracts.ts).

## 6. Core system invariants

| ID | Category | Invariant | Enforcement | Anchor |
| :--- | :--- | :--- | :--- | :--- |
| INV-001 | {{INVARIANT_1_CATEGORY}} | {{INVARIANT_1_STATEMENT}} | {{INVARIANT_1_ENFORCEMENT}} | #sec-{{MODULE_SLUG_1}} |
| INV-002 | {{INVARIANT_2_CATEGORY}} | {{INVARIANT_2_STATEMENT}} | {{INVARIANT_2_ENFORCEMENT}} | #sec-{{MODULE_SLUG_2}} |

## 7. Modular specification index

- [02-tech-spec/01-topology.md](02-tech-spec/01-topology.md)
- [02-tech-spec/02-database-schema.sql](02-tech-spec/02-database-schema.sql)
- [02-tech-spec/03-api-contracts.ts](02-tech-spec/03-api-contracts.ts)
- [02-tech-spec/04-system-invariants.md](02-tech-spec/04-system-invariants.md)

## 8. Open technical questions

- {{OPEN_TECHNICAL_QUESTION_1}}
