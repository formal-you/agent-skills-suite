#!/usr/bin/env python3
"""Scaffold a four-document task bundle from the task-decomposition templates.

The helper is dependency-free on purpose: the skill must keep working when no
package is installed. It copies the four templates into <tasks-dir>/<task-id>/,
substitutes {{TASK_ID}} and {{TASK_TITLE}} in the contract, and leaves the
remaining contract placeholders for the Planner. 02/03 are blank role forms and
04 is initialized with concrete lifecycle values (it is tooling-owned).

Brownfield callers may pass --change-id and --size-class; the helper then adds
those two keys to the contract frontmatter. Without the flags the generated
files are byte-identical to the plain scaffold.

Exit codes: 0 success; 1 overwrite refused / content failure; 2 usage error or
missing assets; 3 unexpected internal error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

__version__ = "2.0.0"

TEMPLATE_FILES = (
    ("01-contract.template.md", "01-contract.md"),
    ("02-dev-workspace.template.md", "02-dev-workspace.md"),
    ("03-qa-verification.template.md", "03-qa-verification.md"),
    ("04-process.template.md", "04-process.md"),
)

TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z0-9_]+\}\}")

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3


class ScaffoldError(Exception):
    """Error carrying the process exit code to use."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def assets_dir() -> Path:
    """Return the skill's assets/templates directory (never the repo root)."""
    return Path(__file__).resolve().parent.parent / "assets" / "templates"


def sanitize_title(raw: str) -> str:
    """Collapse whitespace and normalise quotes so the title is YAML-safe."""
    title = " ".join(raw.split())
    return title.replace('"', "'")


def render(template_text: str, task_id: str, title: str) -> str:
    """Substitute the two scaffold-time placeholders; leave the rest untouched."""
    return template_text.replace("{{TASK_ID}}", task_id).replace("{{TASK_TITLE}}", title)


def inject_brownfield_fields(contract_text: str, change_id: str | None, size_class: str | None) -> str:
    """Add change_id / size_class to the contract frontmatter when supplied.

    The insertion point is right after the title line so the frontmatter keeps a
    stable, readable order. With both arguments None the text is returned
    unchanged, which keeps the default scaffold byte-identical.
    """
    additions = []
    if change_id:
        additions.append('change_id: "' + change_id + '"\n')
    if size_class:
        additions.append('size_class: "' + size_class + '"\n')
    if not additions:
        return contract_text
    lines = contract_text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("title:"):
            lines[index + 1 : index + 1] = additions
            return "".join(lines)
    raise ScaffoldError("cannot locate the title field in the contract template", EXIT_USAGE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold_task.py",
        description="Create a four-document task bundle from the task-decomposition templates.",
        epilog=(
            "Exit codes: 0 success, 1 overwrite refused, 2 usage/assets error, "
            "3 unexpected error. Example: python scaffold_task.py "
            "--task-id task-001-auth --title \"User authentication\" --tasks-dir ./tasks"
        ),
    )
    parser.add_argument("--tasks-dir", "-t", default="./tasks", help="Task root directory (default: ./tasks).")
    parser.add_argument("--task-id", required=True, help="Task directory name; also the contract task_id.")
    parser.add_argument("--title", required=True, help="Short human title written into the contract and headings.")
    parser.add_argument("--dry-run", action="store_true", help="List the files that would be created; write nothing.")
    parser.add_argument("--force", action="store_true", help="Overwrite files in an existing task directory.")
    parser.add_argument(
        "--change-id",
        default=None,
        help="Brownfield change id; adds change_id to the contract frontmatter when supplied.",
    )
    parser.add_argument(
        "--size-class",
        default=None,
        choices=("standard", "micro"),
        help="Brownfield size class; adds size_class to the contract frontmatter when supplied.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def run(args: argparse.Namespace) -> int:
    task_id = args.task_id.strip()
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ScaffoldError(
            "invalid --task-id: use letters, digits, '.', '_' or '-', starting with a letter or digit",
            EXIT_USAGE,
        )

    title = sanitize_title(args.title)
    if not title:
        raise ScaffoldError("--title must not be empty", EXIT_USAGE)

    change_id = (args.change_id or "").strip() or None
    if change_id is not None and not TASK_ID_PATTERN.fullmatch(change_id):
        raise ScaffoldError(
            "invalid --change-id: use letters, digits, '.', '_' or '-', starting with a letter or digit",
            EXIT_USAGE,
        )

    source_dir = assets_dir()
    missing = [src for src, _ in TEMPLATE_FILES if not (source_dir / src).is_file()]
    if missing:
        raise ScaffoldError(
            "missing template assets in " + str(source_dir) + ": " + ", ".join(missing),
            EXIT_USAGE,
        )

    tasks_dir = Path(args.tasks_dir).expanduser()
    try:
        tasks_root = tasks_dir.resolve()
        target = (tasks_dir / task_id).resolve()
    except OSError as exc:
        raise ScaffoldError("cannot resolve --tasks-dir: " + str(exc), EXIT_USAGE)
    if target.parent != tasks_root:
        raise ScaffoldError("--task-id escapes --tasks-dir", EXIT_USAGE)

    if target.exists() and not args.force:
        raise ScaffoldError(
            str(target) + " already exists; pass --force to overwrite", EXIT_REFUSED
        )

    planned = [(source_dir / src, target / dst) for src, dst in TEMPLATE_FILES]

    if args.dry_run:
        for _, destination in planned:
            print("[dry-run] would create " + str(destination))
        print("[dry-run] no files written")
        return EXIT_OK

    try:
        target.mkdir(parents=True, exist_ok=True)
        remaining: set[str] = set()
        for source, destination in planned:
            existed = destination.exists()
            rendered = render(source.read_text(encoding="utf-8"), task_id, title)
            if destination.name == "01-contract.md":
                rendered = inject_brownfield_fields(rendered, change_id, args.size_class)
            destination.write_text(rendered, encoding="utf-8")
            remaining.update(PLACEHOLDER_PATTERN.findall(rendered))
            print(("overwrote " if existed else "created ") + str(destination))
    except OSError as exc:
        raise ScaffoldError("writing the task bundle failed: " + str(exc), EXIT_INTERNAL)

    print("scaffolded " + str(len(planned)) + " documents in " + str(target))
    if remaining:
        print("remaining placeholders to fill: " + ", ".join(sorted(remaining)))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ScaffoldError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return exc.code
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print("error: unexpected failure: " + str(exc), file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
