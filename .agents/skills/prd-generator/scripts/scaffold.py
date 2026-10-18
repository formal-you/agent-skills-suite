#!/usr/bin/env python3
"""Copy this skill's templates into an output tree.

Usage:
    python scripts/scaffold.py [--out .specs] [--dry-run] [--force] [--json]

The script resolves templates from its own skill directory, so the skill can be copied
anywhere. It never imports repository code and never writes outside --out.

Exit codes:
    0 success (including idempotent no-op runs)
    1 reserved for content failures
    2 usage error
    3 unexpected error
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

VERSION = "2.0.0"
SKILL_NAME = "prd-generator"
CREATE_ADR_DIR = False

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "assets" / "templates"


def iter_templates():
    """Yield (source, destination-relative-path) for every copyable template."""
    if not TEMPLATES_DIR.is_dir():
        return
    for source in sorted(TEMPLATES_DIR.rglob("*")):
        if not source.is_file():
            continue
        name = source.name
        if ".template." not in name:
            continue
        if name == "adr.template.md":
            # ADRs are written per decision, not scaffolded as a fixed file.
            continue
        relative = source.relative_to(TEMPLATES_DIR)
        destination_name = name.replace(".template", "", 1)
        yield source, relative.with_name(destination_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold.py",
        description=f"Scaffold the {SKILL_NAME} output tree from bundled templates.",
    )
    parser.add_argument("--out", "-o", default=".specs", help="output directory (default: .specs)")
    parser.add_argument("--dry-run", action="store_true", help="list actions without writing")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(f"{SKILL_NAME} scaffold {VERSION} -> {payload['out']}")
    if payload["dry_run"]:
        for item in payload["actions"]:
            print(f"  would {item['action']}: {item['path']}")
    else:
        for path in payload["created"]:
            print(f"  created: {path}")
        for path in payload["overwritten"]:
            print(f"  overwritten: {path}")
    for path in payload["skipped"]:
        print(f"  skipped (exists; use --force to overwrite): {path}")
    print(
        "summary: created={0} overwritten={1} skipped={2}{3}".format(
            len(payload["created"]),
            len(payload["overwritten"]),
            len(payload["skipped"]),
            " (dry-run)" if payload["dry_run"] else "",
        )
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.out)
    if out_dir.exists() and not out_dir.is_dir():
        print(f"error: --out is not a directory: {out_dir}", file=sys.stderr)
        return 2
    if not TEMPLATES_DIR.is_dir():
        print(f"error: bundled templates not found at {TEMPLATES_DIR}", file=sys.stderr)
        return 3

    payload = {
        "tool": "scaffold",
        "skill": SKILL_NAME,
        "version": VERSION,
        "out": str(out_dir),
        "dry_run": bool(args.dry_run),
        "created": [],
        "overwritten": [],
        "skipped": [],
        "actions": [],
    }
    adr_dir = out_dir / "adr"
    try:
        for source, relative in iter_templates():
            destination = out_dir / relative
            existed = destination.exists()
            if existed and not args.force:
                payload["skipped"].append(str(destination))
                continue
            action = "overwrite" if existed else "create"
            if args.dry_run:
                payload["actions"].append({"action": action, "path": str(destination)})
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            payload["overwritten" if existed else "created"].append(str(destination))
        if CREATE_ADR_DIR:
            if args.dry_run:
                payload["actions"].append({"action": "create-dir", "path": str(adr_dir)})
            else:
                adr_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: scaffold failed: {exc}", file=sys.stderr)
        return 3

    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
