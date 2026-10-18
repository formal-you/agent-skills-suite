#!/usr/bin/env python3
"""Comprehensive test suite for quality-engineering complexity_check tool."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QE_AGENTS_CHECKER = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "complexity_check.py"
QE_SKILLS_CHECKER = ROOT / "skills" / "workflow" / "quality-engineering" / "scripts" / "complexity_check.py"
PLAN_LINTER_AGENTS_DIR = ROOT / ".agents" / "skills" / "plan-linter" / "scripts"
PLAN_LINTER_SKILLS_DIR = ROOT / "skills" / "workflow" / "plan-linter" / "scripts"

ALL_CHECKER_PATHS = [QE_AGENTS_CHECKER, QE_SKILLS_CHECKER]


class ComplexityCheckCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.work_root = Path(self.tmpdir.name)
        self.src_dir = self.work_root / "src"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = QE_AGENTS_CHECKER

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _write_py(self, relative_path: str, content: str) -> Path:
        file_path = self.work_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_checker_files_exist_and_match(self) -> None:
        """Checker must exist in both trees, be identical, and not exist in plan-linter."""
        self.assertEqual(len(ALL_CHECKER_PATHS), 2)
        reference_bytes = None
        for p in ALL_CHECKER_PATHS:
            self.assertTrue(p.is_file(), f"Missing {p}")
            data = p.read_bytes()
            if reference_bytes is None:
                reference_bytes = data
            else:
                self.assertEqual(
                    data,
                    reference_bytes,
                    f"Byte mismatch between canonical checker and {p}",
                )

        # Confirm complexity_check.py is strictly purged from plan-linter
        self.assertFalse(
            (PLAN_LINTER_AGENTS_DIR / "complexity_check.py").exists(),
            "complexity_check.py must not exist in .agents/skills/plan-linter/scripts/",
        )
        self.assertFalse(
            (PLAN_LINTER_SKILLS_DIR / "complexity_check.py").exists(),
            "complexity_check.py must not exist in skills/workflow/plan-linter/scripts/",
        )

    def test_cli_help(self) -> None:
        """Help output must describe quality-engineering gate and not claim Gate 1 helper."""
        for p in ALL_CHECKER_PATHS:
            res = subprocess.run([sys.executable, str(p), "--help"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"--help failed for {p}: {res.stderr}")
            self.assertIn("quality-engineering gate", res.stdout)
            self.assertNotIn("Gate 1 helper", res.stdout)
            for flag in ("--src-dir", "--exclude", "--engine", "--json", "--warn-only", "--version"):
                self.assertIn(flag, res.stdout, f"Flag {flag} missing in {p} --help")

    def test_cli_version(self) -> None:
        """Version output must report program name and version."""
        for p in ALL_CHECKER_PATHS:
            res = subprocess.run([sys.executable, str(p), "--version"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"--version failed for {p}: {res.stderr}")
            self.assertIn("complexity_check", res.stdout)
            self.assertIn("2.0.0", res.stdout)

    def test_standard_complexity_passes(self) -> None:
        """Function with V(G) <= 10 passes with zero warnings or violations."""
        self._write_py("src/simple.py", """
def compute_sum(a, b):
    if a > 0:
        return a + b
    return b
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["violations_count"], 0)
        self.assertEqual(data["warnings_count"], 0)
        self.assertEqual(data["total_functions_scanned"], 1)

    def test_warning_complexity_passes_with_exit_zero(self) -> None:
        """Function with 11 <= V(G) <= 15 emits warning but exits 0."""
        # 11 decision points -> V(G) = 12
        branches = "\n    ".join(f"if x == {i}: return {i}" for i in range(11))
        code = f"""
def warning_fn(x):
    {branches}
    return -1
"""
        self._write_py("src/warning.py", code)
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["violations_count"], 0)
        self.assertEqual(data["warnings_count"], 1)
        self.assertEqual(data["warnings"][0]["function"], "warning_fn")
        self.assertEqual(data["warnings"][0]["vg"], 12)

    def test_critical_complexity_fails_with_exit_one(self) -> None:
        """Function with V(G) > 15 emits critical violation and exits 1."""
        # 15 decision points -> V(G) = 16
        branches = "\n    ".join(f"if x == {i}: return {i}" for i in range(15))
        code = f"""
def critical_fn(x):
    {branches}
    return -1
"""
        self._write_py("src/critical.py", code)
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1, res.stderr)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        self.assertEqual(data["violations_count"], 1)
        self.assertEqual(data["violations"][0]["function"], "critical_fn")
        self.assertEqual(data["violations"][0]["vg"], 16)

    def test_warn_only_flag_exits_zero_on_critical_violation(self) -> None:
        """--warn-only forces exit code 0 even when critical violations exist."""
        branches = "\n    ".join(f"if x == {i}: return {i}" for i in range(15))
        code = f"""
def critical_fn(x):
    {branches}
    return -1
"""
        self._write_py("src/critical.py", code)
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--warn-only", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        self.assertEqual(data["violations_count"], 1)

    def test_custom_exclude_and_multi_src_dir(self) -> None:
        """--exclude skips matching directory names; repeatable --src-dir scans multiple roots."""
        dir_a = self.work_root / "pkg_a"
        dir_b = self.work_root / "pkg_b"
        dir_skip = self.work_root / "ignored_pkg"

        self._write_py("pkg_a/a.py", "def fn_a(): return 1\n")
        self._write_py("pkg_b/b.py", "def fn_b(): return 2\n")
        self._write_py("ignored_pkg/bad.py", """
def bad_fn(x):
""" + "\n".join(f"    if x == {i}: return {i}" for i in range(20)) + "\n    return 0\n")

        res = subprocess.run(
            [
                sys.executable,
                str(self.script_path),
                "--src-dir", str(dir_a),
                "--src-dir", str(dir_b),
                "--exclude", "ignored_pkg",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 2)

    def test_multi_language_scanning_javascript(self) -> None:
        """JavaScript source files are scanned and cyclomatic complexity is computed."""
        js_file = self.work_root / "src" / "math.js"
        js_file.write_text("""
function calculateDiscount(price, isVip, couponCode) {
    if (!price || price <= 0) {
        return 0;
    }
    if (isVip && couponCode) {
        return price * 0.3;
    } else if (isVip || couponCode) {
        return price * 0.15;
    }
    return price * 0.05;
}
""", encoding="utf-8")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertGreaterEqual(data["total_functions_scanned"], 1)
        fn_records = [f for f in data.get("warnings", []) + data.get("violations", []) if f["function"] == "calculateDiscount"]
        # If not warning or violation, find in total scan
        self.assertEqual(data["violations_count"], 0)

    def test_multi_language_scanning_go(self) -> None:
        """Go source files are parsed and evaluated."""
        go_file = self.work_root / "src" / "service.go"
        go_file.write_text("""
package service

func EvaluateAccess(role string, level int) bool {
    if role == "admin" {
        return true
    }
    if role == "member" && level >= 5 {
        return true
    }
    return false
}
""", encoding="utf-8")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertGreaterEqual(data["total_functions_scanned"], 1)

    def test_engine_flag_selection(self) -> None:
        """CLI respects --engine ast, --engine tree-sitter, --engine lizard."""
        self._write_py("src/calc.py", "def calc(a, b):\n    return a + b\n")
        for engine in ("ast", "tree-sitter", "lizard"):
            res = subprocess.run(
                [sys.executable, str(self.script_path), "--src-dir", str(self.src_dir), "--engine", engine, "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"Engine {engine} failed: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["engine"], engine)
            self.assertEqual(data["total_functions_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
