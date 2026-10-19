#!/usr/bin/env python3
"""Regenerate the SHA-256 manifest for the distributable tree.

Usage:
    python tools/gen_manifest.py           # rewrite MANIFEST.sha256
    python tools/gen_manifest.py --check   # exit 1 when the file is stale

The manifest lists every git-tracked file except itself, sorted case-insensitively, as
``<sha256>  <path>``. Line endings are normalized to LF before hashing so the manifest is
identical on every platform.

Exit codes:
    0 success / up to date
    1 stale manifest (--check only)
    2 usage or git error
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "MANIFEST.sha256"
EXCLUDED = {"MANIFEST.sha256"}


class ManifestError(Exception):
    """A git or filesystem problem: exit code 2."""


def tracked_files():
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(ROOT),
            capture_output=True,
        )
    except FileNotFoundError:
        raise ManifestError("git executable not found")
    if result.returncode != 0:
        raise ManifestError(
            "git ls-files failed: " + result.stderr.decode("utf-8", "replace").strip()
        )
    names = [
        item.decode("utf-8", "replace")
        for item in result.stdout.split(b"\0")
        if item
    ]
    return sorted((name for name in names if name not in EXCLUDED), key=str.lower)


def digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def render() -> str:
    lines = []
    for name in tracked_files():
        path = ROOT / name
        if not path.is_file():
            continue
        lines.append(digest(path) + "  " + name)
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gen_manifest",
        description="Regenerate or verify MANIFEST.sha256.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the manifest instead of rewriting it (exit 1 when stale)",
    )
    parser.add_argument("--version", action="version", version="gen_manifest 1.0.0")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        expected = render()
    except ManifestError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return 2

    if args.check:
        current = MANIFEST.read_text(encoding="utf-8") if MANIFEST.is_file() else ""
        if current != expected:
            sys.stderr.write(
                "MANIFEST.sha256 is stale; run: python tools/gen_manifest.py\n"
            )
            return 1
        return 0

    MANIFEST.write_bytes(expected.encode("utf-8"))
    sys.stdout.write("wrote " + str(len(expected.splitlines())) + " entries to " + str(MANIFEST) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
