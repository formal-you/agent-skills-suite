/**
 * Tech Spec: API contract example.
 * Project: {{PROJECT_TITLE}}
 * Version: {{VERSION}}
 *
 * ILLUSTRATIVE ONLY. The transport, resource names and contract language are
 * project-specific. Adapt this shape to the project's API conventions and include
 * only operations that appear in the PRD. Replace every {{UPPER_SNAKE}} placeholder.
 */

/** Standard error envelope. Rename fields to match the project's API conventions. */
export type ApiErrorResponse = {
  code: string;
  message: string;
  details?: Record<string, string>;
};

/**
 * Operation: {{OPERATION_NAME}}
 * Anchor: #sec-{{MODULE_SLUG_1}}
 * Traces to: REQ-001, {{RELATED_ADR}}
 */
export type {{OPERATION_NAME}}Request = {
  {{REQUEST_FIELD_1}}: {{REQUEST_FIELD_1_TYPE}};
  {{REQUEST_FIELD_2}}?: {{REQUEST_FIELD_2_TYPE}};
};

export type {{OPERATION_NAME}}Response = {
  {{RESPONSE_FIELD_1}}: {{RESPONSE_FIELD_1_TYPE}};
  {{RESPONSE_FIELD_2}}: {{RESPONSE_FIELD_2_TYPE}};
};

/**
 * Operation: {{SECOND_OPERATION_NAME}}
 * Anchor: #sec-{{MODULE_SLUG_2}}
 */
export type {{SECOND_OPERATION_NAME}}Request = {
  {{SECOND_REQUEST_FIELD_1}}: {{SECOND_REQUEST_FIELD_1_TYPE}};
};

export type {{SECOND_OPERATION_NAME}}Response = {
  {{SECOND_RESPONSE_FIELD_1}}: {{SECOND_RESPONSE_FIELD_1_TYPE}};
};
