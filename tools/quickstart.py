#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""One-command adoption of the agent-spec skill suite into another repository.

Usage:
    uv run tools/quickstart.py --target ../my-repo
    python tools/quickstart.py --target ../my-repo --copy --with-ci

The installer copies or links, from this checkout into --target:

    .agents/skills/<name>   (selected skills; --dest controls the destination root)
    .agents/rules/*.md      (unless --no-with-rules)
    .github/workflows/*.yml (only with --with-ci)

The gate scripts and CI templates live inside the quality-engineering skill, so --with-ci reads
templates/ci/*.yml from <skill>/assets/templates/ci/ and guarantees that skill is selected. It
never writes anything outside .agents/skills/, .agents/rules/ and .github/workflows/.

It never writes outside --target, refuses to replace an existing item without --force, and
skips symlinks that already point at the same source. The file is self-contained: it needs
the Python standard library only and can be copied on its own next to the suite checkout.

Exit codes:
    0 success (skips count as success)
    1 one or more items failed to install
    2 usage error (bad flags, unknown skill, unsafe destination)
    3 unexpected internal error
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

VERSION = "4.0.0"
DEFAULT_DEST = ".agents/skills"
QUALITY_ENGINEERING = "quality-engineering"
SKIP_DIRS = {"__pycache__", ".git"}
SHELL_SPECIAL = set(' \t"\'$&|;<>()' + chr(96))

TOOL_PATH = Path(__file__).resolve()
SOURCE_ROOT = TOOL_PATH.parent.parent


def ci_templates_dir():
    """CI workflow templates bundled inside the quality-engineering skill."""
    return SOURCE_ROOT / ".agents" / "skills" / QUALITY_ENGINEERING / "assets" / "templates" / "ci"


class UsageError(Exception):
    """A CLI or safety problem: exit code 2."""


class InstallItem(object):
    """One source/destination pair planned by the installer."""

    __slots__ = ("kind", "name", "source", "destination")

    def __init__(self, kind, name, source, destination):
        self.kind = kind
        self.name = name
        self.source = Path(source)
        self.destination = Path(destination)

    def as_dict(self, status, detail):
        return {
            "kind": self.kind,
            "name": self.name,
            "source": str(self.source),
            "destination": str(self.destination),
            "status": status,
            "detail": detail,
        }


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def _absolute(path):
    return Path(os.path.abspath(str(path)))


def _real(path):
    return Path(os.path.realpath(str(path)))


def _is_within(child, root):
    child_text = os.path.normcase(os.path.abspath(str(child)))
    root_text = os.path.normcase(os.path.abspath(str(root)))
    try:
        return os.path.commonpath([child_text, root_text]) == root_text
    except ValueError:  # different drives on Windows
        return False


def destination_problem(destination, target):
    """Return a message when writing to destination would leave target, else None."""
    destination = Path(destination)
    if not _is_within(_absolute(destination), _absolute(target)):
        return "destination escapes --target: " + str(destination)
    parent_real = _real(destination.parent)
    if not _is_within(parent_real, _real(target)):
        return "destination parent resolves outside --target: " + str(destination)
    return None


def validate_dest(raw):
    """Validate --dest as a safe path relative to --target."""
    text = str(raw).strip()
    if not text:
        raise UsageError("--dest must not be empty")
    path = Path(text)
    if path.is_absolute() or path.drive:
        raise UsageError("--dest must be a path relative to --target, not " + repr(text))
    parts = [part for part in path.parts if part not in ("", ".")]
    if ".." in parts:
        raise UsageError("--dest must not contain '..': " + repr(text))
    if not parts:
        return Path(".")
    return Path(*parts)


def resolve_target(raw):
    if raw is None or not str(raw).strip():
        raise UsageError("--target is required (the repository to install into)")
    text = str(raw).strip()
    target = _absolute(Path(text).expanduser())
    if target.exists() and not target.is_dir():
        raise UsageError("--target is not a directory: " + str(target))
    return target


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


def available_skills():
    skills_root = SOURCE_ROOT / ".agents" / "skills"
    if not skills_root.is_dir():
        raise UsageError("no skill suite found at " + str(skills_root))
    return sorted(
        path
        for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file() and path.name not in SKIP_DIRS
    )


def parse_skills(raw, names):
    if not raw:
        return list(names)
    requested = []
    for item in raw.split(","):
        name = item.strip()
        if not name:
            raise UsageError("--skills must be a comma-separated list of skill names")
        if name in (".", "..") or "/" in name or "\\" in name or ":" in name:
            raise UsageError("invalid skill name: " + repr(name))
        if name not in names:
            raise UsageError(
                "unknown skill: " + repr(name) + " (available: " + ", ".join(names) + ")"
            )
        if name not in requested:
            requested.append(name)
    return [name for name in names if name in requested]


def build_items(target, dest_root, selected, with_rules, with_ci):
    """Return (items, problems) where problems are source-side failure messages."""
    items = []
    problems = []
    for skill in selected:
        items.append(InstallItem("skill", skill.name, skill, dest_root / skill.name))

    if with_rules:
        rules_root = SOURCE_ROOT / ".agents" / "rules"
        rules_dest = target / ".agents" / "rules"
        rule_files = sorted(rules_root.glob("*.md")) if rules_root.is_dir() else []
        if not rule_files:
            problems.append("no rule files found at " + str(rules_root))
        for path in rule_files:
            items.append(InstallItem("rule", path.name, path, rules_dest / path.name))

    if with_ci:
        ci_root = ci_templates_dir()
        workflows_dest = target / ".github" / "workflows"
        workflows = sorted(ci_root.glob("*.yml")) if ci_root.is_dir() else []
        if not workflows:
            problems.append(
                "no CI workflow templates found at " + str(ci_root)
                + " (is the quality-engineering skill present?)"
            )
        for path in workflows:
            items.append(InstallItem("ci", path.name, path, workflows_dest / path.name))
    return items, problems


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------


def _copy_ignore(directory, names):
    return [name for name in names if name in SKIP_DIRS or name.endswith(".pyc")]


def _remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(str(path))


def install_item(item, target, copy_mode, force, dry_run):
    destination = item.destination
    if destination.is_symlink():
        try:
            if _real(destination) == _real(item.source):
                return "skipped", "already linked to the source"
        except OSError:
            pass
    if destination.exists() or destination.is_symlink():
        if not force:
            return "skipped", "destination exists (use --force to replace)"

    problem = destination_problem(destination, target)
    if problem:
        return "error", problem

    if dry_run:
        return ("planned-copy" if copy_mode else "planned-link"), str(destination)

    symlink_error = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            _remove(destination)
        if not copy_mode:
            try:
                os.symlink(
                    str(item.source),
                    str(destination),
                    target_is_directory=item.source.is_dir(),
                )
                return "linked", str(destination)
            except (OSError, NotImplementedError) as exc:
                symlink_error = exc
        if item.source.is_dir():
            shutil.copytree(str(item.source), str(destination), ignore=_copy_ignore)
        else:
            shutil.copy2(str(item.source), str(destination))
        if symlink_error is not None:
            return "copied", str(destination) + " (copy fallback: " + type(symlink_error).__name__ + ")"
        return "copied", str(destination)
    except OSError as exc:
        return "error", "cannot install " + str(destination) + ": " + str(exc)


# ---------------------------------------------------------------------------
# One-line command
# ---------------------------------------------------------------------------


def _quote(part):
    if part and not any(character in SHELL_SPECIAL for character in part):
        return part
    return '"' + part.replace('"', '\\"') + '"'


def print_oneliner_command(args):
    """Render the equivalent command for another machine as a single line."""
    if TOOL_PATH == _absolute(Path("tools") / "quickstart.py"):
        script = "tools/quickstart.py"
    else:
        script = str(TOOL_PATH)
    runner = "uv run" if shutil.which("uv") else "python"
    parts = [script]
    parts.extend(["--target", args.target if args.target else "TARGET_REPO_PATH"])
    dest = args.dest if args.dest else DEFAULT_DEST
    if dest != DEFAULT_DEST:
        parts.extend(["--dest", dest])
    if args.skills:
        parts.extend(["--skills", args.skills])
    if args.copy:
        parts.append("--copy")
    if args.force:
        parts.append("--force")
    if args.dry_run:
        parts.append("--dry-run")
    if args.json:
        parts.append("--json")
    if args.with_ci:
        parts.append("--with-ci")
    if not args.with_rules:
        parts.append("--no-with-rules")
    return runner + " " + " ".join(_quote(part) for part in parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="quickstart.py",
        description="Install the agent-spec skill suite into another repository.",
        epilog=(
            "Exit codes: 0 success, 1 install failure, 2 usage error, 3 unexpected error. "
            "Run with --print-oneliner to get a one-line adoption command for another machine."
        ),
    )
    parser.add_argument(
        "--target",
        default=None,
        help="repository to install into (required unless --print-oneliner is used)",
    )
    parser.add_argument(
        "--dest",
        default=DEFAULT_DEST,
        help="skills root relative to --target (default: " + DEFAULT_DEST + ")",
    )
    parser.add_argument("--skills", default=None, help="comma-separated skill names (default: all)")
    parser.add_argument(
        "--copy",
        action="store_true",
        help="copy instead of symlinking (symlink failure also falls back to a copy)",
    )
    parser.add_argument("--force", action="store_true", help="replace existing destinations")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing")
    parser.add_argument("--json", action="store_true", help="print a single machine-readable JSON object")
    parser.add_argument(
        "--with-ci",
        action="store_true",
        help=(
            "install the quality-engineering skill's bundled CI workflows into "
            "<target>/.github/workflows/ (implies --skills quality-engineering)"
        ),
    )
    parser.add_argument(
        "--with-rules",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="install .agents/rules (default: on)",
    )
    parser.add_argument(
        "--print-oneliner",
        action="store_true",
        help="print the equivalent one-line adoption command for another machine and exit",
    )
    parser.add_argument("--version", action="version", version="quickstart " + VERSION)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_oneliner:
        sys.stdout.write(print_oneliner_command(args) + "\n")
        return 0

    try:
        target = resolve_target(args.target)
        dest = validate_dest(args.dest)
        dest_root = target / dest
        if args.with_ci and dest != Path(DEFAULT_DEST):
            raise UsageError(
                "--with-ci requires the default --dest (" + DEFAULT_DEST + "): the workflow "
                "templates call .agents/skills/... scripts"
            )

        skills = available_skills()
        names = [skill.name for skill in skills]
        selected_names = parse_skills(args.skills, names)
        if args.with_ci and QUALITY_ENGINEERING in names and QUALITY_ENGINEERING not in selected_names:
            selected_names.append(QUALITY_ENGINEERING)
        selected = [skill for skill in skills if skill.name in selected_names]

        items, problems = build_items(
            target,
            dest_root,
            selected,
            args.with_rules,
            args.with_ci,
        )
        if problems:
            for problem in problems:
                sys.stderr.write("error: " + problem + "\n")
            return 2

        results = []
        failures = 0
        for item in items:
            status, detail = install_item(item, target, args.copy, args.force, args.dry_run)
            results.append(item.as_dict(status, detail))
            if status == "error":
                failures += 1

        installed = sum(
            1
            for result in results
            if result["status"] in ("linked", "copied", "planned-link", "planned-copy")
        )
        skipped = sum(1 for result in results if result["status"] == "skipped")
        payload = {
            "tool": "quickstart",
            "version": VERSION,
            "source": str(SOURCE_ROOT),
            "target": str(target),
            "dest": dest.as_posix(),
            "copy": bool(args.copy),
            "dry_run": bool(args.dry_run),
            "with_ci": bool(args.with_ci),
            "with_rules": bool(args.with_rules),
            "results": results,
            "installed": installed,
            "skipped": skipped,
            "failures": failures,
            "ok": failures == 0,
        }
        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            verb = "planned" if args.dry_run else "installed"
            sys.stdout.write(
                "quickstart " + VERSION + " -> " + str(target) + " (" + verb + ")\n"
            )
            for result in results:
                sys.stdout.write(
                    "  " + result["status"].ljust(12) + " " + result["kind"] + " "
                    + result["name"] + " -> " + result["destination"]
                    + " (" + result["detail"] + ")\n"
                )
            sys.stdout.write(
                "summary: " + str(len(results)) + " item(s), " + str(installed) + " " + verb
                + ", " + str(skipped) + " skipped, " + str(failures) + " failure(s)"
                + (" (dry-run)" if args.dry_run else "") + "\n"
            )
        return 0 if failures == 0 else 1
    except UsageError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return 2
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write("unexpected error: " + str(exc) + "\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
