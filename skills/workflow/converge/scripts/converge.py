#!/usr/bin/env python3
"""Converge a QA-passed task bundle back into the technical spec.

The converge helper closes the loop between execution and specification:

  check  -> classify every task bundle as converged / pending / blocked
  apply  -> append the confirmed implementation deviations to the spec, mark the
            derived 04-process.md, archive the bundle, close the change proposal

It only depends on the Python standard library (>= 3.9) and never imports
repository packages. Exit codes: 0 success; 1 content-gate refusal (not
converge-ready, archive destination exists); 2 usage or missing-path error;
3 unexpected internal error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

DEFAULT_SPEC = ".specs/02-tech-spec.md"
DEFAULT_TASKS_DIR = "tasks"
DEFAULT_ARCHIVE_DIR = "tasks/archive"
DEFAULT_CHANGES_DIR = ".specs/changes"

CONVERGED_SECTION = "Converged changes"

DEVIATION_HEADER_RE = re.compile(
    r"^\|\s*Deviation ID\s*\|\s*Spec anchor\s*\|\s*Operation\s*\|\s*Confirmed behavior\s*\|\s*$",
    re.IGNORECASE,
)
SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
DEVIATION_ROW_RE = re.compile(
    r"^\|\s*(?P<deviation_id>DEV-\d{3,})\s*\|\s*(?P<anchor>#sec-[a-z0-9-]+)\s*\|"
    r"\s*(?P<operation>add|modify|remove)\s*\|\s*(?P<behavior>.+?)\s*\|\s*$"
)
CHECKBOX_RE = re.compile(
    r"^\s*-\s*\[(?P<mark>[ xX])\]\s*(?P<label>QA_PASSED|REWORK_REQUIRED)\b"
)
YAML_STATUS_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>status\s*:\s*)(?P<quote>[\"']?)(?P<value>[^\"'#\r\n]*)"
    r"(?P=quote)(?P<tail>\s*(?:#.*)?)$",
    re.IGNORECASE,
)
BOLD_STATUS_RE = re.compile(r"^(?P<prefix>\*\*Status\*\*:\s*)(?P<value>.+?)\s*$", re.IGNORECASE)


class UsageError(Exception):
    """A CLI or missing-path problem: exit code 2."""


class RefusalError(Exception):
    """A content-gate refusal: exit code 1."""


# ---------------------------------------------------------------------------
# Small filesystem / text helpers
# ---------------------------------------------------------------------------


def write_text(path, text):
    """Write UTF-8 text with deterministic LF line endings (3.9 compatible)."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def spec_sha256(path):
    """Hash the spec's normalised text so LF/CRLF checkouts agree."""
    return sha256_text(read_text(path))


def utc_now():
    return datetime.now(timezone.utc)


def format_timestamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date(moment):
    return moment.strftime("%Y-%m-%d")


def normalize_cell(value):
    return " ".join(str(value).split())


def display_path(value):
    """Render a path with forward slashes for markdown/JSON output."""
    return str(value).replace("\\", "/")


# ---------------------------------------------------------------------------
# Frontmatter / contract helpers (no YAML dependency)
# ---------------------------------------------------------------------------


def frontmatter_block(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return "\n".join(lines[1:index])
    return ""


def frontmatter_value(text, key):
    block = frontmatter_block(text)
    match = re.search(r"(?m)^\s*" + re.escape(key) + r"\s*:\s*(.+?)\s*$", block)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith("#"):
        return ""
    value = re.sub(r"\s+#.*$", "", value)
    return value.strip().strip("\"'")


# ---------------------------------------------------------------------------
# Deviation log parsing (strict: header row + separator + DEV rows)
# ---------------------------------------------------------------------------


def parse_deviations(text):
    """Return {table_found, rows, none_marker} for the 02 deviation table.

    Only a table whose header is exactly the frozen deviation header is
    considered; every other table in the document is ignored.
    """
    lines = text.splitlines()
    rows = []
    none_marker = False
    table_found = False
    index = 0
    while index < len(lines):
        if not DEVIATION_HEADER_RE.match(lines[index].strip()):
            index += 1
            continue
        table_found = True
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines) or not SEPARATOR_RE.match(lines[cursor].strip()):
            index += 1
            continue
        cursor += 1
        while cursor < len(lines):
            raw = lines[cursor].strip()
            if not raw.startswith("|"):
                break
            match = DEVIATION_ROW_RE.match(raw)
            if match:
                rows.append(
                    {
                        "deviation_id": match.group("deviation_id"),
                        "anchor": match.group("anchor"),
                        "operation": match.group("operation"),
                        "behavior": normalize_cell(match.group("behavior")),
                    }
                )
            else:
                cells = [cell.strip() for cell in raw.strip("|").split("|")]
                if cells and all(cell.lower() == "none" for cell in cells):
                    none_marker = True
            cursor += 1
        index = cursor
    return {"table_found": table_found, "rows": rows, "none_marker": none_marker}


def converged_hash(task_id, rows, none_marker):
    """Deterministic hash of the converged block (no timestamp, no paths)."""
    parts = [task_id]
    if rows:
        for row in rows:
            parts.append(
                "\t".join(
                    [
                        row["deviation_id"],
                        row["anchor"],
                        row["operation"],
                        normalize_cell(row["behavior"]),
                    ]
                )
            )
    else:
        parts.append("None")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def convergence_marker(spec_text, task_id):
    pattern = (
        r"<!--\s*converged:\s*"
        + re.escape(task_id)
        + r"\s+sha256:(?P<hash>[0-9a-f]{64})\s*-->"
    )
    match = re.search(pattern, spec_text)
    return match.group("hash") if match else None


def spec_anchors(spec_text):
    return set(re.findall(r"#sec-[a-z0-9-]+", spec_text))


# ---------------------------------------------------------------------------
# Bundle assessment
# ---------------------------------------------------------------------------


REQUIRED_DOCUMENTS = (
    "02-dev-workspace.md",
    "03-qa-verification.md",
)
OPTIONAL_DOCUMENTS = (
    "01-contract.md",
    "04-process.md",
)


def qa_verdict(qa_text):
    passed = False
    rework = False
    for line in qa_text.splitlines():
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        checked = match.group("mark").lower() == "x"
        if not checked:
            continue
        if match.group("label") == "QA_PASSED":
            passed = True
        elif match.group("label") == "REWORK_REQUIRED":
            rework = True
    if rework:
        return "REWORK_REQUIRED"
    if passed:
        return "QA_PASSED"
    # Tolerant fallback for hand-written verdicts: a bare "Verdict: QA_PASSED"
    # line (no checkbox) still records the verdict. Unchecked boxes never count.
    for line in qa_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if re.match(r"^-\s*\[\s*\]\s*(QA_PASSED|REWORK_REQUIRED)\b", stripped):
            continue
        if "QA_PASSED" in stripped:
            passed = True
        if "REWORK_REQUIRED" in stripped:
            rework = True
    if rework:
        return "REWORK_REQUIRED"
    if passed:
        return "QA_PASSED"
    return None


def assess_bundle(task_dir, spec_text, strict=False):
    """Classify one task bundle as converged / pending / blocked.

    With strict=True an anchor miss for a modify/remove deviation is a
    spec-drift refusal; without it the miss is reported as a warning.
    """
    task_dir = Path(task_dir)
    task_id = task_dir.name
    marker_hash = convergence_marker(spec_text, task_id)
    result = {
        "task_id": task_id,
        "status": "pending",
        "ready": False,
        "reason": None,
        "detail": "",
        "verdict": None,
        "deviation_count": 0,
        "deviations": [],
        "warnings": [],
        "marker": None,
        "title": "",
    }
    if marker_hash:
        result.update(
            status="converged",
            ready=False,
            reason="already_converged",
            detail="spec already contains the convergence marker",
            marker=marker_hash,
        )
        return result

    missing = [name for name in REQUIRED_DOCUMENTS if not (task_dir / name).is_file()]
    if missing:
        result.update(
            status="blocked",
            reason="missing_document",
            detail="task bundle is missing: " + ", ".join(missing),
        )
        return result

    for optional in OPTIONAL_DOCUMENTS:
        if not (task_dir / optional).is_file():
            result["warnings"].append(
                "missing_document: " + optional + " is not part of the bundle"
            )
    contract_path = task_dir / "01-contract.md"
    contract = read_text(contract_path) if contract_path.is_file() else ""
    result["title"] = frontmatter_value(contract, "title")
    verdict = qa_verdict(read_text(task_dir / "03-qa-verification.md"))
    result["verdict"] = verdict
    if verdict == "REWORK_REQUIRED":
        result.update(
            status="blocked",
            reason="rework_active",
            detail="03-qa-verification.md still records an active REWORK_REQUIRED verdict",
        )
        return result
    if verdict != "QA_PASSED":
        result.update(
            status="blocked",
            reason="qa_not_passed",
            detail="03-qa-verification.md does not record a checked QA_PASSED verdict",
        )
        return result

    parsed = parse_deviations(read_text(task_dir / "02-dev-workspace.md"))
    result["deviations"] = parsed["rows"]
    result["deviation_count"] = len(parsed["rows"])
    if not parsed["table_found"]:
        result.update(
            status="blocked",
            reason="deviation_log_missing",
            detail="02-dev-workspace.md has no 'Implementation deviations' table",
        )
        return result
    if not parsed["rows"] and not parsed["none_marker"]:
        result.update(
            status="blocked",
            reason="deviation_log_blank",
            detail="02-dev-workspace.md deviation table has no DEV rows and no explicit None row",
        )
        return result

    anchors = spec_anchors(spec_text)
    drift = sorted(
        {
            row["anchor"]
            for row in parsed["rows"]
            if row["operation"] in ("modify", "remove") and row["anchor"] not in anchors
        }
    )
    if drift:
        detail = "spec is missing anchors referenced by modify/remove deviations: " + ", ".join(
            drift
        )
        if strict:
            result.update(status="blocked", reason="spec_drift", detail=detail)
            return result
        result["warnings"].append("spec_drift: " + detail)

    result.update(status="pending", ready=True, reason="ready", detail="ready to converge")
    return result


# ---------------------------------------------------------------------------
# Spec rendering
# ---------------------------------------------------------------------------


def build_entry(task_id, title, moment, rows, none_marker, marker_hash, archive_rel):
    heading = "### " + task_id + (": " + title if title else "")
    attribution = (
        "> Converged " + format_date(moment) + " (UTC) by ConvergeTool from "
        "`02-dev-workspace.md` after `QA_PASSED`; source bundle archived at `"
        + archive_rel + "`."
    )
    table = [
        "| Deviation ID | Spec anchor | Operation | Confirmed behavior |",
        "| :--- | :--- | :--- | :--- |",
    ]
    if rows:
        for row in rows:
            table.append(
                "| "
                + row["deviation_id"]
                + " | "
                + row["anchor"]
                + " | "
                + row["operation"]
                + " | "
                + normalize_cell(row["behavior"])
                + " |"
            )
    else:
        table.append("| None | None | None | None |")
    marker = "<!-- converged: " + task_id + " sha256:" + marker_hash + " -->"
    return "\n".join([heading, "", attribution, ""] + table + ["", marker])


def insert_entry_into_spec(spec_text, entry):
    """Append entry at the end of the 'Converged changes' section, creating it once."""
    section_re = re.compile(r"^##\s+" + re.escape(CONVERGED_SECTION) + r"\s*$", re.IGNORECASE)
    lines = spec_text.splitlines()
    heading_index = None
    for index, line in enumerate(lines):
        if section_re.match(line):
            heading_index = index
            break
    if heading_index is None:
        body = spec_text.rstrip("\n")
        return body + "\n\n## " + CONVERGED_SECTION + "\n\n" + entry + "\n"
    end_index = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if re.match(r"^#{1,2}\s+", lines[index]):
            end_index = index
            break
    before = "\n".join(lines[:end_index]).rstrip("\n")
    after = "\n".join(lines[end_index:]).strip("\n")
    combined = before + "\n\n" + entry
    if after:
        combined += "\n\n" + after
    return combined + "\n"


# ---------------------------------------------------------------------------
# 04-process.md rendering
# ---------------------------------------------------------------------------


def update_process_text(text, task_id, timestamp, marker_hash, archive_rel, spec_hash):
    updated = re.sub(
        r"(?m)^(macro_status:\s*)(?:\"[^\"]*\"|'[^']*'|[^\s#]+)[^\n]*$",
        r'\1"CONVERGED"',
        text,
        count=1,
    )
    if re.search(
        r"(?m)^\|[^\n]*TASK_CONVERGED[^\n]*" + re.escape(task_id) + r"[^\n]*\|\s*$", updated
    ):
        return updated, False
    row = (
        "| EV-AUTO | "
        + timestamp
        + " | TASK_CONVERGED | ConvergeTool | task="
        + task_id
        + "; archive="
        + archive_rel
        + "; marker="
        + marker_hash
        + "; spec="
        + spec_hash
        + " | 0s |"
    )
    lines = updated.splitlines()
    section_start = None
    for index, line in enumerate(lines):
        if re.match(r"^##\s+2[.)\s]", line) or re.search(r"event log", line, re.IGNORECASE):
            section_start = index
            break
    start = section_start if section_start is not None else 0
    last_row = None
    for index in range(start, len(lines)):
        if index > start and re.match(r"^##\s+", lines[index]):
            break
        if lines[index].strip().startswith("|"):
            last_row = index
    insert_at = last_row + 1 if last_row is not None else len(lines)
    lines.insert(insert_at, row)
    return "\n".join(lines) + "\n", True


# ---------------------------------------------------------------------------
# Change proposal helpers
# ---------------------------------------------------------------------------


def archive_proposal_status(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = YAML_STATUS_RE.match(line)
        if match:
            lines[index] = (
                match.group("indent")
                + match.group("key")
                + match.group("quote")
                + "archived"
                + match.group("quote")
                + match.group("tail")
            )
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    for index, line in enumerate(lines):
        match = BOLD_STATUS_RE.match(line)
        if match:
            lines[index] = match.group("prefix") + "archived"
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text.rstrip("\n") + "\nStatus: archived\n"


def build_convergence_doc(
    change_id,
    task_id,
    title,
    moment,
    rows,
    marker_hash,
    archive_rel,
    spec_rel,
    spec_hash,
):
    table = [
        "| Deviation ID | Spec anchor | Operation | Confirmed behavior |",
        "| :--- | :--- | :--- | :--- |",
    ]
    if rows:
        for row in rows:
            table.append(
                "| "
                + row["deviation_id"]
                + " | "
                + row["anchor"]
                + " | "
                + row["operation"]
                + " | "
                + normalize_cell(row["behavior"])
                + " |"
            )
    else:
        table.append("| None | None | None | None |")
    lines = [
        "# Change Convergence: " + change_id,
        "",
        "> Written by ConvergeTool when the implementing task passed QA. This change",
        "> proposal is archived; do not reopen it for the converged task.",
        "",
        "| Field | Value |",
        "| :--- | :--- |",
        "| Change ID | `" + change_id + "` |",
        "| Task ID | `" + task_id + "` |",
        "| Task title | " + (title if title else "`" + task_id + "`") + " |",
        "| QA verdict | `QA_PASSED` |",
        "| Converged at (UTC) | `" + format_timestamp(moment) + "` |",
        "| Archive path | `" + archive_rel + "` |",
        "| Spec | `" + spec_rel + "` |",
        "| Spec SHA-256 | `" + spec_hash + "` |",
        "| Marker | " + chr(96) + "<!-- converged: " + task_id + " sha256:" + marker_hash + " -->" + chr(96) + " |",
        "",
        "## Deviations folded into the spec",
        "",
    ]
    return "\n".join(lines + table) + "\n"


# ---------------------------------------------------------------------------
# JSON payload helpers
# ---------------------------------------------------------------------------


def emit_json(payload):
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def iter_bundles(tasks_dir):
    if not tasks_dir.is_dir():
        raise UsageError("--tasks-dir does not exist or is not a directory: " + str(tasks_dir))
    bundles = []
    for entry in sorted(tasks_dir.iterdir(), key=lambda path: path.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        docs = (
            (entry / "01-contract.md").is_file()
            or (entry / "02-dev-workspace.md").is_file()
            or (entry / "03-qa-verification.md").is_file()
        )
        if entry.name == "archive" or not docs:
            continue
        bundles.append(entry)
    return bundles


def run_check(args):
    tasks_dir = Path(args.tasks_dir)
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        raise UsageError("--spec does not exist or is not a file: " + display_path(spec_path))
    spec_text = read_text(spec_path)
    results = [
        assess_bundle(bundle, spec_text, strict=bool(getattr(args, "strict", False)))
        for bundle in iter_bundles(tasks_dir)
    ]
    summary = {"converged": 0, "pending": 0, "blocked": 0}
    for item in results:
        summary[item["status"]] += 1
    pending = summary["pending"]
    spec_hash = sha256_text(spec_text)

    if args.json:
        emit_json(
            {
                "tool": "converge",
                "version": __version__,
                "command": "check",
                "spec": display_path(spec_path),
                "spec_sha256": spec_hash,
                "tasks": results,
                "summary": summary,
                "fail_on_pending": bool(args.fail_on_pending),
                "strict": bool(getattr(args, "strict", False)),
            }
        )
    else:
        print("converge " + __version__ + " check - " + str(len(results)) + " task bundle(s)")
        for item in results:
            line = item["status"].upper().ljust(9) + " " + item["task_id"]
            if item["status"] == "pending":
                line += "  ready to converge (" + str(item["deviation_count"]) + " deviation row(s))"
            elif item["status"] == "converged":
                line += "  marker sha256:" + (item["marker"] or "")
            else:
                line += "  " + (item["reason"] or "blocked") + ": " + item["detail"]
            print(line)
        print(
            "summary: "
            + str(summary["converged"])
            + " converged, "
            + str(summary["pending"])
            + " pending, "
            + str(summary["blocked"])
            + " blocked; spec "
            + spec_hash
        )
        if args.fail_on_pending and pending:
            print("error: " + str(pending) + " bundle(s) are pending convergence", file=sys.stderr)

    if args.fail_on_pending and pending:
        return EXIT_REFUSED
    return EXIT_OK


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def archive_destination(archive_dir, task_id):
    return Path(archive_dir) / task_id


def run_apply(args):
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        raise UsageError("--spec does not exist or is not a file: " + display_path(spec_path))
    task_arg = Path(args.task)
    task_id = task_arg.name
    if not task_id:
        raise UsageError("--task must name a task bundle directory")
    spec_text = read_text(spec_path)
    spec_hash_before = sha256_text(spec_text)
    existing_marker = convergence_marker(spec_text, task_id)
    dest = archive_destination(args.archive_dir, task_id)

    if not task_arg.is_dir():
        if existing_marker:
            payload = {
                "tool": "converge",
                "version": __version__,
                "command": "apply",
                "task_id": task_id,
                "status": "no_changes",
                "reason": "already_converged",
                "detail": "spec marker already present; bundle is already archived",
                "marker": existing_marker,
                "spec": display_path(spec_path),
                "spec_sha256": spec_hash_before,
            }
            if args.json:
                emit_json(payload)
            else:
                print("converge " + __version__ + " apply - no changes")
                print("task " + task_id + " is already converged (marker sha256:" + existing_marker + ")")
            return EXIT_OK
        raise UsageError("--task does not exist: " + display_path(task_arg))

    assessment = assess_bundle(task_arg, spec_text, strict=bool(getattr(args, "strict", False)))
    if assessment["status"] == "converged":
        if not dest.exists() and not dest.is_symlink():
            if args.dry_run:
                print(
                    "[dry-run] would archive "
                    + display_path(task_arg)
                    + " -> "
                    + display_path(dest)
                )
                return EXIT_OK
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(task_arg), str(dest))
            print(
                "task " + task_id + " was already converged; finished archiving -> " + display_path(dest)
            )
            return EXIT_OK
        if args.json:
            emit_json(
                {
                    "tool": "converge",
                    "version": __version__,
                    "command": "apply",
                    "task_id": task_id,
                    "status": "no_changes",
                    "reason": "already_converged",
                    "marker": assessment["marker"],
                }
            )
        else:
            print("converge " + __version__ + " apply - no changes")
            print("task " + task_id + " is already converged; nothing to do")
        return EXIT_OK

    if assessment["status"] != "pending":
        raise RefusalError(
            "task "
            + task_id
            + " is not converge-ready ("
            + (assessment["reason"] or "blocked")
            + "): "
            + assessment["detail"]
        )

    if not (task_arg / "04-process.md").is_file():
        raise RefusalError(
            "task " + task_id + " is not converge-ready (missing_document): 04-process.md is absent"
        )
    contract_path = task_arg / "01-contract.md"
    contract = read_text(contract_path) if contract_path.is_file() else ""
    title = frontmatter_value(contract, "title")
    change_id = frontmatter_value(contract, "change_id")
    rows = assessment["deviations"]
    parsed = parse_deviations(read_text(task_arg / "02-dev-workspace.md"))
    none_marker = parsed["none_marker"] and not rows

    if dest.exists() and not args.force:
        raise RefusalError(
            "archive destination already exists: " + display_path(dest) + "; pass --force to replace it"
        )

    moment = utc_now()
    timestamp = format_timestamp(moment)
    marker_hash = converged_hash(task_id, rows, none_marker)
    spec_rel = display_path(spec_path)
    archive_rel = display_path(dest)
    entry = build_entry(task_id, title, moment, rows, none_marker, marker_hash, archive_rel)
    new_spec = insert_entry_into_spec(spec_text, entry)
    new_spec_hash = sha256_text(new_spec)

    process_path = task_arg / "04-process.md"
    new_process, event_appended = update_process_text(
        read_text(process_path), task_id, timestamp, marker_hash, archive_rel, new_spec_hash
    )

    proposal_path = None
    convergence_path = None
    if change_id:
        changes_dir = Path(args.changes_dir)
        candidate = changes_dir / change_id / "proposal.md"
        if candidate.is_file():
            proposal_path = candidate
            convergence_path = changes_dir / change_id / "convergence.md"

    writes = [display_path(spec_path), display_path(process_path)]
    if convergence_path is not None:
        writes.extend([display_path(proposal_path), display_path(convergence_path)])
    writes.append(display_path(task_arg) + " -> " + display_path(dest))

    if args.dry_run:
        if args.json:
            emit_json(
                {
                    "tool": "converge",
                    "version": __version__,
                    "command": "apply",
                    "task_id": task_id,
                    "status": "pending",
                    "dry_run": True,
                    "marker": "sha256:" + marker_hash,
                    "would_write": writes,
                    "spec": spec_rel,
                    "spec_sha256": new_spec_hash,
                    "change_id": change_id or None,
                }
            )
        else:
            print("converge " + __version__ + " apply - dry run, no files written")
            print("task " + task_id + " is converge-ready (" + str(len(rows)) + " deviation row(s))")
            for item in writes:
                print("[dry-run] would write " + item)
            print("[dry-run] would append marker sha256:" + marker_hash)
        return EXIT_OK

    write_text(spec_path, new_spec)
    write_text(process_path, new_process)
    if convergence_path is not None:
        write_text(proposal_path, archive_proposal_status(read_text(proposal_path)))
        convergence_note = build_convergence_doc(
            change_id,
            task_id,
            title,
            moment,
            rows,
            marker_hash,
            archive_rel,
            spec_rel,
            new_spec_hash,
        )
        convergence_path.parent.mkdir(parents=True, exist_ok=True)
        write_text(convergence_path, convergence_note)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    shutil.move(str(task_arg), str(dest))

    if args.json:
        emit_json(
            {
                "tool": "converge",
                "version": __version__,
                "command": "apply",
                "task_id": task_id,
                "status": "converged",
                "marker": "sha256:" + marker_hash,
                "marker_comment": "<!-- converged: " + task_id + " sha256:" + marker_hash + " -->",
                "deviation_count": len(rows),
                "none_marker": none_marker,
                "archive": archive_rel,
                "spec": spec_rel,
                "spec_sha256_before": spec_hash_before,
                "spec_sha256_after": new_spec_hash,
                "event_appended": event_appended,
                "change_id": change_id or None,
                "convergence_file": display_path(convergence_path)
                if convergence_path is not None
                else None,
                "proposal_archived": proposal_path is not None,
            }
        )
    else:
        print("converge " + __version__ + " apply - converged")
        print("task " + task_id + " -> " + archive_rel)
        print("spec " + spec_rel + " -> " + new_spec_hash)
        print("marker sha256:" + marker_hash)
        if convergence_path is not None:
            print("change " + change_id + " archived: " + display_path(convergence_path))
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="converge.py",
        description=(
            "Fold QA-passed implementation deviations into .specs/02-tech-spec.md, "
            "archive the task bundle and close the change proposal."
        ),
        epilog=(
            "Exit codes: 0 success, 1 content-gate refusal, 2 usage or missing path, "
            "3 unexpected error. Example: python converge.py check --tasks-dir ./tasks --json"
        ),
    )
    parser.add_argument(
        "--spec", default=DEFAULT_SPEC, help="technical spec path (default: " + DEFAULT_SPEC + ")"
    )
    parser.add_argument(
        "--spec-sha256",
        action="store_true",
        help="print the spec's sha256 digest and exit (CI drift detection)",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--spec", default=argparse.SUPPRESS, help="technical spec path")
    common.add_argument(
        "--spec-sha256",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print the spec's sha256 digest and exit",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="{check,apply}")

    check = subparsers.add_parser(
        "check",
        parents=[common],
        help="classify task bundles as converged / pending / blocked",
        description="Classify every task bundle as converged, pending (ready to converge) or blocked.",
    )
    check.add_argument(
        "--tasks-dir", default=DEFAULT_TASKS_DIR, help="task root directory (default: tasks)"
    )
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument(
        "--fail-on-pending",
        action="store_true",
        help="exit 1 when at least one bundle is pending convergence",
    )
    check.add_argument(
        "--strict",
        action="store_true",
        help="treat a missing modify/remove spec anchor as a spec-drift refusal",
    )

    apply_parser = subparsers.add_parser(
        "apply",
        parents=[common],
        help="append the converged deviations to the spec and archive the bundle",
        description="Converge one QA-passed task bundle into the technical spec.",
    )
    apply_parser.add_argument(
        "--task", required=True, help="task bundle directory, e.g. tasks/task-001-auth"
    )
    apply_parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help="archive root (default: tasks/archive)",
    )
    apply_parser.add_argument(
        "--changes-dir",
        default=DEFAULT_CHANGES_DIR,
        help="change proposal root (default: .specs/changes)",
    )
    apply_parser.add_argument(
        "--dry-run", action="store_true", help="print the planned writes; write nothing"
    )
    apply_parser.add_argument("--json", action="store_true", help="machine-readable output")
    apply_parser.add_argument(
        "--force", action="store_true", help="replace an existing archive destination"
    )
    apply_parser.add_argument(
        "--strict",
        action="store_true",
        help="treat a missing modify/remove spec anchor as a spec-drift refusal",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if getattr(args, "spec_sha256", False):
            spec_path = Path(args.spec)
            if not spec_path.is_file():
                raise UsageError("--spec does not exist or is not a file: " + display_path(spec_path))
            print(spec_sha256(spec_path))
            return EXIT_OK
        if not getattr(args, "command", None):
            parser.print_help(sys.stderr)
            return EXIT_USAGE
        if args.command == "check":
            return run_check(args)
        if args.command == "apply":
            return run_apply(args)
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    except RefusalError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return EXIT_REFUSED
    except UsageError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print("error: unexpected failure: " + str(exc), file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
