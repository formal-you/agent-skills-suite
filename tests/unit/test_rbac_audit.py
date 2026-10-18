#!/usr/bin/env python3
"""Tests for tools/rbac_audit.py (git-diff based RBAC audit).

Run: python -m unittest discover -s tests/unit -p "test_*.py"
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "rbac_audit.py"

BASE_FILES = {
    "README.md": "# fixture repo\n",
    "src/app.py": "# source\n",
    "tests/acceptance/test_login.py": "# acceptance test\n",
    "tasks/task-001/01-contract.md": "# contract\n",
    "tasks/task-001/04-process.md": (
        "# process\n\n"
        "## 2. Event Log\n\n"
        "| Event ID | Timestamp (UTC) | Event Code |\n"
        "| :--- | :--- | :--- |\n"
        "| EV-01 | 2026-01-01T00:00:00Z | TASK_INITIALIZED |\n"
    ),
}


def git(cwd, *args):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise AssertionError("git " + " ".join(args) + " failed: " + result.stderr)
    return result.stdout


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_tool(cwd, *args):
    return subprocess.run(
        [sys.executable, str(TOOL)] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class RbacAuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "fixture@example.com")
        git(self.repo, "config", "user.name", "Fixture")
        git(self.repo, "config", "commit.gpgsign", "false")
        for path, content in BASE_FILES.items():
            write(self.repo / path, content)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD").strip()

    def tearDown(self):
        self._tmp.cleanup()

    def commit(self, message, role=None):
        git(self.repo, "add", "-A")
        command = ["commit", "-m", message]
        if role is not None:
            command += ["-m", "Agent-Role: " + role]
        git(self.repo, *command)
        return git(self.repo, "rev-parse", "HEAD").strip()

    def test_clean_range_passes(self):
        result = run_tool(self.repo, "--base", self.base, "--head", "HEAD", "--role", "dev")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASSED", result.stdout)

    def test_dev_editing_acceptance_tests_fails(self):
        write(self.repo / "tests" / "acceptance" / "test_login.py", "# changed by dev\n")
        self.commit("edit acceptance test", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["role"], "dev")
        codes = [violation["code"] for violation in payload["violations"]]
        self.assertIn("DEV_EDITED_ACCEPTANCE_TESTS", codes)

    def test_dev_editing_src_passes(self):
        write(self.repo / "src" / "app.py", "# changed by dev\n")
        self.commit("edit source", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_qa_editing_src_fails(self):
        write(self.repo / "src" / "app.py", "# changed by qa\n")
        self.commit("edit source", role="qa")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = [violation["code"] for violation in json.loads(result.stdout)["violations"]]
        self.assertIn("QA_EDITED_SOURCE", codes)

    def test_qa_editing_acceptance_tests_passes(self):
        write(self.repo / "tests" / "acceptance" / "test_login.py", "# changed by qa\n")
        self.commit("edit acceptance test", role="qa")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_planner_editing_contract_fails(self):
        write(self.repo / "tasks" / "task-001" / "01-contract.md", "# changed by dev\n")
        self.commit("edit contract", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = [violation["code"] for violation in json.loads(result.stdout)["violations"]]
        self.assertIn("CONTRACT_EDITED_BY_NON_PLANNER", codes)

    def test_planner_editing_contract_passes(self):
        write(self.repo / "tasks" / "task-001" / "01-contract.md", "# changed by planner\n")
        self.commit("edit contract", role="planner")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_process_event_row_deletion_fails(self):
        process = self.repo / "tasks" / "task-001" / "04-process.md"
        process.write_text(
            "# process\n\n"
            "## 2. Event Log\n\n"
            "| Event ID | Timestamp (UTC) | Event Code |\n"
            "| :--- | :--- | :--- |\n",
            encoding="utf-8",
        )
        self.commit("trim process rows", role="planner")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = [violation["code"] for violation in json.loads(result.stdout)["violations"]]
        self.assertIn("PROCESS_EVENT_ROWS_DELETED", codes)

    def test_process_edit_without_row_deletion_warns(self):
        process = self.repo / "tasks" / "task-001" / "04-process.md"
        process.write_text(
            process.read_text(encoding="utf-8") + "\n<!-- regenerate note -->\n",
            encoding="utf-8",
        )
        self.commit("note in process", role="planner")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("PROCESS_EDITED", codes)

    def test_missing_role_is_usage_error(self):
        write(self.repo / "src" / "app.py", "# change\n")
        self.commit("no trailer")
        result = run_tool(self.repo, "--base", self.base)
        self.assertEqual(result.returncode, 2)
        self.assertIn("role", result.stderr.lower())

    def test_role_flag_overrides_trailer(self):
        write(self.repo / "src" / "app.py", "# change\n")
        self.commit("dev changes source", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--role", "qa", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = [violation["code"] for violation in json.loads(result.stdout)["violations"]]
        self.assertIn("QA_EDITED_SOURCE", codes)

    def test_rename_of_acceptance_test_by_dev_fails(self):
        git(self.repo, "mv", "tests/acceptance/test_login.py", "tests/acceptance/test_login_v2.py")
        self.commit("rename acceptance test", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = [violation["code"] for violation in json.loads(result.stdout)["violations"]]
        self.assertIn("DEV_EDITED_ACCEPTANCE_TESTS", codes)

    def test_json_shape(self):
        write(self.repo / "src" / "app.py", "# change\n")
        self.commit("edit source", role="dev")
        result = run_tool(self.repo, "--base", self.base, "--json")
        payload = json.loads(result.stdout)
        for key in ("passed", "role", "base", "head", "changed_files", "violations", "warnings"):
            self.assertIn(key, payload)

    def test_bad_base_ref_is_usage_error(self):
        result = run_tool(self.repo, "--base", "does-not-exist", "--role", "dev")
        self.assertEqual(result.returncode, 2)

    def test_help_and_version(self):
        result = run_tool(self.repo, "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        result = run_tool(self.repo, "--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("2.0.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
