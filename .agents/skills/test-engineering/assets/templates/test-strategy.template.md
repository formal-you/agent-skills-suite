# Test Strategy — {{PROJECT_NAME}}

> Owner: {{OWNER}} · Version: {{VERSION}} · Status: {{STATUS}} · Last reviewed: {{REVIEW_DATE}}

<!--
Fill every placeholder. Delete sections that genuinely do not apply and say why in Scope.
Do not keep placeholder values as defaults. This document defines standards for the whole
project; it does not accept individual tasks and does not issue task verdicts.
-->

## 1. Scope and context

- **System under test**: {{SYSTEM_SCOPE}}
- **Out of scope**: {{OUT_OF_SCOPE}}
- **Stacks and versions**: {{STACKS}}
- **Build and test commands**: {{TEST_COMMANDS}}
- **Constraints**: {{CONSTRAINTS}} (compliance: {{COMPLIANCE}}, data residency: {{DATA_RESIDENCY}}, environment limits: {{ENVIRONMENT_LIMITS}})
- **Consumers of this strategy**: {{CONSUMERS}}

## 2. Quality attributes

| Attribute | Target for this project | Verification approach | Owner |
| :--- | :--- | :--- | :--- |
| Correctness | {{CORRECTNESS_TARGET}} | {{CORRECTNESS_VERIFICATION}} | {{CORRECTNESS_OWNER}} |
| Reliability | {{RELIABILITY_TARGET}} | {{RELIABILITY_VERIFICATION}} | {{RELIABILITY_OWNER}} |
| Performance | {{PERFORMANCE_TARGET}} | {{PERFORMANCE_VERIFICATION}} | {{PERFORMANCE_OWNER}} |
| Security | {{SECURITY_TARGET}} | {{SECURITY_VERIFICATION}} | {{SECURITY_OWNER}} |
| Compatibility | {{COMPATIBILITY_TARGET}} | {{COMPATIBILITY_VERIFICATION}} | {{COMPATIBILITY_OWNER}} |
| Observability | {{OBSERVABILITY_TARGET}} | {{OBSERVABILITY_VERIFICATION}} | {{OBSERVABILITY_OWNER}} |

## 3. Risk matrix

| Risk ID | Behavior / interface | Likelihood | Impact | Class | Levels | Techniques | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R-01 | {{RISK_1_BEHAVIOR}} | {{RISK_1_LIKELIHOOD}} | {{RISK_1_IMPACT}} | {{RISK_1_CLASS}} | {{RISK_1_LEVELS}} | {{RISK_1_TECHNIQUES}} | {{RISK_1_OWNER}} |
| R-02 | {{RISK_2_BEHAVIOR}} | {{RISK_2_LIKELIHOOD}} | {{RISK_2_IMPACT}} | {{RISK_2_CLASS}} | {{RISK_2_LEVELS}} | {{RISK_2_TECHNIQUES}} | {{RISK_2_OWNER}} |

Risk classes and minimum depth: {{RISK_POLICY}}

## 4. Test levels

| Level | In use | Isolation model | Owner | Exit criteria |
| :--- | :--- | :--- | :--- | :--- |
| Unit | {{LEVEL_UNIT_USE}} | {{LEVEL_UNIT_ISOLATION}} | {{LEVEL_UNIT_OWNER}} | {{LEVEL_UNIT_EXIT}} |
| Integration | {{LEVEL_INTEGRATION_USE}} | {{LEVEL_INTEGRATION_ISOLATION}} | {{LEVEL_INTEGRATION_OWNER}} | {{LEVEL_INTEGRATION_EXIT}} |
| Contract | {{LEVEL_CONTRACT_USE}} | {{LEVEL_CONTRACT_ISOLATION}} | {{LEVEL_CONTRACT_OWNER}} | {{LEVEL_CONTRACT_EXIT}} |
| Acceptance | {{LEVEL_ACCEPTANCE_USE}} | {{LEVEL_ACCEPTANCE_ISOLATION}} | {{LEVEL_ACCEPTANCE_OWNER}} | {{LEVEL_ACCEPTANCE_EXIT}} |
| End-to-end | {{LEVEL_E2E_USE}} | {{LEVEL_E2E_ISOLATION}} | {{LEVEL_E2E_OWNER}} | {{LEVEL_E2E_EXIT}} |

## 5. Technique policy

| Risk class or input model | Required techniques | Forbidden shortcuts |
| :--- | :--- | :--- |
| {{TECHNIQUE_SCOPE_1}} | {{TECHNIQUE_REQUIRED_1}} | {{TECHNIQUE_FORBIDDEN_1}} |
| {{TECHNIQUE_SCOPE_2}} | {{TECHNIQUE_REQUIRED_2}} | {{TECHNIQUE_FORBIDDEN_2}} |

Oracle rule: {{ORACLE_RULE}}

## 6. Test data policy

- **Data classes allowed**: {{ALLOWED_DATA_CLASSES}}
- **Data never allowed**: {{FORBIDDEN_DATA_CLASSES}}
- **Generation and seeds**: {{DATA_GENERATION}}
- **Isolation and cleanup**: {{DATA_ISOLATION}}
- **Ownership and versioning**: {{DATA_OWNERSHIP}}

## 7. Environment policy

- **Environments**: {{ENVIRONMENTS}}
- **Parity and differences**: {{ENVIRONMENT_PARITY}}
- **Required services and substitutes**: {{ENVIRONMENT_SERVICES}}
- **Time, locale, randomness, identifiers**: {{ENVIRONMENT_DETERMINISM}}
- **Network policy**: {{NETWORK_POLICY}}
- **Provenance recorded per run**: {{ENVIRONMENT_PROVENANCE}}

## 8. Test-double policy

- **Preferred doubles and locations**: {{DOUBLE_POLICY}}
- **Forbidden doubles**: {{FORBIDDEN_DOUBLES}}
- **Fake fidelity checks**: {{FAKE_FIDELITY}}

## 9. Flakiness policy

- **Detection method**: {{FLAKE_DETECTION}}
- **Quarantine label, owner, expiry**: {{FLAKE_QUARANTINE}}
- **Retry policy**: {{RETRY_POLICY}}
- **Fix and re-enable criteria**: {{FLAKE_REENABLE}}

## 10. Automation and handoff

- **Tiers and time budgets**: {{TEST_TIERS}}
- **Selecting a tier**: {{TIER_SELECTION}}
- **Required artifacts per run**: {{REQUIRED_ARTIFACTS}}
- **Handoff to QA**: {{QA_HANDOFF}}
- **Handoff to CI owners**: {{CI_HANDOFF}}

## 11. Metrics and thresholds

| Metric | Definition | Target | Owner | Caution |
| :--- | :--- | :--- | :--- | :--- |
| Mutation score | {{METRIC_MUTATION_DEF}} | {{METRIC_MUTATION_TARGET}} | {{METRIC_MUTATION_OWNER}} | {{METRIC_MUTATION_CAUTION}} |
| Coverage | {{METRIC_COVERAGE_DEF}} | {{METRIC_COVERAGE_TARGET}} | {{METRIC_COVERAGE_OWNER}} | {{METRIC_COVERAGE_CAUTION}} |
| Flake rate | {{METRIC_FLAKE_DEF}} | {{METRIC_FLAKE_TARGET}} | {{METRIC_FLAKE_OWNER}} | {{METRIC_FLAKE_CAUTION}} |
| Defect escape rate | {{METRIC_ESCAPE_DEF}} | {{METRIC_ESCAPE_TARGET}} | {{METRIC_ESCAPE_OWNER}} | {{METRIC_ESCAPE_CAUTION}} |
| Time to feedback | {{METRIC_FEEDBACK_DEF}} | {{METRIC_FEEDBACK_TARGET}} | {{METRIC_FEEDBACK_OWNER}} | {{METRIC_FEEDBACK_CAUTION}} |

Blocking thresholds are owned by QA and the CI owners; this strategy defines the metrics, not the
gate behavior.

## 12. RACI

| Activity | Test engineering | QA | Quality engineering | Dev | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| {{RACI_ACTIVITY_1}} | {{RACI_1_TE}} | {{RACI_1_QA}} | {{RACI_1_QE}} | {{RACI_1_DEV}} | {{RACI_1_REVIEW}} |
| {{RACI_ACTIVITY_2}} | {{RACI_2_TE}} | {{RACI_2_QA}} | {{RACI_2_QE}} | {{RACI_2_DEV}} | {{RACI_2_REVIEW}} |

## 13. Adoption roadmap

| Phase | Action | Owner | Target date | Exit criterion |
| :--- | :--- | :--- | :--- | :--- |
| Baseline | {{ROADMAP_BASELINE_ACTION}} | {{ROADMAP_BASELINE_OWNER}} | {{ROADMAP_BASELINE_DATE}} | {{ROADMAP_BASELINE_EXIT}} |
| Pilot | {{ROADMAP_PILOT_ACTION}} | {{ROADMAP_PILOT_OWNER}} | {{ROADMAP_PILOT_DATE}} | {{ROADMAP_PILOT_EXIT}} |
| Ratify | {{ROADMAP_RATIFY_ACTION}} | {{ROADMAP_RATIFY_OWNER}} | {{ROADMAP_RATIFY_DATE}} | {{ROADMAP_RATIFY_EXIT}} |
| Operate | {{ROADMAP_OPERATE_ACTION}} | {{ROADMAP_OPERATE_OWNER}} | {{ROADMAP_OPERATE_DATE}} | {{ROADMAP_OPERATE_EXIT}} |

## 14. Approval checklist

- [ ] Scope, constraints, and stacks are explicit.
- [ ] Every quality attribute has a verification approach and owner.
- [ ] Risk register is populated and each class maps to levels and techniques.
- [ ] Data, environment, test-double, and flakiness policies are actionable.
- [ ] Tiers, artifacts, and handoffs to QA and CI owners are declared.
- [ ] Metrics have definitions, owners, and cautions.
- [ ] RACI and roadmap are agreed with the named owners.
