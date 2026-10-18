#!/usr/bin/env python3
"""Black-box tests for the converge skill and its bundled stdlib helper.

Run from the repository root:
    python -m unittest tests.unit.test_converge -v
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
CONVERGE = SKILLS / "converge"
SCRIPT = CONVERGE / "scripts" / "converge.py"
DEV_SKILL = SKILLS / "dev"
DEV_TEMPLATE = SKILLS / "task-decomposition" / "assets" / "templates" / "02-dev-workspace.template.md"
MARKER_RE = re.compile(r"<!-- converged: (?P<task>[A-Za-z0-9._-]+) sha256:(?P<hash>[0-9a-f]{64}) -->")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ABS_PATH_MARKERS = ("D:\\", "C:\\", "/home/", "/Users/")

SPEC = """# Tech Spec: Demo

## 1. Architecture overview

The platform is split into components that reference #sec-auth and #sec-billing.

## 2. Components and responsibilities

| Component | Responsibility | Anchor |
| :--- | :--- | :--- |
| Auth service | Issues and revokes session tokens. | #sec-auth |
| Billing service | Reconciles invoices. | #sec-billing |
"""

CONTRACT = """---
task_id: "{task_id}"
title: "{title}"
module: auth
estimated_lines: 120
origin_spec_anchor: "#sec-auth"
change_id: "{change_id}"
dod:
  type_check: "python -m compileall src"
  lint: "python -m ruff check src"
  test_file: "tests/acceptance/test_auth.py"
  edge_cases:
    - "empty credentials return 400"
    - "expired token returns 401"
---

# Task {task_id}: {title}

Implementation contract for the converge tests.
"""

DEVIATIONS = """# Dev Workspace

## 5. Handoff to QA

- [x] WAITING_FOR_QA

## Implementation deviations

After implementation, list every place where the code ended up different from the contract or the
spec, one row per deviation.

| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |
| DEV-001 | #sec-auth | modify | Session tokens are opaque and rotate on refresh. |
| DEV-002 | #sec-auth | add | Replayed sessions are rejected with 409 Conflict. |
"""

DEVIATIONS_NONE = """# Dev Workspace

## Implementation deviations

| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |
| None | None | None | None |
"""

DEVIATIONS_MISSING = """# Dev Workspace

## 3. Actual changes

| Action | Path | Approx. lines |
| :--- | :--- | :--- |
| create | src/auth/service.py | 80 |
"""

DEVIATIONS_DRIFT = """# Dev Workspace

## Implementation deviations

| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |
| DEV-001 | #sec-unknown | modify | Undocumented behavior. |
"""

QA_PASSED = """# QA Verification

## 2. Test matrix

| Case ID | Scenario | Status |
| :--- | :--- | :--- |
| TC-01 | sign in | pass |

## 5. Verdict

- [x] QA_PASSED
- [ ] REWORK_REQUIRED
"""

QA_REWORK = """# QA Verification

## 5. Verdict

- [ ] QA_PASSED
- [x] REWORK_REQUIRED

Repeated failure in the token rotation path.
"""

QA_UNFINISHED = """# QA Verification

## 5. Verdict

- [ ] QA_PASSED
- [ ] REWORK_REQUIRED
"""

PROCESS = """# Task {task_id}: Process and Audit Trail (derived)

## 1. Status

~~~yaml
task_id: "{task_id}"
macro_status: "DONE"
micro_phase: "FINISHED"
current_lock_holder: "None"
retry_count: 0
last_heartbeat: ""
~~~

## 2. Event Log

| Event ID | Timestamp (UTC) | Event Code | Actor | Payload / Evidence | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""

PROPOSAL = """---
change_id: "chg-001"
status: proposed
---

# Change Proposal: chg-001

Add opaque session tokens.
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    return match.group(1)


class ConvergeTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="converge-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.tasks = self.root / "tasks"
        self.specs = self.root / ".specs"
        self.spec = self.specs / "02-tech-spec.md"
        self.changes = self.specs / "changes"
        self.tasks.mkdir(parents=True)
        self.specs.mkdir(parents=True)
        self.spec.write_text(SPEC, encoding="utf-8")

    # -- fixture builders ---------------------------------------------------
    def bundle(
        self,
        task_id: str = "task-001-auth",
        title: str = "Opaque session tokens",
        qa: str = QA_PASSED,
        deviations: str = DEVIATIONS,
        change_id: str = "chg-001",
        with_proposal: bool = True,
    ) -> Path:
        task_dir = self.tasks / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "01-contract.md").write_text(
            CONTRACT.format(task_id=task_id, title=title, change_id=change_id), encoding="utf-8"
        )
        (task_dir / "02-dev-workspace.md").write_text(deviations, encoding="utf-8")
        (task_dir / "03-qa-verification.md").write_text(qa, encoding="utf-8")
        (task_dir / "04-process.md").write_text(PROCESS.format(task_id=task_id), encoding="utf-8")
        if with_proposal and change_id:
            proposal_dir = self.changes / change_id
            proposal_dir.mkdir(parents=True, exist_ok=True)
            (proposal_dir / "proposal.md").write_text(PROPOSAL, encoding="utf-8")
        return task_dir

    def run_converge(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT)] + [str(item) for item in args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(self.root),
        )

    def run_json(self, *args: str) -> dict:
        result = self.run_converge(*args, "--json")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic aid
            raise AssertionError(
                "invalid JSON on stdout: " + result.stdout + "\nstderr: " + result.stderr
            ) from exc

    def snapshot(self) -> dict:
        state = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                state[str(path.relative_to(self.root))] = path.read_bytes()
        return state


class TemplateAndSkillTests(unittest.TestCase):
    def test_dev_template_has_token_free_deviation_section(self) -> None:
        text = read_text(DEV_TEMPLATE)
        self.assertIn("## Implementation deviations", text)
        self.assertIn(
            "| Deviation ID | Spec anchor | Operation | Confirmed behavior |", text
        )
        self.assertIn("| :--- | :--- | :--- | :--- |", text)
        self.assertIn("None in every cell", text)
        self.assertNotIn("{{", text)
        self.assertNotIn("[TBD]", text)
        self.assertNotRegex(text, r"\bTODO\b")
        self.assertIn("DEV-001", text)

    def test_skill_frontmatter_name_matches_directory(self) -> None:
        self.assertTrue((CONVERGE / "SKILL.md").is_file())
        self.assertTrue((CONVERGE / "references" / "convergence-protocol.md").is_file())
        text = read_text(CONVERGE / "SKILL.md")
        fm = frontmatter(text)
        self.assertRegex(fm, r"(?m)^name: converge$")
        self.assertRegex(
            fm, r'(?m)^description: ".+Use when .+Do not use .+"$'
        )
        self.assertIn("license:", fm)
        self.assertIn("compatibility:", fm)
        self.assertRegex(fm, r"(?m)^\s+version: ", fm)
        self.assertRegex(fm, r"(?m)^\s+category: ", fm)
        self.assertLess(len(text.splitlines()), 200)

    def test_skill_documents_convergence_contract(self) -> None:
        text = read_text(CONVERGE / "SKILL.md")
        for needle in (
            "QA_PASSED",
            "02-dev-workspace.md",
            "03-qa-verification.md",
            ".specs/02-tech-spec.md",
            "Converged changes",
            "ConvergeTool",
            "manual fallback",
            "REWORK_REQUIRED",
            "never rewrites history",
        ):
            self.assertIn(needle, text, "SKILL.md misses: " + needle)
        protocol = read_text(CONVERGE / "references" / "convergence-protocol.md")
        for needle in (
            "WAITING_FOR_QA",
            "QA_PASSED",
            "CONVERGED",
            "tasks/archive/<task-id>/",
            ".specs/changes/<change-id>/convergence.md",
            "idempot",
            "conflict",
            "structural",
            "spec-generator",
        ):
            self.assertIn(needle, protocol, "protocol reference misses: " + needle)

    def test_skill_is_english_and_has_no_absolute_paths(self) -> None:
        for path in CONVERGE.rglob("*.md"):
            text = read_text(path)
            self.assertIsNone(CJK_RE.search(text), "non-English CJK content in " + str(path))
            for marker in ABS_PATH_MARKERS:
                self.assertNotIn(marker, text, "absolute path " + marker + " in " + str(path))

    def test_skill_relative_links_resolve(self) -> None:
        for path in CONVERGE.rglob("*.md"):
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read_text(path)):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (path.parent / target.split("#")[0]).resolve()
                self.assertTrue(resolved.exists(), "broken link in " + str(path) + ": " + target)


class CliSurfaceTests(ConvergeTestBase):
    def test_help_and_version(self) -> None:
        help_result = self.run_converge("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("usage", help_result.stdout.lower())
        self.assertIn("check", help_result.stdout)
        self.assertIn("apply", help_result.stdout)
        version_result = self.run_converge("--version")
        self.assertEqual(version_result.returncode, 0)
        self.assertRegex(version_result.stdout, r"\d+\.\d+\.\d+")

    def test_spec_sha256_matches_file_content(self) -> None:
        result = self.run_converge("--spec", self.spec, "--spec-sha256")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = sha256_text(self.spec.read_text(encoding="utf-8"))
        self.assertEqual(result.stdout.strip(), expected)
        via_subcommand = self.run_converge("check", "--spec", self.spec, "--spec-sha256")
        self.assertEqual(via_subcommand.returncode, 0, via_subcommand.stderr)
        self.assertEqual(via_subcommand.stdout.strip(), expected)

    def test_missing_spec_is_usage_error(self) -> None:
        result = self.run_converge("check", "--tasks-dir", self.tasks, "--spec", self.root / "absent.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)


class CheckTests(ConvergeTestBase):
    def test_check_with_no_bundles_exits_zero(self) -> None:
        result = self.run_converge("check", "--tasks-dir", self.tasks, "--spec", self.spec, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"], {"converged": 0, "pending": 0, "blocked": 0})
        self.assertEqual(payload["tasks"], [])

    def test_check_classifies_pending_blocked_and_converged(self) -> None:
        self.bundle("task-001-ready")
        self.bundle("task-002-rework", qa=QA_REWORK)
        self.bundle("task-003-unfinished", qa=QA_UNFINISHED)
        self.bundle("task-004-missing-table", deviations=DEVIATIONS_MISSING)
        self.bundle("task-005-converged")
        marker = "<!-- converged: task-005-converged sha256:" + "0" * 64 + " -->"
        self.spec.write_text(read_text(self.spec) + "\n" + marker + "\n", encoding="utf-8")

        result = self.run_converge("check", "--tasks-dir", self.tasks, "--spec", self.spec, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        by_task = {item["task_id"]: item for item in payload["tasks"]}
        self.assertEqual(payload["summary"], {"converged": 1, "pending": 1, "blocked": 3})
        self.assertEqual(by_task["task-001-ready"]["status"], "pending")
        self.assertTrue(by_task["task-001-ready"]["ready"])
        self.assertEqual(by_task["task-001-ready"]["deviation_count"], 2)
        self.assertEqual(by_task["task-002-rework"]["status"], "blocked")
        self.assertEqual(by_task["task-002-rework"]["reason"], "rework_active")
        self.assertEqual(by_task["task-003-unfinished"]["reason"], "qa_not_passed")
        self.assertEqual(by_task["task-004-missing-table"]["reason"], "deviation_log_missing")
        self.assertEqual(by_task["task-005-converged"]["status"], "converged")

    def test_fail_on_pending_only_fails_for_pending(self) -> None:
        self.bundle("task-001-rework", qa=QA_REWORK)
        blocked_only = self.run_converge(
            "check", "--tasks-dir", self.tasks, "--spec", self.spec, "--fail-on-pending"
        )
        self.assertEqual(blocked_only.returncode, 0, blocked_only.stderr)

        self.bundle("task-002-ready")
        pending = self.run_converge(
            "check", "--tasks-dir", self.tasks, "--spec", self.spec, "--fail-on-pending"
        )
        self.assertEqual(pending.returncode, 1)
        self.assertIn("pending convergence", pending.stderr)

    def test_spec_drift_is_warning_by_default_and_refusal_when_strict(self) -> None:
        self.bundle("task-001-drift", deviations=DEVIATIONS_DRIFT)
        payload = self.run_json("check", "--tasks-dir", self.tasks, "--spec", self.spec)
        item = payload["tasks"][0]
        self.assertEqual(item["status"], "pending")
        self.assertTrue(item["warnings"])
        self.assertIn("#sec-unknown", item["warnings"][0])

        strict = self.run_json(
            "check", "--tasks-dir", self.tasks, "--spec", self.spec, "--strict"
        )
        strict_item = strict["tasks"][0]
        self.assertEqual(strict_item["status"], "blocked")
        self.assertEqual(strict_item["reason"], "spec_drift")
        self.assertIn("#sec-unknown", strict_item["detail"])

    def test_unknown_qa_verdict_spellings_are_tolerated(self) -> None:
        bare_verdict = "# QA Verification\n\nVerdict: QA_PASSED\n"
        self.bundle("task-001-bare", qa=bare_verdict)
        payload = self.run_json("check", "--tasks-dir", self.tasks, "--spec", self.spec)
        self.assertEqual(payload["tasks"][0]["status"], "pending")

    def test_bundle_without_contract_is_still_classified(self) -> None:
        task_dir = self.tasks / "task-001-minimal"
        task_dir.mkdir(parents=True)
        (task_dir / "02-dev-workspace.md").write_text(DEVIATIONS, encoding="utf-8")
        (task_dir / "03-qa-verification.md").write_text(QA_PASSED, encoding="utf-8")
        payload = self.run_json("check", "--tasks-dir", self.tasks, "--spec", self.spec)
        self.assertEqual(payload["tasks"][0]["status"], "pending")

    def test_explicit_none_row_is_converge_ready(self) -> None:
        self.bundle("task-001-none", deviations=DEVIATIONS_NONE)
        payload = self.run_json("check", "--tasks-dir", self.tasks, "--spec", self.spec)
        self.assertEqual(payload["tasks"][0]["status"], "pending")
        self.assertEqual(payload["tasks"][0]["deviation_count"], 0)


class ApplyTests(ConvergeTestBase):
    def test_apply_happy_path_writes_spec_process_and_archive(self) -> None:
        task = self.bundle("task-001-auth")
        result = self.run_converge(
            "apply",
            "--task",
            task,
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--changes-dir",
            self.changes,
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "converged")
        self.assertEqual(payload["deviation_count"], 2)
        self.assertTrue(payload["proposal_archived"])

        spec_text = read_text(self.spec)
        self.assertEqual(spec_text.count("## Converged changes"), 1)
        self.assertIn("### task-001-auth: Opaque session tokens", spec_text)
        self.assertIn("| DEV-001 | #sec-auth | modify | Session tokens are opaque", spec_text)
        self.assertIn("| DEV-002 | #sec-auth | add |", spec_text)
        self.assertIn("tasks/archive/task-001-auth", spec_text)
        markers = MARKER_RE.findall(spec_text)
        self.assertEqual([marker[0] for marker in markers], ["task-001-auth"])
        self.assertEqual(payload["marker"], "sha256:" + markers[0][1])

        process_text = read_text(self.tasks / "archive" / "task-001-auth" / "04-process.md")
        self.assertIn('macro_status: "CONVERGED"', process_text)
        self.assertIn("TASK_CONVERGED", process_text)
        self.assertIn("ConvergeTool", process_text)

        self.assertFalse(task.exists(), "task bundle must be moved, not copied")
        archived = self.tasks / "archive" / "task-001-auth"
        for name in ("01-contract.md", "02-dev-workspace.md", "03-qa-verification.md", "04-process.md"):
            self.assertTrue((archived / name).is_file(), "archive misses " + name)

        proposal = read_text(self.changes / "chg-001" / "proposal.md")
        self.assertIn("status: archived", proposal)
        convergence = read_text(self.changes / "chg-001" / "convergence.md")
        self.assertIn("task-001-auth", convergence)
        self.assertIn("chg-001", convergence)
        self.assertIn("<!-- converged: task-001-auth sha256:" + markers[0][1] + " -->", convergence)

    def test_apply_refuses_when_qa_not_passed(self) -> None:
        task = self.bundle("task-001-auth", qa=QA_UNFINISHED)
        spec_before = read_text(self.spec)
        result = self.run_converge(
            "apply", "--task", task, "--spec", self.spec, "--archive-dir", self.tasks / "archive"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("qa_not_passed", result.stderr)
        self.assertEqual(read_text(self.spec), spec_before)
        self.assertTrue(task.is_dir())
        self.assertIn("- [ ] QA_PASSED", read_text(task / "03-qa-verification.md"))

    def test_apply_refuses_active_rework(self) -> None:
        task = self.bundle("task-001-auth", qa=QA_REWORK)
        result = self.run_converge(
            "apply", "--task", task, "--spec", self.spec, "--archive-dir", self.tasks / "archive"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("rework_active", result.stderr)

    def test_apply_refuses_when_deviation_table_is_missing(self) -> None:
        task = self.bundle("task-001-auth", deviations=DEVIATIONS_MISSING)
        spec_before = read_text(self.spec)
        result = self.run_converge(
            "apply", "--task", task, "--spec", self.spec, "--archive-dir", self.tasks / "archive"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("deviation_log_missing", result.stderr)
        self.assertEqual(read_text(self.spec), spec_before)
        self.assertTrue(task.is_dir())

    def test_apply_refuses_spec_drift_when_strict(self) -> None:
        task = self.bundle("task-001-auth", deviations=DEVIATIONS_DRIFT)
        spec_before = read_text(self.spec)
        result = self.run_converge(
            "apply",
            "--task",
            task,
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--strict",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("spec_drift", result.stderr)
        self.assertEqual(read_text(self.spec), spec_before)

    def test_second_apply_is_idempotent(self) -> None:
        task = self.bundle("task-001-auth")
        args = (
            "apply",
            "--task",
            task,
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--changes-dir",
            self.changes,
        )
        first = self.run_converge(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        spec_after_first = read_text(self.spec)
        second = self.run_json(*args)
        self.assertEqual(second["status"], "no_changes")
        self.assertEqual(read_text(self.spec), spec_after_first)
        self.assertEqual(spec_after_first.count("## Converged changes"), 1)

    def test_dry_run_writes_nothing(self) -> None:
        self.bundle("task-001-auth")
        before = self.snapshot()
        result = self.run_converge(
            "apply",
            "--task",
            self.tasks / "task-001-auth",
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--changes-dir",
            self.changes,
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run", result.stdout.lower())
        self.assertEqual(self.snapshot(), before)

    def test_force_replaces_existing_archive_destination(self) -> None:
        task = self.bundle("task-001-auth")
        archive = self.tasks / "archive" / "task-001-auth"
        archive.mkdir(parents=True)
        (archive / "stale.txt").write_text("stale", encoding="utf-8")
        spec_before = read_text(self.spec)

        refused = self.run_converge(
            "apply", "--task", task, "--spec", self.spec, "--archive-dir", self.tasks / "archive"
        )
        self.assertEqual(refused.returncode, 1)
        self.assertIn("--force", refused.stderr)
        self.assertEqual(read_text(self.spec), spec_before)

        forced = self.run_converge(
            "apply",
            "--task",
            task,
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--force",
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)
        self.assertFalse((archive / "stale.txt").exists(), "existing archive must be replaced")
        self.assertTrue((archive / "01-contract.md").is_file())

    def test_default_paths_work_from_repository_root(self) -> None:
        self.bundle("task-001-auth")
        result = self.run_converge("apply", "--task", "tasks/task-001-auth")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Converged changes", read_text(self.spec))
        self.assertTrue((self.tasks / "archive" / "task-001-auth" / "04-process.md").is_file())
        self.assertIn(
            "status: archived", read_text(self.changes / "chg-001" / "proposal.md")
        )
        self.assertTrue((self.changes / "chg-001" / "convergence.md").is_file())

        check = self.run_converge("check", "--json")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(json.loads(check.stdout)["summary"]["pending"], 0)

    def test_second_task_appends_to_existing_section(self) -> None:
        first = self.bundle("task-001-auth", title="First slice")
        second = self.bundle("task-002-billing", title="Second slice", change_id="chg-002")
        common = ("--spec", self.spec, "--archive-dir", self.tasks / "archive", "--changes-dir", self.changes)
        self.assertEqual(self.run_converge("apply", "--task", first, *common).returncode, 0)
        self.assertEqual(self.run_converge("apply", "--task", second, *common).returncode, 0)
        spec_text = read_text(self.spec)
        self.assertEqual(spec_text.count("## Converged changes"), 1)
        converged = [marker[0] for marker in MARKER_RE.findall(spec_text)]
        self.assertEqual(converged, ["task-001-auth", "task-002-billing"])

    def test_none_deviation_row_is_recorded_in_spec(self) -> None:
        task = self.bundle("task-001-none", deviations=DEVIATIONS_NONE)
        result = self.run_converge(
            "apply",
            "--task",
            task,
            "--spec",
            self.spec,
            "--archive-dir",
            self.tasks / "archive",
            "--changes-dir",
            self.changes,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        spec_text = read_text(self.spec)
        self.assertIn("| None | None | None | None |", spec_text)
        self.assertIn("## Converged changes", spec_text)
        self.assertRegex(spec_text, r"<!-- converged: task-001-none sha256:[0-9a-f]{64} -->")


class DevHandoffTests(unittest.TestCase):
    def test_dev_skill_requires_deviation_table_and_converge_ownership(self) -> None:
        for path in (DEV_SKILL / "SKILL.md", DEV_SKILL / "references" / "dev-protocol.md"):
            text = read_text(path)
            self.assertIn("Implementation deviations", text, "missing deviation handoff in " + str(path))
            self.assertIn("converge", text.lower(), "missing converge ownership in " + str(path))
            self.assertIn("02-tech-spec.md", text, "missing spec ownership note in " + str(path))
        skill_text = read_text(DEV_SKILL / "SKILL.md")
        self.assertIn("DEV-001", skill_text)
        self.assertIn("Dev never edits", skill_text)


if __name__ == "__main__":
    unittest.main()
