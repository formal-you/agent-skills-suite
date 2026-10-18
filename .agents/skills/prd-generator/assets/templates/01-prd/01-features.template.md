# PRD: {{PROJECT_TITLE}} - Functional Requirements

> Module: 01-features · Version: {{VERSION}}

<!--
Module contract: one block per functional requirement. Every REQ must trace back to
the user's request, carry a unique #sec-* anchor, and include acceptance criteria.
-->

## Functional requirements (REQ)

### REQ-001: {{FEATURE_NAME_1}}

- **Scope**: {{FEATURE_SCOPE_1}}
- **Category**: {{CATEGORY_1}}
- **Rules and validation**: {{VALIDATION_RULES_1}}
- **State transitions**: {{STATE_TRANSITIONS_1}}
- **Acceptance criteria**: {{ACCEPTANCE_CRITERIA_1}}
- **Anchor**: #sec-{{MODULE_SLUG_1}}

### REQ-002: {{FEATURE_NAME_2}}

- **Scope**: {{FEATURE_SCOPE_2}}
- **Category**: {{CATEGORY_2}}
- **Rules and validation**: {{VALIDATION_RULES_2}}
- **State transitions**: {{STATE_TRANSITIONS_2}}
- **Acceptance criteria**: {{ACCEPTANCE_CRITERIA_2}}
- **Anchor**: #sec-{{MODULE_SLUG_2}}

## Traceability

| Requirement | Anchor | Primary downstream consumer |
| :--- | :--- | :--- |
| REQ-001 | #sec-{{MODULE_SLUG_1}} | spec-generator |
| REQ-002 | #sec-{{MODULE_SLUG_2}} | spec-generator |
