#!/usr/bin/env python3
"""Install this repository's skills into per-user or Claude Code skill directories.

Usage:
    python tools/install_skills.py [--dest PATH]... [--skills a,b] [--copy] [--force]
                                   [--dry-run] [--json]

Defaults install every skill under .agents/skills/ to:
    ~/.agents/skills     (Codex and other AGENTS-aware harnesses)
    ~/.claude/skills     (Claude Code)

Symlinks are preferred; when the platform refuses a symlink (for example Windows without
Developer Mode), the tool falls back to a copy and says so.

Exit codes:
    0 success (skips count as success)
    1 one or more install operations failed
    2 usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

VERSION = "2.0.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / ".agents" / "skills"
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
SKIP_DIRS = {"__pycache__", ".git"}


def skill_directories():
    if not SOURCE_ROOT.is_dir():
        return []
    return sorted(
        path for path in SOURCE_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file() and path.name not in SKIP_DIRS
    )


def frontmatter_name(skill_dir: Path):
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    match = NAME_RE.search(text[:end])
    return match.group(1).strip().strip("'\"") if match else None


def copy_ignore(_directory, names):
    return [name for name in names if name in SKIP_DIRS or name.endswith(".pyc")]


def remove_existing(path: Path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def install_one(source: Path, destination: Path, use_copy: bool, force: bool, dry_run: bool):
    """Return (status, detail) where status is installed|copied|linked|skipped|error."""
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink():
            try:
                if destination.resolve() == source.resolve():
                    return "skipped", "already linked"
            except OSError:
                pass
        if not force:
            return "skipped", "destination exists (use --force to replace)"
    if dry_run:
        mode = "copy" if use_copy else "link"
        return mode, str(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        try:
            remove_existing(destination)
        except OSError as exc:
            return "error", f"cannot replace {destination}: {exc}"
    if not use_copy:
        try:
            os.symlink(source, destination, target_is_directory=True)
            return "linked", str(destination)
        except (OSError, NotImplementedError):
            pass
    try:
        shutil.copytree(source, destination, ignore=copy_ignore)
        return "copied", str(destination)
    except OSError as exc:
        return "error", f"copy failed: {exc}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_skills.py",
        description="Link or copy .agents/skills/<name> into per-user skill directories.",
    )
    parser.add_argument("--dest", action="append", default=None,
                        help="destination skills directory; repeatable "
                             "(default: ~/.agents/skills and ~/.claude/skills)")
    parser.add_argument("--skills", default=None, help="comma-separated skill names (default: all)")
    parser.add_argument("--copy", action="store_true", help="copy instead of symlinking")
    parser.add_argument("--force", action="store_true", help="replace existing destinations")
    parser.add_argument("--dry-run", action="store_true", help="show actions without writing")
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    available = skill_directories()
    if not available:
        print(f"error: no skills found under {SOURCE_ROOT}", file=sys.stderr)
        return 2

    names = [item.name for item in available]
    if args.skills:
        requested = [name.strip() for name in args.skills.split(",") if name.strip()]
        unknown = [name for name in requested if name not in names]
        if unknown:
            print(f"error: unknown skill(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"available: {', '.join(names)}", file=sys.stderr)
            return 2
        selected = [item for item in available if item.name in requested]
    else:
        selected = available

    destinations = [Path(item).expanduser() for item in args.dest] if args.dest else [
        Path.home() / ".agents" / "skills",
        Path.home() / ".claude" / "skills",
    ]

    results = []
    failures = 0
    for destination_root in destinations:
        for skill_dir in selected:
            declared = frontmatter_name(skill_dir)
            if declared and declared != skill_dir.name:
                results.append({"skill": skill_dir.name, "destination": str(destination_root / declared),
                                "status": "error",
                                "detail": f"frontmatter name '{declared}' does not match directory name"})
                failures += 1
                continue
            status, detail = install_one(
                skill_dir, destination_root / skill_dir.name, args.copy, args.force, args.dry_run
            )
            results.append({"skill": skill_dir.name, "destination": str(destination_root / skill_dir.name),
                            "status": status, "detail": detail})
            if status == "error":
                failures += 1

    payload = {
        "tool": "install_skills",
        "version": VERSION,
        "source": str(SOURCE_ROOT),
        "destinations": [str(item) for item in destinations],
        "copy": bool(args.copy),
        "dry_run": bool(args.dry_run),
        "results": results,
        "failures": failures,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"install_skills {VERSION} -> {len(destinations)} destination(s)")
        for item in results:
            print(f"  {item['status']:<9} {item['skill']} -> {item['destination']} ({item['detail']})")
        print(f"summary: {len(results)} operation(s), {failures} failure(s)"
              + (" (dry-run)" if args.dry_run else ""))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
