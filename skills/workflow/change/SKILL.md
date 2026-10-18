---
name: change
description: "Run a bounded brownfield change (bugfix, small feature, behavior tweak) against an existing spec or codebase: proposal -> one task bundle -> dev/QA -> converge -> archive. Use when an existing spec or codebase needs an incremental change (bugfix, small feature, behavior tweak) and a full PRD is overkill. Do not use for greenfield requirements (use prd-generator), architecture decisions (use spec-generator), or pure task slicing (use task-decomposition)."
license: MIT
compatibility: "Harness-agnostic. Python >=3.9 optional for standards extraction, scaffolding and linting; a manual fallback exists."
metadata:
  version: "3.1.0"
  category: spec-pipeline
---

# Change (Brownfield)

Add a bounded, reviewable change to an existing specification and codebase without writing a new
PRD. One change produces **one proposal** plus **exactly one four-document task bundle**; after QA
passes, the confirmed deltas are written back into the spec and the proposal is archived. This skill
is prompt-first: every step has a manual fallback and the bundled scripts are optional helpers.

Pipeline position: `spec-generator` (once, upstream) -> **change** -> `task-decomposition`
(bundle) -> `plan-linter` (Gate 1) -> `review` (Gate 2) -> `dev` ->
`qa` -> `converge` -> archive.

```text
existing spec + bounded change
  -> .specs/change-context/standards.md        (standards_extract.py; implicit constraints)
  -> .specs/changes/<change-id>/proposal.md    (lifecycle: proposed -> applied -> archived)
  -> tasks/<change-id>/01..04                  (one contract, one bundle)
  -> Gate 1 plan-linter -> Gate 2 review -> dev <-> qa -> converge -> archived proposal
```

## Use when

- An existing spec or shipped codebase needs an incremental change: a bugfix, a small feature, a
  behavior tweak, a bounded NFR adjustment.
- The change can reuse an existing `#sec-*` anchor and fits the micro/standard diff budget.
- You want the proposal -> apply -> archive loop while keeping this repository's 4-document task
  protocol and one-owner-per-file roles.

## Do not use when

- The work is greenfield, or no upstream spec exists yet: use `prd-generator`, then
  `spec-generator`, then `task-decomposition`.
- The change needs a new architecture decision, a new component boundary, a new cross-cutting
  invariant, or a brand-new spec section (a new `#sec-*` anchor): escalate to
  `spec-generator` instead of smuggling it into a change.
- You only need to slice an approved spec into tasks: use `task-decomposition`.
- You only need to audit existing bundles or proposals: use `plan-linter`.
- The task is already planned and awaiting implementation/verification: use `dev` /
  `qa`.

## Inputs

- The base specification: `.specs/02-tech-spec.md` (and its modular parts) by default.
- The requirement for the bounded change, written by the requester in plain language.
- The repository conventions report generated in step 1.
- Optional: the existing task bundle the change continues from, and the relevant ADRs.

## Outputs

| Artifact | Owner after scaffolding | Purpose |
| :--- | :--- | :--- |
| `.specs/change-context/standards.md` | Tooling | Deterministic repository standards and implicit constraints (generated, never hand-edited). |
| `.specs/changes/<change-id>/proposal.md` | Planner | Bounded change proposal: motivation, incremental diff, blast radius, invariants/NFR, rollback, verification. |
| `.specs/changes/<change-id>/convergence.md` | Converge tooling | Written after QA passes; records what was folded back into the spec. |
| `tasks/<change-id>/01-contract.md` ... `04-process.md` | Planner / Dev / QA / tooling | Exactly one four-document bundle, reusing the task-decomposition templates. |

The proposal is **not** a PRD and **not** a replacement spec. It is a delta that names the existing
anchors it changes. Full lifecycle and sizing rules:
[references/brownfield-protocol.md](references/brownfield-protocol.md).

## Workflow

1. **Extract repository standards** (once per configuration change):

   ```bash
   python .agents/skills/change/scripts/standards_extract.py --repo-root . --json
   python .agents/skills/change/scripts/standards_extract.py --repo-root . --check
   ```

   Read `.specs/change-context/standards.md` before planning. Its "Implicit constraints"
   section is binding: use only the commands it evidences, respect the declared test layout,
   language/runtime versions, and existing anchors. Exit code `1` from `--check` means
   the report is stale; regenerate it before planning. Never hand-edit the report.

2. **Scaffold the proposal and one task bundle** (the only step that writes files):

   ```bash
   python .agents/skills/change/scripts/scaffold_change.py \
     --change-id CHG-001-rate-limit \
     --title "Rate limit login attempts" \
     --anchor "#sec-auth-tokens" \
     --kind modify \
     --size-class micro \
     --estimated-lines 40 \
     --touch-files "modify:src/auth/rate_limit.py" \
     --repo-root .
   ```

   The scaffolder refuses an unknown anchor and a missing base spec, computes
   `base_spec_sha256`, and delegates the bundle to the `task-decomposition` skill's scaffolder when
   that skill is installed (`scaffold_task.py --change-id ... --size-class ...`).
   When that sibling is absent it still emits a minimal inline four-document bundle and prints a
   warning. Use `--dry-run` to preview and `--force` to overwrite an existing change
   directory.

3. **Planner fills the proposal and the contract.** Replace every guide in the proposal (motivation,
   the `[CHG-<n>]` hunks, affected paths, invariants/NFR impact, rollback, verification) and
   the remaining Planner-only contract placeholders (`module`, `adherence_adrs`,
   `dod`, edge cases, invariant prose). Do not invent paths or anchors. `02` and
   `03` stay blank role forms; `04` is tooling-owned. Keep the proposal
   `status: proposed`.

4. **Gate 1, then Gate 2.** Run the deterministic Gate 1 on the filled contracts (and the open
   proposal), then the read-only semantic review:

   ```bash
   # from the plan-linter skill directory (when that skill is installed)
   python scripts/plan_linter.py --tasks-dir tasks \
     --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
   # from this skill directory
   python scripts/lint_change.py --change-id CHG-001-rate-limit --repo-root .
   ```

   Gate 1 must pass before implementation; Gate 2 must not report `BLOCKED` or
   `REQUEST CHANGES`. Neither gate is a substitute for the other.

5. **Implement and verify.** Run `dev` (only the contract's `touch_files`, fill
   `02`, hand off) and then `qa` (independent acceptance tests under
   `tests/acceptance/`, fill `03`, one verdict). The proposal moves to
   `applied` once implementation and verification are complete but the spec write-back has
   not happened yet.

6. **Converge and archive.** After `QA_PASSED`, run the `converge` skill (when
   installed) to fold the confirmed implementation deviations back into
   `.specs/02-tech-spec.md`, write `.specs/changes/<change-id>/convergence.md`, move
   the bundle to `tasks/archive/<task-id>/`, and set the proposal `status: archived`.
   Without the converge skill, perform the same write-back manually: append an attributed, dated
   "Converged changes" section to the spec, record it in `convergence.md`, then set
   `status: archived`. Never rewrite existing spec prose; append.

## Manual fallback (no Python)

1. Build the standards list by hand: configuration files at the repo root, test directories, top-level
   source directories, runtime versions, and the existing `#sec-*` anchors in `.specs`.
2. Copy `assets/templates/proposal.template.md` to
   `.specs/changes/<change-id>/proposal.md` and fill every token (`{{...}}`); compute
   `base_spec_sha256` with any SHA-256 tool over the base spec file.
3. Create the four task documents under `tasks/<change-id>/`: copy them from the
   `task-decomposition` skill when it is installed, otherwise use the minimal four-document
   structure in [`references/brownfield-protocol.md`](references/brownfield-protocol.md), rename
   away `.template` where applicable, and fill the contract frontmatter
   with `change_id`, `size_class`, `origin_spec_anchor`,
   `estimated_lines`, `dependencies`, and `touch_files`
   (`create`/`modify`).
4. Run the Gate 1 checklist manually from `plan-linter` and the Gate 2 checklist from
   `review`; record the evidence in the task bundle.
5. Follow steps 5 and 6 above with the same artifacts.

## Quality-gate checklist

- [ ] Standards report generated and current (`standards_extract.py --check` exits 0).
- [ ] Proposal frontmatter complete, `status: proposed`, `kind` correct,
      `base_spec_sha256` current.
- [ ] Every `[CHG-<n>]` block names a real `#sec-*` anchor that exists in the base spec.
- [ ] Exactly one task bundle exists; its `change_id` equals the proposal id and its
      `origin_spec_anchor` is one of the proposal's `impact_anchors`.
- [ ] Diff budget honored: micro is one touch file (default 10-49 lines); standard is 1-3 files
      (default 50-250 lines). Numbers are configurable in the plan-linter config.
- [ ] Gate 1 passes on the filled contract and the proposal is open (`proposed`/`applied`).
- [ ] Gate 2 review has no blocking findings; the reviewer is independent and read-only.
- [ ] Dev implemented only `touch_files`; QA issued exactly one verdict with evidence.
- [ ] Converge appended the deltas to the spec and the proposal is `archived`.

## Anti-hallucination rules

- **Never invent file paths.** Every `touch_files` entry must be an existing file to
  `modify` or a new file inside an existing directory to `create`; paths are
  repo-relative and forward-slashed.
- **Every diff hunk names a real anchor.** Reuse an existing `#sec-*` anchor; the scaffolder
  refuses an anchor that is absent from the base spec and `lint_change.py` rejects one that
  drifted.
- **Do not invent commands or conventions.** Only commands evidenced by declared configuration (the
  standards report's section 6) may appear in the contract DoD.
- **A structural change escalates.** If the change needs a new spec section/anchor, a new component,
  a new ADR, or a new cross-cutting invariant, stop and use `spec-generator`; do not widen a
  change.
- **Do not overstate the gates.** Gate 1 is deterministic bookkeeping, Gate 2 is a prompt, and the
  authoritative audit trail is git plus repository CI. Optional scripts are helpers, never
  enforcement guarantees.

## Helper scripts

- `scripts/standards_extract.py` - deterministic repository-standards extractor; writes
  `.specs/change-context/standards.md`; `--json`, `--check`,
  `--dry-run`, `--version`.
- `scripts/scaffold_change.py` - creates the proposal and one task bundle;
  `--dry-run`, `--force`, `--json`, `--version`.
- `scripts/lint_change.py` - proposal/bundle consistency and base-spec drift check;
  `--json`, `--version`.

All helpers are standard-library-only, resolve their own directory, never import repository code,
and use exit codes `0` success, `1` content-gate failure, `2` usage/refusal,
`3` unexpected error.

## Failure handling

- **Missing base spec**: stop. A brownfield change has no meaning without a base; scaffold exits
  `2`.
- **Unknown anchor**: stop and reuse an existing anchor, or escalate to `spec-generator`.
- **Stale standards report or spec drift** (`--check`/lint exit `1`): regenerate the
  report, rebase the proposal on the new spec, and rerun Gate 1; never edit the recorded
  `base_spec_sha256` by hand.
- **Change directory already exists**: rerun with `--force` only when the previous scaffold is
  disposable; otherwise edit the existing proposal.
- **Optional script unavailable**: follow the manual fallback; the workflow must not depend on Python.

## Honest limits

- The standards report describes declared configuration, not necessarily enforced practice; it is a
  prompt for the Planner, not proof of compliance.
- `base_spec_sha256` detects any byte change to the base spec (including formatting); after
  convergence the archived proposal is exempt from the drift check because the spec intentionally
  changed.
- Optional scripts are bypassable; CI plus repository permissions remain authoritative.
