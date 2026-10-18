# Template Set: PRD Generator

These templates are the canonical shapes for the prd-generator skill. They are assets,
not output: scaffold.py copies every file whose name contains ``.template.``,
strips that segment, and writes the result under `--out`. `README.md` (this file) is a
guide and is never copied.

## Files and destinations

| Template | Output | Notes |
| :--- | :--- | :--- |
| 01-prd.template.md | 01-prd.md | Aggregate PRD |
| 01-prd/README.template.md | 01-prd/README.md | Bundle index |
| 01-prd/00-overview.template.md | 01-prd/00-overview.md | Problem, value, scope |
| 01-prd/01-features.template.md | 01-prd/01-features.md | REQ-### + #sec-* anchors |
| 01-prd/02-constraints.template.md | 01-prd/02-constraints.md | CON-### |
| 01-prd/03-nfr.template.md | 01-prd/03-nfr.md | NFR-### + verification |
| 01-prd/04-forks.template.md | 01-prd/04-forks.md | FORK-### |

## Conventions

- Placeholders use `{{UPPER_SNAKE}}`; every placeholder must be replaced before the
  lint gate passes.
- Identifiers: `REQ-###`, `CON-###`, `NFR-###`, `FORK-###`; every REQ carries a unique
  `#sec-<module-slug>` anchor.
- Numeric NFR values are never defaults. Derive them from the user's context, or mark
  them as unknown with the verification method.
- Output paths follow the repository convention: `.specs/01-prd.md` and `.specs/01-prd/`.

## Ownership

Owned by the prd-generator skill. Do not duplicate these files elsewhere; the skill
directory is the single source of truth.
