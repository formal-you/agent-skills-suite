# PRD Artifact Contract

The PRD has two synchronized forms. The aggregate file is authoritative.

| Path | Authoritative | Contents |
| :--- | :--- | :--- |
| `.specs/01-prd.md` | yes | Complete PRD |
| `.specs/01-prd/README.md` | no | Bundle index |
| `.specs/01-prd/00-overview.md` | no | Problem, value, scope |
| `.specs/01-prd/01-features.md` | no | REQ-### with anchors |
| `.specs/01-prd/02-constraints.md` | no | CON-### |
| `.specs/01-prd/03-nfr.md` | no | NFR-### with verification |
| `.specs/01-prd/04-forks.md` | no | FORK-### |

## Identifiers

- `REQ-###` functional requirement, three digits, sequential.
- `CON-###` hard constraint.
- `NFR-###` measurable non-functional target.
- `FORK-###` open architectural decision handed to the spec-generator.
- `#sec-<kebab-case>` unique anchor, lowercase letters, digits and hyphens. One per
  functional requirement; reuse it downstream, never rename it.

## Content rules

- Every REQ has a scope, validation rules, state transitions, acceptance criteria and an anchor.
- Every CON states the rule, its impact and its source.
- Every NFR states a measurable target and how it will be verified. No default numbers:
  targets come from the user's context.
- Every FORK has context, at least two viable options and decision drivers. The PRD does
  not choose the option.
- Every section is traceable to the user's input. No entities, integrations or compliance
  regimes that were not provided or implied.

## Quality rules

- No `{{...}}`, `[TBD]`, `TODO` tokens in the final artifacts.
- Every relative link resolves.
- The aggregate and the bundle describe the same requirements.
- If a section does not apply (for example, there are genuinely no architectural forks),
  remove it and state why in the handoff instead of leaving placeholder content.

## Gate

- Manual: use the checklist in `SKILL.md`.
- Script: `python .agents/skills/prd-generator/scripts/lint_prd.py .specs/01-prd.md` (or `.specs`) and fix all errors.
