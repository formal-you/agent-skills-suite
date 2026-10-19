#!/usr/bin/env python3
"""Branch-isolation guard (layer L1, authoritative in CI).

Fails when the working tree is not on a dedicated task branch: a protected trunk
(`main`, `master`), a branch that does not match the required naming pattern, a
detached HEAD, or a branch that differs from the branch declared in the task's
`02-dev-workspace.md`.

Usage:
    # Local / orchestrator check against the actual working tree
    python .agents/skills/quality-engineering/scripts/branch_guard.py check \
        --repo . --task-dir tasks/<task-id> --require-declared

    # CI check: the branch comes from the pull request event, so git is not queried
    python .agents/skills/quality-engineering/scripts/branch_guard.py check \
        --branch "${{ github.head_ref || github.ref_name }}" \
        --protected main master --json

Options:
    --repo PATH         repository to inspect (default: .)
    --task-dir PATH     task bundle directory that contains 02-dev-workspace.md
    --branch NAME       branch name override; skips git entirely
    --protected LIST    protected branch names, comma- or space-separated
                        (default: main,master; compared case-insensitively)
    --pattern REGEX     required branch-name pattern, applied with re.fullmatch
    --require-declared  fail when the declared Branch value is blank or missing
    --json              emit a machine-readable JSON report

Error codes: BRANCH_PROTECTED, BRANCH_PATTERN_INVALID, BRANCH_DETACHED,
BRANCH_DECLARED_MISSING, BRANCH_MISMATCH, TASK_DOC_MISSING.

Exit codes:
    0  pass - no errors
    1  violation - protected branch, invalid pattern, detached HEAD, missing or
       mismatching declared branch, or a missing task document
    2  usage error - invalid arguments, non-directory --repo, or git failure

The guard is read-only: it never mutates git state and never builds a shell command
string. Every git call passes an argument list to subprocess.run.

Standard library only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

VERSION = "1.0.0"

DEFAULT_PROTECTED = "main,master"
DEFAULT_PATTERN = r"^(feat|fix|task|change|docs|chore|security)/[A-Za-z0-9._-]+$"
DETACHED_HEAD = "HEAD"
TASK_DOC_NAME = "02-dev-workspace.md"


class UsageError(Exception):
    """Invalid CLI input, unusable repository or git failure: exit code 2."""


def error(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def resolve_repo(value: str) -> Path:
    repo = Path(value)
    if not repo.is_dir():
        raise UsageError("--repo is not a directory: " + str(value))
    return repo


def git_branch(repo: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise UsageError("git executable not found")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise UsageError(
            "could not resolve the current branch in " + str(repo)
            + (" (git failed: " + detail + ")" if detail else " (git failed)")
        )
    return result.stdout.strip()


def parse_protected(values: list) -> list:
    names = []
    for value in values:
        for item in value.split(","):
            name = item.strip()
            if name and name.lower() not in names:
                names.append(name.lower())
    if not names:
        raise UsageError("--protected must name at least one branch")
    return names


def parse_branch_row(text: str):
    """Return the second cell of the first `| Branch | ... |` row, or None when absent."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() != "branch":
            continue
        return cells[1].strip().strip("`").strip()
    return None


def read_declared(task_dir: str):
    """Return (declared, missing_error); declared is None when the row is absent."""
    path = Path(task_dir) / TASK_DOC_NAME
    if not path.is_file():
        return None, error("TASK_DOC_MISSING", "task document not found: " + str(path))
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, error(
            "TASK_DOC_MISSING", "task document is unreadable: " + str(path) + " (" + str(exc) + ")"
        )
    return parse_branch_row(text), None


def compare_declared(branch: str, declared, require_declared: bool, errors: list, warnings: list) -> None:
    if not declared:
        message = TASK_DOC_NAME + " does not declare the working branch (expected a '| Branch | ... |' row)"
        if require_declared:
            errors.append(error("BRANCH_DECLARED_MISSING", message + "; --require-declared makes it an error"))
        else:
            warnings.append(error("BRANCH_NOT_DECLARED", message))
        return
    if declared != branch:
        errors.append(
            error(
                "BRANCH_MISMATCH",
                "declared branch '" + declared + "' does not match the current branch '" + branch + "'",
            )
        )


def verify(args: argparse.Namespace) -> dict:
    errors = []
    warnings = []
    protected = parse_protected(args.protected)

    if args.branch is not None:
        branch = args.branch.strip()
        if not branch:
            raise UsageError("--branch must not be empty")
    else:
        branch = git_branch(resolve_repo(args.repo))

    declared = None
    doc_missing = False
    if args.task_dir:
        declared, missing = read_declared(args.task_dir)
        if missing:
            errors.append(missing)
            doc_missing = True

    if branch == DETACHED_HEAD:
        errors.append(error("BRANCH_DETACHED", "HEAD is detached; check out the task branch before working"))
    else:
        if branch.lower() in protected:
            errors.append(
                error(
                    "BRANCH_PROTECTED",
                    "branch '" + branch + "' is a protected trunk branch ("
                    + ", ".join(protected) + ")",
                )
            )
        try:
            pattern = re.compile(args.pattern)
        except re.error as exc:
            raise UsageError("--pattern is not a valid regular expression: " + str(exc))
        if not pattern.fullmatch(branch):
            errors.append(
                error(
                    "BRANCH_PATTERN_INVALID",
                    "branch '" + branch + "' does not match the required pattern " + args.pattern,
                )
            )
        if args.task_dir and not doc_missing:
            compare_declared(branch, declared, args.require_declared, errors, warnings)

    return {
        "passed": not errors,
        "branch": branch,
        "declared": declared,
        "protected": protected,
        "errors": errors,
        "warnings": warnings,
    }


def print_human(payload: dict) -> None:
    if payload["passed"]:
        sys.stdout.write(
            "branch_guard PASSED: branch '" + payload["branch"]
            + "' is not protected and matches the required naming pattern.\n"
        )
    else:
        sys.stdout.write(
            "branch_guard FAILED: branch '" + payload["branch"] + "' has "
            + str(len(payload["errors"])) + " error(s).\n"
        )
        for item in payload["errors"]:
            sys.stdout.write("  " + item["code"] + ": " + item["message"] + "\n")
    if payload["declared"] is not None:
        sys.stdout.write("  declared branch: " + (payload["declared"] or "(blank)") + "\n")
    for item in payload["warnings"]:
        sys.stdout.write("  warning " + item["code"] + ": " + item["message"] + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="branch_guard",
        description="Fail when work is not on a dedicated task branch (L1 branch-isolation guard).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="verify the current or supplied branch")
    check.add_argument("--repo", default=".", help="repository to inspect (default: .)")
    check.add_argument(
        "--task-dir", default=None, help="task bundle directory containing 02-dev-workspace.md"
    )
    check.add_argument("--branch", default=None, help="branch name override; skips git entirely")
    check.add_argument(
        "--protected",
        nargs="+",
        default=[DEFAULT_PROTECTED],
        metavar="NAME",
        help="protected branch names, comma- or space-separated (default: main,master)",
    )
    check.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="required branch-name pattern, applied with re.fullmatch",
    )
    check.add_argument(
        "--require-declared",
        action="store_true",
        help="fail when the declared Branch value is blank or missing",
    )
    check.add_argument("--json", action="store_true", help="print a machine-readable JSON report")
    parser.add_argument("--version", action="version", version="branch_guard " + VERSION)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = verify(args)
    except UsageError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return 2

    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        print_human(payload)
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
