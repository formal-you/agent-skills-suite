#!/usr/bin/env python3
"""Tests for the optional hook scripts: rbac_guard.py and event_bus_logger.py.

Run: python -m unittest discover -s tests/unit -p "test_*.py"
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RBAC = REPO_ROOT / ".agents" / "scripts" / "rbac_guard.py"
EVENT = REPO_ROOT / ".agents" / "scripts" / "event_bus_logger.py"


def run_hook(script, payload=None, raw=None, env_extra=None, cwd=None, args=None):
    env = dict(os.environ)
    env.pop("AGENT_ROLE", None)
    env.pop("AGY_AGENT_ROLE", None)
    env.pop("AGENT_WORKSPACE_ROOT", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("WORKSPACE_ROOT", None)
    if env_extra:
        env.update(env_extra)
    command = [sys.executable, str(script)] + list(args or [])
    stdin_text = raw if raw is not None else json.dumps(payload)
    return subprocess.run(
        command,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd or REPO_ROOT),
        env=env,
    )


def antigravity_payload(path):
    return {"toolCall": {"name": "write_to_file", "args": {"TargetFile": path}}}


def decision(result):
    return json.loads(result.stdout)


class RbacGuardTests(unittest.TestCase):
    def assert_denied(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = decision(result)
        self.assertEqual(payload["decision"], "deny", result.stdout)
        self.assertTrue(payload.get("reason"))

    def assert_allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(decision(result)["decision"], "allow", result.stdout)

    def test_dev_relative_acceptance_denied(self):
        result = run_hook(
            RBAC,
            antigravity_payload("tests/acceptance/test_login.py"),
            env_extra={"AGENT_ROLE": "dev"},
        )
        self.assert_denied(result)

    def test_dev_absolute_acceptance_denied(self):
        target = str(REPO_ROOT / "tests" / "acceptance" / "test_login.py")
        result = run_hook(RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": "dev"})
        self.assert_denied(result)

    def test_dev_windows_backslash_acceptance_denied(self):
        target = str(REPO_ROOT).replace("/", "\\") + "\\tests\\acceptance\\test_login.py"
        result = run_hook(RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": "dev"})
        self.assert_denied(result)

    def test_qa_relative_src_denied(self):
        result = run_hook(
            RBAC,
            antigravity_payload("src/app/service.py"),
            env_extra={"AGENT_ROLE": "qa"},
        )
        self.assert_denied(result)

    def test_process_file_denied_for_every_role(self):
        target = "tasks/task-001/04-process.md"
        for role in ("dev", "qa", "planner", "unknown"):
            with self.subTest(role=role):
                result = run_hook(
                    RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": role}
                )
                self.assert_denied(result)
        result = run_hook(RBAC, antigravity_payload(target))
        self.assert_denied(result)

    def test_contract_file_rules(self):
        target = "tasks/task-001/01-contract.md"
        for role in ("dev", "qa"):
            with self.subTest(role=role):
                result = run_hook(RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": role})
                self.assert_denied(result)
        result = run_hook(RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": "planner"})
        self.assert_allowed(result)
        result = run_hook(RBAC, antigravity_payload(target))
        self.assert_allowed(result)

    def test_other_role_documents(self):
        result = run_hook(
            RBAC,
            antigravity_payload("tasks/task-001/03-qa-verification.md"),
            env_extra={"AGENT_ROLE": "dev"},
        )
        self.assert_denied(result)
        result = run_hook(
            RBAC,
            antigravity_payload("tasks/task-001/02-dev-workspace.md"),
            env_extra={"AGENT_ROLE": "qa"},
        )
        self.assert_denied(result)

    def test_allowed_writes(self):
        result = run_hook(RBAC, antigravity_payload("src/app/service.py"), env_extra={"AGENT_ROLE": "dev"})
        self.assert_allowed(result)
        result = run_hook(
            RBAC, antigravity_payload("tests/acceptance/test_login.py"), env_extra={"AGENT_ROLE": "qa"}
        )
        self.assert_allowed(result)
        result = run_hook(
            RBAC,
            antigravity_payload("tasks/task-001/02-dev-workspace.md"),
            env_extra={"AGENT_ROLE": "dev"},
        )
        self.assert_allowed(result)

    def test_unknown_role_only_process_denied(self):
        result = run_hook(RBAC, antigravity_payload("tests/acceptance/test_login.py"))
        self.assert_allowed(result)
        result = run_hook(RBAC, antigravity_payload("src/app.py"))
        self.assert_allowed(result)
        result = run_hook(RBAC, antigravity_payload("tasks/task-001/04-process.md"))
        self.assert_denied(result)

    def test_agy_agent_role_alias(self):
        result = run_hook(
            RBAC,
            antigravity_payload("src/app.py"),
            env_extra={"AGY_AGENT_ROLE": "QAAgent"},
        )
        self.assert_denied(result)

    def test_claude_and_dsh_payload_shapes(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "tests/acceptance/test_login.py"},
        }
        result = run_hook(RBAC, payload, env_extra={"AGENT_ROLE": "dev"})
        self.assert_denied(result)
        result = run_hook(
            RBAC,
            {"args": {"path": "tasks/task-001/04-process.md"}},
        )
        self.assert_denied(result)

    def test_template_process_file_allowed(self):
        target = ".agents/skills/task-decomposition/assets/templates/04-process.template.md"
        result = run_hook(RBAC, antigravity_payload(target), env_extra={"AGENT_ROLE": "dev"})
        self.assert_allowed(result)

    def test_malformed_payload_allows_with_warning(self):
        result = run_hook(RBAC, raw="{not json")
        self.assert_allowed(result)
        self.assertIn("cannot parse", result.stderr)
        result = run_hook(RBAC, raw="")
        self.assert_allowed(result)

    def test_help_and_version(self):
        result = subprocess.run(
            [sys.executable, str(RBAC), "--help"], capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        result = subprocess.run(
            [sys.executable, str(RBAC), "--version"], capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("2.0.0", result.stdout)


STATUS_BLOCK = (
    "## 1. Status\n\n"
    "macro_status: \"TODO\"\n"
    "current_lock_holder: \"None\"\n"
    "retry_count: {retry}\n\n"
)

EVENT_TABLE = (
    "## 2. Event Log\n\n"
    "| Event ID | Timestamp (UTC) | Event Code | Actor | Payload / Evidence | Duration |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
)


def scaffold(root, task_id="task-001", checked=(), retry=0, include_section=True, include_table=True):
    task_dir = Path(root) / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    dev_lines = ["# Dev workspace", "", "- [ ] WAITING_FOR_QA", ""]
    if "WAITING_FOR_QA" in checked:
        dev_lines[2] = "- [x] **Handoff**: WAITING_FOR_QA"
    (task_dir / "02-dev-workspace.md").write_text("\n".join(dev_lines), encoding="utf-8")

    qa_lines = ["# QA verification", ""]
    qa_lines.append(
        "- [x] **Verdict**: QA_PASSED" if "QA_PASSED" in checked else "- [ ] **Verdict**: QA_PASSED"
    )
    qa_lines.append(
        "- [x] **Verdict**: REWORK_REQUIRED"
        if "REWORK_REQUIRED" in checked
        else "- [ ] **Verdict**: REWORK_REQUIRED"
    )
    qa_lines.append("- [ ] **Literal token in prose**: [x] QA_PASSED")
    qa_lines.append("")
    (task_dir / "03-qa-verification.md").write_text("\n".join(qa_lines), encoding="utf-8")

    process = "# Process\n\n" + STATUS_BLOCK.format(retry=retry)
    if include_section:
        process += EVENT_TABLE if include_table else "## 2. Event Log\n\n(no table yet)\n"
    (task_dir / "04-process.md").write_text(process, encoding="utf-8")
    return task_dir


class EventBusLoggerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_bus(self, args=None, payload=None, cwd=None):
        return run_hook(EVENT, payload=payload or {}, args=args, cwd=cwd or self.root)

    def process_text(self, task_dir):
        return (task_dir / "04-process.md").read_text(encoding="utf-8")

    def test_fresh_scaffold_produces_no_events(self):
        task_dir = scaffold(self.root)
        before = self.process_text(task_dir)
        result = self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "{}")
        self.assertEqual(self.process_text(task_dir), before)

    def test_checked_handoff_appends_exactly_one_event(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",))
        result = self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(result.returncode, 0)
        text = self.process_text(task_dir)
        self.assertEqual(text.count("HANDOFF_QA_REQUESTED"), 1)
        self.assertIn("macro_status: \"VERIFYING\"", text)
        self.assertIn("current_lock_holder: \"QAAgent\"", text)
        self.assertIn("EV-AUTO", text)

    def test_rerun_is_idempotent(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",))
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        first = self.process_text(task_dir)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        second = self.process_text(task_dir)
        self.assertEqual(first, second)
        self.assertEqual(second.count("HANDOFF_QA_REQUESTED"), 1)

    def test_checked_qa_pass_event(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA", "QA_PASSED"))
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        text = self.process_text(task_dir)
        self.assertEqual(text.count("HANDOFF_QA_REQUESTED"), 1)
        self.assertEqual(text.count("TASK_TERMINATED_DONE"), 1)
        self.assertIn("macro_status: \"DONE\"", text)
        self.assertIn("current_lock_holder: \"None\"", text)

    def test_rework_event_and_retry_cap(self):
        task_dir = scaffold(self.root, checked=("REWORK_REQUIRED",), retry=2)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        text = self.process_text(task_dir)
        self.assertEqual(text.count("REWORK_TRIGGERED"), 1)
        self.assertIn("macro_status: \"REWORKING\"", text)
        self.assertIn("current_lock_holder: \"DevAgent\"", text)
        self.assertIn("retry_count: 3", text)

        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        text = self.process_text(task_dir)
        self.assertIn("retry_count: 3", text)
        self.assertEqual(text.count("REWORK_TRIGGERED"), 1)

        task_dir_2 = scaffold(self.root, task_id="task-002", checked=("REWORK_REQUIRED",), retry=3)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertIn("retry_count: 3", self.process_text(task_dir_2))

    def test_literal_token_under_unchecked_box_does_not_trigger(self):
        task_dir = scaffold(self.root)
        before = self.process_text(task_dir)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(self.process_text(task_dir), before)

    def test_missing_section_does_not_mutate_status(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",), include_section=False)
        before = self.process_text(task_dir)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(self.process_text(task_dir), before)
        self.assertIn("macro_status: \"TODO\"", before)

    def test_missing_table_does_not_mutate_status(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",), include_table=False)
        before = self.process_text(task_dir)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(self.process_text(task_dir), before)

    def test_task_dir_from_changed_file_payload(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",))
        other_cwd = Path(self._tmp.name) / "elsewhere"
        other_cwd.mkdir()
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(task_dir / "02-dev-workspace.md")},
        }
        result = self.run_bus(payload=payload, cwd=other_cwd)
        self.assertEqual(result.returncode, 0)
        self.assertIn("HANDOFF_QA_REQUESTED", self.process_text(task_dir))

    def test_default_tasks_dir(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",))
        self.run_bus(cwd=self.root)
        self.assertIn("HANDOFF_QA_REQUESTED", self.process_text(task_dir))

    def test_only_checked_task_is_updated(self):
        checked_dir = scaffold(self.root, task_id="task-001", checked=("WAITING_FOR_QA",))
        idle_dir = scaffold(self.root, task_id="task-002")
        before_idle = self.process_text(idle_dir)
        self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertIn("HANDOFF_QA_REQUESTED", self.process_text(checked_dir))
        self.assertEqual(self.process_text(idle_dir), before_idle)

    def test_missing_process_file_is_a_noop(self):
        task_dir = scaffold(self.root, checked=("WAITING_FOR_QA",))
        (task_dir / "04-process.md").unlink()
        result = self.run_bus(args=["--tasks-dir", str(self.root / "tasks")])
        self.assertEqual(result.returncode, 0)
        self.assertFalse((task_dir / "04-process.md").exists())

    def test_help_and_version(self):
        result = subprocess.run(
            [sys.executable, str(EVENT), "--help"], capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        result = subprocess.run(
            [sys.executable, str(EVENT), "--version"], capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("2.0.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
