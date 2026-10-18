#!/usr/bin/env python3
"""Comprehensive test suite for quality-engineering complexity_check tool."""

from __future__ import annotations

import contextlib
import importlib.util
import io
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


def _module_available(*names: str) -> bool:
    for name in names:
        try:
            if importlib.util.find_spec(name) is not None:
                return True
        except (ImportError, ValueError):
            continue
    return False


HAS_TREE_SITTER_LANGUAGES = _module_available("tree_sitter_languages")
HAS_TREE_SITTER = _module_available("tree_sitter")
HAS_LIZARD = _module_available("lizard")


def _auto_multi_language_available() -> bool:
    """Mirror the checker's auto engine resolution for non-Python files."""
    if HAS_TREE_SITTER_LANGUAGES:
        return True
    if HAS_TREE_SITTER:
        # The checker resolves tree-sitter but has no grammar resolver without
        # tree_sitter_languages, so non-Python files surface as scan errors.
        return False
    return HAS_LIZARD


def _load_checker_module():
    spec = importlib.util.spec_from_file_location("complexity_check_under_test", QE_AGENTS_CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _critical_function(name: str, branches: int = 15) -> str:
    body = "\n    ".join(f"if x == {i}: return {i}" for i in range(branches))
    return f"\ndef {name}(x):\n    {body}\n    return -1\n"


class ComplexityCheckCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.work_root = Path(self.tmpdir.name)
        self.src_dir = self.work_root / "src"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = QE_AGENTS_CHECKER

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _run(self, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.script_path), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd is not None else None,
        )

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
            for flag in (
                "--src-dir",
                "--changed-files",
                "--exclude",
                "--engine",
                "--json",
                "--warn-only",
                "--version",
            ):
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
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
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
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["violations_count"], 0)
        self.assertEqual(data["warnings_count"], 1)
        self.assertEqual(data["warnings"][0]["function"], "warning_fn")
        self.assertEqual(data["warnings"][0]["vg"], 12)

    def test_critical_complexity_fails_with_exit_one(self) -> None:
        """Function with V(G) > 15 emits critical violation and exits 1."""
        self._write_py("src/critical.py", _critical_function("critical_fn"))
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
        self.assertEqual(res.returncode, 1, res.stderr)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        self.assertEqual(data["violations_count"], 1)
        self.assertEqual(data["violations"][0]["function"], "critical_fn")
        self.assertEqual(data["violations"][0]["vg"], 16)

    def test_warn_only_flag_exits_zero_on_critical_violation(self) -> None:
        """--warn-only forces exit code 0 even when critical violations exist."""
        self._write_py("src/critical.py", _critical_function("critical_fn"))
        res = self._run(["--src-dir", str(self.src_dir), "--warn-only", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        self.assertEqual(data["violations_count"], 1)

    def test_custom_exclude_and_multi_src_dir(self) -> None:
        """--exclude skips matching directory names; repeatable --src-dir scans multiple roots."""
        dir_a = self.work_root / "pkg_a"
        dir_b = self.work_root / "pkg_b"

        self._write_py("pkg_a/a.py", "def fn_a(): return 1\n")
        self._write_py("pkg_b/b.py", "def fn_b(): return 2\n")
        self._write_py("ignored_pkg/bad.py", _critical_function("bad_fn", branches=20))

        res = self._run(
            [
                "--src-dir", str(dir_a),
                "--src-dir", str(dir_b),
                "--exclude", "ignored_pkg",
                "--json",
            ]
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 2)
        self.assertEqual({fn["function"] for fn in data["functions"]}, {"fn_a", "fn_b"})

    def test_default_excludes_skill_tool_and_template_trees(self) -> None:
        """Default excludes prevent accidental '.' scans from analyzing repository plumbing."""
        self._write_py("src/good.py", "def good_fn(): return 1\n")
        for directory in ("skills", "tools", "templates", "tasks", "docs", "specs"):
            self._write_py(f"{directory}/fake/bad.py", _critical_function(f"{directory}_bad"))
        # Explicitly scanning the working root is allowed; the default excludes
        # must still remove skill/tool/template/task/doc/spec trees.
        res = self._run(["--src-dir", ".", "--json"], cwd=self.work_root)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 1)
        self.assertEqual([fn["function"] for fn in data["functions"]], ["good_fn"])

    def test_no_src_and_no_src_dir_returns_usage_error(self) -> None:
        """Without --src-dir and without ./src the tool must fail closed (exit 2)."""
        empty_root = self.work_root / "empty_project"
        empty_root.mkdir()
        res = self._run(["--json"], cwd=empty_root)
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertIn("--src-dir", res.stderr)
        self.assertIn("src", res.stderr)
        self.assertEqual(res.stdout.strip(), "")

    def test_default_src_directory_used_when_present(self) -> None:
        """Without --src-dir, ./src is used when it exists (never '.')."""
        self._write_py("src/simple.py", "def simple_fn(a):\n    return a\n")
        self._write_py("outside.py", _critical_function("outside_fn"))
        res = self._run(["--json"], cwd=self.work_root)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 1)
        self.assertEqual(data["functions"][0]["file"], "src/simple.py")
        self.assertEqual(data["functions"][0]["function"], "simple_fn")

    def test_missing_explicit_src_dir_returns_usage_error(self) -> None:
        """An explicit --src-dir that does not exist is a usage error, not a silent pass."""
        res = self._run(["--src-dir", str(self.work_root / "does_not_exist"), "--json"])
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertIn("does not exist", res.stderr)
        self.assertEqual(res.stdout.strip(), "")

    def test_explicit_src_dir_scans_only_that_tree(self) -> None:
        """--src-dir limits scanning to the requested tree."""
        self._write_py("src/good.py", "def good_fn(): return 1\n")
        self._write_py("other/bad.py", _critical_function("bad_fn"))
        res = self._run(["--src-dir", "src", "--json"], cwd=self.work_root)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 1)
        self.assertEqual([fn["function"] for fn in data["functions"]], ["good_fn"])

    def test_changed_files_filters_records(self) -> None:
        """--changed-files only scans the listed files."""
        self._write_py("src/a.py", "def fn_a(): return 1\n")
        self._write_py("src/b.py", "def fn_b(): return 2\n")
        self._write_py("src/c.py", _critical_function("fn_c"))
        changed = self.work_root / "changed.txt"
        changed.write_text("# changed files\nsrc/b.py\n", encoding="utf-8")

        res = self._run(["--changed-files", "changed.txt", "--json"], cwd=self.work_root)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 1)
        self.assertEqual(data["functions"], [{"file": "src/b.py", "line": 1, "function": "fn_b", "vg": 1}])
        self.assertEqual(data["skipped_unsupported"], [])

    def test_empty_changed_files_list_returns_usage_error(self) -> None:
        """An empty --changed-files list fails closed instead of passing with zero results."""
        changed = self.work_root / "changed.txt"
        changed.write_text("\n\n", encoding="utf-8")
        res = self._run(["--changed-files", str(changed), "--json"], cwd=self.work_root)
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertIn("empty", res.stderr)
        self.assertEqual(res.stdout.strip(), "")

    def test_report_contains_all_functions(self) -> None:
        """JSON report lists every scanned function with file/line/function/vg."""
        self._write_py("src/mixed.py", (
            "def simple_fn(a):\n"
            "    return a\n"
            + "\ndef warning_fn(x):\n    "
            + "\n    ".join(f"if x == {i}: return {i}" for i in range(11))
            + "\n    return -1\n"
            + _critical_function("critical_fn")
        ))
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
        self.assertEqual(res.returncode, 1, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["total_functions_scanned"], 3)
        self.assertEqual(len(data["functions"]), 3)
        names = [fn["function"] for fn in data["functions"]]
        self.assertEqual(sorted(names), ["critical_fn", "simple_fn", "warning_fn"])
        for function in data["functions"]:
            self.assertEqual(set(function.keys()), {"file", "line", "function", "vg"})
            self.assertIsInstance(function["line"], int)
            self.assertIsInstance(function["vg"], int)
            self.assertGreater(function["vg"], 0)
        self.assertEqual([fn["function"] for fn in data["violations"]], ["critical_fn"])
        self.assertEqual([fn["function"] for fn in data["warnings"]], ["warning_fn"])

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
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
        if _auto_multi_language_available():
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(res.stdout)
            self.assertTrue(data["passed"])
            self.assertGreaterEqual(data["total_functions_scanned"], 1)
            self.assertIn("calculateDiscount", [fn["function"] for fn in data["functions"]])
            self.assertEqual(data["violations_count"], 0)
        else:
            data = json.loads(res.stdout)
            self.assertEqual(res.returncode, 1, res.stderr)
            self.assertFalse(data["passed"])
            self.assertTrue(
                any(path.endswith("math.js") for path in data["skipped_unsupported"]),
                data["skipped_unsupported"],
            )

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
        res = self._run(["--src-dir", str(self.src_dir), "--json"])
        if _auto_multi_language_available():
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(res.stdout)
            self.assertTrue(data["passed"])
            self.assertGreaterEqual(data["total_functions_scanned"], 1)
        else:
            data = json.loads(res.stdout)
            self.assertEqual(res.returncode, 1, res.stderr)
            self.assertFalse(data["passed"])
            self.assertTrue(
                any(path.endswith("service.go") for path in data["skipped_unsupported"]),
                data["skipped_unsupported"],
            )

    def test_engine_flag_selection(self) -> None:
        """CLI honors explicit engines and fails closed when one is unavailable."""
        self._write_py("src/calc.py", "def calc(a, b):\n    return a + b\n")
        available = {
            "ast": True,
            "tree-sitter": HAS_TREE_SITTER or HAS_TREE_SITTER_LANGUAGES,
            "lizard": HAS_LIZARD,
        }
        for engine, is_available in available.items():
            res = self._run(["--src-dir", str(self.src_dir), "--engine", engine, "--json"])
            if is_available:
                self.assertEqual(res.returncode, 0, f"Engine {engine} failed: {res.stderr}")
                data = json.loads(res.stdout)
                self.assertEqual(data["engine"], engine)
                self.assertEqual(data["total_functions_scanned"], 1)
            else:
                self.assertEqual(res.returncode, 2, f"Engine {engine} should fail closed: {res.stderr}")
                self.assertIn(engine, res.stderr)

    def test_tree_sitter_requested_but_unavailable_exits_usage_error(self) -> None:
        """Requesting tree-sitter when it is not installed is a configuration error."""
        self._write_py("src/calc.py", "def calc(a, b):\n    return a + b\n")
        module = _load_checker_module()
        module._TREE_SITTER_AVAILABLE = False
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = module.main(
                ["--src-dir", str(self.src_dir), "--engine", "tree-sitter", "--json"]
            )
        self.assertEqual(exit_code, 2)
        self.assertIn("tree-sitter", stderr.getvalue())
        self.assertEqual(stdout.getvalue().strip(), "")

    def test_non_python_without_engine_is_not_silently_passed(self) -> None:
        """Non-Python files that no engine can analyze must not yield passed=True."""
        self._write_py("src/safe.py", "def safe_fn(a):\n    return a\n")
        js_file = self.work_root / "src" / "math.js"
        js_file.write_text("function add(a, b) { return a + b; }\n", encoding="utf-8")

        module = _load_checker_module()
        module._TREE_SITTER_AVAILABLE = False
        module._LIZARD_AVAILABLE = False
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = module.main(["--src-dir", str(self.src_dir), "--json"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1, stderr.getvalue())
        self.assertFalse(data["passed"])
        self.assertEqual(data["total_functions_scanned"], 1)
        self.assertEqual([fn["function"] for fn in data["functions"]], ["safe_fn"])
        self.assertTrue(
            any(path.endswith("math.js") for path in data["skipped_unsupported"]),
            data["skipped_unsupported"],
        )


if __name__ == "__main__":
    unittest.main()
