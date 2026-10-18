#!/usr/bin/env python3
"""Tests for the plan-linter v2 Gate 1 checker.

Run: python -m unittest discover -s tests/unit -p "test_*.py"
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LINTER = REPO_ROOT / ".agents" / "skills" / "plan-linter" / "scripts" / "plan_linter.py"
if str(LINTER.parent) not in sys.path:
    sys.path.insert(0, str(LINTER.parent))
from plan_linter import _lint_qa_mutation, Finding
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "plan-linter"
BT = chr(96)

DOC_02 = "# Dev workspace\n\n- [ ] WAITING_FOR_QA\n"
DOC_03 = "# QA verification\n\n- [ ] QA_PASSED\n- [ ] REWORK_REQUIRED\n"
DOC_04 = (
    "# Process\n\n"
    "## 1. Status\n\n"
    "macro_status: \"TODO\"\n"
    "current_lock_holder: \"None\"\n"
    "retry_count: 0\n\n"
    "## 2. Event Log\n\n"
    "| Event ID | Timestamp (UTC) | Event Code | Actor | Payload / Evidence | Duration |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
)


def frontmatter_contract(
    task_id="task-001",
    dependencies="[]",
    estimated_lines=120,
    touch_files=None,
    anchor="#sec-example",
    adrs="[ADR-001]",
    lint=True,
    deps=None,
    size_class=None,
    change_id=None,
):
    if touch_files is None:
        touch_files = [
            ("create", "src/example.py"),
            ("modify", "src/routes.py"),
        ]
    lines = [
        "---",
        "task_id: " + task_id,
        "title: \"Example task\"",
        "module: core",
        "dependencies: " + (dependencies if deps is None else deps),
        "estimated_lines: " + str(estimated_lines),
        "touch_files:",
    ]
    for action, path in touch_files:
        lines.append("  - action: " + action)
        lines.append("    path: " + path)
    if size_class:
        lines.append("size_class: " + size_class)
    if change_id:
        lines.append("change_id: " + change_id)
    lines.append("origin_spec_anchor: \"" + anchor + "\"")
    lines.append("adherence_adrs: " + adrs)
    lines.append("dod:")
    lines.append("  type_check: \"npm run type-check\"")
    if lint:
        lines.append("  lint: \"npm run lint\"")
    lines.append("  test_file: \"tests/acceptance/test_example.ts\"")
    lines.append("  edge_cases:")
    lines.append("    - \"empty input returns 400\"")
    lines.append("    - \"expired token returns 401\"")
    lines.append("---")
    lines.append("")
    lines.append("# Task: Example")
    lines.append("")
    lines.append("Human readable detail.")
    return "\n".join(lines) + "\n"


def legacy_contract(task_id="task-001", deps="", include_lint=True, anchor="02-tech-spec.md#sec-example"):
    lines = [
        "# Task contract",
        "",
        "| 属性 | 规格值 |",
        "| :--- | :--- |",
        "| **Task ID** | " + BT + task_id + BT + " |",
        "| **前置依赖** | " + BT + "[" + deps + "]" + BT + " |",
        "| **预估代码量** | " + BT + "120 行" + BT + " |",
        "| **Tech Spec 锚点** | " + BT + anchor + BT + " |",
        "",
        "## Inherited ADRs",
        "- [ ] **继承 [ADR-001]**: keep it",
        "",
        "## DoD",
        "- [ ] 类型检查命令通过: " + BT + "python -m mypy src" + BT,
    ]
    if include_lint:
        lines.append("- [ ] 代码风格检查通过: " + BT + "python -m ruff check src" + BT)
    lines.extend([
        "- [ ] 对应验收测试文件: " + BT + "tests/acceptance/test_auth.py" + BT,
        "- [ ] **反向/边界场景用例 1**: empty input returns 400",
        "- [ ] **反向/边界场景用例 2**: expired token returns 401",
        "",
        "### 2.1 White list",
        "- " + BT + "[CREATE]" + BT + " " + BT + "src/auth.py" + BT,
        "- " + BT + "[MODIFY]" + BT + " " + BT + "src/main.py" + BT,
    ])
    return "\n".join(lines) + "\n"


def write_task(tasks_dir, task_id, contract_text=None, docs=("02", "03", "04")):
    task_dir = Path(tasks_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "01-contract.md").write_text(
        contract_text if contract_text is not None else frontmatter_contract(task_id=task_id),
        encoding="utf-8",
    )
    if "02" in docs:
        (task_dir / "02-dev-workspace.md").write_text(DOC_02, encoding="utf-8")
    if "03" in docs:
        (task_dir / "03-qa-verification.md").write_text(DOC_03, encoding="utf-8")
    if "04" in docs:
        (task_dir / "04-process.md").write_text(DOC_04, encoding="utf-8")
    return task_dir


def run_linter(args, cwd=None, script=None):
    command = [sys.executable, str(script or LINTER)] + list(args)
    return subprocess.run(
        command,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=None,
    )


class PlanLinterV2Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tasks_dir = Path(self._tmp.name) / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def lint(self, *extra):
        return run_linter(["--tasks-dir", str(self.tasks_dir)] + list(extra))

    def lint_json(self, *extra):
        result = self.lint("--json", *extra)
        payload = json.loads(result.stdout)
        return result, payload

    def test_frontmatter_contract_passes(self):
        write_task(self.tasks_dir, "task-001")
        result = self.lint()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Gate 1 PASSED", result.stdout)

    def test_legacy_contract_passes_with_warning(self):
        write_task(self.tasks_dir, "task-001", legacy_contract())
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("LEGACY_FORMAT", codes)

    def test_english_legacy_tables_also_parse(self):
        write_task(self.tasks_dir, "task-001", legacy_contract().replace("前置依赖", "Dependencies"))
        result = self.lint()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_six_invalid_cases_fail(self):
        cases = {
            "missing lint command": (
                frontmatter_contract(lint=False),
                "MISSING_LINT",
            ),
            "missing adr": (
                frontmatter_contract(adrs="[]"),
                "MISSING_ADRS",
            ),
            "placeholder anchor": (
                frontmatter_contract(anchor="#sec-{{ANCHOR}}"),
                "INVALID_ANCHOR",
            ),
            "missing task id": (
                frontmatter_contract().replace("task_id: task-001\n", ""),
                "MISSING_TASK_ID",
            ),
        }
        for label, (contract, expected_code) in cases.items():
            with self.subTest(label):
                for child in self.tasks_dir.iterdir():
                    shutil.rmtree(child)
                write_task(self.tasks_dir, "task-001", contract)
                result = self.lint("--json")
                self.assertEqual(result.returncode, 1, label + ": " + result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                codes = [error["code"] for error in payload["errors"]]
                self.assertIn(expected_code, codes, label + ": " + str(codes))

        with self.subTest("missing docs"):
            for child in self.tasks_dir.iterdir():
                shutil.rmtree(child)
            write_task(self.tasks_dir, "task-001", frontmatter_contract(), docs=())
            result = self.lint("--json")
            self.assertEqual(result.returncode, 1, result.stdout)
            codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
            self.assertEqual(codes.count("MISSING_DOC"), 3, str(codes))

        with self.subTest("duplicate task id"):
            for child in self.tasks_dir.iterdir():
                shutil.rmtree(child)
            write_task(self.tasks_dir, "task-001", frontmatter_contract(task_id="task-001"))
            write_task(self.tasks_dir, "task-002", frontmatter_contract(task_id="task-001"))
            result = self.lint("--json")
            self.assertEqual(result.returncode, 1, result.stdout)
            codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
            self.assertIn("DUPLICATE_TASK_ID", codes, str(codes))

        with self.subTest("task id vs directory mismatch"):
            for child in self.tasks_dir.iterdir():
                shutil.rmtree(child)
            write_task(self.tasks_dir, "task-999", frontmatter_contract(task_id="task-001"))
            result = self.lint("--json")
            self.assertEqual(result.returncode, 1, result.stdout)
            codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
            self.assertIn("TASK_ID_MISMATCH", codes, str(codes))

    def test_json_payload_shape(self):
        write_task(self.tasks_dir, "task-001")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["gate"], "1")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["tasks_scanned"], 1)
        self.assertEqual(payload["errors"], [])
        self.assertIsInstance(payload["warnings"], list)

    def test_json_error_entry_shape(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract(lint=False))
        payload = json.loads(self.lint("--json").stdout)
        error = payload["errors"][0]
        for key in ("task", "code", "message", "file", "line"):
            self.assertIn(key, error)
        self.assertEqual(error["code"], "MISSING_LINT")

    def test_config_overrides(self):
        config_path = Path(self._tmp.name) / "plan-linter.json"
        config_path.write_text(
            json.dumps(
                {
                    "max_touch_files": 4,
                    "min_diff_lines": 10,
                    "max_diff_lines": 400,
                }
            ),
            encoding="utf-8",
        )
        touch_files = [
            ("create", "src/a.py"),
            ("create", "src/b.py"),
            ("create", "src/c.py"),
            ("create", "src/d.py"),
        ]
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(touch_files=touch_files, estimated_lines=20),
        )
        result = self.lint("--config", str(config_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        bad_config = Path(self._tmp.name) / "bad.json"
        bad_config.write_text(json.dumps({"max_touch_files": "three"}), encoding="utf-8")
        result = self.lint("--config", str(bad_config))
        self.assertEqual(result.returncode, 2)

        result = self.lint("--config", str(Path(self._tmp.name) / "missing.json"))
        self.assertEqual(result.returncode, 2)

    def test_default_limits_still_enforced(self):
        touch_files = [
            ("create", "src/a.py"),
            ("create", "src/b.py"),
            ("create", "src/c.py"),
            ("create", "src/d.py"),
        ]
        write_task(self.tasks_dir, "task-001", frontmatter_contract(touch_files=touch_files))
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("TOO_MANY_TOUCH_FILES", codes)

        for child in self.tasks_dir.iterdir():
            shutil.rmtree(child)
        write_task(self.tasks_dir, "task-001", frontmatter_contract(estimated_lines=30))
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("DIFF_TOO_SMALL", codes)

    def test_forbidden_touch_prefix(self):
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(
                touch_files=[("modify", "tests/acceptance/test_login.py")]
            ),
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("FORBIDDEN_TOUCH_FILE", codes)

    def test_placeholder_scan_can_be_disabled(self):
        task_dir = write_task(self.tasks_dir, "task-001")
        (task_dir / "02-dev-workspace.md").write_text(
            "# Dev workspace\n\nTODO: fill this in\n", encoding="utf-8"
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("PLACEHOLDER", codes)

        result = self.lint("--no-placeholder-scan", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_04_process_is_not_placeholder_scanned(self):
        task_dir = write_task(self.tasks_dir, "task-001")
        (task_dir / "04-process.md").write_text(
            DOC_04 + '\nmacro_status: "{{MACRO_STATUS}}"\ncurrent_lock_holder: "{{LOCK_HOLDER}}"\n',
            encoding="utf-8",
        )
        result = self.lint("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_token_free_02_and_03_pass_with_filled_contract(self):
        task_dir = write_task(self.tasks_dir, "task-001")
        self.assertNotIn("{{", (task_dir / "02-dev-workspace.md").read_text(encoding="utf-8"))
        self.assertNotIn("{{", (task_dir / "03-qa-verification.md").read_text(encoding="utf-8"))
        result = self.lint()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dag_cycle_and_missing_dependency(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract(task_id="task-001", deps="[task-002]"))
        write_task(self.tasks_dir, "task-002", frontmatter_contract(task_id="task-002", deps="[task-001]"))
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("DAG_CYCLE", codes)

        for child in self.tasks_dir.iterdir():
            shutil.rmtree(child)
        write_task(self.tasks_dir, "task-001", frontmatter_contract(deps="[task-404]"))
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("DEPENDENCY_NOT_FOUND", codes)

    def test_usage_errors(self):
        result = run_linter(["--tasks-dir", str(Path(self._tmp.name) / "missing")])
        self.assertEqual(result.returncode, 2)
        result = run_linter(["--definitely-not-a-flag"])
        self.assertEqual(result.returncode, 2)
        result = run_linter(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        result = run_linter(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("3.0.0", result.stdout)

    def test_empty_tasks_dir_is_violation(self):
        result = self.lint("--json")
        self.assertEqual(result.returncode, 1)
        codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
        self.assertIn("NO_TASKS", codes)

    def test_unparseable_frontmatter_is_violation(self):
        write_task(
            self.tasks_dir,
            "task-001",
            "---\ntask_id: task-001\n  broken: indentation\n---\n# body\n",
        )
        result = self.lint()
        self.assertEqual(result.returncode, 1)
        self.assertIn("frontmatter", result.stderr.lower())

    def test_relocation_proof(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "plan-linter"
            shutil.copytree(SKILL_DIR, copied)
            script = copied / "scripts" / "plan_linter.py"
            self.assertTrue(script.is_file())
            result = run_linter(["--help"], cwd=temp_dir, script=script)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            valid_tasks = Path(temp_dir) / "tasks"
            write_task(valid_tasks, "task-001")
            result = run_linter(["--tasks-dir", str(valid_tasks)], cwd=temp_dir, script=script)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class PlanLinterV3Tests(unittest.TestCase):
    """Micro tier, reverse topology, anchor coverage and change proposals."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tasks_dir = self.root / "tasks"
        self.tasks_dir.mkdir()
        (self.root / "src").mkdir()
        (self.root / "src" / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def lint(self, *extra):
        return run_linter(
            ["--tasks-dir", str(self.tasks_dir), "--repo-root", str(self.root)] + list(extra)
        )

    def clear_tasks(self):
        for child in self.tasks_dir.iterdir():
            shutil.rmtree(child)

    def test_micro_size_class_budget(self):
        write_task(
            self.tasks_dir,
            "chg-001",
            frontmatter_contract(
                task_id="chg-001",
                estimated_lines=30,
                touch_files=[("modify", "src/existing.py")],
                size_class="micro",
                change_id="CHG-001",
            ),
        )
        result = self.lint("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        cases = [
            (dict(estimated_lines=60), "MICRO_DIFF_TOO_LARGE"),
            (dict(estimated_lines=5), "MICRO_DIFF_TOO_SMALL"),
            (dict(change_id=None), "MICRO_REQUIRES_CHANGE_ID"),
            (dict(touch_files=[("modify", "src/existing.py"), ("modify", "src/existing.py")]),
             "MICRO_TOO_MANY_TOUCH_FILES"),
        ]
        for overrides, expected in cases:
            with self.subTest(code=expected):
                self.clear_tasks()
                params = dict(
                    task_id="chg-001",
                    estimated_lines=30,
                    touch_files=[("modify", "src/existing.py")],
                    size_class="micro",
                    change_id="CHG-001",
                )
                params.update(overrides)
                write_task(self.tasks_dir, "chg-001", frontmatter_contract(**params))
                payload = json.loads(self.lint("--json").stdout)
                codes = [error["code"] for error in payload["errors"]]
                self.assertIn(expected, codes)

    def test_standard_budget_unchanged(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract(estimated_lines=30))
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("DIFF_TOO_SMALL", codes)

    def test_reverse_topology_warnings_and_strict_mode(self):
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(touch_files=[("modify", "src/missing.py")]),
        )
        payload = json.loads(self.lint("--json").stdout)
        self.assertTrue(payload["passed"])
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("TOUCH_FILE_MISSING", codes)

        result = self.lint("--strict-topology", "--json")
        self.assertEqual(result.returncode, 1)
        codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
        self.assertIn("TOUCH_FILE_MISSING", codes)

        self.clear_tasks()
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(touch_files=[("create", "src/existing.py")]),
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("TOUCH_FILE_EXISTS", codes)

        self.clear_tasks()
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(
                touch_files=[("modify", "src/existing.py"), ("create", "src/fresh.py")],
            ),
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertNotIn("TOUCH_FILE_MISSING", codes)
        self.assertNotIn("TOUCH_FILE_EXISTS", codes)

        self.clear_tasks()
        write_task(
            self.tasks_dir,
            "task-001",
            frontmatter_contract(touch_files=[("modify", "../escape.py")]),
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("TOUCH_PATH_OUTSIDE_ROOT", codes)

    def test_anchor_coverage_matrix(self):
        spec = self.root / "spec.md"
        spec.write_text(
            "# Spec\n\n## Alpha {#sec-alpha}\n\n## Beta {#sec-beta}\n\n## Gamma {#sec-gamma}\n",
            encoding="utf-8",
        )
        write_task(
            self.tasks_dir, "task-001",
            frontmatter_contract(task_id="task-001", anchor="#sec-alpha",
                                 touch_files=[("modify", "src/existing.py")]),
        )
        write_task(
            self.tasks_dir, "task-002",
            frontmatter_contract(task_id="task-002", anchor="#sec-beta",
                                 touch_files=[("modify", "src/existing.py")]),
        )
        payload = json.loads(self.lint("--spec", str(spec), "--json").stdout)
        coverage = payload["coverage"]
        self.assertEqual(coverage["spec_anchors"], 3)
        self.assertEqual(coverage["covered"], ["#sec-alpha", "#sec-beta"])
        self.assertEqual(coverage["uncovered"], ["#sec-gamma"])
        self.assertEqual(coverage["contract_anchors_missing_from_spec"], [])
        self.assertAlmostEqual(coverage["coverage_ratio"], 0.6667, places=3)

        report = self.root / "reports" / "coverage.json"
        result = self.lint("--spec", str(spec), "--coverage-out", str(report), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["uncovered"], ["#sec-gamma"])

        result = self.lint("--spec", str(spec), "--require-full-coverage", "--json")
        self.assertEqual(result.returncode, 1)
        codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
        self.assertIn("SPEC_SECTION_UNCOVERED", codes)

        write_task(
            self.tasks_dir, "task-003",
            frontmatter_contract(task_id="task-003", anchor="#sec-delta"),
        )
        payload = json.loads(self.lint("--spec", str(spec), "--json").stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("ANCHOR_NOT_IN_SPEC", codes)
        result = self.lint("--spec", str(spec), "--strict-anchor", "--json")
        codes = [error["code"] for error in json.loads(result.stdout)["errors"]]
        self.assertIn("ANCHOR_NOT_IN_SPEC", codes)

    def test_coverage_flags_usage_errors(self):
        result = self.lint("--coverage-out", str(self.root / "c.json"))
        self.assertEqual(result.returncode, 2)
        result = self.lint("--spec", str(self.root / "missing-spec.md"))
        self.assertEqual(result.returncode, 2)

    def test_change_proposal_lifecycle(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract(change_id="CHG-9"))
        changes = self.root / ".specs" / "changes"
        payload = json.loads(self.lint("--changes-dir", str(changes), "--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("CHANGE_PROPOSAL_MISSING", codes)

        proposal_dir = changes / "CHG-9"
        proposal_dir.mkdir(parents=True)
        proposal = proposal_dir / "proposal.md"
        proposal.write_text("---\nchange_id: CHG-9\nstatus: proposed\n---\n# Change\n",
                            encoding="utf-8")
        result = self.lint("--changes-dir", str(changes), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        proposal.write_text("---\nchange_id: CHG-9\nstatus: rejected\n---\n# Change\n",
                            encoding="utf-8")
        payload = json.loads(self.lint("--changes-dir", str(changes), "--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("CHANGE_NOT_OPEN", codes)

    def test_archive_directories_are_ignored(self):
        write_task(self.tasks_dir, "task-001",
                   frontmatter_contract(touch_files=[("modify", "src/existing.py")]))
        archived = self.tasks_dir / "archive" / "task-old"
        archived.mkdir(parents=True)
        (archived / "01-contract.md").write_text("# historical record only\n", encoding="utf-8")
        result = self.lint("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tasks_scanned"], 1)
        codes = [error["code"] for error in payload["errors"]]
        self.assertNotIn("MISSING_CONTRACT", codes)

    def test_archived_change_proposal_is_a_warning(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract(change_id="CHG-ARCH"))
        changes = self.root / ".specs" / "changes"
        proposal_dir = changes / "CHG-ARCH"
        proposal_dir.mkdir(parents=True)
        (proposal_dir / "proposal.md").write_text(
            "---\nchange_id: CHG-ARCH\nstatus: archived\n---\n# Archived change\n",
            encoding="utf-8",
        )
        result = self.lint("--changes-dir", str(changes), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        codes = [warning["code"] for warning in payload["warnings"]]
        self.assertIn("CHANGE_ALREADY_ARCHIVED", codes)

    def test_invalid_size_class_and_change_id(self):
        write_task(
            self.tasks_dir, "task-001",
            frontmatter_contract(size_class="huge", change_id="bad id"),
        )
        payload = json.loads(self.lint("--json").stdout)
        codes = [error["code"] for error in payload["errors"]]
        self.assertIn("INVALID_SIZE_CLASS", codes)
        self.assertIn("INVALID_CHANGE_ID", codes)


class PlanLinterBddTests(unittest.TestCase):
    """Feature 20: BDD scenario linting validation in plan_linter.py."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tasks_dir = Path(self._tmp.name) / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def lint_json(self, *extra):
        result = run_linter(["--tasks-dir", str(self.tasks_dir), "--json"] + list(extra))
        payload = json.loads(result.stdout)
        return result, payload

    def test_bdd_valid_contract_passes(self):
        contract = frontmatter_contract()
        contract = contract.replace(
            '- "empty input returns 400"',
            '- "Given empty input payload, When submitted to API, Then return 400 Bad Request"',
        ).replace(
            '- "expired token returns 401"',
            '- "Given expired token, When authenticated, Then return 401 Unauthorized"',
        )
        write_task(self.tasks_dir, "task-001", contract)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])
        bdd_warnings = [w for w in payload["warnings"] if w["code"] == "BDD_INVALID_SCENARIO"]
        self.assertEqual(len(bdd_warnings), 0)

    def test_bdd_missing_precondition_in_edge_cases(self):
        contract = frontmatter_contract().replace(
            '- "empty input returns 400"',
            '- "When submitted to API, Then return 400 Bad Request"',
        )
        write_task(self.tasks_dir, "task-001", contract)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)

    def test_bdd_missing_action_in_edge_cases(self):
        contract = frontmatter_contract().replace(
            '- "empty input returns 400"',
            '- "Given empty input payload, Then return 400 Bad Request"',
        )
        write_task(self.tasks_dir, "task-001", contract)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_ACTION", codes)

    def test_bdd_missing_outcome_in_edge_cases(self):
        contract = frontmatter_contract().replace(
            '- "empty input returns 400"',
            '- "Given empty input payload, When submitted to API"',
        )
        write_task(self.tasks_dir, "task-001", contract)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_scenarios_validation(self):
        body_with_bad_scenario = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Input validation\n"
            + "- **When** credentials submitted\n"
            + "- **Then** rejected with 400\n"
        )
        write_task(self.tasks_dir, "task-001", body_with_bad_scenario)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)

    def test_bdd_legacy_plain_string_emits_warning_not_error(self):
        write_task(self.tasks_dir, "task-001", frontmatter_contract())
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(payload["passed"])
        codes = [w["code"] for w in payload["warnings"]]
        self.assertIn("BDD_INVALID_SCENARIO", codes)

    def test_bdd_section4_empty_bold_clauses_emit_errors(self):
        """Empty bold clauses (- **Given**, * **When**, + **Then**) must emit all three BDD error codes."""
        body_with_empty_bold = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Mixed empty bold bullets\n"
            + "- **Given**\n"
            + "* **When**\n"
            + "+ **Then**\n"
        )
        write_task(self.tasks_dir, "task-001", body_with_empty_bold)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)
        self.assertIn("BDD_MISSING_ACTION", codes)
        self.assertIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_empty_bold_given_emits_missing_precondition(self):
        """Scenario with only - **Given** empty emits BDD_MISSING_PRECONDITION."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Empty given\n"
            + "- **Given**\n"
            + "* **When** credentials submitted\n"
            + "+ **Then** access granted\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)
        self.assertNotIn("BDD_MISSING_ACTION", codes)
        self.assertNotIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_empty_bold_when_emits_missing_action(self):
        """Scenario with only * **When** empty emits BDD_MISSING_ACTION."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Empty when\n"
            + "- **Given** user exists\n"
            + "* **When**\n"
            + "+ **Then** access granted\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertNotIn("BDD_MISSING_PRECONDITION", codes)
        self.assertIn("BDD_MISSING_ACTION", codes)
        self.assertNotIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_empty_bold_then_emits_missing_outcome(self):
        """Scenario with only + **Then** empty emits BDD_MISSING_OUTCOME."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Empty then\n"
            + "- **Given** user exists\n"
            + "* **When** credentials submitted\n"
            + "+ **Then**\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertNotIn("BDD_MISSING_PRECONDITION", codes)
        self.assertNotIn("BDD_MISSING_ACTION", codes)
        self.assertIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_empty_bold_clauses_with_colons(self):
        """Empty bold clauses with colons and whitespace still emit errors."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Colon empty bold clauses\n"
            + "- **Given**:\n"
            + "* **When**:  \n"
            + "+ **Then**:\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)
        self.assertIn("BDD_MISSING_ACTION", codes)
        self.assertIn("BDD_MISSING_OUTCOME", codes)

    def test_bdd_section4_mixed_bullet_markers_pass(self):
        """Populated scenarios using mixed list bullets (-, *, +) pass Gate 1 with 0 errors."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Valid mixed bullets\n"
            + "- **Given** valid user session in pending state\n"
            + "* **When** email verification token submitted\n"
            + "+ **Then** session state transitions to active\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])

    def test_bdd_section4_all_dash_empty_bold_clauses(self):
        """Standard dash-bullet empty bold clauses emit all three error codes."""
        body = (
            frontmatter_contract()
            + "\n## 4. Behavioral contract and invariants\n\n"
            + "### Feature: Authentication\n\n"
            + "#### Scenario 1: Standard dash empty\n"
            + "- **Given**\n"
            + "- **When**\n"
            + "- **Then**\n"
        )
        write_task(self.tasks_dir, "task-001", body)
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("BDD_MISSING_PRECONDITION", codes)
        self.assertIn("BDD_MISSING_ACTION", codes)
        self.assertIn("BDD_MISSING_OUTCOME", codes)




class PlanLinterComplexityTests(unittest.TestCase):
    """Features 21 and 23: Cyclomatic complexity and basis path static validation in plan_linter.py."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tasks_dir = Path(self._tmp.name) / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def lint_json(self, *extra):
        result = run_linter(["--tasks-dir", str(self.tasks_dir), "--json"] + list(extra))
        payload = json.loads(result.stdout)
        return result, payload

    def test_complexity_unchecked_qa_passed_backward_compatible(self):
        """When 03-qa-verification.md has unchecked [-] QA_PASSED, complexity checks do not run."""
        task_dir = write_task(self.tasks_dir, "task-001")
        (task_dir / "03-qa-verification.md").write_text(
            "# QA verification\n\n- [ ] QA_PASSED\n- [ ] REWORK_REQUIRED\n", encoding="utf-8"
        )
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])

    def test_complexity_missing_section_on_qa_passed(self):
        """When QA signs off with QA_PASSED but Section 3 is missing, emit COMPLEXITY_MISSING_SECTION."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 1. Verification metadata\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
            "- [ ] REWORK_REQUIRED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("COMPLEXITY_MISSING_SECTION", codes)

    def test_complexity_empty_table_on_qa_passed(self):
        """When QA signs off with QA_PASSED but Section 3 table has no data rows, emit COMPLEXITY_MISSING_SECTION."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "|  |  |  |  |  |\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
            "- [ ] REWORK_REQUIRED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("COMPLEXITY_MISSING_SECTION", codes)

    def test_complexity_exceeds_max_threshold_error(self):
        """When V(G) > 15, emit error COMPLEXITY_EXCEEDS_MAX_THRESHOLD."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| complex_router | 18 | P1..P18 | TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-14, TC-15, TC-16, TC-17, TC-18 | NO |\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("COMPLEXITY_EXCEEDS_MAX_THRESHOLD", codes)
        self.assertNotIn("COMPLEXITY_BASIS_PATH_INSUFFICIENT", codes)

    def test_complexity_exceeds_standard_threshold_warning(self):
        """When 11 <= V(G) <= 15, emit warning COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD, Gate 1 passes if basis paths sufficient."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| auth_dispatch | 12 | P1..P12 | TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12 | NO (Approved) |\n\n"
            "## 4. Mutation testing and MSI audit\n"
            "| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| src/auth.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90.0% | PASS |\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])
        w_codes = [w["code"] for w in payload["warnings"]]
        self.assertIn("COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD", w_codes)

    def test_complexity_basis_path_insufficient_error(self):
        """When test case count < V(G), emit error COMPLEXITY_BASIS_PATH_INSUFFICIENT."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| process_payment | 5 | P1..P5 | TC-01, TC-02, TC-03 | NO |\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("COMPLEXITY_BASIS_PATH_INSUFFICIENT", codes)

    def test_complexity_compliant_passes(self):
        """When V(G) <= 10 and test cases >= V(G), passes Gate 1 with 0 errors and 0 warnings."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| calculate_fee | 3 | P1, P2, P3 | TC-01, TC-02, TC-03 | YES |\n\n"
            "## 4. Mutation testing and MSI audit\n"
            "| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| src/fee.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90.0% | PASS |\n\n"
            "## 5. Verdict\n\n"
            "- [x] QA_PASSED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])
        complexity_warnings = [w for w in payload["warnings"] if "COMPLEXITY" in w.get("code", "")]
        self.assertEqual(len(complexity_warnings), 0)

    def test_complexity_multiple_rows_aggregation(self):
        """Multiple rows aggregate their respective warnings and errors."""
        task_dir = write_task(self.tasks_dir, "task-001")
        qa_content = (
            "# QA verification\n\n"
            "## 3. Complexity and basis path coverage\n\n"
            "| Target Function | V(G) Complexity | Independent Basis Paths | Mapped Test Cases | Path Coverage |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| helper_fn | 2 | P1, P2 | TC-01, TC-02 | 100% |\n"
            "| auth_dispatch | 12 | P1..P12 | TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12 | 100% |\n"
            "| data_crunch | 7 | P1..P7 | TC-20, TC-21 | 28.5% |\n\n"
            "## 6. Verdict\n\n"
            "- [x] QA_PASSED\n"
        )
        (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        err_codes = [e["code"] for e in payload["errors"]]
        warn_codes = [w["code"] for w in payload["warnings"]]
        self.assertIn("COMPLEXITY_BASIS_PATH_INSUFFICIENT", err_codes)
        self.assertIn("COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD", warn_codes)




class PlanLinterMutationTests(unittest.TestCase):
    """Features 22 and 27: Mutation testing and MSI static validation in plan_linter.py."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tasks_dir = Path(self._tmp.name) / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.task_dir = self.tasks_dir / "task-001"
        self.task_name = "task-001"

    def tearDown(self):
        self._tmp.cleanup()

    def lint_json(self, *extra):
        result = run_linter(["--tasks-dir", str(self.tasks_dir), "--json"] + list(extra))
        payload = json.loads(result.stdout)
        return result, payload

    def _write_qa(self, content: str) -> None:
        self.task_dir.mkdir(parents=True, exist_ok=True)
        (self.task_dir / "01-contract.md").write_text(frontmatter_contract(task_id=self.task_name), encoding="utf-8")
        (self.task_dir / "02-dev-workspace.md").write_text(DOC_02, encoding="utf-8")
        (self.task_dir / "03-qa-verification.md").write_text(content, encoding="utf-8")
        (self.task_dir / "04-process.md").write_text(DOC_04, encoding="utf-8")

    def test_mutation_unchecked_qa_passed_backward_compatible(self) -> None:
        """When QA_PASSED is unchecked, linter does NOT require mutation table."""
        self._write_qa("""# QA Verification
- [ ] QA_PASSED
- [ ] REWORK_REQUIRED
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_missing_section_on_qa_passed(self) -> None:
        """When QA_PASSED is checked but Section 4 is missing, emit QA_MISSING_MUTATION_EVIDENCE."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_MISSING_MUTATION_EVIDENCE")

    def test_mutation_empty_table_on_qa_passed(self) -> None:
        """When Section 4 heading exists but table has no data rows, emit QA_MISSING_MUTATION_EVIDENCE."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |  |  |  |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_MISSING_MUTATION_EVIDENCE")

    def test_mutation_valid_score_passes(self) -> None:
        """When MSI >= 80%, verification passes with zero findings."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 8 | 2 | 0 | 0 | 80% | PASS |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_score_below_80_emits_error(self) -> None:
        """When MSI < 80%, emit QA_INVALID_MSI_SCORE error."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 7 | 3 | 0 | 0 | 70% | FAIL |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_INVALID_MSI_SCORE")
        self.assertIn("70.0%", findings[0].message)

    def test_mutation_invalid_score_format_emits_error(self) -> None:
        """When MSI value is non-numeric, emit QA_INVALID_MSI_SCORE error."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 8 | 2 | 0 | 0 | N/A | FAIL |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_INVALID_MSI_SCORE")

    def test_mutation_kv_format_supported(self) -> None:
        """Key-value format with MSI >= 80% passes."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | Synthetic agent fallback |
| Total mutants generated | 6 |
| Killed mutants | 5 |
| Mutation Score Indicator (MSI) | 100.0% |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_kv_format_below_threshold_fails(self) -> None:
        """Key-value format with MSI < 80% emits QA_INVALID_MSI_SCORE."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | Synthetic agent fallback |
| Mutation Score Indicator (MSI) | 65.0% |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_INVALID_MSI_SCORE")
        self.assertIn("65.0%", findings[0].message)

    def test_mutation_multiple_rows_aggregation(self) -> None:
        """Multiple target files: valid file passes, failing file emits error."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/token.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90.0% | PASS |
| src/auth/login.py | mutmut | 10 | 6 | 4 | 0 | 0 | 60.0% | FAIL |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_INVALID_MSI_SCORE")
        self.assertIn("src/auth/login.py", findings[0].message)

    def test_mutation_cli_end_to_end_pass(self) -> None:
        """CLI end-to-end integration: task passes Gate 1 when both Section 3 and Section 4 are compliant."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90.0% | PASS |
""")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["errors"], [])

    def test_mutation_cli_end_to_end_fail_low_msi(self) -> None:
        """CLI end-to-end integration: fails when MSI < 80%."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 6 | 4 | 0 | 0 | 60.0% | FAIL |
""")
        result, payload = self.lint_json()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["passed"])
        codes = [e["code"] for e in payload["errors"]]
        self.assertIn("QA_INVALID_MSI_SCORE", codes)

    def test_mutation_dual_table_both_compliant_passes(self) -> None:
        """Dual-table: both per-target table and KV summary table pass with zero errors."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/login.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | mutmut |
| Total mutants generated | 10 |
| Killed mutants | 9 |
| Timed-out mutants | 0 |
| Equivalent mutants | 0 |
| Survived mutants | 1 |
| Mutation Score Indicator (MSI) | 90.0% |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_dual_table_table1_filled_table2_scaffolded_passes(self) -> None:
        """Dual-table: Table 1 filled and Table 2 scaffolded blank passes with zero errors."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/login.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine |  |
| Total mutants generated |  |
| Killed mutants |  |
| Timed-out mutants |  |
| Equivalent mutants |  |
| Survived mutants |  |
| Mutation Score Indicator (MSI) |  |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_dual_table_table1_scaffolded_table2_filled_passes(self) -> None:
        """Dual-table: Table 1 scaffolded blank and Table 2 filled passes with zero errors."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |  |  |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | mutmut |
| Total mutants generated | 10 |
| Killed mutants | 9 |
| Timed-out mutants | 0 |
| Equivalent mutants | 0 |
| Survived mutants | 1 |
| Mutation Score Indicator (MSI) | 90.0% |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 0)

    def test_mutation_dual_table_both_scaffolded_fails(self) -> None:
        """Dual-table: both tables unpopulated scaffolded emits QA_MISSING_MUTATION_EVIDENCE."""
        self._write_qa("""# QA Verification
- [x] QA_PASSED

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |  |  |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine |  |
| Total mutants generated |  |
| Killed mutants |  |
| Timed-out mutants |  |
| Equivalent mutants |  |
| Survived mutants |  |
| Mutation Score Indicator (MSI) |  |
""")
        findings: list[Finding] = []
        _lint_qa_mutation(self.task_name, self.task_dir, findings)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "QA_MISSING_MUTATION_EVIDENCE")


if __name__ == "__main__":
    unittest.main()

