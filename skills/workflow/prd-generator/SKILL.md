---
name: prd-generator
description: "Turn an ambiguous product idea into a modular PRD bundle (.specs/01-prd.md and .specs/01-prd/). Use when the user asks for a PRD, product requirements, feature scoping, MVP definition, or a PRD revision. Do not use for architecture decisions or engineering specifications; use spec-generator after the PRD exists."
license: MIT
compatibility: "Harness-agnostic. Python >=3.9 is optional for scaffolding and structural linting; every step has a manual fallback."
metadata:
  version: "2.0.0"
  category: spec-pipeline
---

# PRD Generator

Convert an ambiguous product idea into a product requirements document that a
downstream architecture review can consume without guessing. The skill supplies
judgment (clarification, four-role review, convergence) and templates; it does not
invent domain content.

## When to use

- The user asks for a PRD, product requirements, feature scoping, MVP boundaries, or a PRD revision.
- A one-line idea, a notes dump, or a broken draft must become a structured requirements document.
- A downstream step needs stable REQ/CON/NFR/FORK identifiers and `#sec-*` anchors.

Do not use when:

- The request is an architecture decision, ADR, or engineering specification: use `spec-generator` after the PRD exists.
- The user only needs a quick summary of an existing document: answer directly.
- The task is implementation, test design, or task slicing: use the downstream skills.

## Inputs

- The user's idea, notes, or existing documents. Ask only for what blocks a decision.
- Optional: domain hint, constraints, target users, non-goals, existing PRD to revise.

## Outputs

| Path | Contents |
| :--- | :--- |
| `.specs/01-prd.md` | Aggregate PRD: REQ-###, CON-###, NFR-###, FORK-###, #sec-* anchors |
| `.specs/01-prd/00-overview.md` | Problem, value, scope, milestones |
| `.specs/01-prd/01-features.md` | Functional requirements with anchors |
| `.specs/01-prd/02-constraints.md` | Non-negotiable constraints |
| `.specs/01-prd/03-nfr.md` | Measurable non-functional targets |
| `.specs/01-prd/04-forks.md` | Architectural unknowns handed to spec-generator |

The aggregate file is authoritative; the bundle is its modular copy.

## Workflow

1. **Intake and clarify.** Extract the goal, users, constraints, non-goals, and
   measurable outcomes. If a gap blocks the PRD, ask a focused question; do not fill
   gaps with assumptions from other domains.
2. **Review the idea from four perspectives.** Prefer independent reviewers when the
   host provides subagent tools. Otherwise run the same four roles as an explicit
   in-context review round. Roles, veto rule, scoring and tie-break are in
   [references/deliberation-protocol.md](references/deliberation-protocol.md).
3. **Converge.** Record the decisions and the unresolved architectural forks
   (`FORK-*`) with at least two viable options and decision drivers. Never pre-select
   an option in the PRD.
4. **Scaffold (optional).** From the repository root:
   `python .agents/skills/prd-generator/scripts/scaffold.py --out .specs` (add `--dry-run` first).
5. **Author the artifacts.** Follow [references/prd-format.md](references/prd-format.md).
   Replace every `{{UPPER_SNAKE}}` placeholder; keep identifiers consistent and each anchor tied to its module.
6. **Lint (optional).** `python .agents/skills/prd-generator/scripts/lint_prd.py .specs/01-prd.md` (or `.specs`).
   Fix every error before handing off.
7. **Hand off.** State the output paths and the unresolved `FORK-*` items. The next
   step is `spec-generator`.

## Tooling (optional)

All helpers are stdlib-only Python and resolve paths from their own location, so the
skill directory can be copied anywhere. Run them from the repository root with
`--help` instead of reading the source.

| Command | Purpose |
| :--- | :--- |
| `python .agents/skills/prd-generator/scripts/scaffold.py --out .specs [--dry-run] [--force] [--json]` | Copy templates into the output tree |
| `python .agents/skills/prd-generator/scripts/lint_prd.py .specs [--json]` | Structural gate: placeholders, anchors, required tokens, links |
| `python .agents/skills/prd-generator/scripts/engine.py run --idea "..." --output-dir .specs` | Optional engine proxy |

Exit codes: `0` success, `1` content/gate failure, `2` optional dependency or usage
unavailable, `3` unexpected error.

The engine is optional and never required. If it is not installed, `engine.py` exits
`2` with install guidance. Scaffolding, authoring and linting still work.

### Manual fallback (no Python)

1. Create `.specs/01-prd/`.
2. Copy each `*.template.*` file under `assets/templates/` into `.specs/`, removing
   the `.template` segment from the name (`01-prd.template.md` -> `01-prd.md`); skip
   `README.md`, which is a guide.
3. Fill every placeholder, then self-check against the quality gate below.
4. Record the same checks (placeholders, anchors, required tokens, links) in your summary.

## Quality gate

- No `{{...}}`, `[TBD]`, or `TODO` tokens remain.
- Every functional requirement has a `#sec-<kebab-case>` anchor; repeated references to the same anchor are fine.
- At least one `REQ-###`, `CON-###`, `NFR-###` and `FORK-###` (omit a category only when
  the user's context genuinely has none, and say so).
- Every NFR has a measurable target and a verification method.
- Every relative link resolves.
- Content is traceable to the user's request; no examples from this template or other domains.

## Anti-hallucination rules

- Do not add entities, roles, integrations or compliance regimes the user did not
  provide or imply.
- Mark uncertain items as open questions instead of inventing answers.
- Templates are shapes, not content: never copy their illustrative values into the output.

## References

- [references/deliberation-protocol.md](references/deliberation-protocol.md) - roles, rounds, veto, scoring, tie-break.
- [references/prd-format.md](references/prd-format.md) - artifact contract, identifiers and anchors.
- [references/agent-platform-patterns.md](references/agent-platform-patterns.md) - optional domain note; read only when the product is an agent platform.
- [references/zh-CN.md](references/zh-CN.md) - optional Chinese quick reference.
