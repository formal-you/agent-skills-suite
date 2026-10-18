#!/usr/bin/env python3
"""Assemble a clean, distributable copy of the agent-skill suite.

Copies only the skills, their rules, the helper tools, the CI templates,
the user-facing docs and the skill-related unit tests out of this repository into
a self-contained directory (and optionally a deterministic zip). The result does
not contain demo projects, generated artifacts, engines, specs, task bundles or
internal development reports (audit archive, pilot reports, design contracts); those
stay in the development repository.

Usage:
    python tools/package_skills.py --out ../agent-skills-v3 [--no-zip] [--force]
                                   [--dry-run] [--json] [--verify]

Exit codes: 0 success, 1 verification failure or existing output without --force,
2 usage error, 3 unexpected internal error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

__version__ = "3.1.0"
PACKAGE_VERSION = "3.1.0"

PLUGIN_NAME = "agent-skills-suite"
MARKETPLACE_NAME = "agent-skills-market"
DEFAULT_REPO_URL = "https://github.com/OWNER/agent-skills-suite"
SKILLS_SOURCE = ".agents/skills"
SKILLS_PACKAGE = "skills"
SKILL_CATEGORIES = {
    "diagnose-windows-sandbox-acl": "platform",
}
DEFAULT_SKILL_CATEGORY = "workflow"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT.parent / ("agent-skills-v" + PACKAGE_VERSION.split(".")[0])
PACKAGING_DIR = "packaging"

# User-facing documentation only. Development-process documents (audit archive, pilot
# report, v2 design contract) are deliberately not shipped; the benchmark scorecard is
# user-facing and stays.
DOC_FILES = (
    "docs/skills-guide.zh-CN.md",
    "docs/brownfield-convergence.zh-CN.md",
    "docs/skills-compatibility.md",
    "docs/skills-benchmark.zh-CN.md",
)

TEST_FILES = (
    "tests/unit/__init__.py",
    "tests/unit/test_plan_linter.py",
    "tests/unit/test_rbac_audit.py",
    "tests/unit/test_task_templates.py",
    "tests/unit/test_skill_scripts.py",
    "tests/unit/test_execution_skills.py",
    "tests/unit/test_review_skill.py",
    "tests/unit/test_change_skill.py",
    "tests/unit/test_converge.py",
    "tests/unit/test_distribution.py",
)

TOOL_FILES = (
    "tools/quickstart.py",
    "tools/install_skills.py",
    "tools/rbac_audit.py",
    "tools/package_skills.py",
)

TREE_DIRS = (
    ".agents/skills",
    ".agents/rules",
    "templates/ci",
)

SINGLE_FILES = (
    "AGENTS.md",
) + DOC_FILES + TEST_FILES + TOOL_FILES

IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".git"}

README_TEMPLATE = """# Agent Skills Suite v__VERSION__

[![CI](__REPO_URL__/actions/workflows/ci.yml/badge.svg)](__REPO_URL__/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-__VERSION__-blue.svg)](CHANGELOG.md)

Nine prompt-first, harness-neutral skills that turn an idea or an existing codebase into
planned, reviewed, implemented and spec-converged work - plus the rules, helper scripts and
CI templates that make the gates enforceable.

## Installation (30-second setup)

Pick **one** installer per agent: plugin installers update themselves, while the copied
files from `npx skills` are edited and updated by hand. Installing both gives you every
skill twice.

### Claude Code (plugin, updates itself)

@@@bash
/plugin marketplace add __SHORTHAND__
/plugin install __PLUGIN__@__MARKETPLACE__
@@@

Without a marketplace: `claude --plugin-dir /path/to/agent-skills-suite`.

### Codex (plugin marketplace)

@@@bash
codex plugin marketplace add __SHORTHAND__
codex plugin add __PLUGIN__@__MARKETPLACE__
@@@

### GitHub Copilot (CLI and VS Code)

@@@bash
copilot plugin marketplace add __SHORTHAND__
copilot plugin install __PLUGIN__@__MARKETPLACE__
@@@

### Gemini CLI (manual updates)

@@@bash
gemini skills install https://github.com/__SHORTHAND__.git --path skills/workflow
gemini skills install https://github.com/__SHORTHAND__.git --path skills/platform
@@@

### Any other agent, or editable files

@@@bash
# cursor, opencode, devin, windsurf, amp, pi; omit -a to choose interactively
npx skills@latest add __SHORTHAND__ -a <agent>
@@@

### Clone and install locally, or adopt into another repository

@@@bash
python tools/install_skills.py --dest ~/.agents/skills
python tools/install_skills.py --dest .claude/skills --copy   # Windows fallback
python tools/quickstart.py --target ../another-repo --copy --with-ci
@@@

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
| Any skill-aware agent | no | `npx skills@latest add __SHORTHAND__` |

## What is inside

| Directory | Contents |
| :--- | :--- |
| `skills/` | **installable layout**: `skills/<category>/<skill>/SKILL.md` (categories: `workflow`, `platform`). This is what skills.sh, Gemini and the plugin manifest read. |
| `.agents/skills/` | The same skill files under the AGENTS discovery path, kept byte-identical by `tools/package_skills.py` (used by tests and local installers). |
| `.agents/rules/` | Role rules (Planner, Dev, QA, Reviewer, Orchestrator, PM, Architect) plus the `enforcement.md` role matrix and honest enforcement model |
| `tools/` | `quickstart.py`, `install_skills.py`, `rbac_audit.py`, `package_skills.py` |
| `templates/ci/` | GitHub Actions: RBAC gate and Gate 1 plan gate |
| `docs/` | User guides: skills guide, brownfield/convergence guide, harness compatibility, benchmark report |
| `tests/unit/` | Black-box tests for the skills and helpers |
| `.claude-plugin/` | Claude Code plugin and marketplace manifests (skills point at `skills/`) |

Every skill directory is self-contained: `SKILL.md` only references files bundled inside that
directory, so plugin and per-skill installs need no extra checkout. Repository rules (`AGENTS.md`,
`.agents/rules/`) and the guides under `docs/` are optional context that skills follow when present.

## Pipeline

@@@text
idea    -> prd-generator -> spec-generator -> task-decomposition -> plan-linter -> review -> dev <-> qa -> converge
change  -> change (brownfield proposal + one task bundle) -> the same gates -> dev <-> qa -> converge
@@@

## Quality gates

1. **Gate 1 (deterministic):** `plan-linter` checks contract fields, DAG, placeholders, the
   change proposal, anchor coverage and real-file topology.
2. **Gate 2 (semantic):** an independent read-only reviewer audits truthfulness to the spec.
3. **Convergence:** after `QA_PASSED`, `converge` appends confirmed deviations to the spec,
   archives the task bundle and closes the change proposal.

@@@bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
@@@

## Docs

- `docs/skills-guide.zh-CN.md` - how the nine skills work and how to use them
- `docs/brownfield-convergence.zh-CN.md` - change proposals, convergence and Gate 2 heuristics
- `docs/skills-compatibility.md` - harness discovery, installation, enforcement layers
- `docs/skills-benchmark.zh-CN.md` - scorecard versus open-source alternatives
- `.agents/rules/enforcement.md` - role write scopes and the honest enforcement model

## Development

@@@bash
python -m unittest discover -s tests/unit -p "test_*.py"
claude plugin validate .
@@@

Python 3.9+ is optional: every skill has a manual fallback and no helper calls the network.

## Layout vs the upstream project

This tree is the distributable package. It contains no demo projects, generated artifacts,
optional spec engines, task workspaces or internal development reports; those stay in the
upstream development repository.

## License and contributions

MIT - see `LICENSE`. Contribution rules: `CONTRIBUTING.md`; release steps: `RELEASING.md`;
security policy: `SECURITY.md`.
"""


class PackageError(Exception):
    """Error carrying the process exit code."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def iter_files(root, directory):
    base = root / directory
    if not base.is_dir():
        return []
    files = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_NAMES for part in path.relative_to(root).parts):
            continue
        if path.suffix == ".pyc":
            continue
        files.append(path)
    return files


def collect(root):
    files = []
    for directory in TREE_DIRS:
        files.extend(iter_files(root, directory))
    for relative in SINGLE_FILES:
        path = root / relative
        if path.is_file():
            files.append(path)
    missing = [relative for relative in SINGLE_FILES if not (root / relative).is_file()]
    if missing:
        raise PackageError("missing required sources: " + ", ".join(sorted(missing)), 2)
    packaging = iter_files(root, PACKAGING_DIR)
    if not packaging:
        raise PackageError("missing release files under " + PACKAGING_DIR + "/", 2)
    return (
        sorted(files, key=lambda path: path.relative_to(root).as_posix()),
        packaging,
    )


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(out):
    lines = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        lines.append(sha256(path) + "  " + path.relative_to(out).as_posix())
    return "\n".join(lines) + "\n"


def write_zip(out, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(out).as_posix()
            info = zipfile.ZipInfo(relative)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def repo_shorthand(repo_url):
    text = repo_url.rstrip("/")
    for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
        if text.startswith(prefix):
            return text[len(prefix):].removesuffix(".git")
    return text


def mirror_skills(root, out):
    """Copy .agents/skills/<name> to skills/<category>/<name> for skills.sh and plugins."""
    source = root / SKILLS_SOURCE
    if not source.is_dir():
        raise PackageError("missing skill sources: " + SKILLS_SOURCE, 2)
    mirrored = []
    for skill_dir in sorted(source.iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
            continue
        category = SKILL_CATEGORIES.get(skill_dir.name, DEFAULT_SKILL_CATEGORY)
        destination = out / SKILLS_PACKAGE / category / skill_dir.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            skill_dir,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        mirrored.append(destination.relative_to(out).as_posix())
    if not mirrored:
        raise PackageError("no SKILL.md found under " + SKILLS_SOURCE, 2)
    return mirrored


def write_skills_index(out, mirrored):
    header = (
        "# Skills\n\n"
        "Installable layout: one directory per skill, grouped by category. The same SKILL.md\n"
        "files are kept under `.agents/skills/` for harnesses that discover that path; both\n"
        "trees are generated from the same source.\n\n"
        "| Category | Skills |\n"
        "| :--- | :--- |\n"
    )
    by_category = {}
    for relative in mirrored:
        parts = Path(relative).parts
        by_category.setdefault(parts[1], []).append(parts[2])
    rows = []
    for category in sorted(by_category):
        names = ", ".join(sorted(by_category[category]))
        rows.append("| " + category + " | " + names + " |")
    (out / SKILLS_PACKAGE / "README.md").write_text(
        header + "\n".join(rows) + "\n", encoding="utf-8"
    )


def write_release_metadata(out, repo_url, mirrored_skills):
    plugin = {
        "name": PLUGIN_NAME,
        "displayName": "Agent Skills Suite",
        "version": PACKAGE_VERSION,
        "description": (
            "Nine prompt-first skills for spec-driven, role-isolated, verifiable agent "
            "development: PRD to spec to tasks, Gate 1/2 review, dev, QA and convergence."
        ),
        "author": {"name": "Agent Skills Suite contributors"},
        "homepage": repo_url,
        "repository": repo_url,
        "license": "MIT",
        "keywords": [
            "agent-skills",
            "spec-driven-development",
            "brownfield",
            "code-review",
            "qa",
            "multi-agent",
            "claude-code",
            "codex",
            "antigravity",
        ],
        "skills": ["./" + relative + "/" for relative in mirrored_skills],
    }
    marketplace = {
        "name": MARKETPLACE_NAME,
        "description": "Agent Skills Suite: spec-driven development skills for coding agents.",
        "owner": {"name": "Agent Skills Suite contributors"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": "./",
                "description": "Nine prompt-first skills with deterministic gates and convergence.",
                "version": PACKAGE_VERSION,
            }
        ],
    }
    plugin_dir = out / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin, indent=2) + "\n", encoding="utf-8"
    )
    (plugin_dir / "marketplace.json").write_text(
        json.dumps(marketplace, indent=2) + "\n", encoding="utf-8"
    )
    readme = README_TEMPLATE
    for token, value in (
        ("__VERSION__", PACKAGE_VERSION),
        ("__REPO_URL__", repo_url),
        ("__SHORTHAND__", repo_shorthand(repo_url)),
        ("__PLUGIN__", PLUGIN_NAME),
        ("__MARKETPLACE__", MARKETPLACE_NAME),
    ):
        readme = readme.replace(token, value)
    readme = readme.replace("@@@", "`" * 3).replace("@@", "`")
    (out / "README.md").write_text(readme, encoding="utf-8")


def assemble(root, out, force, repo_url):
    if out.exists():
        if not force:
            raise PackageError("output already exists: " + str(out) + " (pass --force to replace)", 1)
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files, packaging = collect(root)
    for source in files:
        destination = out / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for source in packaging:
        destination = out / source.relative_to(root / PACKAGING_DIR)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    mirrored = mirror_skills(root, out)
    write_skills_index(out, mirrored)
    (out / "VERSION").write_text(PACKAGE_VERSION + "\n", encoding="utf-8")
    write_release_metadata(out, repo_url, mirrored)
    manifest = build_manifest(out)
    (out / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return files, packaging


def build_parser():
    parser = argparse.ArgumentParser(
        prog="package_skills.py",
        description="Copy the skill suite into a publishable package with plugin manifests.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory (default: " + str(DEFAULT_OUT) + ")")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL,
                        help="public repository URL written into plugin/README metadata")
    parser.add_argument("--no-zip", action="store_true", help="skip the deterministic .zip next to --out")
    parser.add_argument("--force", action="store_true", help="replace an existing output directory")
    parser.add_argument("--dry-run", action="store_true", help="list the files that would be copied")
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    parser.add_argument("--verify", action="store_true", help="run the packaged unit tests after building")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def run(args):
    root = REPO_ROOT
    out = Path(args.out).expanduser().resolve()
    if out == root or root in out.parents:
        raise PackageError("--out must be outside the source repository: " + str(out), 2)
    if out == out.parent or out.name in ("", ".", ".."):
        raise PackageError("--out must be a dedicated directory, not a filesystem root", 2)
    files, packaging = collect(root)
    if args.dry_run:
        for path in files + packaging:
            print("[dry-run] would copy " + path.relative_to(root).as_posix())
        print("[dry-run] " + str(len(files) + len(packaging)) + " files; no files written")
        return 0
    files, packaging = assemble(root, out, args.force, args.repo_url)
    zip_path = None
    if not args.no_zip:
        zip_path = out.with_suffix(".zip")
        write_zip(out, zip_path)
    verified = None
    if args.verify:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_*.py"],
            cwd=str(out),
            capture_output=True,
            text=True,
        )
        verified = result.returncode == 0
        if not verified:
            sys.stderr.write(result.stdout[-2000:] + result.stderr[-2000:])
            raise PackageError("packaged tests failed", 1)
    payload = {
        "tool": "package_skills",
        "version": PACKAGE_VERSION,
        "out": str(out),
        "zip": str(zip_path) if zip_path else None,
        "files": len(files) + len(packaging) + 4,
        "plugin": PLUGIN_NAME,
        "marketplace": MARKETPLACE_NAME,
        "repo_url": args.repo_url,
        "verified": verified,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("packaged " + str(payload["files"]) + " files into " + str(out))
        print("plugin: " + PLUGIN_NAME + " (marketplace: " + MARKETPLACE_NAME + ")")
        if zip_path:
            print("wrote " + str(zip_path))
        if verified is not None:
            print("packaged tests: " + ("passed" if verified else "FAILED"))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except PackageError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return exc.code
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        sys.stderr.write("error: unexpected failure: " + str(exc) + "\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
