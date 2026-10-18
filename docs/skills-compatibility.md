# Skills Compatibility

This document states exactly how the skills in [`.agents/skills/`](../.agents/skills/README.md)
are discovered, installed and enforced on each supported harness. It is deliberately
honest about what is universal and what is host-specific.

## Canonical layout

```text
.agents/skills/<skill>/
  SKILL.md          # required; frontmatter name must equal the directory name
  references/       # optional deep docs and optional zh-CN translations
  assets/templates/ # optional canonical templates
  scripts/          # optional stdlib helpers (scaffold, lint, optional engine proxy)
```

`.agents/skills/` is the single source of truth. There are no duplicate template or script
copies at the repository root.

## Self-containment and plugin packaging

Every skill is self-contained: its `SKILL.md` references only files inside its own directory
(`references/`, `assets/`, `scripts/`). Role boundaries are bundled per skill (for example
`references/role-boundaries.md`), so a skill installed on its own still works.

Repository role rules (`.agents/rules/*.md`, including `enforcement.md`), `AGENTS.md`, `tools/`,
`templates/ci/` and the guides under `docs/` are an **optional suite layer**. Skills follow them
when the adopting repository has them, but they are not runtime dependencies.

| Install path | What is shipped | Why it works |
| :--- | :--- | :--- |
| Claude Code / Codex / Copilot plugin | the plugin tree; each listed skill directory is loaded with its bundled files | `SKILL.md` only reaches into its own directory |
| `npx skills add` / Gemini `--path skills/<category>` | one skill directory | the same bundled files travel with it |
| `tools/install_skills.py` | skill directories only | rules and docs are not required |
| `tools/quickstart.py --with-rules --with-ci` | skills + rules + CI templates | adds the optional suite layer for adopters |

Command examples inside a `SKILL.md` use the repository-adoption path
(`.agents/skills/<name>/scripts/...`). When a skill is installed elsewhere, run the same script from
that skill's own `scripts/` directory; the scripts resolve their resources relative to their
location.

## Discovery matrix

| Harness | Native location | Rules mechanism | Enforcement |
| :--- | :--- | :--- | :--- |
| OpenAI Codex | `.agents/skills/` (scanned from CWD to repo root) and `~/.agents/skills/` | `AGENTS.md` | advisory prompt rules; CI audit |
| Google Antigravity | `.agents/skills/` (legacy `.agent/skills/`) and `~/.gemini/config/skills/` | `.agents/rules/*.md` with `trigger:` frontmatter, plus `AGENTS.md` | advisory prompt rules; CI audit (no local hook adapter shipped) |
| Claude Code | `.claude/skills/<name>/` (personal `~/.claude/skills/`) | `CLAUDE.md` / rules | advisory prompt rules; CI audit |
| DeepSeek Harness (DSH) | `.agents/skills/` | `AGENTS.md` | advisory prompt rules; CI audit |
| Generic agent | manual paste / skill directory | project prompt | none |

### After cloning: who sees what automatically

`.agents/skills/` is the AGENTS/Codex convention. **Claude Code does not read it**: its
project location is `.claude/skills/`, its personal location is `~/.claude/skills/`, and
plugins load skills from `<plugin>/skills/`. That is why this repository ships three
equivalent surfaces (all generated from one source):

| Surface in this repo | Used by |
| :--- | :--- |
| `.agents/skills/<name>/` | Codex, DSH, Antigravity: scanned automatically from the CWD up to the repo root (and `~/.agents/skills` for user scope) |
| `skills/<category>/<name>/` | skills.sh / `npx skills`, Gemini `--path`, and the plugin manifest; this is the installable layout |
| `.claude-plugin/plugin.json` | Claude Code plugin: `/plugin marketplace add ...` then install; or `claude --plugin-dir <repo>` |

| Harness | Clone the repo and open it | One extra command (optional) |
| :--- | :--- | :--- |
| Codex | Skills are found in `.agents/skills/` automatically | none (or add `~/.agents/skills`) |
| DSH / Antigravity | Skills are found in `.agents/skills/` automatically | none |
| Claude Code | **Not automatic**: `.agents/skills/` is ignored | `python tools/install_skills.py --dest .claude/skills` (symlinks; add `--copy` on Windows) or install the plugin |
| Gemini CLI | Repo layout is `skills/<category>/` | `gemini skills install <repo-url>.git --path skills/workflow` |
| Any skill-aware agent | - | `npx skills@latest add <owner>/<repo>` |

Claude Code **does** follow symlinked skill directories (one symlink per skill is the
supported form), so the installer can link each `.claude/skills/<name>` to
`.agents/skills/<name>` and updates stay in one place.

## Installation

The skills are always usable in place. `tools/install_skills.py` adds per-user or
Claude Code installs:

```bash
# Link every skill to ~/.agents/skills and ~/.claude/skills
python tools/install_skills.py

# One destination, copies instead of symlinks (Windows fallback)
python tools/install_skills.py --dest ~/.claude/skills --copy

# One skill, replace an existing install
python tools/install_skills.py --dest .claude/skills --skills plan-linter --force
```

Symlinks are preferred; when the platform refuses one (Windows without Developer Mode),
the tool falls back to a copy and reports it. `--dry-run` prints the plan without writing.
Exit codes: `0` success, `1` install failure, `2` usage error.

## Distribution and CI adoption

`tools/quickstart.py` adopts the suite into another repository in one command:

```bash
uv run tools/quickstart.py --target ../adopting-repo --copy --with-ci
```

It installs skills into `--dest` (default `.agents/skills/`), the rules,
`tools/rbac_audit.py`, and, with `--with-ci`, the GitHub Actions workflows from
`templates/ci/`: `rbac-gate.yml` (L1 RBAC audit on every pull request),
`plan-gate.yml` (Gate 1 on `tasks/**` and `.specs/**` changes), and `quality-gate.yml`
(multi-stage quality gate owned by `quality-engineering`: Gate 1, RBAC, complexity check,
acceptance tests, and Gate 3 audit). All workflows need only `permissions: contents: read`;
`rbac-gate.yml` and `quality-gate.yml` also need `fetch-depth: 0`. The audit
workflow resolves the role from the repository variable `RBAC_ROLE` or from the
`Agent-Role:` commit trailer. Installation, pinning and troubleshooting are documented
in `templates/ci/README.md`.

CI is the authoritative layer. Pin adoption to
a tag or commit SHA and commit the copies, so upgrades stay reviewable diffs.

## Enforcement layers

The 4-document workflow and role isolation are repository conventions. Enforcement is
layered, and only the lower layers are authoritative:

| Layer | Mechanism | Scope | Guarantee |
| :--- | :--- | :--- | :--- |
| L0 | Prompt rules (`AGENTS.md`, role rules) and skill instructions | every harness | advisory |
| L1 | `tools/rbac_audit.py` in CI (git diff + declared role) | any git repository | authoritative for committed changes |
| L2 | Branch protection, required reviewers, CODEOWNERS | repository settings | authoritative |

Prompt rules are **not** physical enforcement. The authoritative protection is L1 plus repository
permissions. This package ships no local hook adapter; adopters may add host-side hooks, but they
remain best-effort and bypassable.

## Optional Python engine

The `prd_generator` / `spec_generator` packages are an optional accelerator, distributed
as `agent-spec-suite`. Skills never import them through `sys.path` and never require a
global CLI.

| Environment | Behavior |
| :--- | :--- |
| No Python, no engine | Full prompt workflow; manual fallback in each SKILL.md |
| Python, no engine | scaffold/lint helpers work; `scripts/engine.py` exits `2` with install guidance |
| Engine installed | `engine.py` forwards to the engine; scaffold/lint still work |
| CI | Gates run with the engine installed or with the stdlib helpers |

## Helper contract

All bundled helpers are stdlib-only Python (`>=3.9`), resolve paths from their own
location, never write outside their output directory, and support `--help` and
`--version`.

| Exit code | Meaning |
| :--- | :--- |
| `0` | success |
| `1` | content or gate failure |
| `2` | optional dependency unavailable, missing target, or usage error |
| `3` | unexpected internal error |

Install guidance for the optional engine:

```bash
uv tool install agent-spec-suite     # or: pip install agent-spec-suite
```

## Platform-specific skill

`diagnose-windows-sandbox-acl` is bundled for Windows/DSH sandbox ACL diagnosis only. It
is not part of the PRD -> spec -> task pipeline; install it only on Windows hosts
where DSH sandbox ACL diagnosis is relevant.

## Versioning and change notes

- Each skill declares `metadata.version` in `SKILL.md`.
- Layout or behavior changes must update this document and the affected `SKILL.md`
  files, and must be recorded in `CHANGELOG.md`.
- `.agents/skills/` remains the only place where templates and helper scripts live.
