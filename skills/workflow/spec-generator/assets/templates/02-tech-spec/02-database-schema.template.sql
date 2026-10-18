-- ============================================================================
-- Tech Spec: Data model and illustrative DDL
-- Project: {{PROJECT_TITLE}}
-- Target engine: {{DATABASE_ENGINE}}
-- ============================================================================
-- ILLUSTRATIVE ONLY. This file shows a shape, not a recommended schema or stack.
-- Adapt types, constraints and syntax to {{DATABASE_ENGINE}}, and include only
-- entities that appear in the PRD. Replace every {{UPPER_SNAKE}} placeholder.
-- Do not add columns or tables that the design does not require.
-- ============================================================================

-- Table: {{PRIMARY_TABLE_NAME}} (primary entity of {{MODULE_NAME_1}})
-- Anchor: #sec-{{MODULE_SLUG_1}}
CREATE TABLE {{PRIMARY_TABLE_NAME}} (
    {{PRIMARY_KEY_COLUMN}} {{PRIMARY_KEY_TYPE}} PRIMARY KEY,
    {{BUSINESS_KEY_COLUMN}} VARCHAR({{BUSINESS_KEY_LENGTH}}) NOT NULL UNIQUE,
    {{STATUS_COLUMN}} VARCHAR({{STATUS_LENGTH}}) NOT NULL,
    {{CREATED_AT_COLUMN}} TIMESTAMP NOT NULL,
    {{UPDATED_AT_COLUMN}} TIMESTAMP NOT NULL
);

CREATE INDEX idx_{{PRIMARY_TABLE_NAME}}_business_key
    ON {{PRIMARY_TABLE_NAME}} ({{BUSINESS_KEY_COLUMN}});

-- Table: {{SECONDARY_TABLE_NAME}} (related entity; remove if not needed)
-- Anchor: #sec-{{MODULE_SLUG_2}}
CREATE TABLE {{SECONDARY_TABLE_NAME}} (
    {{SECONDARY_KEY_COLUMN}} {{PRIMARY_KEY_TYPE}} PRIMARY KEY,
    {{PARENT_KEY_COLUMN}} {{PRIMARY_KEY_TYPE}} NOT NULL,
    {{SECONDARY_STATUS_COLUMN}} VARCHAR({{STATUS_LENGTH}}) NOT NULL,
    {{SECONDARY_CREATED_AT_COLUMN}} TIMESTAMP NOT NULL,
    FOREIGN KEY ({{PARENT_KEY_COLUMN}}) REFERENCES {{PRIMARY_TABLE_NAME}} ({{PRIMARY_KEY_COLUMN}})
);

-- Add further tables only when the PRD requires them (for example, an audit, idempotency
-- or history table). Keep every table traceable to a REQ-### or an ADR-###.
