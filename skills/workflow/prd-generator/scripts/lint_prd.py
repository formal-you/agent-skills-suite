#!/usr/bin/env python3
"""Structural gate for PRD artifacts.

Checks placeholders, #sec-* anchors, required identifier tokens, and relative links.
The script is stdlib-only and resolves everything from its arguments, so the skill can
be copied outside the repository.

Usage:
    python scripts/lint_prd.py [TARGET] [--json]

TARGET may be a PRD file or a directory containing 01-prd.md / 01-prd/.

Exit codes:
    0 pass
    1 structural violations
    2 usage or missing target
    3 unexpected error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = "2.0.0"
PLACEHOLDER_RE = re.compile(r"\{\{[^{}\n]+\}\}")
TODO_PATTERNS = [
    ("PLACEHOLDER_TBD", re.compile(r"\[TBD\]", re.IGNORECASE)),
    ("PLACEHOLDER_TODO", re.compile(r"<TODO>", re.IGNORECASE)),
    ("PLACEHOLDER_TODO", re.compile(r"\bTODO\b")),
]
ANCHOR_RE = re.compile(r"#sec-([a-z0-9]+(?:-[a-z0-9]+)*)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^\s*(\x60{3}|~{3})")
REQUIRED_TOKENS = [
    ("REQ", re.compile(r"\bREQ-\d{3}\b")),
    ("CON", re.compile(r"\bCON-\d{3}\b")),
    ("NFR", re.compile(r"\bNFR-\d{3}\b")),
    ("FORK", re.compile(r"\bFORK-\d{3}\b")),
]
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def error(file: str, line: int, code: str, message: str) -> dict:
    return {"file": file, "line": line, "code": code, "message": message}


def warning(file: str, line: int, code: str, message: str) -> dict:
    return {"file": file, "line": line, "code": code, "message": message, "severity": "warning"}


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def mask_code_fences(text: str):
    """Return text with fenced code lines blanked (line numbers preserved) and errors."""
    errors = []
    lines = text.splitlines(keepends=True)
    masked = []
    fence = None
    for line in lines:
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
                masked.append("\n" if line.endswith("\n") else "")
                continue
            if marker == fence:
                fence = None
                masked.append("\n" if line.endswith("\n") else "")
                continue
        if fence is not None:
            masked.append("\n" if line.endswith("\n") else "")
        else:
            masked.append(line)
    if fence is not None:
        errors.append(error("", len(lines), "UNCLOSED_FENCE", "code fence opened but never closed"))
    return "".join(masked), errors


def check_links(path: Path, masked: str):
    errors = []
    for match in LINK_RE.finditer(masked):
        target = match.group(1).strip()
        if not target or target.lower().startswith(SKIP_LINK_PREFIXES):
            continue
        if target.startswith("/"):
            errors.append(error(str(path), line_number(masked, match.start()), "ABSOLUTE_LINK",
                                f"link should be relative to the document: {target}"))
            continue
        clean = target.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        if not (path.parent / clean).exists():
            errors.append(error(str(path), line_number(masked, match.start()), "DANGLING_LINK",
                                f"relative link does not resolve: {target}"))
    return errors


def scan_file(path: Path):
    errors = []
    warnings = []
    text = read_text(path)
    masked, fence_errors = mask_code_fences(text)
    for item in fence_errors:
        item["file"] = str(path)
        errors.append(item)

    for match in PLACEHOLDER_RE.finditer(masked):
        errors.append(error(str(path), line_number(masked, match.start()), "PLACEHOLDER",
                            f"unreplaced placeholder: {match.group(0)}"))
    for code, pattern in TODO_PATTERNS:
        for match in pattern.finditer(masked):
            errors.append(error(str(path), line_number(masked, match.start()), code,
                                f"unresolved marker: {match.group(0)}"))

    anchors = []
    for match in ANCHOR_RE.finditer(masked):
        anchors.append((match.group(0), str(path), line_number(masked, match.start())))

    errors.extend(check_links(path, masked))
    return errors, warnings, anchors, masked


def collect_files(target: Path):
    if target.is_file():
        return [target], target.name
    files = []
    aggregate = target / "01-prd.md"
    if aggregate.is_file():
        files.append(aggregate)
    bundle = target / "01-prd"
    if bundle.is_dir():
        files.extend(sorted(bundle.rglob("*.md")))
    if files:
        return files, target.name
    return sorted(target.rglob("*.md")), target.name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_prd.py",
        description="Structural gate for PRD artifacts (placeholders, anchors, required tokens, links).",
    )
    parser.add_argument("target", nargs="?", default=".specs", help="PRD file or directory (default: .specs)")
    parser.add_argument("--json", action="store_true", help="print one machine-readable JSON object")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"error: target does not exist: {target}", file=sys.stderr)
        return 2
    try:
        files, scope_name = collect_files(target)
    except OSError as exc:
        print(f"error: cannot read target: {exc}", file=sys.stderr)
        return 3
    if not files:
        print(f"error: no PRD markdown files found under {target}", file=sys.stderr)
        return 2

    errors = []
    warnings = []
    all_anchors = []
    corpus = []
    try:
        for path in files:
            file_errors, file_warnings, anchors, masked = scan_file(path)
            errors.extend(file_errors)
            warnings.extend(file_warnings)
            all_anchors.extend(anchors)
            corpus.append(masked)
    except OSError as exc:
        print(f"error: cannot read a PRD file: {exc}", file=sys.stderr)
        return 3

    combined = "\n".join(corpus)
    seen = {}
    warned_same = set()
    cross_warned = set()
    for anchor, file, line in all_anchors:
        if anchor not in seen:
            seen[anchor] = (file, line)
        elif seen[anchor][0] == file:
            if (anchor, file) not in warned_same:
                warned_same.add((anchor, file))
                warnings.append(warning(file, line, "DUPLICATE_ANCHOR",
                                        f"anchor {anchor} appears more than once in this file "
                                        "(repeated references are allowed; verify they mean the same module)"))
        elif anchor not in cross_warned:
            cross_warned.add(anchor)
            warnings.append(warning(file, line, "CROSS_FILE_ANCHOR",
                                    f"anchor {anchor} also appears in {seen[anchor][0]} "
                                    "(expected for aggregate/bundle copies)"))
    if not all_anchors:
        errors.append(error(scope_name, 0, "NO_ANCHORS",
                            "no #sec-* anchor found; every functional requirement needs one"))

    for label, pattern in REQUIRED_TOKENS:
        if not pattern.search(combined):
            errors.append(error(scope_name, 0, "MISSING_SECTION",
                                f"no {label}-### identifier found in the PRD bundle"))

    req_count = len(re.findall(r"\bREQ-\d{3}\b", combined))
    if req_count > len(all_anchors):
        warnings.append(warning(scope_name, 0, "ANCHOR_COVERAGE",
                                f"{req_count} REQ identifiers but only {len(all_anchors)} anchors"))

    payload = {
        "tool": "lint_prd",
        "version": VERSION,
        "passed": not errors,
        "target": str(target),
        "files_scanned": len(files),
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"lint_prd {VERSION}: {target} ({len(files)} file(s))")
        for item in errors:
            location = f"{item['file']}:{item['line']}" if item["file"] else "bundle"
            print(f"  ERROR {location} [{item['code']}] {item['message']}")
        for item in warnings:
            location = f"{item['file']}:{item['line']}" if item["file"] else "bundle"
            print(f"  WARN  {location} [{item['code']}] {item['message']}")
        print("PASS" if not errors else f"FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
