#!/usr/bin/env python3
"""Comprehensive test suite for Gate 3 verification_linter tool."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QE_AGENTS_LINTER = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "verification_linter.py"
QE_SKILLS_LINTER = ROOT / "skills" / "workflow" / "quality-engineering" / "scripts" / "verification_linter.py"

ALL_LINTER_PATHS = [QE_AGENTS_LINTER, QE_SKILLS_LINTER]


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
        self.assertEqual(len(ALL_LINTER_PATHS), 2)
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
            for flag in ("--tasks-dir", "--task", "--json", "--strict", "--min-msi", "--no-mutation", "--no-evidence", "--version"):
                self.assertIn(flag, res.stdout, f"Flag {flag} missing in {p} --help")

    def test_cli_version(self) -> None:
        for p in ALL_LINTER_PATHS:
            res = subprocess.run([sys.executable, str(p), "--version"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"--version failed for {p}: {res.stderr}")
            self.assertIn("verification_linter", res.stdout)
            self.assertIn("1.0.0", res.stdout)

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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
        """When both Section 4 tables are present and compliant, Gate 3 passes with zero errors."""
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

    def test_cli_passed_dual_table_table1_filled_table2_blank_passes(self) -> None:
        """When Table 1 is filled and Table 2 is retained in blank template state, Gate 3 passes."""
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
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

    def test_cli_passed_dual_table_table1_blank_table2_filled_passes(self) -> None:
        """When Table 1 is blank scaffolded and Table 2 is filled, Gate 3 passes."""
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
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["errors"]), 0)

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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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


if __name__ == "__main__":
    unittest.main()

