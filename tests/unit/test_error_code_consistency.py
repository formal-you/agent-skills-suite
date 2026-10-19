#!/usr/bin/env python3
"""Error-code drift guard.

Every deterministic code that a linter/tool can emit must be documented, and the
documentation must not keep retired codes that no tool emits.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QE_SKILL = ROOT / ".agents" / "skills" / "quality-engineering" / "SKILL.md"
QE_TRIAGE = ROOT / ".agents" / "skills" / "quality-engineering" / "references" / "triage-routing.md"
VERIFICATION = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "verification_linter.py"
MUTATION_GATE = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "mutation_gate.py"
BRANCH_GUARD = ROOT / ".agents" / "skills" / "quality-engineering" / "scripts" / "branch_guard.py"
PLAN_SKILL = ROOT / ".agents" / "skills" / "plan-linter" / "SKILL.md"
PLAN_LINTER = ROOT / ".agents" / "skills" / "plan-linter" / "scripts" / "plan_linter.py"
GUIDE = ROOT / "docs" / "skills-guide.zh-CN.md"
CI_README = ROOT / ".agents" / "skills" / "quality-engineering" / "assets" / "templates" / "ci" / "README.md"

GATE3_CODES = {
    "COMPLEXITY_MISSING_SECTION",
    "COMPLEXITY_EXCEEDS_MAX_THRESHOLD",
    "COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD",
    "COMPLEXITY_BASIS_PATH_INSUFFICIENT",
    "COMPLEXITY_REPORT_MISSING",
    "COMPLEXITY_FUNCTION_MISSING_IN_03",
    "COMPLEXITY_MISMATCH_WITH_AST",
    "COMPLEXITY_PHANTOM_FUNCTION",
    "QA_MISSING_MUTATION_EVIDENCE",
    "QA_INVALID_MSI_SCORE",
    "MUTATION_TABLE_INCONSISTENT",
    "MUTATION_EQUIVALENT_JUSTIFICATION_MISSING",
    "MUTATION_REPORT_MISSING",
    "MUTATION_MISMATCH_WITH_REPORT",
    "MUTATION_PHANTOM_TARGET",
    "MUTATION_TARGET_MISSING_IN_03",
    "EVIDENCE_MISSING_COMMAND",
    "EVIDENCE_MISSING_RESULT",
    "EVIDENCE_MISSING_ARTIFACT",
    "EVIDENCE_HASH_INVALID",
    "TOUCH_FILES_UNREADABLE",
}

MUTATION_CODES = {
    "MUTATION_REPORT_MISSING",
    "MUTATION_REPORT_INVALID",
    "MUTATION_THRESHOLD_FAILED",
    "MUTATION_COMMAND_FAILED",
}

PLAN_BDD_CODES = {
    "MISSING_FEATURE_FILE",
    "BDD_FEATURE_FILE_EXTENSION",
    "FEATURE_FILE_OUTSIDE_ACCEPTANCE",
    "BDD_GHERKIN_BLOCK_MISSING",
    "BDD_GHERKIN_INVALID",
    "BDD_STEP_DEFINITIONS_INVALID",
}

BRANCH_CODES = {
    "BRANCH_PROTECTED",
    "BRANCH_PATTERN_INVALID",
    "BRANCH_DETACHED",
    "BRANCH_DECLARED_MISSING",
    "BRANCH_MISMATCH",
    "TASK_DOC_MISSING",
}

RETIRED_CODES = {
    "BASIS_PATH_INSUFFICIENT",
    "MUTATION_MISSING_SECTION",
    "MUTATION_NO_SCORE",
    "MUTATION_SCORE_BELOW_THRESHOLD",
    "MUTATION_SCORE_MARGINAL",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ErrorCodeConsistencyTests(unittest.TestCase):
    def test_gate3_codes_are_emitted_documented_and_routed(self) -> None:
        emitted = read(VERIFICATION)
        documented = read(QE_SKILL)
        routed = read(QE_TRIAGE)
        missing_emitted = sorted(code for code in GATE3_CODES if code not in emitted)
        missing_documented = sorted(code for code in GATE3_CODES if code not in documented)
        missing_routed = sorted(code for code in GATE3_CODES if code not in routed)
        self.assertEqual(missing_emitted, [], "codes not emitted by verification_linter.py")
        self.assertEqual(missing_documented, [], "codes missing from quality-engineering/SKILL.md")
        self.assertEqual(missing_routed, [], "codes missing from references/triage-routing.md")

    def test_mutation_gate_codes_are_emitted_and_routed(self) -> None:
        emitted = read(MUTATION_GATE)
        routed = read(QE_TRIAGE)
        missing_emitted = sorted(code for code in MUTATION_CODES if code not in emitted)
        missing_routed = sorted(code for code in MUTATION_CODES if code not in routed)
        self.assertEqual(missing_emitted, [], "codes not emitted by quality-engineering/scripts/mutation_gate.py")
        self.assertEqual(missing_routed, [], "codes missing from triage-routing.md")

    def test_retired_codes_are_not_documented(self) -> None:
        for path in (QE_SKILL, PLAN_SKILL, GUIDE, CI_README):
            text = read(path)
            for code in RETIRED_CODES:
                pattern = r"(?<![A-Z0-9_])" + re.escape(code) + r"(?![A-Z0-9_])"
                self.assertIsNone(
                    re.search(pattern, text),
                    "retired code %r still documented in %s" % (code, path),
                )

    def test_plan_gate_critical_codes_are_emitted_and_documented(self) -> None:
        emitted = read(PLAN_LINTER)
        documented = read(PLAN_SKILL)
        for code in ("BDD_MISSING_PRECONDITION", "FORBIDDEN_TOUCH_FILE", "DAG_CYCLE"):
            self.assertIn(code, emitted, "plan_linter.py does not emit " + code)
            self.assertIn(code, documented, "plan-linter/SKILL.md does not document " + code)

    def test_plan_bdd_codes_are_emitted_and_documented(self) -> None:
        emitted = read(PLAN_LINTER)
        documented = read(PLAN_SKILL)
        for code in sorted(PLAN_BDD_CODES):
            self.assertIn(code, emitted, "plan_linter.py does not emit " + code)
            self.assertIn("`" + code + "`", documented, "plan-linter/SKILL.md does not document " + code)

    def test_branch_guard_codes_are_emitted_documented_and_routed(self) -> None:
        emitted = read(BRANCH_GUARD)
        documented = read(QE_SKILL)
        routed = read(QE_TRIAGE)
        for code in sorted(BRANCH_CODES):
            self.assertIn(code, emitted, "branch_guard.py does not emit " + code)
            self.assertIn("`" + code + "`", documented, "quality-engineering/SKILL.md does not document " + code)
            self.assertIn("`" + code + "`", routed, "triage-routing.md does not route " + code)

    def test_code_tables_are_backticked(self) -> None:
        # Guard against prose mentions that accidentally look like a registry entry.
        for path in (QE_SKILL, PLAN_SKILL, QE_TRIAGE):
            text = read(path)
            for code in re.findall(r"\b[A-Z][A-Z0-9_]{4,}\b", text):
                if code in GATE3_CODES | MUTATION_CODES:
                    self.assertIn("`" + code + "`", text, "%s not backticked in %s" % (code, path))


if __name__ == "__main__":
    unittest.main()
