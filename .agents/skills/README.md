# Agent Skills — Specification & Execution Pipeline (v2)

Nine reusable, harness-neutral skills that turn a vague idea or an existing codebase into a reviewed,
implemented, independently verified and spec-converged change:

```text
idea    → prd-generator → spec-generator → task-decomposition → plan-linter → review → dev ↔ qa → converge → done
           (.specs/01-prd*)  (.specs/02-tech-spec*, .specs/adr/*)   (tasks/task-*)      (Gate 1)      (Gate 2)  (implement + verify)  (spec write-back)
change  → change (brownfield proposal + one task bundle) → the same Gate 1/2 → dev ↔ qa → converge
```

This directory is the **single source of truth**. The skills are prompt-first: they work with any
agent harness and degrade to a manual checklist when no helper script or Python interpreter is
available. Deterministic gates are optional helpers; repository CI is the authoritative enforcement
layer (see `.agents/rules` and `docs/skills-compatibility.md`).

中文使用指南：[docs/skills-guide.zh-CN.md](../../docs/skills-guide.zh-CN.md)。

---

## Skills

| Skill | Use it for | Inputs | Outputs | Bundled helpers |
| :--- | :--- | :--- | :--- | :--- |
| [`prd-generator`](prd-generator/SKILL.md) | Turn an ambiguous idea into a modular product requirements document | User idea / notes | `.specs/01-prd.md`, `.specs/01-prd/` | `scaffold.py`, `lint_prd.py`, optional `engine.py` |
| [`spec-generator`](spec-generator/SKILL.md) | Turn a PRD into architecture decisions and an engineering spec | `.specs/01-prd.md` | `.specs/adr/*.md`, `.specs/02-tech-spec.md`, `.specs/02-tech-spec/` | `scaffold.py`, `lint_spec.py`, optional `engine.py` |
| [`task-decomposition`](task-decomposition/SKILL.md) | Slice a spec into atomic, independently verifiable task bundles | PRD + ADRs + tech spec | `tasks/task-*/01-contract.md` … `04-process.md` | `scaffold_task.py` |
| [`change`](change/SKILL.md) | Run a bounded brownfield change: proposal, one task bundle, archive | Existing `.specs/02-tech-spec.md` + repository | `.specs/changes/<change-id>/proposal.md`, one `tasks/<task-id>/` bundle, standards report | `scaffold_change.py`, `standards_extract.py`, `lint_change.py` |
| [`plan-linter`](plan-linter/SKILL.md) | Run deterministic Gate 1 on task bundles | `tasks/` (+ optional spec, repo root, change dir) | Gate 1 report; JSON; coverage matrix | `plan_linter.py` |
| [`review`](review/SKILL.md) | Independently review a plan (Gate 2) or a code change | plans/tasks, or diff + evidence | Findings + `PASS`/`REQUEST CHANGES`/`BLOCKED` | none (prompt workflow) |
| [`dev`](dev/SKILL.md) | Implement one task bundle within its blast radius and hand off to QA | `tasks/<task-id>/01-contract.md` + project commands | Code changes, filled `02`, `WAITING_FOR_QA` | none (prompt workflow) |
| [`qa`](qa/SKILL.md) | Independently verify a handoff and issue one verdict | `01`, filled `02`, project test command | `tests/acceptance/**`, filled `03`, `QA_PASSED`/`REWORK_REQUIRED` | none (prompt workflow) |
| [`converge`](converge/SKILL.md) | Fold QA-confirmed deviations back into the spec and archive the bundle | `01`, filled `02` deviation log, checked `03` | Updated `.specs/02-tech-spec.md`, `CONVERGED` status, archived bundle | `converge.py` |

The first four skills produce the plan (`change` is the brownfield entry that reuses
`task-decomposition`), `plan-linter` validates its structure and emits Gate 2 heuristics, `review`
audits semantics (and can review a change), `dev`/`qa` execute and verify, and `converge` closes the
loop by writing confirmed behavior back into the spec. Skills are self-contained: each one bundles
the role boundaries it needs in its own `references/` directory. Repository role rules
(`.agents/rules/*.md`, including `enforcement.md`) are an optional suite layer that skills follow
when present, not a runtime dependency.

Platform-specific helpers may also live in this directory (for example a Windows sandbox
diagnostic skill when installed). They are not part of the specification pipeline and must declare a
`compatibility` field in their frontmatter.

---

## Discovery and installation

| Harness | Native location | Notes |
| :--- | :--- | :--- |
| Codex | `.agents/skills/<name>/` | Discovered from the current directory up to the repo root, and from `~/.agents/skills`. |
| Antigravity | `.agents/skills/<name>/` | Workspace scope; global scope is `~/.gemini/config/skills/`. |
| DeepSeek Harness (DSH) | `.agents/skills/<name>/` | Workspace skills are loaded directly. |
| Claude Code | `.claude/skills/<name>/` | Does **not** read `.agents/skills/`; use `tools/install_skills.py` to link or copy the same directories, or install the plugin. |

> Claude Code also supports symlinked skill directories, so one `install_skills.py` run keeps
> `.claude/skills/` pointing at `.agents/skills/` without duplicating files.

```bash
# Optional: install for personal / Claude Code use
python tools/install_skills.py --dest ~/.agents/skills
python tools/install_skills.py --dest .claude/skills --copy   # Windows fallback

# Adopt the whole suite into another repository (skills + rules + audit + CI templates)
python tools/quickstart.py --target ../another-repo --with-ci
```

The packaging tool (`package_skills.py`) is maintainer-only and lives in the upstream development
repository; this tree is its generated output.

The packaged tree is also a Claude Code plugin + one-plugin marketplace: after publishing it,
users run `/plugin marketplace add <owner>/agent-skills-suite` then
`/plugin install agent-skills-suite@agent-skills-market`. The plugin manifest points at
`.agents/skills/`, so every harness reads the same single copy.

Each skill is self-contained **as a prompt package**: `SKILL.md` + `references/` + `assets/templates/`
+ optional stdlib `scripts/`. No skill imports repository code and no skill requires a global CLI.
The optional `agent-spec-suite` Python package (the `prd_generator` / `spec_generator` engines) is an
accelerator only; if it is absent the skills continue with scaffolding + manual authoring + linting.

---

## Repository conventions (configurable)

The pipeline produces and consumes these conventions by default; each can be changed in the target
repository without editing skill code.

- **Specs**: `.specs/01-prd.md` + `.specs/01-prd/`; `.specs/02-tech-spec.md` + `.specs/02-tech-spec/`; `.specs/adr/*.md`.
- **Brownfield changes**: `.specs/changes/<change-id>/proposal.md` (+ `convergence.md` after convergence); optional `.specs/change-context/standards.md`.
- **Archives**: converged bundles move to `tasks/archive/<task-id>/`; nothing is deleted by a gate or by `converge`.
- **Tasks**: `tasks/<task-id>/` with four documents — `01-contract.md` (contract), `02-dev-workspace.md` (Dev), `03-qa-verification.md` (QA), `04-process.md` (derived audit trail; never hand-edited).
- **Goldilocks defaults**: at most 3 touched files, 50–250 estimated diff lines. Override in the linter config.
- **Traceability**: each task declares `origin_spec_anchor` (`#sec-*`) and `adherence_adrs`.
- **Agent rules**: `.agents/rules/*.md` for hosts that support rules; `AGENTS.md` for all others.

---

## Enforcement layers (honest model)

| Layer | Mechanism | Scope | Guarantee |
| :--- | :--- | :--- | :--- |
| L0 | Prompt rules + role instructions | every harness | advisory |
| L1 | `.agents/hooks.json` (Antigravity adapter) | Antigravity only | best effort; bypassable through shell/other tools |
| L2 | `tools/rbac_audit.py` in CI | every harness with git | authoritative for committed changes |
| L3 | Branch protection / code owners | repository settings | authoritative |

**Do not** describe L1 as "physical enforcement". The authoritative protection for the 4-document
protocol is CI plus repository permissions.

---

## Quality gates

1. **Gate 1 — deterministic**: `plan-linter` validates granularity, DoD, traceability, placeholders and DAG acyclicity.
   ```bash
   python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks
   python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks --json
   ```
2. **Gate 2 — semantic review**: a prompt-only anti-hallucination audit performed by a read-only reviewer
   agent (see `plan-linter/references/gate-2-review.md`). It is not automated; never claim it is.
   Gate 1 can pre-compute two heuristics for the reviewer: the spec anchor coverage matrix
   (`--spec`, `--coverage-out`) and the reverse topology check of declared paths (`--repo-root`).
3. **Convergence — after QA_PASSED**: `converge` writes the confirmed deviation log from `02` into
   `.specs/02-tech-spec.md` (append-only, with a marker), sets `04` to `CONVERGED` and archives the
   bundle. This is what keeps the spec a living document rather than a one-shot deliverable.

Exit codes for all bundled helpers: `0` success, `1` content/gate failure, `2` optional dependency or
usage unavailable, `3` unexpected error. Pass `--help` first; scripts are intended as black boxes.

---

## Versioning

- Skill versions are declared in each `SKILL.md` frontmatter (`metadata.version`).
- Layout/behavior changes are recorded in [`docs/skills-compatibility.md`](../../docs/skills-compatibility.md).
- No duplicated template or script copies exist outside these skill directories.

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
