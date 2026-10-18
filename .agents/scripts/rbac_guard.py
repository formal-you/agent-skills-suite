#!/usr/bin/env python3
"""RBAC guard - optional PreToolUse hook adapter (Antigravity format).

Layer L1 (best effort) of the layered RBAC model. It blocks the obvious
cross-role writes when a hook-capable harness runs it. The authoritative layer
is the git audit in tools/rbac_audit.py, which runs in CI and cannot be
bypassed by a prompt.

Payload compatibility:
  * Antigravity: {"toolCall": {"args": {"TargetFile" | "target_file": ...}}}
  * Claude / DSH: {"tool_input": {"file_path": ...}} (also top-level file_path)
  * generic:     {"args": {"path": ...}}

Behaviour:
  * relative paths are resolved against the workspace root;
  * matching is by path segments, never by leading-slash substrings;
  * the role comes from AGENT_ROLE or AGY_AGENT_ROLE (aliases accepted);
  * the decision is always printed as Antigravity decision JSON and the
    process exit code is always 0 so a hook can never break a tool call;
  * a parse failure allows the call and emits a warning on stderr.

Standard library only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

VERSION = "2.0.0"

ROLE_ALIASES = {
    "dev": "dev",
    "devagent": "dev",
    "dev-agent": "dev",
    "qa": "qa",
    "qaagent": "qa",
    "qa-agent": "qa",
    "planner": "planner",
    "planneragent": "planner",
    "planner-agent": "planner",
}

PROCESS_FILE = "04-process.md"
CONTRACT_FILE = "01-contract.md"
QA_REPORT_FILE = "03-qa-verification.md"
DEV_WORKSPACE_FILE = "02-dev-workspace.md"


def _allow():
    return {"decision": "allow"}


def _deny(reason):
    return {"decision": "deny", "reason": reason}


def _first_string(mapping, keys):
    if not isinstance(mapping, dict):
        return ""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_target(payload):
    """Return the target path from any supported hook payload shape."""
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


def workspace_root(payload):
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


def resolve_target(target, root):
    candidate = Path(target).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve()
    except OSError:
        return Path(os.path.abspath(str(candidate)))


def role():
    raw = os.environ.get("AGENT_ROLE") or os.environ.get("AGY_AGENT_ROLE") or ""
    normalized = raw.strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)


def _has_segments(segments, sequence):
    if not sequence:
        return False
    length = len(sequence)
    for index in range(0, len(segments) - length + 1):
        if tuple(segments[index : index + length]) == tuple(sequence):
            return True
    return False


def decide(payload):
    current_role = role()
    target = extract_target(payload)
    if not target:
        return _allow()

    root = workspace_root(payload)
    resolved = resolve_target(target, root)
    segments = [part.lower() for part in resolved.parts]
    name = segments[-1] if segments else ""

    # Any role: tasks/*/04-process.md is tooling-owned.
    if name == PROCESS_FILE and "tasks" in segments:
        return _deny(
            "RBAC: " + PROCESS_FILE + " is maintained by the event bus; agents must not edit it."
        )

    if current_role == "dev":
        if name in (CONTRACT_FILE, QA_REPORT_FILE):
            return _deny(
                "RBAC: the dev role must not edit " + name + " (contract and QA report are read-only for dev)."
            )
        if _has_segments(segments, ("tests", "acceptance")):
            return _deny(
                "RBAC: the dev role must not edit acceptance tests under tests/acceptance/."
            )

    if current_role == "qa":
        if name in (CONTRACT_FILE, DEV_WORKSPACE_FILE):
            return _deny(
                "RBAC: the QA role must not edit " + name + " (contract and dev workspace are read-only for QA)."
            )
        if "src" in segments:
            return _deny(
                "RBAC: the QA role must not edit source code under src/; report the bug instead."
            )

    # planner and unknown roles: only the process file is protected.
    return _allow()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rbac_guard",
        description="Optional PreToolUse RBAC adapter; prints an Antigravity decision JSON object.",
    )
    parser.add_argument("--version", action="version", version="rbac_guard " + VERSION)
    try:
        parser.parse_known_args(argv)
    except SystemExit:
        raise

    try:
        raw = "" if sys.stdin.isatty() else sys.stdin.read()
    except (OSError, ValueError):
        raw = ""

    if not raw.strip():
        sys.stdout.write(json.dumps(_allow()) + "\n")
        return 0

    try:
        payload = json.loads(raw)
    except ValueError as exc:
        sys.stderr.write("rbac_guard: cannot parse hook payload (" + str(exc) + "); allowing the call.\n")
        sys.stdout.write(json.dumps(_allow()) + "\n")
        return 0

    try:
        result = decide(payload)
    except Exception as exc:  # pragma: no cover - defensive, hooks must not fail closed
        sys.stderr.write("rbac_guard: internal error (" + str(exc) + "); allowing the call.\n")
        result = _allow()

    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
