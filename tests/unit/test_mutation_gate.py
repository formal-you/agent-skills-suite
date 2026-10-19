#!/usr/bin/env python3
"""Tests for the quality-engineering mutation_gate.py script (fail-closed mutation gate)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "mutation_gate.py"


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

    def write_config(self, mutation, schema_version=1, name="quality-gate.config.json") -> Path:
        path = self.work_root / name
        payload = {"schema_version": schema_version, "mutation": mutation}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_report_helper(self) -> str:
        helper = self.work_root / "write_report.py"
        helper.write_text(
            "import json, sys\n"
            "payload = {'tool': 'helper', 'targets': [{'file': 'src/a.py', 'total': 10, "
            "'killed': 10, 'timed_out': 0, 'equivalent': 0, 'survived': 0}]}\n"
            "open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps(payload))\n",
            encoding="utf-8",
        )
        return subprocess.list2cmdline([sys.executable, str(helper), str(self.report_path)])

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

    # ------------------------------------------------------------------
    # --config: config-driven command/report/min_msi and validation
    # ------------------------------------------------------------------

    def test_config_provides_command_report_and_min_msi_for_run(self) -> None:
        command = self.write_report_helper()
        config = self.write_config(
            {
                "command": command,
                "report": str(self.report_path),
                "min_msi": 80,
                "core_min_msi": 90,
            }
        )
        result = run_tool("run", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["msi"], 100.0)

    def test_check_uses_config_report_and_min_msi(self) -> None:
        self.write_report(
            [self.target(total=11, killed=8, timed_out=1, equivalent=1, survived=1)]
        )
        config = self.write_config(
            {"report": str(self.report_path), "min_msi": 80, "core_min_msi": 90}
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_cli_command_overrides_config_command(self) -> None:
        command = self.write_report_helper()
        failing = subprocess.list2cmdline(
            [sys.executable, "-c", "import sys; sys.exit(3)"]
        )
        config = self.write_config(
            {
                "command": failing,
                "report": str(self.report_path),
                "min_msi": 80,
            }
        )
        result = run_tool("run", "--config", str(config), "--command", command, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_cli_min_msi_overrides_config(self) -> None:
        # Report MSI is 50%; config demands 90% (fails), CLI relaxes to 40% (passes).
        self.write_report(
            [self.target(total=10, killed=5, timed_out=0, equivalent=0, survived=5)]
        )
        config = self.write_config(
            {"report": str(self.report_path), "min_msi": 90}
        )
        result_config = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result_config.returncode, 1)
        self.assertEqual(
            json.loads(result_config.stdout)["errors"][0]["code"],
            "MUTATION_THRESHOLD_FAILED",
        )
        result_cli = run_tool(
            "check", "--config", str(config), "--min-msi", "40", "--json"
        )
        self.assertEqual(result_cli.returncode, 0, result_cli.stderr + result_cli.stdout)
        self.assertTrue(json.loads(result_cli.stdout)["passed"])

    def test_cli_report_overrides_config_report(self) -> None:
        self.write_report(
            [self.target(total=11, killed=8, timed_out=1, equivalent=1, survived=1)]
        )
        config = self.write_config(
            {"report": str(self.work_root / "missing-report.json"), "min_msi": 80}
        )
        result = run_tool(
            "check", "--config", str(config), "--report", str(self.report_path), "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_missing_config_file_exits_2(self) -> None:
        result = run_tool(
            "check",
            "--config",
            str(self.work_root / "does-not-exist.config.json"),
            "--report",
            str(self.report_path),
            "--json",
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("config file not found", result.stderr.lower())

    def test_invalid_json_config_exits_2(self) -> None:
        config = self.work_root / "broken.config.json"
        config.write_text("{not json", encoding="utf-8")
        result = run_tool(
            "check", "--config", str(config), "--report", str(self.report_path), "--json"
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("not valid json", result.stderr.lower())

    def test_config_schema_version_must_be_1(self) -> None:
        config = self.write_config(
            {"report": str(self.report_path), "min_msi": 80}, schema_version=2
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("schema_version", result.stderr)

    def test_config_without_mutation_object_exits_2(self) -> None:
        config = self.work_root / "no-mutation.config.json"
        config.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        result = run_tool(
            "check", "--config", str(config), "--report", str(self.report_path), "--json"
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("mutation", result.stderr.lower())

    def test_config_min_msi_must_be_numeric(self) -> None:
        config = self.write_config(
            {"report": str(self.report_path), "min_msi": "eighty"}
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("min_msi must be numeric", result.stderr)

    def test_config_core_min_msi_must_be_numeric(self) -> None:
        config = self.write_config(
            {
                "report": str(self.report_path),
                "min_msi": 80,
                "core_min_msi": "90",
            }
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("core_min_msi must be numeric", result.stderr)

    def test_config_core_min_msi_must_be_at_least_min_msi(self) -> None:
        config = self.write_config(
            {
                "report": str(self.report_path),
                "min_msi": 80,
                "core_min_msi": 70,
            }
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("must be >= mutation.min_msi", result.stderr)

    def test_config_core_min_msi_must_not_exceed_100(self) -> None:
        config = self.write_config(
            {
                "report": str(self.report_path),
                "min_msi": 80,
                "core_min_msi": 120,
            }
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("between 0 and 100", result.stderr)

    def test_config_valid_core_min_msi_is_accepted(self) -> None:
        self.write_report(
            [self.target(total=11, killed=8, timed_out=1, equivalent=1, survived=1)]
        )
        config = self.write_config(
            {
                "report": str(self.report_path),
                "min_msi": 80,
                "core_min_msi": 90,
            }
        )
        result = run_tool("check", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_run_without_command_anywhere_fails_closed(self) -> None:
        config = self.write_config(
            {"report": str(self.report_path), "min_msi": 80}
        )
        result = run_tool("run", "--config", str(config), "--json")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("no mutation command configured", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
