# Topology: {{PROJECT_TITLE}}

> Module: 01-topology · Version: {{VERSION}}

<!--
Module contract: the topology must match the architecture review outcome and use only
components that exist in this design. Delete unused nodes instead of keeping examples.
-->

## 1. System topology

@`@@mermaid
flowchart TD
    User["{{ACTOR_NAME}}"]
    Entry["{{ENTRY_COMPONENT}}"]
    ServiceA["{{SERVICE_A_NAME}}"]
    Store["{{DATA_STORE_NAME}}"]
    User --> Entry
    Entry --> ServiceA
    ServiceA --> Store
@`@@

## 2. Components and responsibilities

| Component | Runtime | Responsibility | Trust boundary | Dependencies | Anchor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| {{COMPONENT_1_NAME}} | {{COMPONENT_1_RUNTIME}} | {{COMPONENT_1_RESPONSIBILITY}} | {{COMPONENT_1_TRUST_BOUNDARY}} | {{COMPONENT_1_DEPENDENCIES}} | #sec-{{MODULE_SLUG_1}} |
| {{COMPONENT_2_NAME}} | {{COMPONENT_2_RUNTIME}} | {{COMPONENT_2_RESPONSIBILITY}} | {{COMPONENT_2_TRUST_BOUNDARY}} | {{COMPONENT_2_DEPENDENCIES}} | #sec-{{MODULE_SLUG_2}} |

## 3. Why this shape

- **Constraints that shaped it**: {{TOPOLOGY_CONSTRAINTS}}
- **Alternatives rejected**: {{TOPOLOGY_REJECTED_ALTERNATIVES}}
- **Related decisions**: {{TOPOLOGY_ADR_REFERENCES}}
