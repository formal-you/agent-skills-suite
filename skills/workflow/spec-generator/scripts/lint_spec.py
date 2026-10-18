#!/usr/bin/env python3
"""Structural gate for tech-spec artifacts.

Checks placeholders, #sec-* anchors, required identifiers, Mermaid fences and bracket
balance, ADR sections, and relative links. Stdlib-only; the skill can be copied outside
the repository.

Usage:
    python scripts/lint_spec.py [TARGET] [--json]

TARGET may be a .specs directory, a 02-tech-spec.md file, or a modular spec directory.

Exit codes:
    0 pass
    1 structural violations
    2 usage or no spec artifacts found
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
MERMAID_OPEN_RE = re.compile(r"^\s*(\x60{3}|~{3})\s*mermaid\b", re.IGNORECASE)
MERMAID_TYPES = re.compile(
    r"^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|stateDiagram-v2|erDiagram|"
    r"gantt|pie|journey|mindmap|timeline|gitGraph|C4Context|block-beta|quadrantChart)\b"
)
REQUIRED_TOKENS = [
    ("NFR", re.compile(r"\bNFR-\d{3}\b")),
    ("INV", re.compile(r"\bINV-\d{3}\b")),
]
ADR_SECTIONS = [
    ("Status", re.compile(r"^##\s+Status\b", re.IGNORECASE | re.MULTILINE)),
    ("Context", re.compile(r"^##\s+Context\b", re.IGNORECASE | re.MULTILINE)),
    ("Considered options", re.compile(r"^##\s+Considered options\b", re.IGNORECASE | re.MULTILINE)),
    ("Decision", re.compile(r"^##\s+Decision\b", re.IGNORECASE | re.MULTILINE)),
    ("Consequences", re.compile(r"^##\s+Consequences\b", re.IGNORECASE | re.MULTILINE)),
]
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")
TEXT_SUFFIXES = {".md", ".sql", ".ts", ".json", ".yaml", ".yml"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def error(file: str, line: int, code: str, message: str) -> dict:
    return {"file": file, "line": line, "code": code, "message": message}


def warning(file: str, line: int, code: str, message: str) -> dict:
    return {"file": file, "line": line, "code": code, "message": message, "severity": "warning"}


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def mask_code_fences(text: str):
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


def check_mermaid(text: str, path: Path, errors: list, warnings: list):
    lines = text.splitlines()
    index = 0
    seen_block = False
    while index < len(lines):
        opener = MERMAID_OPEN_RE.match(lines[index])
        if not opener:
            index += 1
            continue
        seen_block = True
        marker = opener.group(1)
        start_line = index + 1
        block = []
        closed = False
        cursor = index + 1
        while cursor < len(lines):
            if lines[cursor].strip() == marker or lines[cursor].strip().startswith(marker):
                closed = True
                break
            block.append(lines[cursor])
            cursor += 1
        if not closed:
            errors.append(error(str(path), start_line, "MERMAID_UNCLOSED",
                                "Mermaid block has no closing fence"))
            index = cursor
            continue
        first = next((line.strip() for line in block if line.strip()), "")
        if first and not MERMAID_TYPES.match(first):
            warnings.append(warning(str(path), start_line + 1, "MERMAID_TYPE",
                                    f"unrecognised Mermaid diagram type: {first[:40]}"))
        stack = []
        pairs = {")": "(", "]": "[", "}": "{"}
        quote = None
        broken = False
        for offset, line in enumerate(block, 1):
            for char in line:
                if quote:
                    if char == quote:
                        quote = None
                    continue
                if char in ("'", '"'):
                    quote = char
                    continue
                if char in "([{":
                    stack.append(char)
                elif char in ")]}":
                    if not stack or stack.pop() != pairs[char]:
                        errors.append(error(str(path), start_line + offset, "MERMAID_BRACKET",
                                            "unbalanced bracket in Mermaid block"))
                        broken = True
                        break
            if broken:
                break
        if not broken and stack:
            errors.append(error(str(path), start_line, "MERMAID_BRACKET",
                                "unclosed bracket in Mermaid block"))
        index = cursor + 1
    return seen_block


def check_adr_sections(text: str, path: Path, errors: list):
    for label, pattern in ADR_SECTIONS:
        if not pattern.search(text):
            errors.append(error(str(path), 0, "ADR_SECTION_MISSING",
                                f"ADR is missing a required section: {label}"))


def scan_file(path: Path):
    errors = []
    warnings = []
    text = read_text(path)
    is_markdown = path.suffix == ".md"
    if is_markdown:
        masked, fence_errors = mask_code_fences(text)
        for item in fence_errors:
            item["file"] = str(path)
            errors.append(item)
    else:
        masked = text

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

    if is_markdown:
        seen_mermaid = check_mermaid(text, path, errors, warnings)
        if path.parent.name == "adr":
            check_adr_sections(text, path, errors)
        if path.name == "02-tech-spec.md" and not seen_mermaid:
            warnings.append(warning(str(path), 0, "MERMAID_MISSING",
                                    "aggregate spec has no Mermaid topology block"))

    if path.suffix == ".ts":
        for match in re.finditer(r"\binterface\s+\w+", masked):
            warnings.append(warning(str(path), line_number(masked, match.start()), "PROJECT_CONVENTION",
                                    "interface declaration found; confirm the project's preferred type style"))
    if path.suffix == ".sql":
        if masked.count("(") != masked.count(")"):
            warnings.append(warning(str(path), 0, "SQL_PARENS",
                                    "unbalanced parentheses in the DDL example"))
    return errors, warnings, anchors, masked


def collect_files(target: Path):
    if target.is_file():
        return [target], target.name, False
    files = []
    aggregate = target / "02-tech-spec.md"
    if aggregate.is_file():
        files.append(aggregate)
    modular = target / "02-tech-spec"
    if modular.is_dir():
        files.extend(sorted(p for p in modular.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES))
    adr = target / "adr"
    if adr.is_dir():
        files.extend(sorted(adr.glob("*.md")))
    if files:
        return files, target.name, len(files) == 0
    fallback = sorted(p for p in target.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)
    return fallback, target.name, False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_spec.py",
        description="Structural gate for tech-spec artifacts (placeholders, anchors, Mermaid, ADRs, links).",
    )
    parser.add_argument("target", nargs="?", default=".specs", help="spec file or directory (default: .specs)")
    parser.add_argument("--json", action="store_true", help="print one machine-readable JSON object")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"error: target does not exist: {target}", file=sys.stderr)
        return 2
    try:
        files, scope_name, _ = collect_files(target)
    except OSError as exc:
        print(f"error: cannot read target: {exc}", file=sys.stderr)
        return 3
    if not files:
        print(f"error: no spec artifacts found under {target}", file=sys.stderr)
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
        print(f"error: cannot read a spec file: {exc}", file=sys.stderr)
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
                            "no #sec-* anchor found; the spec must reuse PRD anchors"))

    for label, pattern in REQUIRED_TOKENS:
        if not pattern.search(combined):
            errors.append(error(scope_name, 0, "MISSING_SECTION",
                                f"no {label}-### identifier found in the spec bundle"))

    payload = {
        "tool": "lint_spec",
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
        print(f"lint_spec {VERSION}: {target} ({len(files)} file(s))")
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
