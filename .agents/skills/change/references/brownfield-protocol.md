# Brownfield Change Protocol

This reference defines how a bounded change moves through the repository without writing a new PRD:
the proposal lifecycle, the delta-versus-new-section decision, sizing and escalation rules, how the
generated standards report constrains planning, and what "archived" means.

## 1. Proposal lifecycle

A proposal lives at `.specs/changes/<change-id>/proposal.md` and carries its state in the
frontmatter `status` field. The directory is never moved; status is authoritative.

| State | Set by | Meaning | Drift check |
| :--- | :--- | :--- | :--- |
| `proposed` | `scaffold_change.py`, then Planner | The delta is scaffolded and being planned; Gate 1/Gate 2 may still reject it. | Active: `base_spec_sha256` must match or the proposal is stale. |
| `applied` | Planner or converge tooling | Implementation and QA are complete; the confirmed deltas have not been written back to the spec yet. | Active: the spec must not change under the proposal. |
| `archived` | `converge` tooling (or the Planner during manual convergence) | The deltas were folded into the base spec and the bundle was archived; the proposal is history. | Exempt: convergence intentionally changes the spec. |

Transitions:

1. `proposed -> applied` after `QA_PASSED` on the task bundle, before spec write-back.
2. `applied -> archived` after convergence appended the confirmed deltas to the base spec and
   wrote `.specs/changes/<change-id>/convergence.md`.
3. A proposal that is rejected goes back to `proposed` for rework; it is never silently
   deleted. Delete only after the work is abandoned and recorded in the task bundle notes.

`plan_linter.py --changes-dir` treats `proposed`/`applied` as open and reports
`CHANGE_NOT_OPEN` for anything else, so run Gate 1 while the change is still open.
`lint_change.py` still validates archived proposals structurally but skips the drift error.

## 2. Delta versus new spec section

A change is legal only when it is a **delta inside an existing anchor**. Use this test:

| Question | Delta (use this skill) | New section (escalate) |
| :--- | :--- | :--- |
| Does an existing `#sec-*` anchor describe the behavior being changed? | Yes | No |
| Does the change add a component, service, datastore or public interface? | No | Yes |
| Does it introduce or weaken a system invariant or a cross-cutting NFR? | No | Yes |
| Does it need a new ADR or contradict an accepted ADR? | No | Yes |
| Can it be reverted without a data migration design? | Yes | Usually no |
| Does it fit the diff budget below? | Yes | Split or escalate |

If the answer points to "escalate", stop: revise the spec with `spec-generator` (and its ADRs)
first, then slice the resulting work with `task-decomposition`. Do not add a new
`#sec-*` anchor inside a change; the scaffolder refuses anchors that already exist in the base
spec and the linter rejects unknown ones.

## 3. Sizing rules

The defaults below are repository conventions and are configurable in the plan-linter config.

| Size class | Touch files | Estimated diff lines | Hunks | Extra rule |
| :--- | :--- | :--- | :--- | :--- |
| `micro` | exactly 1 | 10-49 (default `micro_min_diff_lines`..`min_diff_lines-1`) | 1 | Must declare `change_id`; plan-linter reports `MICRO_REQUIRES_CHANGE_ID` otherwise. |
| `standard` | 1-3 | 50-250 (default `min_diff_lines`..`max_diff_lines`) | 1-3 | A structural change escalates instead of growing. |

Rules of thumb:

- One change = one behavior = one bundle. If you need a second bundle, scaffold a second change id.
- Prefer the smaller class. A `micro` change that grows past its budget is re-scaffolded as
  `standard`, not silently widened.
- `touch_files` is a hard blast radius. Any file the implementation actually edits must be
  declared; anything else is a scope violation for the Dev role.

## 4. Escalation rules

Escalate to `spec-generator` (and then re-slice with `task-decomposition`) when:

- a new `#sec-*` anchor is required, or an existing anchor must be split or merged;
- the change introduces/removes a component boundary, an external interface, a datastore or a
  migration;
- an invariant, security property, availability/latency target or other NFR changes;
- a new ADR is needed, or an accepted ADR must be superseded;
- the diff budget is exceeded and the work cannot be split into independent micro/standard changes;
- two changes need to modify the same anchor in incompatible ways. Sequence them as two changes with
  a dependency edge, or converge them in one spec revision.

Escalation is a success condition of this protocol: it prevents a structural change from being
smuggled in as a "small fix".

## 5. The standards report as implicit constraints

`standards_extract.py` writes `.specs/change-context/standards.md`: detected
configuration files, test layout, top-level source directories, existing `#sec-*` anchors,
language/runtime versions and the commands implied by declared configuration. The report is
deterministic and timestamp-free; `--check` exits `1` when it no longer matches the
repository, so CI can enforce freshness.

Treat the report as binding, implicit input to planning:

1. **Commands.** Only commands listed under "Commands implied by declared configuration" may be
   quoted in the contract `dod`. Do not invent a type-check or lint command.
2. **Runtime floors.** A declared `requires-python`/`engines` value is a compatibility
   floor: any bundled helper or generated snippet must run on it.
3. **Test layout.** Acceptance tests belong under the detected test tree (`tests/acceptance/`
   by default); unit tests run from the repository root.
4. **Anchors.** The report lists every anchor that exists in `.specs`. Proposals may only
   reuse those anchors.
5. **Freshness.** Regenerate after any configuration change; a stale report invalidates the plan
   review. The report is generated output: never hand-edit it.

## 6. Artifacts and archive layout

```text
.specs/
  change-context/standards.md          # generated; freshness-checked
  changes/<change-id>/
    proposal.md                        # lifecycle proposal; status is authoritative
    convergence.md                     # written by converge after QA_PASSED
tasks/
  <change-id>/01-contract.md .. 04-process.md   # active bundle
  archive/<change-id>/ ...                       # after convergence
```

- The task bundle is created by delegating to
  `task-decomposition/scripts/scaffold_task.py --change-id <id> --size-class <class>`, so the
  contract carries `change_id` and `size_class` and stays compatible with the Gate 1
  change checks.
- `02-dev-workspace.md` and `03-qa-verification.md` stay token-free blank role forms;
  `04-process.md` stays tooling-owned.
- Convergence never deletes history: it appends a "Converged changes" section to the spec and moves
  the bundle to `tasks/archive/`. The archived proposal remains in
  `.specs/changes/<change-id>/` as the audit record.

## 7. Idempotency and re-scaffolding

- `scaffold_change.py` refuses an existing change or bundle directory unless `--force`
  is passed; `--force` only makes the scaffold disposable, it does not rewrite Planner edits
  elsewhere.
- `lint_change.py` is read-only and safe to rerun; it reports the same violations until the
  files change.
- `standards_extract.py` is deterministic: the same tree produces the same report, so
  `--check` is a stable CI signal.
- Re-running `converge` on an already archived change is a no-op (see the converge skill).

## 8. Minimal four-document fallback (no sibling skill)

When the `task-decomposition` skill is not installed, create `tasks/<change-id>/` with these four
documents and the same contract fields the scaffolder would emit:

| Document | Minimum content |
| :--- | :--- |
| `01-contract.md` | YAML frontmatter first: `task_id` (= directory name), `title`, `module`, `change_id`, `size_class`, `dependencies`, `estimated_lines`, `touch_files`, `origin_spec_anchor`, `adherence_adrs`, `dod`; then the human sections. |
| `02-dev-workspace.md` | Token-free blank role form with Dev scope, self-verification table and the `- [ ] WAITING_FOR_QA` box unchecked. |
| `03-qa-verification.md` | Token-free blank QA form with the test matrix, evidence section and both verdict boxes unchecked. |
| `04-process.md` | Initialized derived state (`TODO` / `UNASSIGNED` / `None` / retry `0`, empty event table). |

Keep `02`/`03`/`04` token-free so Gate 1 passes on the planned bundle. The inline fallback emitted
by `scaffold_change.py` produces the same four documents; the manual path must not invent extra
sections.

