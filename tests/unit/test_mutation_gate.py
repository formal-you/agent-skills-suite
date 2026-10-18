#!/usr/bin/env python3
"""Tests for tools/mutation_gate.py (fail-closed mutation gate)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "mutation_gate.py"


def run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL)] + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class MutationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.work_root = Path(self.tmpdir.name)
        self.report_path = self.work_root / "mutation-report.json"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def write_report(self, targets, msi=None) -> None:
        payload = {"tool": "fixture", "targets": targets}
        if msi is not None:
            payload["msi"] = msi
        self.report_path.write_text(json.dumps(payload), encoding="utf-8")

    def target(self, survived=0, total=10, killed=8, timed_out=1, equivalent=1):
        return {
            "file": "src/service.py",
            "total": total,
            "killed": killed,
            "timed_out": timed_out,
            "equivalent": equivalent,
            "survived": survived,
        }

    def test_check_passes_at_threshold(self) -> None:
        self.write_report([self.target(total=11, killed=8, timed_out=1, equivalent=1, survived=1)])
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["msi"], 90.0)

    def test_check_fails_below_threshold(self) -> None:
        self.write_report([self.target(total=10, killed=6, timed_out=1, equivalent=0, survived=3)])
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["errors"][0]["code"], "MUTATION_THRESHOLD_FAILED")

    def test_missing_report_fails_closed(self) -> None:
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "MUTATION_REPORT_MISSING")

    def test_invalid_json_fails_closed(self) -> None:
        self.report_path.write_text("{not json", encoding="utf-8")
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "MUTATION_REPORT_INVALID")

    def test_invalid_target_shape_fails_closed(self) -> None:
        self.report_path.write_text(json.dumps({"targets": [{"file": "src/x.py"}]}), encoding="utf-8")
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "MUTATION_REPORT_INVALID")

    def test_zero_denominator_is_handled(self) -> None:
        self.write_report([self.target(total=0, killed=0, timed_out=0, equivalent=0, survived=0)])
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["msi"], 100.0)

    def test_declared_msi_is_recomputed(self) -> None:
        self.write_report([self.target(total=10, killed=5, timed_out=0, equivalent=0, survived=5)], msi=100.0)
        result = run_tool("check", "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["msi"], 50.0)
        self.assertTrue(any("differs from computed" in note for note in payload["notes"]))

    def test_run_executes_command_and_evaluates_report(self) -> None:
        helper = self.work_root / "write_report.py"
        helper.write_text(
            "import json, sys\n"
            "payload = {'tool': 'helper', 'targets': [{'file': 'src/a.py', 'total': 10, "
            "'killed': 10, 'timed_out': 0, 'equivalent': 0, 'survived': 0}]}\n"
            "open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps(payload))\n",
            encoding="utf-8",
        )
        command = subprocess.list2cmdline([sys.executable, str(helper), str(self.report_path)])
        result = run_tool("run", "--command", command, "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["msi"], 100.0)

    def test_run_command_failure_fails_closed(self) -> None:
        command = subprocess.list2cmdline([sys.executable, "-c", "import sys; sys.exit(3)"])
        result = run_tool("run", "--command", command, "--report", str(self.report_path), "--json")
        self.assertEqual(result.returncode, 1, "stdout=%r stderr=%r" % (result.stdout, result.stderr))
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail("stdout is not JSON: %r stderr=%r command=%r" % (result.stdout, result.stderr, command))
        self.assertEqual(payload["errors"][0]["code"], "MUTATION_COMMAND_FAILED")

    def test_usage_requires_subcommand(self) -> None:
        result = run_tool("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("mutation_gate", result.stdout)


if __name__ == "__main__":
    unittest.main()
