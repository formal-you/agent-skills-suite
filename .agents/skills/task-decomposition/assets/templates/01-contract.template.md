---
# Task contract. This YAML frontmatter is the machine-readable, authoritative part of the contract.
# Fill every placeholder token before use. task_id MUST equal the task directory name.
# Paths are relative to the repository root and use forward slashes.
task_id: "{{TASK_ID}}"
title: "{{TASK_TITLE}}"
module: "{{MODULE_NAME}}"
risk_level: standard  # standard | core; optional, defaults to standard (core raises the MSI floor to 90%)
dependencies: []  # [] when there are no dependencies; otherwise e.g. [task-000-bootstrap]
estimated_lines: {{ESTIMATED_LINES}}
touch_files:
  - action: create  # create | modify
    path: "{{TOUCH_FILE_1}}"
  - action: modify  # create | modify
    path: "{{TOUCH_FILE_2}}"
origin_spec_anchor: "#sec-{{MODULE_SLUG}}"
adherence_adrs: ["{{ADR_ID_1}}"]  # at least one ADR; add more list items if needed
dod:
  type_check: "{{TYPE_CHECK_COMMAND}}"
  lint: "{{LINT_COMMAND}}"
  test_file: "{{TEST_FILE_PATH}}"  # BDD runner/test target executed for acceptance; never a .feature file
  feature_file: "{{FEATURE_FILE_PATH}}"  # required: Gherkin .feature file under tests/acceptance/
  step_definitions: "{{STEP_DEFINITIONS_PATH}}"  # optional: glue code for the BDD runner; omit the line when the project has no glue layer
  edge_cases:
    # Format: "Given [precondition], When [action], Then [outcome]"
    - "{{EDGE_CASE_1}}"
    - "{{EDGE_CASE_2}}"
---

# Task {{TASK_ID}}: {{TASK_TITLE}}

> The frontmatter above is authoritative. This document is read-only for Dev and QA after
> planning. An instantiated contract must contain no unresolved placeholder tokens.

## 1. Goal and scope

{{GOAL_AND_SCOPE}}

## 2. Out of scope

{{OUT_OF_SCOPE}}

## 3. Blast radius

Only the paths declared in frontmatter `touch_files` may be created or modified. Anything else is a
scope violation: stop and escalate instead of editing outside the contract.

## 4. Behavioral contract and invariants

The fenced `gherkin` block below is extracted verbatim into `dod.feature_file`. It must contain one
`Feature:` line and at least two `Scenario:` blocks, each with `Given`, `When` and `Then` clauses.
QA owns the feature file and its step definitions under `tests/acceptance/`; Dev only reads them.

```gherkin
Feature: {{FEATURE_NAME}}

  Scenario: {{SCENARIO_1_TITLE}}
    Given {{SCENARIO_1_GIVEN}}
    When {{SCENARIO_1_WHEN}}
    Then {{SCENARIO_1_THEN}}

  Scenario: {{SCENARIO_2_TITLE}}
    Given {{SCENARIO_2_GIVEN}}
    When {{SCENARIO_2_WHEN}}
    Then {{SCENARIO_2_THEN}}

  Scenario: {{SCENARIO_3_TITLE}}
    Given {{SCENARIO_3_GIVEN}}
    When {{SCENARIO_3_WHEN}}
    Then {{SCENARIO_3_THEN}}
```

## 5. Inherited architecture decisions

The frontmatter `adherence_adrs` list is authoritative. Summarize the inherited decisions here:
- {{INHERITED_ADR_SUMMARY}}

## 6. Verifiability notes

- Type check: `{{TYPE_CHECK_COMMAND}}` (must exit 0)
- Lint: `{{LINT_COMMAND}}` (must exit 0)
- Gherkin feature file: `{{FEATURE_FILE_PATH}}` (scenarios in Section 4; QA-owned)
- BDD runner/test target: `{{TEST_FILE_PATH}}` (entrypoint executed for acceptance; never the `.feature` file)
- Step definitions (when present): `{{STEP_DEFINITIONS_PATH}}`
- Edge cases in `dod.edge_cases` (the list below must match it):
  - {{EDGE_CASE_1}}
  - {{EDGE_CASE_2}}

## 7. Notes and open questions

{{NOTES}}
