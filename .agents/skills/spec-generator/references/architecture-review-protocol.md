# Architecture Review Protocol

Four perspectives review the PRD before the technical spec is written. The goal is a
recorded decision per fork, not a unanimous opinion.

## Roles

| Role | Focus | Hard veto |
| :--- | :--- | :--- |
| System architect | Topology, component boundaries, interfaces, data ownership | No |
| Security / compliance | Threat model, authentication and authorization, data protection, audit | Yes: may reject a proposal that violates a stated constraint or a legal requirement |
| Performance / scale | Throughput, latency, capacity, caching, failure behaviour | No |
| YAGNI / simplicity | Complexity budget, operational cost, delivery risk, avoidable technology | No |

Only security holds a veto, and it must cite the specific constraint. Preferences and
style disagreements are not vetoes.

## Rounds

1. **Proposal** - each role states its position per `FORK-*$: preferred option, evidence,
   and the risks it accepts.
2. **Cross-critique** - each role attacks the other positions with evidence (load
   estimates, failure modes, compliance constraints, measured baselines). Ask for missing
   data instead of inventing it.
3. **Convergence** - the architect resolves or escalates. Every accepted decision becomes
   an ADR with its rejected options and consequences.

When the host provides subagent tools, spawn one reviewer per role and collect short,
evidence-based reports. Otherwise run the same four roles in-context, one at a time, and
keep the evidence rules.

## Scoring (optional)

- Criteria are specific to this system; do not reuse scores from another project.
- Weights sum to 1.0000; no role weight below 0.10.
- Record per-option scores 0-10, weighted total and the deciding role.
- Deterministic tie-break: (1) compliance/security, (2) domain fit, (3) simpler option,
  (4) alphabetical identifier. Never break a tie randomly.

## Output per fork

- Decision and rationale, linked to the PRD `FORK-*` and `#sec-*` anchors.
- Options considered, with pros and cons, including the rejected ones.
- Consequences and accepted trade-offs, plus mitigations.
- Open questions that could not be resolved without the user.

No decision may introduce a component, dependency or data store that the PRD does not
require. "We need it anyway" is a finding for the user, not a silent addition.
