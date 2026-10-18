#!/usr/bin/env python3
"""Consistency linter for brownfield change proposals and their task bundles.

Validates the proposal frontmatter, the #sec-* anchors against the base spec, the
incremental diff blocks and the matching task bundle. It also detects base-spec
drift: when the base spec changed after scaffolding, an open proposal is stale.
Archived proposals are structurally checked but exempt from drift because the
convergence step intentionally rewrites the spec.

Exit codes: 0 pass; 1 violations; 2 usage error; 3 unexpected internal error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

__version__ = "3.0.0"

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

REQUIRED_KEYS = (
    "change_id",
    "title",
    "status",
    "kind",
    "base_spec",
    "base_spec_sha256",
    "impact_anchors",
    "created",
)
STATUSES = ("proposed", "applied", "archived")
KINDS = ("add", "modify", "remove")
ANCHOR_RE = re.compile(r"^#sec-[a-z0-9-]+$")
ANCHOR_TOKEN_RE = re.compile(r"#sec-[a-z0-9-]+")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHANGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
BLOCK_RE = re.compile(r"^###\s+\[CHG-(\d+)\]\s+(#sec-[a-z0-9-]+)\b(.*)$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s+(Before|After|Files)\s*:\s*(.*)$", re.MULTILINE)
GUIDANCE_RE = re.compile(r"<[^>\n]+>")
CHANGE_ID_LINE_RE = re.compile(r"^change_id:\s*(.+?)\s*$")


def relative_posix(path, root):
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.resolve().as_posix()


def resolve_path(value, root):
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def strip_inline_comment(value):
    quote = None
    for index, char in enumerate(value):
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "#" and index > 0 and value[index - 1].isspace():
            return value[:index].rstrip()
    return value.rstrip()


def parse_scalar(raw):
    value = strip_inline_comment(raw).strip()
    if not value:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """Parse the small YAML subset used by proposal frontmatter.

    Returns (mapping, body_start_line) where body_start_line is the zero-based index
    of the first body line. Raises ValueError for an indented line without a key.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0
    close = None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            close = index
            break
    if close is None:
        return None, 0
    mapping = {}
    current = None
    for raw in lines[1:close]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw[0] in (" ", "\t"):
            if current is None:
                raise ValueError("indented frontmatter line without a key: " + raw)
            if stripped.startswith("- "):
                item = parse_scalar(stripped[2:])
                if not isinstance(mapping.get(current), list):
                    mapping[current] = []
                if item is not None:
                    mapping[current].append(item)
            continue
        if ":" not in raw:
            raise ValueError("expected key: value in frontmatter, got: " + raw)
        key, rest = raw.split(":", 1)
        key = key.strip()
        value = parse_scalar(rest)
        if value is None:
            mapping[key] = []
            current = key
        elif value.startswith("[") and value.endswith("]"):
            body = value[1:-1].strip()
            if body:
                parsed = [parse_scalar(part) for part in body.split(",")]
                mapping[key] = [item for item in parsed if item is not None]
            else:
                mapping[key] = []
            current = None
        else:
            mapping[key] = value
            current = None
    return mapping, close + 1


def as_string(mapping, key):
    value = mapping.get(key)
    if isinstance(value, str):
        return value.strip()
    return None


def as_list(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def contract_change_id(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            break
        match = CHANGE_ID_LINE_RE.match(lines[index])
        if match:
            return parse_scalar(match.group(1))
    return None


def find_task_bundles(tasks_root, change_id):
    matches = []
    if not tasks_root.is_dir():
        return matches
    for contract in sorted(tasks_root.rglob("01-contract.md")):
        try:
            text = contract.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if contract_change_id(text) == change_id:
            matches.append(contract)
    return matches


def add_error(errors, code, message, file, line=0):
    errors.append({"code": code, "message": message, "file": file, "line": line})


def add_warning(warnings, code, message, file, line=0):
    warnings.append({"code": code, "message": message, "file": file, "line": line})


def lint_one(proposal_path, expected_change_id, repo_root, tasks_root, fallback_spec):
    errors = []
    warnings = []
    label = relative_posix(proposal_path, repo_root)

    try:
        text = proposal_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        add_error(errors, "PROPOSAL_UNREADABLE", "cannot read proposal: " + str(exc), label)
        return {
            "change_id": expected_change_id,
            "proposal": label,
            "status": None,
            "errors": errors,
            "warnings": warnings,
        }

    try:
        mapping, body_start = parse_frontmatter(text)
    except ValueError as exc:
        add_error(errors, "INVALID_FRONTMATTER", str(exc), label)
        mapping, body_start = None, 0
    if mapping is None:
        add_error(
            errors,
            "MISSING_FRONTMATTER",
            "proposal must start with a YAML frontmatter block",
            label,
        )
        return {
            "change_id": expected_change_id,
            "proposal": label,
            "status": None,
            "errors": errors,
            "warnings": warnings,
        }

    lines = text.splitlines()
    body = "\n".join(lines[body_start:])
    body_line_offset = body_start

    change_id = as_string(mapping, "change_id")
    status = as_string(mapping, "status")
    kind = as_string(mapping, "kind")

    for key in REQUIRED_KEYS:
        if mapping.get(key) in (None, "", []):
            add_error(
                errors,
                "MISSING_KEY",
                "proposal frontmatter is missing required key: " + key,
                label,
            )
    if change_id and expected_change_id and change_id != expected_change_id:
        add_error(
            errors,
            "CHANGE_ID_MISMATCH",
            "proposal change_id " + repr(change_id) + " does not equal the directory name "
            + repr(expected_change_id),
            label,
        )
    if change_id and not CHANGE_ID_RE.fullmatch(change_id):
        add_error(
            errors,
            "INVALID_CHANGE_ID",
            "change_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}: " + repr(change_id),
            label,
        )
    if status is not None and status not in STATUSES:
        add_error(
            errors,
            "INVALID_STATUS",
            "status must be one of " + ", ".join(STATUSES) + "; got " + repr(status),
            label,
        )
    if kind is not None and kind not in KINDS:
        add_error(
            errors,
            "INVALID_KIND",
            "kind must be one of " + ", ".join(KINDS) + "; got " + repr(kind),
            label,
        )
    created = as_string(mapping, "created")
    if created is not None:
        if not DATE_RE.fullmatch(created):
            add_error(errors, "INVALID_CREATED", "created must be YYYY-MM-DD: " + repr(created), label)
        else:
            try:
                datetime.date.fromisoformat(created)
            except ValueError:
                add_error(
                    errors, "INVALID_CREATED", "created is not a real date: " + repr(created), label
                )

    declared_anchors = as_list(mapping.get("impact_anchors"))
    if not declared_anchors:
        add_error(
            errors,
            "MISSING_IMPACT_ANCHORS",
            "impact_anchors must list at least one #sec-* anchor",
            label,
        )
    for anchor in declared_anchors:
        if not ANCHOR_RE.fullmatch(anchor):
            add_error(
                errors,
                "INVALID_ANCHOR",
                "impact anchor does not match #sec-[a-z0-9-]+: " + repr(anchor),
                label,
            )

    base_spec_value = as_string(mapping, "base_spec")
    base_spec_path = (
        resolve_path(base_spec_value, repo_root) if base_spec_value else fallback_spec
    )
    spec_anchors = None
    if base_spec_path is None or not base_spec_path.is_file():
        add_error(
            errors,
            "BASE_SPEC_MISSING",
            "base spec does not exist: " + str(base_spec_path),
            label,
        )
    else:
        try:
            spec_text = base_spec_path.read_text(encoding="utf-8", errors="replace")
            spec_anchors = set(ANCHOR_TOKEN_RE.findall(spec_text))
        except OSError as exc:
            add_error(errors, "BASE_SPEC_UNREADABLE", "cannot read base spec: " + str(exc), label)
            spec_anchors = None
        if spec_anchors is not None:
            for anchor in declared_anchors:
                if ANCHOR_RE.fullmatch(anchor) and anchor not in spec_anchors:
                    add_error(
                        errors,
                        "UNKNOWN_ANCHOR",
                        "impact anchor "
                        + anchor
                        + " does not exist in "
                        + relative_posix(base_spec_path, repo_root),
                        label,
                    )
        expected_sha = as_string(mapping, "base_spec_sha256")
        if expected_sha is not None and not SHA_RE.fullmatch(expected_sha):
            add_error(
                errors,
                "INVALID_SHA256",
                "base_spec_sha256 must be 64 lowercase hex characters",
                label,
            )
        elif expected_sha is not None and spec_anchors is not None:
            try:
                actual_sha = hashlib.sha256(base_spec_path.read_bytes()).hexdigest()
            except OSError:
                actual_sha = None
            if actual_sha is not None and actual_sha != expected_sha:
                if status == "archived":
                    add_warning(
                        warnings,
                        "ARCHIVED_DRIFT_SKIPPED",
                        "archived proposal: base spec changed after convergence; drift is expected",
                        label,
                    )
                else:
                    add_error(
                        errors,
                        "BASE_SPEC_DRIFT",
                        "base spec changed since scaffold (expected "
                        + expected_sha[:12]
                        + ", found "
                        + actual_sha[:12]
                        + "); rebase the proposal or archive it",
                        label,
                    )

    matches = list(BLOCK_RE.finditer(body))
    if not matches:
        add_error(
            errors,
            "MISSING_DIFF_BLOCKS",
            "section 2 must contain at least one '### [CHG-<n>] #sec-*' block",
            label,
        )
    declared_lookup = set(declared_anchors)
    for position, match in enumerate(matches):
        number = int(match.group(1))
        anchor = match.group(2)
        line = body_line_offset + 1 + body[: match.start()].count("\n")
        if number != position + 1:
            add_error(
                errors,
                "BLOCK_SEQUENCE",
                "diff blocks must be numbered [CHG-1], [CHG-2], ... in order; found [CHG-"
                + str(number)
                + "] at position "
                + str(position + 1),
                label,
                line,
            )
        if anchor not in declared_lookup:
            add_error(
                errors,
                "BLOCK_ANCHOR_NOT_DECLARED",
                "diff block anchor " + anchor + " is not listed in impact_anchors",
                label,
                line,
            )
        if spec_anchors is not None and anchor not in spec_anchors:
            add_error(
                errors,
                "BLOCK_ANCHOR_UNKNOWN",
                "diff block anchor " + anchor + " does not exist in the base spec",
                label,
                line,
            )
        end = matches[position + 1].start() if position + 1 < len(matches) else len(body)
        block = body[match.end() : end]
        next_section = re.search(r"\n##\s", block)
        if next_section:
            block = block[: next_section.start()]
        fields = {}
        for field_name, field_value in FIELD_RE.findall(block):
            fields[field_name] = field_value.strip()
        for required in ("Before", "After", "Files"):
            if not fields.get(required):
                add_error(
                    errors,
                    "BLOCK_FIELD_MISSING",
                    "diff block [CHG-"
                    + str(number)
                    + "] is missing a non-empty '- "
                    + required
                    + ":' line",
                    label,
                    line,
                )
        if GUIDANCE_RE.search(block):
            add_warning(
                warnings,
                "GUIDANCE_REMAINS",
                "diff block [CHG-"
                + str(number)
                + "] still contains angle-bracket guidance; the Planner must replace it",
                label,
                line,
            )

    bundles = find_task_bundles(tasks_root, expected_change_id) if expected_change_id else []
    if not bundles:
        add_error(
            errors,
            "TASK_BUNDLE_MISSING",
            "no task bundle under "
            + relative_posix(tasks_root, repo_root)
            + " has a contract change_id equal to "
            + repr(expected_change_id),
            label,
        )
    elif len(bundles) > 1:
        add_error(
            errors,
            "TASK_BUNDLE_DUPLICATE",
            "more than one task bundle declares change_id "
            + repr(expected_change_id)
            + ": "
            + ", ".join(relative_posix(path, repo_root) for path in bundles),
            label,
        )

    return {
        "change_id": change_id or expected_change_id,
        "proposal": label,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lint_change.py",
        description="Validate brownfield change proposals against their base spec and task bundle.",
        epilog=(
            "Exit codes: 0 pass, 1 violations, 2 usage error, 3 unexpected error. "
            "Example: python lint_change.py --change-id CHG-001-rate-limit --repo-root ."
        ),
    )
    parser.add_argument("--change-id", default=None, help="Lint only this change id (default: every change directory).")
    parser.add_argument("--changes-dir", default=None, help="Change root (default: .specs/changes under --repo-root).")
    parser.add_argument("--tasks-dir", default=None, help="Task root (default: tasks under --repo-root).")
    parser.add_argument("--spec", default=None, help="Fallback base spec (default: .specs/02-tech-spec.md under --repo-root).")
    parser.add_argument("--repo-root", default=".", help="Repository root; relative paths resolve under it (default: .).")
    parser.add_argument("--json", action="store_true", help="Print a single machine-readable JSON object.")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def run(args):
    repo_root = resolve_path(args.repo_root, Path.cwd())
    if not repo_root.is_dir():
        print("error: --repo-root is not a directory: " + str(repo_root), file=sys.stderr)
        return EXIT_USAGE
    changes_root = resolve_path(args.changes_dir or ".specs/changes", repo_root)
    tasks_root = resolve_path(args.tasks_dir or "tasks", repo_root)
    fallback_spec = resolve_path(args.spec or ".specs/02-tech-spec.md", repo_root)

    results = []
    if args.change_id:
        change_id = args.change_id.strip()
        if not CHANGE_ID_RE.fullmatch(change_id):
            print("error: invalid --change-id: " + repr(args.change_id), file=sys.stderr)
            return EXIT_USAGE
        proposal = changes_root / change_id / "proposal.md"
        if not proposal.is_file():
            print("error: proposal not found: " + str(proposal), file=sys.stderr)
            return EXIT_USAGE
        results.append(lint_one(proposal, change_id, repo_root, tasks_root, fallback_spec))
    else:
        if not changes_root.is_dir():
            print("error: change directory does not exist: " + str(changes_root), file=sys.stderr)
            return EXIT_USAGE
        proposals = sorted(
            path / "proposal.md"
            for path in changes_root.iterdir()
            if path.is_dir() and (path / "proposal.md").is_file()
        )
        if not proposals:
            results.append(
                {
                    "change_id": None,
                    "proposal": relative_posix(changes_root, repo_root),
                    "status": None,
                    "errors": [
                        {
                            "code": "NO_CHANGES",
                            "message": "no change proposals found under " + str(changes_root),
                            "file": relative_posix(changes_root, repo_root),
                            "line": 0,
                        }
                    ],
                    "warnings": [],
                }
            )
        for proposal in proposals:
            results.append(
                lint_one(proposal, proposal.parent.name, repo_root, tasks_root, fallback_spec)
            )

    total_errors = sum(len(result["errors"]) for result in results)
    passed = total_errors == 0
    payload = {
        "tool": "lint_change",
        "passed": passed,
        "changes": results,
        "error_count": total_errors,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for result in results:
            change_id = result["change_id"] or "-"
            if result["errors"]:
                print(
                    "FAIL change "
                    + str(change_id)
                    + ": "
                    + str(len(result["errors"]))
                    + " violation(s)"
                )
                for error in result["errors"]:
                    location = error["file"]
                    if error.get("line"):
                        location = location + ":" + str(error["line"])
                    print("  [" + error["code"] + "] " + error["message"] + " (" + location + ")")
            else:
                print("PASS change " + str(change_id) + ": proposal and task bundle are consistent.")
            for warning in result["warnings"]:
                print("  warning [" + warning["code"] + "] " + warning["message"])
    return EXIT_OK if passed else EXIT_VIOLATIONS


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print("error: unexpected failure: " + str(exc), file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
