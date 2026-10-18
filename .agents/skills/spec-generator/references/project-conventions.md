# Project Conventions (configurable)

These are team defaults, not universal truths. Override them in the target repository and
record the override; the skill workflow stays the same.

## Artifact layout

- `.specs/01-prd.md` + `.specs/01-prd/`
- `.specs/02-tech-spec.md` + `.specs/02-tech-spec/`
- `.specs/adr/NNN-title.md`
- `tasks/<task-id>/01-contract.md` ... `04-process.md` (downstream)

## Contract style

- If the project uses TypeScript, prefer one declaration style for request/response types
  (for example type aliases) and apply it consistently. The illustrative template uses
  type aliases; it is not a rule for projects that use another language.
- Keep the error envelope and naming conventions consistent with the existing API surface.

## Anti-contamination

- No entity, table, route, component or compliance regime may appear unless it is in the
  PRD or an accepted ADR.
- If a project has a known contamination list (for example, domain terms that must never
  appear in other domains), keep that list in the repository's own lint configuration,
  not in this skill.

## Titles, IDs and numbering

- ADR numbers are sequential three-digit: `001`, `002`, ...
- Task IDs are `task-NNN-short-slug`.
- Anchors are `#sec-<kebab-case>`, lowercase, stable across PRD and spec.

## What is not a convention

- A specific database, broker, cache, gateway, cloud or framework.
- A specific latency, throughput, availability or RPO/RTO value.
- Multi-tenancy, an authentication scheme or a deployment topology.

Those come from the product requirements and the architecture review, and must be
justified in an ADR.
