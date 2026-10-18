# PRD: {{PROJECT_TITLE}}

> Status: {{DOCUMENT_STATUS}} · Version: {{VERSION}} · Domain: {{DOMAIN}} · Author: {{AUTHOR}}

<!--
AUTHORING CONTRACT (replace this comment after authoring)
- Derive every statement from the user's request. This file is a shape, not content:
  do not copy examples from this template or from other domains.
- Replace every {{UPPER_SNAKE}} placeholder. Do not leave placeholders or TBDs behind.
- Keep the identifiers: REQ-### functional requirements, CON-### constraints,
  NFR-### non-functional targets, FORK-### architectural unknowns.
- Give every functional requirement a unique kebab-case anchor: #sec-<module-slug>.
- Outputs: .specs/01-prd.md (this aggregate) and .specs/01-prd/ (modular copy).
-->

## 1. Executive summary and goals

{{EXECUTIVE_SUMMARY}}

- **Problem**: {{CORE_PROBLEM}}
- **Outcomes and measures**: {{SUCCESS_METRICS}}
- **Target users / personas**: {{TARGET_PERSONAS}}

## 2. Functional requirements (REQ)

### REQ-001: {{FEATURE_NAME_1}}

- **Scope**: {{FEATURE_SCOPE_1}}
- **Rules and validation**: {{VALIDATION_RULES_1}}
- **State transitions**: {{STATE_TRANSITIONS_1}}
- **Acceptance criteria**: {{ACCEPTANCE_CRITERIA_1}}
- **Anchor**: #sec-{{MODULE_SLUG_1}}

### REQ-002: {{FEATURE_NAME_2}}

- **Scope**: {{FEATURE_SCOPE_2}}
- **Rules and validation**: {{VALIDATION_RULES_2}}
- **State transitions**: {{STATE_TRANSITIONS_2}}
- **Acceptance criteria**: {{ACCEPTANCE_CRITERIA_2}}
- **Anchor**: #sec-{{MODULE_SLUG_2}}

## 3. Business constraints (CON)

- **CON-001 ({{CONSTRAINT_TITLE_1}})**: {{CONSTRAINT_STATEMENT_1}}
  - **Impact**: {{CONSTRAINT_IMPACT_1}}
  - **Source / basis**: {{CONSTRAINT_SOURCE_1}}
- **CON-002 ({{CONSTRAINT_TITLE_2}})**: {{CONSTRAINT_STATEMENT_2}}
  - **Impact**: {{CONSTRAINT_IMPACT_2}}
  - **Source / basis**: {{CONSTRAINT_SOURCE_2}}

## 4. Non-functional requirements (NFR)

<!-- Checklist, not recommended values. Derive every target from the user's context
     and state how it will be verified. -->

- **NFR-001 (Throughput / scale)**: {{NFR_THROUGHPUT_TARGET}}
  - **Verification**: {{NFR_THROUGHPUT_VERIFICATION}}
- **NFR-002 (Latency)**: {{NFR_LATENCY_TARGET}}
  - **Verification**: {{NFR_LATENCY_VERIFICATION}}
- **NFR-003 (Availability)**: {{NFR_AVAILABILITY_TARGET}}
  - **Verification**: {{NFR_AVAILABILITY_VERIFICATION}}
- **NFR-004 (Durability / recovery)**: {{NFR_DURABILITY_TARGET}}
  - **Verification**: {{NFR_DURABILITY_VERIFICATION}}

## 5. Architectural unknowns and forks (FORK)

<!-- Keep only forks that genuinely need a decision downstream. Remove this section
     entirely when there are none. Do not pre-select an option here. -->

### FORK-001: {{FORK_TITLE_1}}

- **Context**: {{FORK_CONTEXT_1}}
- **Candidate options**:
  - {{OPTION_1A_NAME}}: {{OPTION_1A_DESCRIPTION}}
  - {{OPTION_1B_NAME}}: {{OPTION_1B_DESCRIPTION}}
- **Decision drivers**: {{DECISION_DRIVERS_1}}

### FORK-002: {{FORK_TITLE_2}}

- **Context**: {{FORK_CONTEXT_2}}
- **Candidate options**:
  - {{OPTION_2A_NAME}}: {{OPTION_2A_DESCRIPTION}}
  - {{OPTION_2B_NAME}}: {{OPTION_2B_DESCRIPTION}}
- **Decision drivers**: {{DECISION_DRIVERS_2}}

## 6. Open questions

- {{OPEN_QUESTION_1}}
- {{OPEN_QUESTION_2}}
