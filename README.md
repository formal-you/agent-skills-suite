# Agent Skills Suite v3.2.0

[![CI](https://github.com/formal-you/agent-skills-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/formal-you/agent-skills-suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.2.0-blue.svg)](CHANGELOG.md)

Ten prompt-first, harness-neutral skills that turn an idea or an existing codebase into
planned, reviewed, implemented and spec-converged work - plus the rules, helper scripts and
CI templates that make the gates enforceable.

## Installation (30-second setup)

Pick **one** installer per agent: plugin installers update themselves, while the copied
files from `npx skills` are edited and updated by hand. Installing both gives you every
skill twice.

### Claude Code (plugin, updates itself)

```bash
/plugin marketplace add formal-you/agent-skills-suite
/plugin install agent-skills-suite@agent-skills-market
```

Without a marketplace: `claude --plugin-dir /path/to/agent-skills-suite`.

### Codex (plugin marketplace)

```bash
codex plugin marketplace add formal-you/agent-skills-suite
codex plugin add agent-skills-suite@agent-skills-market
```

### GitHub Copilot (CLI and VS Code)

```bash
copilot plugin marketplace add formal-you/agent-skills-suite
copilot plugin install agent-skills-suite@agent-skills-market
```

### Gemini CLI (manual updates)

```bash
gemini skills install https://github.com/formal-you/agent-skills-suite.git --path skills/workflow
gemini skills install https://github.com/formal-you/agent-skills-suite.git --path skills/platform
```

### Any other agent, or editable files

```bash
# cursor, opencode, devin, windsurf, amp, pi; omit -a to choose interactively
npx skills@latest add formal-you/agent-skills-suite -a <agent>
```

### Clone and install locally, or adopt into another repository

```bash
python tools/install_skills.py --dest ~/.agents/skills
python tools/install_skills.py --dest .claude/skills --copy   # Windows fallback
python tools/quickstart.py --target ../another-repo --copy --with-ci
```

## After cloning: who sees the skills automatically

`.agents/skills/` is the Codex/AGENTS convention. Claude Code does **not** read it:
its project location is `.claude/skills/`, its personal location is `~/.claude/skills/`,
and plugins load from `<plugin>/skills/` (this repository ships both layouts, generated
from one source).

| Harness | Cloning this repo is enough? | What to do |
| :--- | :--- | :--- |
| Codex | yes | `.agents/skills/` is scanned from the current directory up to the repo root; user scope is `~/.agents/skills/` |
| DSH / Antigravity | yes | workspace `.agents/skills/` |
| Claude Code | no | install the plugin, or run `python tools/install_skills.py --dest .claude/skills` (add `--copy` on Windows); `claude --plugin-dir .` also works |
| Gemini CLI | no | `gemini skills install <repo-url>.git --path skills/workflow` |
| Any skill-aware agent | no | `npx skills@latest add formal-you/agent-skills-suite` |

## What is inside

| Directory | Contents |
| :--- | :--- |
| `skills/` | **installable layout**: `skills/<category>/<skill>/SKILL.md` (categories: `workflow`, `platform`). This is what skills.sh, Gemini and the plugin manifest read. |
| `.agents/skills/` | The same skill files under the AGENTS discovery path, kept byte-identical by the upstream packaging build (used by tests and local installers) |
| `.agents/rules/` | Role rules (Planner, Dev, QA, Reviewer, Orchestrator, PM, Architect) plus the `enforcement.md` role matrix and honest enforcement model |
| `tools/` | `quickstart.py`, `install_skills.py`, `rbac_audit.py`, `mutation_gate.py` |
| `templates/ci/` | GitHub Actions: full quality gate (Python reference), RBAC gate, Gate 1 plan gate, and per-stack profiles |
| `docs/` | User guides: skills guide, brownfield/convergence guide, harness compatibility, benchmark report |
| `tests/unit/` | Black-box tests for the skills and helpers |
| `.claude-plugin/` | Claude Code plugin and marketplace manifests (skills point at `skills/`) |

Every skill directory is self-contained: `SKILL.md` only references files bundled inside that
directory, so plugin and per-skill installs need no extra checkout. Repository rules (`AGENTS.md`,
`.agents/rules/`) and the guides under `docs/` are optional context that skills follow when present.

## Pipeline

```text
idea    -> prd-generator -> spec-generator -> task-decomposition -> plan-linter -> review -> dev <-> qa -> quality-engineering (Gate 3 + mutation) -> converge
change  -> change (brownfield proposal + one task bundle) -> the same gates -> dev <-> qa -> quality-engineering -> converge
```

## Quality gates

1. **Gate 1 (deterministic):** `plan-linter` checks contract fields, DAG, placeholders, the
   change proposal, anchor coverage and real-file topology.
2. **Gate 2 (semantic):** an independent read-only reviewer audits truthfulness to the spec.
3. **Gate 3 (evidence):** `verification_linter.py` cross-checks `03` V(G) against the live AST
   artifact and audits basis-path coverage plus MSI (80%, 90% for `risk_level: core`).
4. **Mutation gate:** `tools/mutation_gate.py` runs the project's mutation command on trunk and
   fails closed on a missing report or low MSI.
5. **Convergence:** after `QA_PASSED`, `converge` appends confirmed deviations to the spec,
   archives the task bundle and closes the change proposal.

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks   --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
```

## Docs

- `docs/skills-guide.zh-CN.md` - how the ten skills work and how to use them
- `docs/brownfield-convergence.zh-CN.md` - change proposals, convergence and Gate 2 heuristics
- `docs/skills-compatibility.md` - harness discovery, installation, enforcement layers
- `docs/ci-stack-profiles.zh-CN.md` - Python/Node/Go/Java/Rust/.NET/C++ CI profile adoption
- `docs/skills-benchmark.zh-CN.md` - scorecard versus open-source alternatives
- `.agents/rules/enforcement.md` - role write scopes and the honest enforcement model

## Development

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
claude plugin validate .
```

Python 3.9+ is optional: every skill has a manual fallback and no helper calls the network.

The packaging tool that regenerates this tree (`package_skills.py`) is maintainer-only and lives in
the upstream development repository; it is not shipped here.

## Layout vs the upstream project

This tree is the distributable package. It contains no demo projects, generated artifacts,
optional spec engines, task workspaces or internal development reports; those stay in the
upstream development repository.

## License and contributions

MIT - see `LICENSE`. Contribution rules: `CONTRIBUTING.md`; release steps: `RELEASING.md`;
security policy: `SECURITY.md`.
