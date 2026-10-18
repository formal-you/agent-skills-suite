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

## Discovery matrix

| Harness | Native location | Rules mechanism | Hooks / enforcement |
| :--- | :--- | :--- | :--- |
| OpenAI Codex | `.agents/skills/` (scanned from CWD to repo root) and `~/.agents/skills/` | `AGENTS.md` | no hook contract used; rely on CI audit |
| Google Antigravity | `.agents/skills/` (legacy `.agent/skills/`) and `~/.gemini/config/skills/` | `.agents/rules/*.md` with `trigger:` frontmatter, plus `AGENTS.md` | optional `.agents/hooks.json` adapter (best effort) |
| Claude Code | `.claude/skills/<name>/` (personal `~/.claude/skills/`) | `CLAUDE.md` / rules | optional `.claude/settings.json` hooks; not installed by default |
| DeepSeek Harness (DSH) | `.agents/skills/` | `AGENTS.md` | no hook contract used; rely on CI audit |
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

It installs skills into `--dest` (default `.agents/skills/`), the rules, scripts and
hooks, `tools/rbac_audit.py`, and, with `--with-ci`, the GitHub Actions workflows from
`templates/ci/`: `rbac-gate.yml` (L2 RBAC audit on every pull request) and
`plan-gate.yml` (Gate 1 on `tasks/**` and `.specs/**` changes). Both need only
`permissions: contents: read`; `rbac-gate.yml` also needs `fetch-depth: 0`. The audit
workflow resolves the role from the repository variable `RBAC_ROLE` or from the
`Agent-Role:` commit trailer. Installation, pinning and troubleshooting are documented
in `templates/ci/README.md`.

CI is the authoritative layer; `.agents/hooks.json` remains best-effort. Pin adoption to
a tag or commit SHA and commit the copies, so upgrades stay reviewable diffs.

## Enforcement layers

The 4-document workflow and role isolation are repository conventions. Enforcement is
layered, and only the lower layers are authoritative:

| Layer | Mechanism | Scope | Guarantee |
| :--- | :--- | :--- | :--- |
| L0 | Prompt rules (`AGENTS.md`, role rules) and skill instructions | every harness | advisory |
| L1 | `.agents/hooks.json` (Antigravity adapter) | Antigravity only | best effort; bypassable through shell commands or other tools |
| L2 | `tools/rbac_audit.py` in CI (git diff + declared role) | any git repository | authoritative for committed changes |
| L3 | Branch protection, required reviewers, CODEOWNERS | repository settings | authoritative |

Do not describe L1 as physical enforcement. The authoritative protection is CI plus
repository permissions. Removing `.agents/hooks.json` must not break any skill or workflow.

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
- Layout or behavior changes must update this document and
  [`docs/skills-v2-spec.md`](./skills-v2-spec.md).
- `.agents/skills/` remains the only place where templates and helper scripts live.
