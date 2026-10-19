#!/usr/bin/env python3
"""Tests for the quality-engineering branch_guard.py script (branch-isolation gate).

The tests are black-box: they invoke the shipped script in subprocesses against temporary
local git repositories and assert the documented exit codes, error codes and JSON shape.

Run from the repository root:
    python -m unittest tests.unit.test_branch_guard -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = (
    REPO_ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "branch_guard.py"
)

FEATURE = "feat/task-001-x"
GIT_IDENTITY = (
    "-c",
    "user.email=fixture@example.com",
    "-c",
    "user.name=Fixture",
    "-c",
    "commit.gpgsign=false",
)


def git(cwd, *args):
    result = subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise AssertionError("git " + " ".join(args) + " failed: " + result.stderr)
    return result.stdout


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_task_doc(directory: Path, branch_cell: str) -> None:
    write(
        directory / "02-dev-workspace.md",
        "# Dev Workspace\n\n"
        "## 1. Execution metadata\n\n"
        "| Field | Value |\n"
        "| :--- | :--- |\n"
        "| Dev agent | Fixture |\n"
        "| Branch | " + branch_cell + " |\n"
        "| Handoff commit | deadbeef |\n",
    )


def run_tool(cwd: Path, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def codes(payload: dict, key: str = "errors") -> list:
    return [item["code"] for item in payload[key]]


class BranchGuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="branch-guard-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        git(self.repo, "commit", "--allow-empty", "-m", "base")
        self.task_dir = self.root / "tasks" / "task-001"

    def set_branch(self, name: str) -> None:
        git(self.repo, "checkout", "-B", name)

    def test_feature_branch_passes(self):
        self.set_branch(FEATURE)
        result = run_tool(self.repo, "check", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["branch"], FEATURE)
        self.assertEqual(payload["errors"], [])

    def test_human_output_reports_pass(self):
        self.set_branch(FEATURE)
        result = run_tool(self.repo, "check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASSED", result.stdout)

    def test_main_branch_is_violation(self):
        self.set_branch("main")
        result = run_tool(self.repo, "check", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertIn("BRANCH_PROTECTED", codes(payload))
        self.assertIn("BRANCH_PATTERN_INVALID", codes(payload))

    def test_master_branch_is_violation(self):
        self.set_branch("master")
        result = run_tool(self.repo, "check", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BRANCH_PROTECTED", codes(json.loads(result.stdout)))

    def test_human_output_lists_each_error(self):
        self.set_branch("main")
        result = run_tool(self.repo, "check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED", result.stdout)
        self.assertIn("BRANCH_PROTECTED", result.stdout)
        self.assertIn("BRANCH_PATTERN_INVALID", result.stdout)

    def test_branch_override_bypasses_git(self):
        plain = self.root / "plain-directory"
        plain.mkdir()
        result = run_tool(plain, "check", "--repo", plain, "--branch", FEATURE, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["branch"], FEATURE)

    def test_detached_head_is_violation(self):
        self.set_branch(FEATURE)
        git(self.repo, "checkout", "--detach", "HEAD")
        result = run_tool(self.repo, "check", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["branch"], "HEAD")
        self.assertIn("BRANCH_DETACHED", codes(payload))

    def test_default_pattern_rejects_unknown_prefix(self):
        self.set_branch("feature/task-001")
        result = run_tool(self.repo, "check", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BRANCH_PATTERN_INVALID", codes(json.loads(result.stdout)))

    def test_pattern_override_accepts_custom_prefix(self):
        self.set_branch("feature/task-001")
        result = run_tool(
            self.repo, "check", "--pattern", r"^feature/[a-z0-9-]+$", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_invalid_pattern_is_usage_error(self):
        result = run_tool(self.repo, "check", "--branch", FEATURE, "--pattern", "[")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_declared_branch_match_passes(self):
        self.set_branch(FEATURE)
        write_task_doc(self.task_dir, "`" + FEATURE + "`")
        result = run_tool(self.repo, "check", "--task-dir", self.task_dir, "--require-declared", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["declared"], FEATURE)
        self.assertTrue(payload["passed"])

    def test_declared_branch_mismatch_fails(self):
        self.set_branch(FEATURE)
        write_task_doc(self.task_dir, "feat/task-999-other")
        result = run_tool(self.repo, "check", "--task-dir", self.task_dir, "--require-declared", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["declared"], "feat/task-999-other")
        self.assertIn("BRANCH_MISMATCH", codes(payload))

    def test_blank_declared_with_require_declared_fails(self):
        self.set_branch(FEATURE)
        write_task_doc(self.task_dir, "")
        result = run_tool(self.repo, "check", "--task-dir", self.task_dir, "--require-declared", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BRANCH_DECLARED_MISSING", codes(json.loads(result.stdout)))

    def test_blank_declared_without_require_declared_warns_only(self):
        self.set_branch(FEATURE)
        write_task_doc(self.task_dir, "")
        result = run_tool(self.repo, "check", "--task-dir", self.task_dir, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertIn("BRANCH_NOT_DECLARED", codes(payload, "warnings"))

    def test_missing_task_doc_is_violation(self):
        self.set_branch(FEATURE)
        missing = self.root / "tasks" / "task-404"
        result = run_tool(self.repo, "check", "--task-dir", missing, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertIn("TASK_DOC_MISSING", codes(payload))

    def test_protected_list_accepts_commas_and_is_case_insensitive(self):
        result = run_tool(
            self.repo, "check", "--branch", "MAIN", "--protected", "main,master", "--json"
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BRANCH_PROTECTED", codes(json.loads(result.stdout)))

    def test_custom_protected_list_replaces_the_default(self):
        result = run_tool(
            self.repo, "check", "--branch", FEATURE, "--protected", "release", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["protected"], ["release"])

    def test_json_shape(self):
        self.set_branch(FEATURE)
        write_task_doc(self.task_dir, FEATURE)
        result = run_tool(
            self.repo, "check", "--task-dir", self.task_dir, "--require-declared", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        for key in ("passed", "branch", "declared", "protected", "errors", "warnings"):
            self.assertIn(key, payload)
        self.assertIsInstance(payload["errors"], list)
        self.assertIsInstance(payload["warnings"], list)
        self.assertIsInstance(payload["protected"], list)

        failure = run_tool(self.repo, "check", "--branch", "main", "--json")
        failure_payload = json.loads(failure.stdout)
        self.assertTrue(failure_payload["errors"])
        for item in failure_payload["errors"]:
            self.assertEqual(set(item), {"code", "message"})

    def test_bad_repo_is_usage_error(self):
        target = self.root / "not-a-directory"
        target.write_text("x", encoding="utf-8")
        result = run_tool(self.repo, "check", "--repo", target)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("error", result.stderr.lower())

    def test_non_git_directory_is_usage_error(self):
        plain = self.root / "plain-directory"
        plain.mkdir()
        result = run_tool(plain, "check", "--repo", plain)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_help_and_version(self):
        result = run_tool(self.repo, "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        self.assertIn("check", result.stdout)
        result = run_tool(self.repo, "--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("branch_guard 1.0.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
