#!/usr/bin/env python3
"""Event bus logger - optional PostToolUse hook adapter (Antigravity format).

Appends one event row to a task's 04-process.md when a real checkbox line is
checked, updates the task status card, and never touches anything when the
target section/table is missing.

Detection rule (per spec): a line that starts with a checked markdown checkbox
and then names one of the trigger tokens, e.g.

    - [x] WAITING_FOR_QA
    - [x] **Handoff**: WAITING_FOR_QA
    - [x] QA_PASSED

A bare token inside prose or inside an unchecked box is NOT a trigger.

Idempotency is per (task, event code): an event row that already contains the
same code is never appended twice. Writes are atomic (temp file + os.replace).

Tasks directory resolution: --tasks-dir, else the task dir of the changed file
in the hook payload, else ./tasks.

The process file is a derived artifact; the authoritative audit chain is git
plus tools/rbac_audit.py. Standard library only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = "2.0.0"

TRIGGER_RE = re.compile(
    r"^\s*-\s*\[x\]\s*(.*?)\b(WAITING_FOR_QA|QA_PASSED|REWORK_REQUIRED)\b",
    re.IGNORECASE,
)

EVENTS = {
    "WAITING_FOR_QA": {
        "code": "HANDOFF_QA_REQUESTED",
        "actor": "DevAgent",
        "macro_status": "VERIFYING",
        "lock_holder": "QAAgent",
        "payload": "Dev handoff requested",
        "bump_retry": False,
    },
    "QA_PASSED": {
        "code": "TASK_TERMINATED_DONE",
        "actor": "QAAgent",
        "macro_status": "DONE",
        "lock_holder": "None",
        "payload": "QA passed; task accepted",
        "bump_retry": False,
    },
    "REWORK_REQUIRED": {
        "code": "REWORK_TRIGGERED",
        "actor": "QAAgent",
        "macro_status": "REWORKING",
        "lock_holder": "DevAgent",
        "payload": "QA requested rework",
        "bump_retry": True,
    },
}

EVENT_ORDER = ("WAITING_FOR_QA", "QA_PASSED", "REWORK_REQUIRED")

SECTION2_RE = re.compile(r"^##\s+2(?:[.)\s]|$)")
H2_RE = re.compile(r"^##\s+")
SECTION_HINT_RE = re.compile(
    r"event|audit|lifecycle|status|状态机|审计|流转|事件", re.IGNORECASE
)
RETRY_CAP = 3


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _first_string(mapping, keys):
    if not isinstance(mapping, dict):
        return ""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_target(payload):
    if not isinstance(payload, dict):
        return ""
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        target = _first_string(
            tool_call.get("args"), ("TargetFile", "target_file", "file_path", "path")
        )
        if target:
            return target
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        target = _first_string(
            tool_input, ("file_path", "path", "TargetFile", "target_file")
        )
        if target:
            return target
    target = _first_string(payload.get("args"), ("path", "file_path", "TargetFile", "target_file"))
    if target:
        return target
    return _first_string(payload, ("file_path", "path", "TargetFile", "target_file"))


def _workspace_root(payload):
    if isinstance(payload, dict):
        for key in ("workspace_root", "cwd", "project_dir"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                candidate = Path(value).expanduser()
                if candidate.is_absolute():
                    return candidate
    for name in ("AGENT_WORKSPACE_ROOT", "CLAUDE_PROJECT_DIR", "WORKSPACE_ROOT"):
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser()
    return Path.cwd()


def _resolve(target, root):
    candidate = Path(target).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve()
    except OSError:
        return Path(os.path.abspath(str(candidate)))


def triggered_tokens(text):
    """Return the set of event tokens that have a real checked checkbox line."""
    found = set()
    for line in text.splitlines():
        match = TRIGGER_RE.match(line)
        if match:
            found.add(match.group(2).upper())
    return found


def existing_codes(text):
    """Return the set of event codes already present in markdown table rows."""
    codes = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        for spec in EVENTS.values():
            if spec["code"] in stripped:
                codes.add(spec["code"])
    return codes


def _find_section(lines):
    for index, line in enumerate(lines):
        stripped = line.strip()
        if SECTION2_RE.match(stripped):
            return index
    for index, line in enumerate(lines):
        stripped = line.strip()
        if H2_RE.match(stripped) and SECTION_HINT_RE.search(stripped):
            return index
    return None


def _is_separator(line):
    stripped = line.strip()
    if "-" not in stripped:
        return False
    return all(char in "|-: " for char in stripped)


def _table_bounds(lines, section_start):
    indices = []
    for index in range(section_start + 1, len(lines)):
        stripped = lines[index].strip()
        if H2_RE.match(stripped):
            break
        if stripped.startswith("|"):
            indices.append(index)
    if len(indices) < 2:
        return None
    if not _is_separator(lines[indices[1]]):
        return None
    header_cells = [cell for cell in lines[indices[0]].strip().strip("|").split("|")]
    return indices[0], indices[-1], len(header_cells)


def _build_row(columns, spec):
    cells = [
        "EV-AUTO",
        _now_iso(),
        spec["code"],
        spec["actor"],
        spec["payload"],
        "1s",
    ]
    if columns <= 0:
        columns = len(cells)
    if len(cells) > columns:
        cells = cells[:columns]
    while len(cells) < columns:
        cells.append("")
    return "| " + " | ".join(cells) + " |"


def _replace_field(text, key, value):
    pattern = re.compile(
        r"(?m)^(\s*" + re.escape(key) + r"\s*:\s*)(\"[^\"]*\"|'[^']*'|[^\s#]+)(.*)$"
    )
    return pattern.sub(lambda match: match.group(1) + value + match.group(3), text, count=1)


def _bump_retry(text):
    pattern = re.compile(r"(?m)^(\s*retry_count\s*:\s*)(\d+)")

    def replace(match):
        current = int(match.group(2))
        return match.group(1) + str(min(current + 1, RETRY_CAP))

    return pattern.sub(replace, text, count=1)


def _apply_status(text, spec):
    text = _replace_field(text, "macro_status", '"' + spec["macro_status"] + '"')
    text = _replace_field(text, "current_lock_holder", '"' + spec["lock_holder"] + '"')
    if spec["bump_retry"]:
        text = _bump_retry(text)
    return text


def _insert_event(text, spec):
    """Insert one event row; return the new text or None when no table exists."""
    lines = text.splitlines()
    section_start = _find_section(lines)
    if section_start is None:
        return None
    bounds = _table_bounds(lines, section_start)
    if bounds is None:
        return None
    _header, last_row, columns = bounds
    lines.insert(last_row + 1, _build_row(columns, spec))
    updated = "\n".join(lines)
    if text.endswith("\n"):
        updated += "\n"
    return _apply_status(updated, spec)


def atomic_write(path, text):
    directory = str(path.parent)
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + path.name + ".", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def process_task(task_dir):
    process_file = task_dir / "04-process.md"
    if not process_file.is_file():
        return False
    text = _read(process_file)
    if not text:
        return False

    workspace_text = _read(task_dir / "02-dev-workspace.md")
    qa_text = _read(task_dir / "03-qa-verification.md")
    triggers = triggered_tokens(workspace_text) | triggered_tokens(qa_text)
    triggered = set()

    if "WAITING_FOR_QA" in triggers:
        triggered.add("WAITING_FOR_QA")
    if "QA_PASSED" in triggers:
        triggered.add("QA_PASSED")
    if "REWORK_REQUIRED" in triggers:
        triggered.add("REWORK_REQUIRED")

    changed = False
    for token in EVENT_ORDER:
        if token not in triggered:
            continue
        spec = EVENTS[token]
        if spec["code"] in existing_codes(text):
            continue
        updated = _insert_event(text, spec)
        if updated is None:
            continue
        text = updated
        changed = True

    if changed:
        atomic_write(process_file, text)
    return changed


def _task_dirs_from_root(root):
    if not root.is_dir():
        return []
    directories = []
    for item in sorted(os.listdir(root)):
        if item.startswith("."):
            continue
        candidate = root / item
        if candidate.is_dir():
            directories.append(candidate)
    return directories


def _task_dir_from_payload(payload):
    target = extract_target(payload)
    if not target:
        return None
    resolved = _resolve(target, _workspace_root(payload))
    parts = resolved.parts
    lowered = [part.lower() for part in parts]
    if "tasks" not in lowered:
        return None
    index = len(lowered) - 1 - lowered[::-1].index("tasks")
    if len(parts) <= index + 2:
        return None
    candidate = Path(*parts[: index + 2])
    if candidate.is_dir():
        return candidate
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="event_bus_logger",
        description="Optional PostToolUse event bus adapter for 04-process.md.",
    )
    parser.add_argument("--tasks-dir", default=None, help="tasks directory (default: ./tasks)")
    parser.add_argument("--version", action="version", version="event_bus_logger " + VERSION)
    args, _unknown = parser.parse_known_args(argv)

    payload = {}
    try:
        raw = "" if sys.stdin.isatty() else sys.stdin.read()
        if raw.strip():
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {}
    except (OSError, ValueError):
        payload = {}

    try:
        if args.tasks_dir:
            task_dirs = _task_dirs_from_root(Path(args.tasks_dir).expanduser())
        else:
            task_dir = _task_dir_from_payload(payload)
            if task_dir is not None:
                task_dirs = [task_dir]
            else:
                task_dirs = _task_dirs_from_root(Path("./tasks"))
        for task_dir in task_dirs:
            try:
                process_task(task_dir)
            except Exception as exc:  # one broken task must not stop the rest
                sys.stderr.write(
                    "event_bus_logger: skipped " + str(task_dir) + " (" + str(exc) + ")\n"
                )
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write("event_bus_logger: internal error (" + str(exc) + ")\n")

    sys.stdout.write("{}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
