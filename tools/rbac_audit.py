#!/usr/bin/env python3
"""Harness-neutral RBAC audit (layer L2, authoritative in CI).

Diffs a git range and fails when a commit changed files its role may not touch:

  * dev editing tests/acceptance/**            -> violation
  * qa editing src/**                          -> violation
  * a non-planner editing tasks/*/01-contract.md -> violation
  * any role deleting event rows from a 04-process.md -> violation
    (editing 04-process.md without deleting event rows only warns)

The role comes from --role or from the commit trailer:

    Agent-Role: dev|qa|planner

Exit codes: 0 pass, 1 violations, 2 usage/git error.

Standard library only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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
VALID_ROLES = ("dev", "qa", "planner")
TRAILER_RE = re.compile(r"^\s*Agent-Role\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


class AuditError(Exception):
    """Usage or git error: exit code 2."""


def _normalize_role(value):
    if value is None:
        return None
    normalized = value.strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)


def git(args, cwd):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise AuditError("git executable not found")
    if result.returncode != 0:
        raise AuditError("git " + " ".join(args) + " failed: " + (result.stderr or "").strip())
    return result.stdout


def repo_root(cwd):
    output = git(["rev-parse", "--show-toplevel"], cwd).strip()
    if not output:
        raise AuditError("not inside a git repository")
    return Path(output)


def resolve_role(explicit, head, root):
    if explicit:
        role = _normalize_role(explicit)
        if role not in VALID_ROLES:
            raise AuditError("invalid role: " + str(explicit))
        return role
    message = git(["log", "-1", "--format=%B", head], root)
    match = TRAILER_RE.search(message)
    if not match:
        raise AuditError(
            "no role available: pass --role or add an 'Agent-Role: <role>' commit trailer"
        )
    role = _normalize_role(match.group(1))
    if role not in VALID_ROLES:
        raise AuditError("commit trailer Agent-Role is not one of " + ", ".join(VALID_ROLES))
    return role


def changed_files(base, head, root):
    output = git(["diff", "--name-status", base + "..." + head], root)
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1].strip()
        if path:
            files.append((status, path.replace("\\", "/")))
    return files


def _segments(path):
    return [part for part in path.split("/") if part]


def _starts_with(segments, prefix):
    return segments[: len(prefix)] == list(prefix)


def process_rows_deleted(base, head, path, root):
    diff = git(["diff", "--unified=0", base + "..." + head, "--", path], root)
    for line in diff.splitlines():
        if not line.startswith("-") or line.startswith("---"):
            continue
        removed = line[1:]
        if "|" in removed and re.search(r"EV-[A-Za-z0-9_-]*", removed):
            return True
    return False


def audit(base, head, role, tasks_dir, root):
    violations = []
    warnings = []
    files = changed_files(base, head, root)
    tasks_prefix = _segments(tasks_dir.replace("\\", "/"))

    for _status, path in files:
        segments = _segments(path)
        name = segments[-1] if segments else ""

        if role == "dev" and _starts_with(segments, ("tests", "acceptance")):
            violations.append(
                {
                    "code": "DEV_EDITED_ACCEPTANCE_TESTS",
                    "path": path,
                    "message": "the dev role must not edit acceptance tests",
                }
            )
        if role == "qa" and _starts_with(segments, ("src",)):
            violations.append(
                {
                    "code": "QA_EDITED_SOURCE",
                    "path": path,
                    "message": "the qa role must not edit source code",
                }
            )
        if (
            role != "planner"
            and name == "01-contract.md"
            and tasks_prefix
            and _starts_with(segments, tasks_prefix)
        ):
            violations.append(
                {
                    "code": "CONTRACT_EDITED_BY_NON_PLANNER",
                    "path": path,
                    "message": "only the planner role may edit task contracts",
                }
            )
        if name == "04-process.md":
            if process_rows_deleted(base, head, path, root):
                violations.append(
                    {
                        "code": "PROCESS_EVENT_ROWS_DELETED",
                        "path": path,
                        "message": "event rows may not be deleted from 04-process.md",
                    }
                )
            else:
                warnings.append(
                    {
                        "code": "PROCESS_EDITED",
                        "path": path,
                        "message": "04-process.md was edited; prefer regenerating it from the tools",
                    }
                )
    return files, violations, warnings


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rbac_audit",
        description="Git-diff based RBAC audit (authoritative enforcement layer).",
    )
    parser.add_argument("--base", required=True, help="base git ref (for example origin/main)")
    parser.add_argument("--head", default="HEAD", help="head git ref (default: HEAD)")
    parser.add_argument("--role", choices=VALID_ROLES, default=None, help="role for the range")
    parser.add_argument("--tasks-dir", default="tasks", help="task bundle root (default: tasks)")
    parser.add_argument("--json", action="store_true", help="print a machine-readable JSON object")
    parser.add_argument("--version", action="version", version="rbac_audit " + VERSION)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = repo_root(Path.cwd())
        role = resolve_role(args.role, args.head, root)
        files, violations, warnings = audit(args.base, args.head, role, args.tasks_dir, root)
    except AuditError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return 2

    passed = not violations
    if args.json:
        payload = {
            "passed": passed,
            "role": role,
            "base": args.base,
            "head": args.head,
            "changed_files": [path for _status, path in files],
            "violations": violations,
            "warnings": warnings,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        if passed:
            sys.stdout.write("RBAC audit PASSED for role " + role + " (" + str(len(files)) + " changed file(s)).\n")
        else:
            sys.stdout.write(
                "RBAC audit FAILED for role " + role + ": " + str(len(violations)) + " violation(s).\n"
            )
            for violation in violations:
                sys.stdout.write(
                    "  " + violation["code"] + ": " + violation["path"] + " - " + violation["message"] + "\n"
                )
        for warning in warnings:
            sys.stdout.write("  warning " + warning["code"] + ": " + warning["path"] + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
