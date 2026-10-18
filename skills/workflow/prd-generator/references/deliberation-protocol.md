# PRD Deliberation Protocol

Four perspectives are reviewed before the PRD is written. The goal is not consensus
theatre: it is to expose trade-offs early and record the unresolved ones as `FORK-*`.

## Roles

| Role | Focus | Hard veto |
| :--- | :--- | :--- |
| Product architect | Value proposition, MVP boundary, business state machine, module boundaries | No |
| Business / compliance | Commercial viability, legal and regulatory constraints, data handling, audit | Yes: may reject a proposal that violates a stated hard constraint |
| UX / user journey | End-to-end user paths, low cognitive load, error and recovery states, state clarity | No |
| Feasibility / YAGNI | Engineering feasibility, cost, schedule, avoidance of over-design | No |

Only the compliance role holds a veto, and only on a constraint the user supplied or
that is legally unavoidable. A veto must name the constraint; it cannot be a preference.

## Rounds

1. **Proposal** - each role states its goals, concerns and candidate requirements.
2. **Cross-critique** - each role challenges the others' proposals with evidence:
   user quotes, constraints, measurements, or missing information. Prefer questions
   over invented answers.
3. **Convergence** - the lead resolves conflicts, keeps the MVP minimal, and records
   what remains undecided.

When the host provides subagent tools, run the four roles as independent reviewers and
collect their reports. When it does not, run the same four roles as an explicit
in-context round, one role at a time, and keep the same evidence rules.

## Scoring and tie-break (optional)

Use scoring only when a decision must be justified quantitatively:

- Criteria are chosen for the product, not copied from this document.
- Weights sum to 1.0000; no role weight is below 0.10.
- Score each option 0-10 per role; record the weighted result.
- Deterministic tie-break order: (1) domain fit, (2) simpler option, (3) the role that
  owns the domain, (4) alphabetical identifier. Never break a tie randomly.

## Output

- A short decision log: what was decided, by which role, on what evidence.
- Explicit `FORK-*` items with context, at least two viable options and decision drivers.
- Open questions that block the PRD, tagged for the user.
- No invented domain content: if the user did not say it, it is either an open question
  or it is out of scope.

## Modes

- **Independent reviewers** (preferred): spawn one reviewer per role, ask each for a
  short evidence-based report, then converge. This is a quality mode, not a requirement.
- **In-context review**: write the four role sections explicitly, critique them in a
  second pass, then converge. Keep it short; the artifact matters more than the transcript.
