---
# Brownfield change proposal. The YAML frontmatter below is authoritative.
# Lifecycle: proposed -> applied -> archived (see the change skill's references/brownfield-protocol.md).
# Fill every double-brace token; the scaffolder replaces the ones derived from its flags.
change_id: "{{CHANGE_ID}}"
title: "{{TITLE}}"
status: "proposed"
kind: "{{KIND}}"
base_spec: "{{BASE_SPEC}}"
base_spec_sha256: "{{BASE_SPEC_SHA256}}"
impact_anchors:
  - "{{ANCHOR}}"
created: "{{CREATED}}"
---

# Change Proposal: {{TITLE}}

> Owner: Planner. This bounded change reuses an existing specification anchor and produces exactly
> one task bundle. It is neither a PRD replacement nor a spec revision; confirmed deltas are folded
> back into the base spec by the convergence step and the proposal is then archived.

## 1. Motivation

<!-- One short paragraph: the observable problem, who is affected, and why a full PRD cycle is
overkill. Do not restate the whole spec. -->

## 2. Incremental diff

> One block per hunk. Title each block `[CHG-<n>]` and name the real `#sec-*` anchor
> it changes. Reuse an existing anchor from the base spec; never invent one. A structural change
> that needs a new section escalates to the `spec-generator` skill.

### [CHG-1] {{ANCHOR}}

- Before: <current behavior at this anchor>
- After: <new behavior introduced by this change>
- Files: {{TOUCH_FILES_LINE}}

## 3. Affected code paths

{{AFFECTED_PATHS}}

## 4. Invariants and NFR impact

<!-- List the system invariants that still hold, and any NFR that changes. State explicitly when an
invariant or NFR is untouched. -->

## 5. Rollback

<!-- How to revert the change safely: feature flag, revert commit, data migration rollback.
Never propose deleting data as a rollback. -->

## 6. Verification

<!-- How the change is proven: the acceptance test file, the edge cases, the commands evidenced by
.specs/change-context/standards.md. Do not claim commands that the standards report does not list. -->
