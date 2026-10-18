---
name: spec-generator
description: "Turn a PRD into architecture decisions (ADRs) and an engineering spec (.specs/02-tech-spec.md and .specs/02-tech-spec/). Use when the user provides a PRD or asks for an architecture review, ADR, or technical specification. Do not use when requirements are still being brainstormed (use prd-generator) or when the task is already implementation."
license: MIT
compatibility: "Harness-agnostic. Python >=3.9 is optional for scaffolding and structural linting; every step has a manual fallback."
metadata:
  version: "2.0.0"
  category: spec-pipeline
---

# Spec Generator

Turn a PRD into explicit architecture decisions and a technical specification that a
task planner can slice. The skill supplies judgment (architecture review, trade-offs,
decision records) and templates; it does not invent requirements.

## When to use

- The user provides a PRD (or PRD directory) and asks for architecture, ADRs, or a technical spec.
- A requirement contains `FORK-*` items that must become recorded decisions.
- A downstream planner needs stable `#sec-*` anchors, `NFR-###` targets and `INV-###` invariants.

Do not use when:

- Requirements are still ambiguous or missing: use `prd-generator` first.
- The request is implementation or task slicing: use the downstream skills.
- The user only asks to explain an existing spec: answer directly.

## Inputs

- `.specs/01-prd.md` (aggregate) or `.specs/01-prd/` (bundle). Prefer the aggregate.
- Any existing ADRs, constraints, and the target repository's conventions.

## Outputs

| Path | Contents |
| :--- | :--- |
| `.specs/adr/NNN-title.md` | One ADR per accepted architectural decision |
| `.specs/02-tech-spec.md` | Aggregate technical specification |
| `.specs/02-tech-spec/01-topology.md` | Topology and component responsibilities |
| `.specs/02-tech-spec/02-database-schema.sql` | Data model and illustrative DDL (only if data is persisted) |
| `.specs/02-tech-spec/03-api-contracts.ts` | API contract example (transport and language are project-specific) |
| `.specs/02-tech-spec/04-system-invariants.md` | Invariants and enforcement |

The aggregate file is authoritative; the bundle is its modular copy.

## Workflow

1. **Ingest the PRD.** Extract every `REQ-*`, `CON-*`, `NFR-*` and `FORK-*` item and
   reuse its `#sec-*` anchor. Do not rename anchors that downstream tasks consume.
2. **Architecture review from four perspectives.** Prefer independent reviewers when the
   host provides subagent tools. Otherwise run the same four roles as an explicit
   in-context review. Roles, veto, scoring and tie-break are in
   [references/architecture-review-protocol.md](references/architecture-review-protocol.md).
3. **Decide every fork.** For each `FORK-*`, evaluate at least two options, record the
   decision and its consequences as an ADR under `.specs/adr/`. An unresolved fork must
   be reported, not silently chosen.
4. **Scaffold (optional).** From this skill directory:
   `python scripts/scaffold.py --out .specs` (add `--dry-run` first).
5. **Author the artifacts.** Follow [references/spec-format.md](references/spec-format.md)
   and the project conventions in [references/project-conventions.md](references/project-conventions.md).
   Replace every `{{UPPER_SNAKE}}` placeholder; keep anchors consistent with the PRD.
6. **Lint (optional).** `python scripts/lint_spec.py .specs` (or the aggregate file).
   Fix every error before handing off.
7. **Hand off.** State the ADR list, the spec paths, and any open technical questions.
   The next step is `task-decomposition`.

## Tooling (optional)

All helpers are stdlib-only Python and resolve paths from their own location, so the
skill directory can be copied anywhere. Run them with `--help` instead of reading the
source.

| Command | Purpose |
| :--- | :--- |
| `python scripts/scaffold.py --out .specs [--dry-run] [--force] [--json]` | Copy templates into the output tree; creates `.specs/adr/` |
| `python scripts/lint_spec.py .specs [--json]` | Structural gate: placeholders, anchors, required tokens, Mermaid blocks, links, ADR sections |
| `python scripts/engine.py run --prd .specs/01-prd.md --output-dir .specs` | Optional engine proxy |

Exit codes: `0` success, `1` content/gate failure, `2` optional dependency or usage
unavailable, `3` unexpected error.

The engine is optional and never required. If it is not installed, `engine.py` exits
`2` with install guidance. Scaffolding, authoring and linting still work.

### Manual fallback (no Python)

1. Create `.specs/02-tech-spec/` and `.specs/adr/`.
2. Copy each `*.template.*` file under `assets/templates/` into `.specs/`, removing
   the `.template` segment from the name (`02-tech-spec.template.md` -> `02-tech-spec.md`);
   skip `README.md`. `adr.template.md` is a shape for writing individual ADRs; it is
   not copied.
3. Fill every placeholder, then self-check against the quality gate below.
4. Write one ADR per accepted decision, using the ADR template.

## Quality gate

- No `{{...}}`, `[TBD]`, or `TODO` tokens remain in the spec or ADRs.
- At least one `#sec-*` anchor; anchors reuse PRD identifiers and repeated references are fine.
- At least one `NFR-###` and one `INV-###`; every NFR has a verification method.
- Every Mermaid block has a matching fence and balanced brackets.
- Every relative link resolves.
- Every ADR contains Status, Context, Considered Options, Decision, Consequences.
- No requirement, component or table lacks a trace to a REQ or ADR.

## Anti-hallucination rules

- Do not add components, tables or interfaces that the PRD/ADRs do not require.
- Templates are shapes, not content: never copy their illustrative values into the output.
- Mark unresolved forks and open questions explicitly; do not fabricate a decision.

## References

- [references/architecture-review-protocol.md](references/architecture-review-protocol.md) - roles, rounds, veto, scoring, tie-break.
- [references/spec-format.md](references/spec-format.md) - artifact contract, anchors, Mermaid/DDL/API guidance.
- [references/project-conventions.md](references/project-conventions.md) - configurable team conventions.
- [references/zh-CN.md](references/zh-CN.md) - optional Chinese quick reference.
