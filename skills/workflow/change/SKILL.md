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

Pipeline position: `spec-generator` -> **change** -> `task-decomposition` -> `plan-linter` (Gate 1) -> `review` (Gate 2) -> `dev` -> `qa` -> `converge` -> archive.

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
anchors it changes. Full lifecycle and sizing rules: [references/brownfield-protocol.md](references/brownfield-protocol.md).

## Workflow

1. **Extract repository standards** (once per configuration change):

   ```bash
   python .agents/skills/change/scripts/standards_extract.py --repo-root . --json
   python .agents/skills/change/scripts/standards_extract.py --repo-root . --check
   ```

   Read `.specs/change-context/standards.md` before planning. Its "Implicit constraints"
   section is binding: use only the commands it evidences, respect declared test layout,
   runtime floors, and existing anchors. Exit code `1` from `--check` means the report is
   stale; regenerate before planning. Never hand-edit the report.

2. **Scaffold the proposal and one task bundle** (the only step that writes files):

   ```bash
   python .agents/skills/change/scripts/scaffold_change.py \
     --change-id CHG-001-rate-limit \
     --title "Rate limit login attempts" \
     --anchor "#sec-auth-tokens" \
     --kind modify \
     --size-class micro --estimated-lines 40 \
     --touch-files "modify:src/auth/rate_limit.py" \
     --repo-root .
   ```

   The scaffolder validates anchors against the base spec, computes `base_spec_sha256`,
   and delegates to `task-decomposition` (`scaffold_task.py`) or emits a minimal inline
   bundle if absent. Use `--dry-run` to preview and `--force` to overwrite disposable runs.

3. **Planner fills the proposal and the contract.** Replace guides in proposal (`motivation`,
   `[CHG-<n>]` hunks, paths, invariants/NFR, rollback, verification) and contract placeholders
   (`module`, `adherence_adrs`, `dod`, edge cases, invariant prose). Do not invent paths or anchors.
   Keep `02`/`03` blank role forms; keep proposal `status: proposed`.

4. **Gate 1, then Gate 2.** Run deterministic Gate 1, then independent semantic review:

   ```bash
   # Run from the repository root. The Gate 1 helper requires the plan-linter skill to be installed.
   python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
   python .agents/skills/change/scripts/lint_change.py --change-id CHG-001-rate-limit --repo-root .
   ```

   Gate 1 must pass before implementation; Gate 2 must not report `BLOCKED` or `REQUEST CHANGES`.

5. **Implement and verify.** Run `dev` (only declared `touch_files`, fill `02`, hand off) and
   `qa` (independent tests under `tests/acceptance/`, fill `03`, one verdict). Proposal
   moves to `applied` once implementation and verification pass.

6. **Converge and archive.** After `QA_PASSED`, run `converge` to append confirmed deviations
   to `.specs/02-tech-spec.md`, write `convergence.md`, move bundle to `tasks/archive/`, and
   set proposal `status: archived`. Without `converge`, perform identical append write-back manually.

## Manual fallback (no Python)

1. Build standards list by hand: repo-root configs, test/source trees, runtimes, `#sec-*` anchors.
2. Copy `assets/templates/proposal.template.md` to `.specs/changes/<change-id>/proposal.md`, fill every token (`{{...}}`), and compute `base_spec_sha256`.
3. Create `tasks/<change-id>/` four-document bundle using `task-decomposition` templates or the fallback in [references/brownfield-protocol.md](references/brownfield-protocol.md).
4. Run Gate 1 / Gate 2 checklists manually; record evidence in the bundle.
5. Follow workflow steps 5–6 with the same artifacts.

## Quality-gate checklist

- [ ] Standards report generated and current (`standards_extract.py --check` exits 0).
- [ ] Proposal frontmatter complete, `status: proposed`, `kind` correct,
      `base_spec_sha256` current.
- [ ] Every `[CHG-<n>]` block names a real `#sec-*` anchor that exists in the base spec.
- [ ] Exactly one task bundle exists; `change_id` equals proposal id and
      `origin_spec_anchor` is one of the proposal's `impact_anchors`.
- [ ] Diff budget honored: micro is 1 touch file (default 10-49 lines); standard is
      1-3 files (default 50-250 lines). Numbers configurable in plan-linter config.
- [ ] Gate 1 passes on the filled contract and proposal is open (`proposed`/`applied`).
- [ ] Gate 2 review has no blocking findings; reviewer is independent and read-only.
- [ ] Dev implemented only `touch_files`; QA issued exactly one verdict with evidence.
- [ ] Converge appended deltas to the spec and the proposal is `archived`.

## Anti-hallucination rules

- **Never invent file paths.** Every `touch_files` entry must be an existing file
  to `modify` or a new file in an existing directory to `create` (repo-relative, forward-slashed).
- **Every diff hunk names a real anchor.** Reuse an existing `#sec-*` anchor;
  the scaffolder and linter reject missing or drifted anchors.
- **Do not invent commands or conventions.** Only commands evidenced by declared
  configuration (the standards report) may appear in the contract DoD.
- **A structural change escalates.** If the change needs a new spec section/anchor,
  a new component, a new ADR, or an invariant change, stop and use `spec-generator`.
- **Do not overstate the gates.** Gate 1 is deterministic bookkeeping, Gate 2 is
  prompt review; git and CI remain authoritative.

## Helper scripts

- `scripts/standards_extract.py` — deterministic standards extractor; writes
  `.specs/change-context/standards.md` (`--json`, `--check`, `--dry-run`, `--version`).
- `scripts/scaffold_change.py` — creates proposal and one task bundle
  (`--dry-run`, `--force`, `--json`, `--version`).
- `scripts/lint_change.py` — proposal/bundle consistency and base-spec drift check
  (`--json`, `--version`).

All helpers are stdlib-only, resolve their own directory, and exit `0` (success), `1` (gate failure), `2` (usage error), `3` (unexpected error).

## Failure handling

- **Missing base spec**: Stop. A brownfield change requires a base spec; scaffold exits `2`.
- **Unknown anchor**: Stop and reuse an existing anchor, or escalate to `spec-generator`.
- **Stale report or spec drift** (exit `1`): Regenerate report, rebase proposal, rerun Gate 1; never hand-edit `base_spec_sha256`.
- **Change directory exists**: Rerun with `--force` only if disposable; otherwise edit existing proposal.
- **Scripts unavailable**: Follow manual fallback; workflow is prompt-first.

## Honest limits

- The standards report describes declared configuration, not necessarily enforced practice; it is a prompt for the Planner, not proof of compliance.
- `base_spec_sha256` detects any byte change to the base spec; after convergence the archived proposal is exempt from drift checks.
- Optional scripts are bypassable; CI plus repository permissions remain authoritative.
