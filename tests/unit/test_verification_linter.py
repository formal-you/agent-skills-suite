#!/usr/bin/env python3
"""Comprehensive test suite for Gate 3 verification_linter tool."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QE_AGENTS_LINTER = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "verification_linter.py"
QE_SKILLS_LINTER = ROOT / "skills" / "workflow" / "quality-engineering" / "scripts" / "verification_linter.py"
QA_AGENTS_LINTER = ROOT / ".agents" / "skills" / "qa" / "scripts" / "verification_linter.py"
QA_SKILLS_LINTER = ROOT / "skills" / "workflow" / "qa" / "scripts" / "verification_linter.py"

ALL_LINTER_PATHS = [QE_AGENTS_LINTER, QE_SKILLS_LINTER, QA_AGENTS_LINTER, QA_SKILLS_LINTER]


class VerificationLinterCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.work_root = Path(self.tmpdir.name)
        self.tasks_dir = self.work_root / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = QE_AGENTS_LINTER

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _create_task(self, task_id: str, qa_content: str) -> Path:
        td = self.tasks_dir / task_id
        td.mkdir(parents=True, exist_ok=True)
        (td / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        return td

    def test_linter_files_exist_and_match(self) -> None:
        self.assertEqual(len(ALL_LINTER_PATHS), 4)
        reference_bytes = None
        for p in ALL_LINTER_PATHS:
            self.assertTrue(p.is_file(), f"Missing {p}")
            data = p.read_bytes()
            if reference_bytes is None:
                reference_bytes = data
            else:
                self.assertEqual(
                    data,
                    reference_bytes,
                    f"Byte mismatch between canonical linter and {p}",
                )

    def test_cli_help(self) -> None:
        for p in ALL_LINTER_PATHS:
            res = subprocess.run([sys.executable, str(p), "--help"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"--help failed for {p}: {res.stderr}")
            self.assertIn("Gate 3", res.stdout)
            for flag in (
                "--tasks-dir",
                "--task",
                "--json",
                "--strict",
                "--min-msi",
                "--actual-complexity",
                "--require-actual-complexity",
                "--actual-mutation",
                "--require-actual-mutation",
                "--repo-root",
                "--require-provenance",
                "--no-mutation",
                "--no-evidence",
                "--version",
            ):
                self.assertIn(flag, res.stdout, f"Flag {flag} missing in {p} --help")

    def test_cli_version(self) -> None:
        for p in ALL_LINTER_PATHS:
            res = subprocess.run([sys.executable, str(p), "--version"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"--version failed for {p}: {res.stderr}")
            self.assertIn("verification_linter", res.stdout)
            self.assertIn("1.1.0", res.stdout)

    def test_cli_unpassed_task_passes_backward_compatibility(self) -> None:
        self._create_task("task-001", """# QA Verification
- [ ] QA_PASSED
- [ ] REWORK_REQUIRED
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

    def test_cli_passed_missing_both_sections_fails(self) -> None:
        self._create_task("task-002", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("COMPLEXITY_MISSING_SECTION", codes)
        self.assertIn("QA_MISSING_MUTATION_EVIDENCE", codes)

    def test_cli_passed_compliant_passes(self) -> None:
        self._create_task("task-003", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 3 | P1, P2, P3 | TC-01, TC-02, TC-03 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

    def test_cli_passed_low_msi_fails(self) -> None:
        self._create_task("task-004", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/auth/login.py | mutmut | 10 | 7 | 3 | 0 | 0 | 70% | FAIL |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("QA_INVALID_MSI_SCORE", codes)

    def test_cli_kv_table_format_supported(self) -> None:
        self._create_task("task-005", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Target Function | V(G) Complexity | Independent Basis Paths | Mapped Test Cases | Path Coverage |
| :--- | :--- | :--- | :--- | :--- |
| handle_webhook | 2 | P1, P2 | TC-01, TC-02 | 100% |

## 4. Mutation testing and MSI audit
| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | Synthetic agent fallback |
| Total mutants generated | 6 |
| Killed mutants | 5 |
| Mutation Score Indicator (MSI) | 100.0% |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

    def test_cli_vg_exceeds_max_threshold_fails(self) -> None:
        self._create_task("task-006", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| monster_fn | 18 | P1..P18 | TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-14, TC-15, TC-16, TC-17, TC-18 | NO |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/monster.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("COMPLEXITY_EXCEEDS_MAX_THRESHOLD", codes)

    def test_cli_basis_path_insufficient_fails(self) -> None:
        self._create_task("task-007", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| route_req | 5 | P1..P5 | TC-01, TC-02 | NO |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/route.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("COMPLEXITY_BASIS_PATH_INSUFFICIENT", codes)

    def test_cli_strict_flag_promotes_warning(self) -> None:
        self._create_task("task-008", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| warning_fn | 12 | P1..P12 | TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12 | NO (Approved) |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/warn.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |
""")
        # Normal run: warning is emitted but exit code 0
        res_normal = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_normal.returncode, 0)
        data_normal = json.loads(res_normal.stdout)
        self.assertTrue(data_normal["passed"])
        self.assertEqual(len(data_normal["errors"]), 0)
        self.assertEqual(len(data_normal["warnings"]), 1)

        # Strict run: warning promoted to error, exit code 1
        res_strict = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json", "--strict"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_strict.returncode, 1)
        data_strict = json.loads(res_strict.stdout)
        self.assertFalse(data_strict["passed"])
        self.assertEqual(len(data_strict["errors"]), 1)

    def test_cli_passed_dual_table_both_compliant_passes(self) -> None:
        """When both Section 4 tables are present, populated and consistent, Gate 3 passes."""
        self._create_task("task-009", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

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
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

    def test_cli_passed_dual_table_table1_filled_table2_blank_fails(self) -> None:
        """A populated table can no longer mask a blank companion table (loophole closed)."""
        self._create_task("task-010", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

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
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("MUTATION_TABLE_INCONSISTENT", codes)

    def test_cli_passed_dual_table_table1_blank_table2_filled_fails(self) -> None:
        """A blank per-file table can no longer be masked by a filled summary table."""
        self._create_task("task-011", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

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
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("MUTATION_TABLE_INCONSISTENT", codes)

    def test_cli_dual_table_inconsistent_metrics_fails(self) -> None:
        """Two populated Section 4 tables must agree on MSI and totals."""
        self._create_task("task-016", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/login.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | mutmut |
| Total mutants generated | 10 |
| Killed mutants | 10 |
| Timed-out mutants | 0 |
| Equivalent mutants | 0 |
| Survived mutants | 0 |
| Mutation Score Indicator (MSI) | 100.0% |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("MUTATION_TABLE_INCONSISTENT", codes)

    def test_cli_per_target_missing_msi_not_masked_fails(self) -> None:
        """A per-target row without MSI fails even when the summary table is 100%."""
        self._create_task("task-017", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| login_user | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool / Recipe | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail (>=80%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/login.py | mutmut | 10 | 10 | 0 | 0 | 0 |  | PASS |

| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | mutmut |
| Total mutants generated | 10 |
| Killed mutants | 10 |
| Timed-out mutants | 0 |
| Equivalent mutants | 0 |
| Survived mutants | 0 |
| Mutation Score Indicator (MSI) | 100.0% |
""")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["passed"])
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("QA_INVALID_MSI_SCORE", codes)

    def test_cli_quality_engineering_path_ci_execution(self) -> None:
        """Verify the exact CI quality gate command using the QE linter path."""
        self._create_task("task-012", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| parse_config | 4 | P1..P4 | TC-01, TC-02, TC-03, TC-04 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/config.py | mutmut | 20 | 18 | 2 | 0 | 0 | 90% | PASS |

## 5. Execution evidence
| Field | Value |
| :--- | :--- |
| Command | pytest tests/unit/test_config.py |
| Result | 4 passed in 0.05s |
""")
        res = subprocess.run(
            [sys.executable, str(QE_AGENTS_LINTER), "--tasks-dir", str(self.tasks_dir), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"QE linter CI execution failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)
        self.assertEqual(data.get("gate"), "3")

    def test_cli_min_msi_configurable(self) -> None:
        """Verify --min-msi allows configuring the minimum acceptable MSI score."""
        self._create_task("task-013", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| compute_score | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/score.py | mutmut | 20 | 15 | 5 | 0 | 0 | 75% | FAIL |
""")
        # Default min-msi is 80: 75% should fail
        res_default = subprocess.run(
            [sys.executable, str(QE_AGENTS_LINTER), "--tasks-dir", str(self.tasks_dir), "--task", "task-013", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_default.returncode, 1)
        data_default = json.loads(res_default.stdout)
        self.assertFalse(data_default["passed"])
        self.assertIn("QA_INVALID_MSI_SCORE", [e["code"] for e in data_default["errors"]])

        # Custom min-msi=70: 75% should pass
        res_custom = subprocess.run(
            [sys.executable, str(QE_AGENTS_LINTER), "--tasks-dir", str(self.tasks_dir), "--task", "task-013", "--min-msi", "70", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_custom.returncode, 0)
        data_custom = json.loads(res_custom.stdout)
        self.assertTrue(data_custom["passed"])
        self.assertEqual(len(data_custom["errors"]), 0)

    def test_cli_no_mutation_flag(self) -> None:
        """Verify --no-mutation flag skips the Section 4 mutation testing audit."""
        self._create_task("task-014", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| legacy_fn | 2 | P1, P2 | TC-01, TC-02 | YES |
""")
        # Normal run without mutation section: fails
        res_normal = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--task", "task-014", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_normal.returncode, 1)
        self.assertIn("QA_MISSING_MUTATION_EVIDENCE", [e["code"] for e in json.loads(res_normal.stdout)["errors"]])

        # With --no-mutation: passes
        res_no_mut = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--task", "task-014", "--no-mutation", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_no_mut.returncode, 0)
        self.assertTrue(json.loads(res_no_mut.stdout)["passed"])

    def test_cli_execution_evidence_validation(self) -> None:
        """Verify Section 5 execution evidence validation and --no-evidence bypass."""
        self._create_task("task-015", """# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| audit_fn | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/audit.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |

## 5. Execution evidence
| Field | Value |
| :--- | :--- |
| Command |  |
| Result |  |
""")
        # Blank command and result fails
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--task", "task-015", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("EVIDENCE_MISSING_COMMAND", codes)
        self.assertIn("EVIDENCE_MISSING_RESULT", codes)

        # With --no-evidence: passes
        res_skip = subprocess.run(
            [sys.executable, str(self.script_path), "--tasks-dir", str(self.tasks_dir), "--task", "task-015", "--no-evidence", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_skip.returncode, 0)
        self.assertTrue(json.loads(res_skip.stdout)["passed"])


class _Gate3FixtureBase(unittest.TestCase):
    """Shared fixture helpers for the cross-validation and provenance suites."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.work_root = Path(self.tmpdir.name)
        self.tasks_dir = self.work_root / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = QE_AGENTS_LINTER

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _create_task(
        self, task_id: str, qa_content: str, contract_content: str = ""
    ) -> Path:
        td = self.tasks_dir / task_id
        td.mkdir(parents=True, exist_ok=True)
        (td / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")
        if contract_content:
            (td / "01-contract.md").write_text(contract_content, encoding="utf-8")
        return td

    def _write_actual_report(self, functions) -> Path:
        report_path = self.work_root / "actual-complexity.json"
        report_path.write_text(
            json.dumps({"functions": functions}), encoding="utf-8"
        )
        return report_path

    def _write_mutation_report(self, targets, tool="fixture", name="mutation-report.json") -> Path:
        report_path = self.work_root / name
        report_path.write_text(
            json.dumps({"tool": tool, "targets": targets}), encoding="utf-8"
        )
        return report_path

    def _run(self, *extra: str, report_path=None, mutation_report=None):
        command = [
            sys.executable,
            str(self.script_path),
            "--tasks-dir",
            str(self.tasks_dir),
            "--json",
        ]
        if report_path is not None:
            command.extend(["--actual-complexity", str(report_path)])
        if mutation_report is not None:
            command.extend(["--actual-mutation", str(mutation_report)])
        command.extend(extra)
        return subprocess.run(command, capture_output=True, text=True)

    def _write_artifact(self, rel_path: str, content: str):
        artifact_path = self.work_root / rel_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        return rel_path, digest


COMPLEXITY_CONTRACT = """---
task_id: "task-200"
title: "Cross-validation fixture"
touch_files:
  - action: modify
    path: "src/app.py"
---
# Task
"""

CORE_CONTRACT = """---
task_id: "task-201"
title: "Core profile fixture"
risk_level: core
touch_files:
  - action: modify
    path: "src/app.py"
---
# Task
"""

STANDARD_CONTRACT = """---
task_id: "task-202"
title: "Standard profile fixture"
risk_level: standard
touch_files:
  - action: modify
    path: "src/app.py"
---
# Task
"""


def _cross_check_qa(handler_rows: str = "") -> str:
    if not handler_rows:
        handler_rows = "| handler | 3 | P1, P2, P3 | TC-01, TC-02, TC-03 | YES |"
    return f"""# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
{handler_rows}

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| src/app.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |
"""


class Gate3CrossValidationTests(_Gate3FixtureBase):
    """WP-05: Gate 3 must cross-check reported V(G) against the actual AST report."""

    def test_actual_complexity_match_passes(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [{"file": "src/app.py", "line": 10, "function": "handler", "vg": 3}]
        )
        res = self._run("--require-actual-complexity", report_path=report)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["errors"], [])

    def test_backslash_and_dot_prefix_paths_normalized(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [{"file": ".\\src\\app.py", "line": 10, "function": "handler", "vg": 3}]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(json.loads(res.stdout)["passed"])

    def test_vg_mismatch_with_ast_fails(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [{"file": "src/app.py", "line": 10, "function": "handler", "vg": 5}]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        codes = [e["code"] for e in data["errors"]]
        self.assertIn("COMPLEXITY_MISMATCH_WITH_AST", codes)

    def test_basis_path_uses_actual_vg(self) -> None:
        # Reported V(G)=2 with 3 test cases would satisfy the reported value, but the
        # actual AST V(G)=5 makes the basis-path evidence insufficient.
        qa = _cross_check_qa("| handler | 2 | P1, P2 | TC-01, TC-02, TC-03 | YES |")
        self._create_task("task-200", qa, COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [{"file": "src/app.py", "line": 10, "function": "handler", "vg": 5}]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_BASIS_PATH_INSUFFICIENT", codes)

    def test_function_present_in_ast_but_missing_in_03_fails(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [
                {"file": "src/app.py", "line": 10, "function": "handler", "vg": 3},
                {"file": "src/app.py", "line": 40, "function": "validate", "vg": 2},
            ]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_FUNCTION_MISSING_IN_03", codes)

    def test_phantom_function_fails(self) -> None:
        rows = (
            "| handler | 3 | P1, P2, P3 | TC-01, TC-02, TC-03 | YES |\n"
            "| ghost_fn | 2 | P1, P2 | TC-04, TC-05 | YES |"
        )
        self._create_task("task-200", _cross_check_qa(rows), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [{"file": "src/app.py", "line": 10, "function": "handler", "vg": 3}]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_PHANTOM_FUNCTION", codes)

    def test_actual_functions_outside_touch_files_are_ignored(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self._write_actual_report(
            [
                {"file": "src/app.py", "line": 10, "function": "handler", "vg": 3},
                {"file": "src/other.py", "line": 5, "function": "unrelated", "vg": 4},
            ]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(json.loads(res.stdout)["passed"])

    def test_touch_files_unreadable_emits_warning(self) -> None:
        # No 01-contract.md: the cross-check cannot scope by touch_files.
        self._create_task("task-200", _cross_check_qa())
        report = self._write_actual_report(
            [{"file": "src/app.py", "line": 10, "function": "handler", "vg": 3}]
        )
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        warnings = json.loads(res.stdout)["warnings"]
        self.assertIn("TOUCH_FILES_UNREADABLE", [w["code"] for w in warnings])

    def test_require_actual_complexity_without_report_fails(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        res = self._run("--require-actual-complexity")
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_REPORT_MISSING", codes)

    def test_actual_complexity_report_missing_file_fails(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        missing = self.work_root / "does-not-exist.json"
        res = self._run("--require-actual-complexity", report_path=missing)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_REPORT_MISSING", codes)

    def test_actual_complexity_report_invalid_json_fails(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        report = self.work_root / "broken.json"
        report.write_text("{not json", encoding="utf-8")
        res = self._run(report_path=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("COMPLEXITY_REPORT_MISSING", codes)

    def test_without_actual_complexity_keeps_legacy_behavior(self) -> None:
        self._create_task("task-200", _cross_check_qa(), COMPLEXITY_CONTRACT)
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["errors"], [])


def _mutation_cross_check_qa(target_rows: str = "") -> str:
    if not target_rows:
        target_rows = "| src/app.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |"
    return f"""# QA Verification
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 3. Complexity and basis path coverage
| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |
| :--- | :--- | :--- | :--- | :--- |
| handler | 2 | P1, P2 | TC-01, TC-02 | YES |

## 4. Mutation testing and MSI audit
| Target Source File | Mutation Tool | Total Mutants | Killed | Survived | Timeout | Equivalent | MSI (%) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{target_rows}
"""


def _mutation_target(
    file: str = "src/app.py",
    total: int = 10,
    killed: int = 9,
    timed_out: int = 0,
    equivalent: int = 0,
    survived: int = 1,
    **extra,
):
    target = {
        "file": file,
        "total": total,
        "killed": killed,
        "timed_out": timed_out,
        "equivalent": equivalent,
        "survived": survived,
    }
    target.update(extra)
    return target


class Gate3MutationCrossValidationTests(_Gate3FixtureBase):
    """WP-06: Gate 3 cross-checks Section 4 against the normalized mutation report."""

    def test_actual_mutation_match_passes(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report([_mutation_target()])
        res = self._run("--require-actual-mutation", mutation_report=report)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["errors"], [])

    def test_aggregate_mismatch_with_report_fails(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report(
            [_mutation_target(killed=5, survived=5)]
        )
        res = self._run(mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_MISMATCH_WITH_REPORT", codes)

    def test_per_target_mismatch_with_report_fails(self) -> None:
        # Counts agree with the report but the reported per-target MSI does not.
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report([_mutation_target(msi=80)])
        res = self._run(mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_MISMATCH_WITH_REPORT", codes)

    def test_target_in_03_absent_from_report_fails(self) -> None:
        rows = (
            "| src/app.py | mutmut | 10 | 9 | 1 | 0 | 0 | 90% | PASS |\n"
            "| src/ghost.py | mutmut | 0 | 0 | 0 | 0 | 0 | 100% | PASS |"
        )
        self._create_task("task-400", _mutation_cross_check_qa(rows))
        report = self._write_mutation_report([_mutation_target()])
        res = self._run(mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_PHANTOM_TARGET", codes)

    def test_report_target_absent_from_03_fails(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report(
            [
                _mutation_target(),
                _mutation_target(
                    file="src/extra.py", total=0, killed=0, survived=0
                ),
            ]
        )
        res = self._run(mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_TARGET_MISSING_IN_03", codes)

    def test_require_actual_mutation_without_report_fails(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        res = self._run("--require-actual-mutation")
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_REPORT_MISSING", codes)

    def test_missing_mutation_report_file_fails_closed(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        missing = self.work_root / "does-not-exist-mutation.json"
        res = self._run("--require-actual-mutation", mutation_report=missing)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_REPORT_MISSING", codes)

    def test_empty_targets_report_fails_closed(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report([])
        res = self._run("--require-actual-mutation", mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_REPORT_MISSING", codes)

    def test_actual_mutation_without_require_flag_still_cross_checks(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        report = self._write_mutation_report(
            [_mutation_target(killed=5, survived=5)]
        )
        res = self._run(mutation_report=report)
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_MISMATCH_WITH_REPORT", codes)

    def test_without_actual_mutation_keeps_legacy_behavior(self) -> None:
        self._create_task("task-400", _mutation_cross_check_qa())
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["errors"], [])


class Gate3ProvenanceTests(_Gate3FixtureBase):
    """WP-08: provenance, equivalent-mutant justification and core profile."""

    def _qa(
        self,
        *,
        equivalent: str = "0",
        justification=None,
        artifact_path=None,
        artifact_sha=None,
        msi: str = "90.0%",
        include_evidence_section: bool = True,
    ) -> str:
        lines = [
            "# QA Verification",
            "- [x] QA_PASSED",
            "- [ ] REWORK_REQUIRED",
            "",
            "## 3. Complexity and basis path coverage",
            "| Function / Module | Cyclomatic Complexity V(G) | Independent Basis Paths | Test Case IDs | Compliance (<=10) |",
            "| :--- | :--- | :--- | :--- | :--- |",
            "| handler | 2 | P1, P2 | TC-01, TC-02 | YES |",
            "",
            "## 4. Mutation testing and MSI audit",
            "| Metric / Field | Value |",
            "| :--- | :--- |",
            "| Mutation tool / engine | mutmut |",
            "| Total mutants generated | 10 |",
            "| Killed mutants | 9 |",
            "| Timed-out mutants | 0 |",
            f"| Equivalent mutants | {equivalent} |",
            "| Survived mutants | 1 |",
            f"| Mutation Score Indicator (MSI) | {msi} |",
        ]
        if justification is not None:
            lines.append(f"| Equivalent mutant justification | {justification} |")
        if include_evidence_section:
            lines.extend(
                [
                    "",
                    "## 5. Execution evidence",
                    "| Field | Value |",
                    "| :--- | :--- |",
                    "| Command | pytest tests/acceptance -q |",
                    "| Result | 2 passed |",
                ]
            )
            if artifact_path is not None:
                lines.append(f"| Artifact path | {artifact_path} |")
            if artifact_sha is not None:
                lines.append(f"| Artifact SHA-256 | {artifact_sha} |")
        return "\n".join(lines) + "\n"

    def test_without_flag_provenance_is_optional_backward_compatible(self) -> None:
        self._create_task("task-300", self._qa())
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(json.loads(res.stdout)["passed"])

    def test_missing_artifact_path_fails(self) -> None:
        self._create_task("task-300", self._qa())
        res = self._run("--require-provenance")
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("EVIDENCE_MISSING_ARTIFACT", codes)

    def test_missing_artifact_file_fails(self) -> None:
        qa = self._qa(
            artifact_path="artifacts/missing-evidence.log",
            artifact_sha="0" * 64,
        )
        self._create_task("task-300", qa)
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("EVIDENCE_MISSING_ARTIFACT", codes)

    def test_artifact_hash_mismatch_fails(self) -> None:
        qa = self._qa(
            artifact_path="artifacts/qa-evidence.log",
            artifact_sha="0" * 64,
        )
        self._create_task("task-300", qa)
        self._write_artifact("artifacts/qa-evidence.log", "2 passed\n")
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("EVIDENCE_HASH_INVALID", codes)

    def test_valid_artifact_and_hash_passes(self) -> None:
        rel_path, digest = self._write_artifact("artifacts/qa-evidence.log", "2 passed\n")
        qa = self._qa(artifact_path=rel_path, artifact_sha=digest)
        self._create_task("task-300", qa)
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(json.loads(res.stdout)["passed"])

    def test_sha256_prefix_and_uppercase_hash_accepted(self) -> None:
        rel_path, digest = self._write_artifact("artifacts/qa-evidence.log", "2 passed\n")
        qa = self._qa(artifact_path=rel_path, artifact_sha="sha256:" + digest.upper())
        self._create_task("task-300", qa)
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_equivalent_mutant_requires_justification(self) -> None:
        rel_path, digest = self._write_artifact("artifacts/qa-evidence.log", "2 passed\n")
        qa = self._qa(equivalent="2", artifact_path=rel_path, artifact_sha=digest)
        self._create_task("task-300", qa)
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 1)
        codes = [e["code"] for e in json.loads(res.stdout)["errors"]]
        self.assertIn("MUTATION_EQUIVALENT_JUSTIFICATION_MISSING", codes)

    def test_equivalent_mutant_with_justification_passes(self) -> None:
        rel_path, digest = self._write_artifact("artifacts/qa-evidence.log", "2 passed\n")
        qa = self._qa(
            equivalent="2",
            justification="Both mutants only alter log message text; behavior is unchanged.",
            artifact_path=rel_path,
            artifact_sha=digest,
        )
        self._create_task("task-300", qa)
        res = self._run("--require-provenance", "--repo-root", str(self.work_root))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_core_risk_level_uses_90_percent_threshold(self) -> None:
        self._create_task("task-300", self._qa(msi="85.0%"), CORE_CONTRACT)
        res = self._run()
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        core_errors = [e for e in data["errors"] if e["code"] == "QA_INVALID_MSI_SCORE"]
        self.assertTrue(core_errors)
        lowered = core_errors[0]["message"].lower()
        self.assertIn("core", lowered)
        self.assertIn("90", core_errors[0]["message"])

    def test_standard_risk_level_uses_80_percent_threshold(self) -> None:
        self._create_task("task-300", self._qa(msi="85.0%"), STANDARD_CONTRACT)
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_core_risk_level_passes_above_90_percent(self) -> None:
        self._create_task("task-300", self._qa(msi="92.0%"), CORE_CONTRACT)
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
