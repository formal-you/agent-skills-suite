# Agent Skills Suite v3.1.0

[![CI](https://github.com/formal-you/agent-skills-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/formal-you/agent-skills-suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](CHANGELOG.md)

Nine prompt-first, harness-neutral skills that turn an idea or an existing codebase into
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

## What is inside

| Directory | Contents |
| :--- | :--- |
| `skills/` | **installable layout**: `skills/<category>/<skill>/SKILL.md` (categories: `workflow`, `platform`). This is what skills.sh, Gemini and the plugin manifest read. |
| `.agents/skills/` | The same skill files under the AGENTS discovery path, kept byte-identical by `tools/package_skills.py` (used by tests and local installers). |
| `.agents/rules/` | Role rules (Planner, Dev, QA, Reviewer, Orchestrator, PM, Architect) |
| `.agents/scripts/` | Optional local hook adapters (`rbac_guard.py`, `event_bus_logger.py`) |
| `.agents/hooks.json` | Optional Antigravity hook wiring (best effort; CI is authoritative) |
| `tools/` | `quickstart.py`, `install_skills.py`, `rbac_audit.py`, `package_skills.py` |
| `templates/ci/` | GitHub Actions: RBAC gate and Gate 1 plan gate |
| `docs/` | Skills guide, brownfield/convergence guide, compatibility, design contract, benchmark, pilot report, audit |
| `tests/unit/` | Black-box tests for the skills and helpers |
| `.claude-plugin/` | Claude Code plugin and marketplace manifests (skills point at `skills/`) |

## Pipeline

```text
idea    -> prd-generator -> spec-generator -> task-decomposition -> plan-linter -> review -> dev <-> qa -> converge
change  -> change (brownfield proposal + one task bundle) -> the same gates -> dev <-> qa -> converge
```

## Quality gates

1. **Gate 1 (deterministic):** `plan-linter` checks contract fields, DAG, placeholders, the
   change proposal, anchor coverage and real-file topology.
2. **Gate 2 (semantic):** an independent read-only reviewer audits truthfulness to the spec.
3. **Convergence:** after `QA_PASSED`, `converge` appends confirmed deviations to the spec,
   archives the task bundle and closes the change proposal.

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks   --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
```

## Docs

- `docs/skills-guide.zh-CN.md` - how the nine skills work and how to use them
- `docs/brownfield-convergence.zh-CN.md` - change proposals, convergence and Gate 2 heuristics
- `docs/skills-compatibility.md` - harness discovery, installation, enforcement layers
- `docs/skills-v2-spec.md` - design contract (with v3 addendum)
- `docs/skills-benchmark.zh-CN.md` - scorecard versus open-source alternatives
- `docs/v3-pilot.zh-CN.md` - a real repository pilot with evidence
- `docs/audit/` - audit findings and evidence

## Development

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
claude plugin validate .
```

Python 3.9+ is optional: every skill has a manual fallback and no helper calls the network.

## Layout vs the upstream project

This tree is the distributable package. It contains no demo projects, generated artifacts,
optional spec engines or task workspaces; those stay in the upstream development repository.

## License and contributions

MIT - see `LICENSE`. Contribution rules: `CONTRIBUTING.md`; release steps: `RELEASING.md`;
security policy: `SECURITY.md`.
