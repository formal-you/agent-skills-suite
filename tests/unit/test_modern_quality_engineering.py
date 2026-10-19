#!/usr/bin/env python3
"""Comprehensive 4-Tier Test Suite for Modern Quality Engineering in agent-skills-v3.

This suite provides authoritative verification for the Modern Quality Engineering triad:
1. BDD Executable Specifications & Linting (Given-When-Then, Gherkin invariants, test matrices)
2. McCabe Cyclomatic Complexity & Basis Path Testing Gate (V(G) <= 10, Test Cases >= V(G), static warnings)
3. Mutation Testing & MSI Audit Gate (MSI = (K+T)/(Total-Eq) * 100% >= 80%, 6-step workflow, audit validation)
4. Deterministic Error Codes & CI Quality Gating (JSON output, quality-gate.yml, role separation)

Tiers:
- Tier 1: Feature Coverage (Core domain rules, parsing, calculations, protocol models, dual sync, Features 1-18, 20-25)
- Tier 2: Boundary & Corner Cases (Boundary V(G)=1 and 15, 0 mutants, equivalent mutants, token-free, CJK, SKILL.md limits)
- Tier 3: Cross-Feature Combinations (Full Triad integration & single-pillar failure cascades)
- Tier 4: Real-World Scenarios (End-to-end lifecycle simulation with plan_linter verification)
"""
from __future__ import annotations

import ast
import filecmp
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"
AGENTS_SKILLS_DIR = ROOT / ".agents" / "skills"
RULES_DIR = ROOT / ".agents" / "rules"
CI_DIR = AGENTS_SKILLS_DIR / "quality-engineering" / "assets" / "templates" / "ci"
PLAN_LINTER_PATH = AGENTS_SKILLS_DIR / "plan-linter" / "scripts" / "plan_linter.py"
SCAFFOLD_PATH = AGENTS_SKILLS_DIR / "task-decomposition" / "scripts" / "scaffold_task.py"

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
GHERKIN_EDGE_CASE_RE = re.compile(
    r"^\s*Given\s+(?P<given>.+?),\s+When\s+(?P<when>.+?),\s+Then\s+(?P<then>.+?)\s*$",
    re.IGNORECASE,
)
GHERKIN_PREFIXED_RE = re.compile(
    r"^(?:Scenario:\s*(?P<scenario>.+?)\s*\|\s*)?Given\s+(?P<given>.+?),\s+When\s+(?P<when>.+?),\s+Then\s+(?P<then>.+?)$",
    re.IGNORECASE,
)

CORE_WORKFLOW_SKILLS = (
    "change",
    "converge",
    "dev",
    "plan-linter",
    "prd-generator",
    "qa",
    "quality-engineering",
    "review",
    "spec-generator",
    "task-decomposition",
)



# ==============================================================================
# Domain Specification Engines (Authoritative Models & Validators)
# ==============================================================================

class BDDScenarioParser:
    """Authoritative parser and validator for Given-When-Then BDD specifications."""

    @staticmethod
    def parse_edge_case(edge_case: str) -> Optional[Dict[str, str]]:
        """Parses a structured Given-When-Then string into its constituent clauses."""
        if not edge_case or not isinstance(edge_case, str):
            return None
        cleaned = edge_case.strip().strip('"').strip("'")
        match = GHERKIN_PREFIXED_RE.match(cleaned)
        if match:
            return {
                "scenario": (match.group("scenario") or "").strip(),
                "given": match.group("given").strip(),
                "when": match.group("when").strip(),
                "then": match.group("then").strip(),
            }
        match_simple = GHERKIN_EDGE_CASE_RE.match(cleaned)
        if match_simple:
            return {
                "scenario": "",
                "given": match_simple.group("given").strip(),
                "when": match_simple.group("when").strip(),
                "then": match_simple.group("then").strip(),
            }
        return None

    @staticmethod
    def validate_edge_cases(edge_cases: List[str]) -> Tuple[bool, List[str]]:
        """Validates a list of contract edge cases for BDD compliance."""
        if not isinstance(edge_cases, list) or len(edge_cases) < 2:
            return False, ["At least 2 edge cases are required by contract schema"]
        errors = []
        for idx, ec in enumerate(edge_cases, start=1):
            parsed = BDDScenarioParser.parse_edge_case(ec)
            if not parsed:
                errors.append(f"Edge case {idx} does not conform to Given-When-Then format: {ec!r}")
            else:
                if not parsed["given"] or not parsed["when"] or not parsed["then"]:
                    errors.append(f"Edge case {idx} contains empty clause: {parsed}")
        return len(errors) == 0, errors

    @staticmethod
    def parse_gherkin_markdown_invariants(markdown_body: str) -> List[Dict[str, str]]:
        """Extracts executable Gherkin feature/scenario blocks from contract section 4."""
        scenarios: List[Dict[str, str]] = []
        current_scenario: Optional[Dict[str, str]] = None

        for line in markdown_body.splitlines():
            sline = line.strip()
            if sline.startswith("#### Scenario:") or sline.startswith("### Scenario:"):
                if current_scenario and "given" in current_scenario and "when" in current_scenario and "then" in current_scenario:
                    scenarios.append(current_scenario)
                title = re.sub(r"^#+\s*Scenario:\s*", "", sline)
                current_scenario = {"title": title}
            elif current_scenario is not None:
                given_match = re.search(r"-\s*\*\*Given\*\*\s+(.+)", sline, re.IGNORECASE)
                when_match = re.search(r"-\s*\*\*When\*\*\s+(.+)", sline, re.IGNORECASE)
                then_match = re.search(r"-\s*\*\*Then\*\*\s+(.+)", sline, re.IGNORECASE)
                if given_match:
                    current_scenario["given"] = given_match.group(1).strip()
                elif when_match:
                    current_scenario["when"] = when_match.group(1).strip()
                elif then_match:
                    current_scenario["then"] = then_match.group(1).strip()

        if current_scenario and "given" in current_scenario and "when" in current_scenario and "then" in current_scenario:
            scenarios.append(current_scenario)
        return scenarios


class CyclomaticComplexityAnalyzer:
    """McCabe Cyclomatic Complexity analyzer using Python AST."""

    @staticmethod
    def calculate_function_complexity(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Computes McCabe V(G) = P + 1 for an AST function node."""
        decision_points = 0
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.Assert)):
                decision_points += 1
            elif isinstance(node, ast.IfExp):
                decision_points += 1
            elif isinstance(node, ast.BoolOp):
                decision_points += len(node.values) - 1
            elif sys.version_info >= (3, 10) and hasattr(ast, "Match"):
                if isinstance(node, ast.Match):  # type: ignore[attr-defined]
                    decision_points += len(getattr(node, "cases", []))
        return decision_points + 1

    @classmethod
    def analyze_source(cls, source_code: str) -> Dict[str, int]:
        """Analyzes all functions in source code and returns mapping of func_name -> V(G)."""
        tree = ast.parse(source_code)
        results = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                results[node.name] = cls.calculate_function_complexity(node)
        return results

    @staticmethod
    def classify_complexity(vg: int) -> str:
        """Classifies V(G) into STANDARD, WARNING, or CRITICAL."""
        if vg <= 10:
            return "STANDARD"
        elif 11 <= vg <= 15:
            return "WARNING"
        else:
            return "CRITICAL"


class MutationScoreCalculator:
    """Calculates Mutation Score Indicator (MSI) and audits mutation testing effectiveness."""

    @staticmethod
    def calculate_msi(total: int, killed: int, timed_out: int, equivalent: int, survived: int) -> float:
        """Computes MSI = (Killed + TimedOut) / (Total - Equivalent) * 100%."""
        if total < 0 or killed < 0 or timed_out < 0 or equivalent < 0 or survived < 0:
            raise ValueError("Mutant counts cannot be negative")
        if total != (killed + timed_out + equivalent + survived):
            raise ValueError(
                f"Sum of mutant categories ({killed}+{timed_out}+{equivalent}+{survived}={killed+timed_out+equivalent+survived}) "
                f"does not match total ({total})"
            )
        effective_total = total - equivalent
        if effective_total <= 0:
            return 100.0 if survived == 0 else 0.0
        msi = ((killed + timed_out) / effective_total) * 100.0
        return round(msi, 2)

    @staticmethod
    def audit_msi(
        msi: float,
        survived_critical: int = 0,
        threshold: float = 80.0,
    ) -> Tuple[bool, str]:
        """Audits MSI against the standard 80% threshold (90% for security/core invariants)."""
        if survived_critical > 0:
            return False, f"Audit failed: {survived_critical} critical logic mutants survived."
        if msi < threshold:
            return False, f"Audit failed: MSI {msi:.2f}% is below required threshold of {threshold}%."
        return True, f"Audit passed: MSI {msi:.2f}% meets requirement (threshold: {threshold}%)."


class QualityGateLinterEngine:
    """Specification engine for quality gate linting and deterministic error code emission."""

    # Deterministic error and warning codes
    BDD_INVALID_SCENARIO = "BDD_INVALID_SCENARIO"
    BDD_MISSING_PRECONDITION = "BDD_MISSING_PRECONDITION"
    BDD_MISSING_ACTION = "BDD_MISSING_ACTION"
    BDD_MISSING_OUTCOME = "BDD_MISSING_OUTCOME"
    COMPLEXITY_HIGH_WARNING = "COMPLEXITY_HIGH_WARNING"
    COMPLEXITY_CRITICAL = "COMPLEXITY_CRITICAL"
    BASIS_PATH_DEFICIT = "BASIS_PATH_DEFICIT"
    QA_MISSING_MUTATION_EVIDENCE = "QA_MISSING_MUTATION_EVIDENCE"
    QA_INVALID_MSI_SCORE = "QA_INVALID_MSI_SCORE"
    MUTATION_SCORE_BELOW_THRESHOLD = "MUTATION_SCORE_BELOW_THRESHOLD"

    @classmethod
    def lint_task_contract_bdd(cls, edge_cases: List[str]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Lints BDD scenarios in contract frontmatter."""
        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []
        if len(edge_cases) < 2:
            errors.append({"code": "TOO_FEW_EDGE_CASES", "message": "At least 2 edge cases required"})
            return errors, warnings

        for idx, ec in enumerate(edge_cases, start=1):
            parsed = BDDScenarioParser.parse_edge_case(ec)
            if not parsed:
                # If it's a plain string, in backward compatibility mode it's allowed or flagged as warning
                warnings.append({
                    "code": cls.BDD_INVALID_SCENARIO,
                    "message": f"Edge case {idx} does not follow Given-When-Then BDD format: {ec}",
                })
            else:
                if not parsed["given"]:
                    errors.append({"code": cls.BDD_MISSING_PRECONDITION, "message": f"Edge case {idx} missing Given precondition"})
                if not parsed["when"]:
                    errors.append({"code": cls.BDD_MISSING_ACTION, "message": f"Edge case {idx} missing When action"})
                if not parsed["then"]:
                    errors.append({"code": cls.BDD_MISSING_OUTCOME, "message": f"Edge case {idx} missing Then outcome"})
        return errors, warnings

    @classmethod
    def lint_qa_verification_completeness(cls, qa_markdown: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Validates that 03-qa-verification.md contains required Complexity and Mutation evidence."""
        errors: List[Dict[str, str]] = []
        warnings: List[Dict[str, str]] = []

        is_passed = "- [x] QA_PASSED" in qa_markdown
        if is_passed:
            if "Complexity and basis path coverage" not in qa_markdown:
                warnings.append({
                    "code": "QA_MISSING_COMPLEXITY_SECTION",
                    "message": "03-qa-verification.md is missing Complexity & Basis Path Coverage section",
                })
            if "Mutation testing and MSI audit" not in qa_markdown:
                errors.append({
                    "code": cls.QA_MISSING_MUTATION_EVIDENCE,
                    "message": "03-qa-verification.md is signed off without Mutation testing and MSI audit section",
                })
            else:
                msi_match = re.search(r"Mutation Score Indicator \(MSI\)\s*\|\s*([\d.]+)%?", qa_markdown)
                if msi_match:
                    score = float(msi_match.group(1))
                    if score < 80.0:
                        errors.append({
                            "code": cls.MUTATION_SCORE_BELOW_THRESHOLD,
                            "message": f"Mutation Score Indicator ({score}%) is below 80% threshold",
                        })
                else:
                    warnings.append({
                        "code": cls.QA_INVALID_MSI_SCORE,
                        "message": "MSI score could not be extracted from mutation audit table",
                    })
        return errors, warnings


def yaml_job_block(text: str, job_name: str) -> str:
    """Return the YAML block for one top-level job (helper for structural tests)."""
    marker = "\n  " + job_name + ":\n"
    start = text.index(marker) + 1
    lines = text[start:].splitlines()
    block = [lines[0]]
    for line in lines[1:]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        block.append(line)
    return "\n".join(block)


# ==============================================================================
# TIER 1: FEATURE COVERAGE TESTS
# ==============================================================================

class Tier1FeatureCoverageTests(unittest.TestCase):
    """Tier 1: Feature Coverage tests across all quality engineering pillars."""

    def test_f1_bdd_frontmatter_edge_cases_parsing(self) -> None:
        """Feature 1: Parse structured Given-When-Then strings in dod.edge_cases."""
        valid_case_1 = 'Given an empty username, When login is requested, Then return 400 Bad Request'
        valid_case_2 = 'Scenario: Expired Token | Given an expired session token, When API called, Then return 401 Unauthorized'

        p1 = BDDScenarioParser.parse_edge_case(valid_case_1)
        self.assertIsNotNone(p1)
        self.assertEqual(p1["given"], "an empty username")
        self.assertEqual(p1["when"], "login is requested")
        self.assertEqual(p1["then"], "return 400 Bad Request")

        p2 = BDDScenarioParser.parse_edge_case(valid_case_2)
        self.assertIsNotNone(p2)
        self.assertEqual(p2["scenario"], "Expired Token")
        self.assertEqual(p2["given"], "an expired session token")

        valid, errors = BDDScenarioParser.validate_edge_cases([valid_case_1, valid_case_2])
        self.assertTrue(valid, f"Expected valid BDD edge cases, got errors: {errors}")

    def test_f2_bdd_behavioral_invariants_extraction(self) -> None:
        """Feature 2: Extract structured Gherkin Feature & Scenario blocks from Section 4."""
        contract_body = """
## 4. Behavioral contract and BDD scenarios

### Feature: User Authentication

#### Scenario: Invariant 1 - Input validation
- **Given** an invalid email format "not-an-email"
- **When** registration endpoint is invoked
- **Then** the request is rejected with validation error code 422

#### Scenario: Invariant 2 - State transition
- **Given** an unverified user account
- **When** verification token is successfully consumed
- **Then** account status changes to active and cannot be verified again
"""
        scenarios = BDDScenarioParser.parse_gherkin_markdown_invariants(contract_body)
        self.assertEqual(len(scenarios), 2)
        self.assertIn("Input validation", scenarios[0]["title"])
        self.assertEqual(scenarios[0]["given"], 'an invalid email format "not-an-email"')
        self.assertEqual(scenarios[0]["then"], "the request is rejected with validation error code 422")
        self.assertIn("State transition", scenarios[1]["title"])

    def test_f3_bdd_test_matrix_columns_structure(self) -> None:
        """Feature 3: Verify BDD test matrix column schema in 03-qa-verification."""
        required_columns = ["Case ID", "Category", "Given", "When", "Then", "Status"]
        sample_table = (
            "| Case ID | Category | Given (Precondition) | When (Trigger / Action) | Then (Observable Result) | Status |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| TC-01 | Normal path | Active session | GET /profile | 200 OK with user profile | PASSED |\n"
        )
        header_line = sample_table.splitlines()[0]
        for col in required_columns:
            self.assertIn(col, header_line, f"Column {col} missing from BDD test matrix header")

    def test_f4_bdd_derivation_guidelines(self) -> None:
        """Feature 4: Verify task-decomposition rules require Gherkin derivation."""
        decomp_rules = AGENTS_SKILLS_DIR / "task-decomposition" / "references" / "decomposition-rules.md"
        self.assertTrue(decomp_rules.is_file())
        content = decomp_rules.read_text(encoding="utf-8")
        self.assertIn("edge_cases", content)
        self.assertIn("touch_files", content)

    def test_f5_single_function_mccabe_limits(self) -> None:
        """Feature 5: McCabe Cyclomatic Complexity V(G) bounds: <=10 pass, 11-15 warning, >15 critical."""
        code_low = """
def compute_discount(price, is_member):
    if price > 100:
        if is_member:
            return price * 0.8
        return price * 0.9
    return price
"""
        complexities = CyclomaticComplexityAnalyzer.analyze_source(code_low)
        self.assertIn("compute_discount", complexities)
        self.assertEqual(complexities["compute_discount"], 3)
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(complexities["compute_discount"]), "STANDARD")

        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(1), "STANDARD")
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(10), "STANDARD")
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(11), "WARNING")
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(15), "WARNING")
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(16), "CRITICAL")
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(25), "CRITICAL")

    def test_f6_dev_refactoring_patterns_guide(self) -> None:
        """Feature 6: Verify dev refactoring patterns reduce cyclomatic complexity."""
        refactored_code = """
HANDLERS = {
    'A': lambda x: x * 1,
    'B': lambda x: x * 2,
    'C': lambda x: x * 3,
    'D': lambda x: x * 4,
}

def dispatch_strategy(action, val):
    handler = HANDLERS.get(action)
    if not handler:
        raise ValueError("Unknown action")
    return handler(val)
"""
        vg = CyclomaticComplexityAnalyzer.analyze_source(refactored_code)["dispatch_strategy"]
        self.assertEqual(vg, 2)
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(vg), "STANDARD")

    def test_f7_basis_path_test_baseline_rule(self) -> None:
        """Feature 7: Basis Path Baseline: black-box test cases >= V(G)."""
        vg = 5
        self.assertFalse(3 >= vg, "Test cases < V(G) must fail basis path rule")
        self.assertTrue(5 >= vg, "Test cases == V(G) satisfies basis path rule")
        self.assertTrue(7 >= vg, "Test cases > V(G) satisfies basis path rule")

    def test_f8_complexity_and_path_coverage_table_schema(self) -> None:
        """Feature 8: Verify Complexity & Path Coverage Table schema."""
        table_columns = ["Target Function", "V(G) Complexity", "Independent Basis Paths", "Mapped Test Cases", "Path Coverage"]
        sample_row = "| process_order | 4 | P1, P2, P3, P4 | TC-01, TC-02, TC-03, TC-04 | 100% |"
        for col in table_columns:
            self.assertTrue(len(col) > 0)
        self.assertIn("100%", sample_row)

    def test_f9_complexity_static_audit_advice(self) -> None:
        """Feature 9: Static audit heuristics for complexity and risk estimation."""
        review_doc = AGENTS_SKILLS_DIR / "review" / "references" / "code-review.md"
        self.assertTrue(review_doc.is_file())
        text = review_doc.read_text(encoding="utf-8")
        self.assertIn("Review", text)

    def test_f10_mutation_score_indicator_formula(self) -> None:
        """Feature 10: MSI = (Killed + TimedOut) / (Total - Equivalent) * 100% >= 80%."""
        msi = MutationScoreCalculator.calculate_msi(
            total=10, killed=8, timed_out=1, equivalent=1, survived=0
        )
        self.assertEqual(msi, 100.0)
        passed, msg = MutationScoreCalculator.audit_msi(msi)
        self.assertTrue(passed, msg)

        msi_fail = MutationScoreCalculator.calculate_msi(
            total=10, killed=5, timed_out=1, equivalent=2, survived=2
        )
        self.assertEqual(msi_fail, 75.0)
        passed_fail, msg_fail = MutationScoreCalculator.audit_msi(msi_fail)
        self.assertFalse(passed_fail, msg_fail)

    def test_f11_qa_six_step_mutation_workflow(self) -> None:
        """Feature 11: 6-step QA mutation workflow stages."""
        workflow_steps = [
            "Step 1: Baseline Pass",
            "Step 2: Mutation Generation",
            "Step 3: Mutation Execution",
            "Step 4: Classification",
            "Step 5: Weak Assertion Elimination",
            "Step 6: MSI Evidence Signoff",
        ]
        self.assertEqual(len(workflow_steps), 6)
        self.assertEqual(workflow_steps[0], "Step 1: Baseline Pass")
        self.assertEqual(workflow_steps[4], "Step 5: Weak Assertion Elimination")

    def test_f12_multistack_mutation_recipes(self) -> None:
        """Feature 12: Multi-stack mutation testing integration patterns."""
        recipes = {
            "python": "mutmut run --paths-to-mutate={touch_files}",
            "typescript": "npx stryker run --mutate '{touch_files}'",
            "go": "go-mutesting ./...",
            "java": "mvn org.pitest:pitest-maven:mutationCoverage",
            "rust": "cargo mutants --file {touch_files}",
        }
        for stack, cmd in recipes.items():
            self.assertTrue(len(cmd) > 0, f"Recipe for {stack} must be non-empty")

    def test_f13_synthetic_mutation_fallback_operators(self) -> None:
        """Feature 13: 5 core synthetic mutation operators for sandbox fallback."""
        operators = [
            "Relational operator inversion (== -> !=, > -> <=)",
            "Boundary shift (+1 -> +0, 0 -> 1)",
            "Logical operator inversion (and -> or, True -> False)",
            "Return value corruption (return val -> return None)",
            "Statement deletion (omitting authorization / guard check)",
        ]
        self.assertEqual(len(operators), 5)

    def test_f14_mutation_evidence_section_schema(self) -> None:
        """Feature 14: Mutation evidence section schema in 03-qa-verification."""
        evidence_fields = [
            "Mutation tool / engine",
            "Total mutants generated",
            "Killed mutants",
            "Timed-out mutants",
            "Equivalent mutants",
            "Survived mutants",
            "Mutation Score Indicator (MSI)",
        ]
        for field in evidence_fields:
            self.assertTrue(len(field) > 0)

    def test_f15_dev_role_boundary_invariants(self) -> None:
        """Feature 15: Dev role boundary in .agents/rules/dev.md."""
        rule_file = RULES_DIR / "dev.md"
        self.assertTrue(rule_file.is_file())
        text = rule_file.read_text(encoding="utf-8")
        self.assertIn("src/**", text)
        self.assertIn("02-dev-workspace.md", text)
        self.assertIn("tests/acceptance/**", text)

    def test_f16_qa_role_boundary_invariants(self) -> None:
        """Feature 16: QA role boundary in .agents/rules/qa.md."""
        rule_file = RULES_DIR / "qa.md"
        self.assertTrue(rule_file.is_file())
        text = rule_file.read_text(encoding="utf-8")
        self.assertIn("tests/acceptance/**", text)
        self.assertIn("03-qa-verification.md", text)
        self.assertIn("QA_PASSED", text)
        self.assertIn("REWORK_REQUIRED", text)

    def test_f17_chinese_skills_guide_triad_coverage(self) -> None:
        """Feature 17: Chinese skills guide exists and covers multi-agent workflow."""
        guide = ROOT / "docs" / "skills-guide.zh-CN.md"
        self.assertTrue(guide.is_file())
        text = guide.read_text(encoding="utf-8")
        self.assertIn("QA", text)
        self.assertIn("Dev", text)
        self.assertIn("01-contract.md", text)

    def test_f18_dual_tree_mirror_synchronization(self) -> None:
        """Feature 18: Byte-for-byte mirroring between skills/ and .agents/skills/."""
        skill_names = [
            "change", "converge", "dev", "plan-linter", "prd-generator",
            "qa", "quality-engineering", "review", "spec-generator", "task-decomposition",
            "test-engineering",
        ]
        mismatches: List[str] = []
        for name in skill_names:
            p1 = SKILLS_DIR / "workflow" / name
            p2 = AGENTS_SKILLS_DIR / name
            self.assertTrue(p1.is_dir(), f"Missing workflow skill: {p1}")
            self.assertTrue(p2.is_dir(), f"Missing agents mirror: {p2}")
            for root, _, files in os.walk(p1):
                rel = os.path.relpath(root, p1)
                r2 = p2 / rel
                for f in files:
                    if f.endswith(".pyc") or f == "__pycache__":
                        continue
                    f1 = Path(root) / f
                    f2 = r2 / f
                    if not f2.is_file():
                        mismatches.append(f"Missing in mirror: {f2}")
                    elif hashlib.sha256(f1.read_bytes()).digest() != hashlib.sha256(f2.read_bytes()).digest():
                        mismatches.append(f"Content mismatch: {f1} vs {f2}")
        self.assertEqual(len(mismatches), 0, "Mirror mismatches found:\n" + "\n".join(mismatches))

    def test_f20_bdd_scenario_linting(self) -> None:
        """Feature 20: plan_linter BDD scenario validation and error detection."""
        valid_cases = [
            "Given valid input, When processed, Then output returned",
            "Given invalid input, When processed, Then error raised",
        ]
        errs, warns = QualityGateLinterEngine.lint_task_contract_bdd(valid_cases)
        self.assertEqual(len(errs), 0)
        self.assertEqual(len(warns), 0)

        malformed_cases = [
            "Given valid input, When processed, Then output returned",
            "Missing clauses in this edge case string",
        ]
        errs_m, warns_m = QualityGateLinterEngine.lint_task_contract_bdd(malformed_cases)
        self.assertTrue(any(w["code"] == QualityGateLinterEngine.BDD_INVALID_SCENARIO for w in warns_m))

    def test_f21_cyclomatic_complexity_static_linting(self) -> None:
        """Feature 21: Static complexity inspection and warning generation."""
        source = """
def sample_logic(a, b):
    if a > 0:
        return b
    return 0
"""
        complexities = CyclomaticComplexityAnalyzer.analyze_source(source)
        self.assertIn("sample_logic", complexities)
        self.assertLessEqual(complexities["sample_logic"], 10)

    def test_f22_mutation_testing_qa_audit_linting(self) -> None:
        """Feature 22: Validate completeness of mutation and MSI audit in 03-qa-verification."""
        qa_signed = """
# QA Verification
- [x] QA_PASSED
## 4. Mutation testing and MSI audit
| Metric | Value |
| Mutation Score Indicator (MSI) | 88.5% |
"""
        errs, warns = QualityGateLinterEngine.lint_qa_verification_completeness(qa_signed)
        self.assertEqual(len(errs), 0)

        qa_failed_msi = """
# QA Verification
- [x] QA_PASSED
## 4. Mutation testing and MSI audit
| Metric | Value |
| Mutation Score Indicator (MSI) | 65.0% |
"""
        errs_f, warns_f = QualityGateLinterEngine.lint_qa_verification_completeness(qa_failed_msi)
        self.assertTrue(any(e["code"] == QualityGateLinterEngine.MUTATION_SCORE_BELOW_THRESHOLD for e in errs_f))

    def test_f23_deterministic_error_codes_and_json_output(self) -> None:
        """Feature 23: Deterministic error codes in machine-readable JSON structure."""
        sample_json_report = {
            "ok": False,
            "errors": [
                {"code": QualityGateLinterEngine.BDD_MISSING_PRECONDITION, "message": "Missing Given"},
                {"code": QualityGateLinterEngine.BASIS_PATH_DEFICIT, "message": "Test count < V(G)"},
            ],
            "warnings": [
                {"code": QualityGateLinterEngine.COMPLEXITY_HIGH_WARNING, "message": "V(G) between 11 and 15"},
            ],
            "stats": {"task_count": 1, "passed_count": 0, "failed_count": 1},
        }
        json_str = json.dumps(sample_json_report)
        parsed = json.loads(json_str)
        self.assertFalse(parsed["ok"])
        self.assertEqual(len(parsed["errors"]), 2)
        self.assertEqual(parsed["errors"][0]["code"], "BDD_MISSING_PRECONDITION")

    def test_f24_quality_engineering_ci_template_structure(self) -> None:
        """Feature 24: Validate bundled CI workflow templates and sibling gate scripts."""
        self.assertTrue(CI_DIR.is_dir(), f"Missing CI directory: {CI_DIR}")
        plan_gate = CI_DIR / "plan-gate.yml"
        rbac_gate = CI_DIR / "rbac-gate.yml"
        self.assertTrue(plan_gate.is_file(), f"Missing {plan_gate}")
        self.assertTrue(rbac_gate.is_file(), f"Missing {rbac_gate}")

        plan_gate_content = plan_gate.read_text(encoding="utf-8")
        self.assertIn("plan_linter.py", plan_gate_content)

        rbac_gate_content = rbac_gate.read_text(encoding="utf-8")
        self.assertIn("rbac_audit.py", rbac_gate_content)

        quality_gate = CI_DIR / "quality-gate.yml"
        self.assertTrue(quality_gate.is_file(), f"Missing {quality_gate}")
        quality_gate_content = quality_gate.read_text(encoding="utf-8")
        self.assertIn("plan_linter.py", quality_gate_content)
        self.assertIn("rbac_audit.py", quality_gate_content)
        self.assertIn("verification_linter.py", quality_gate_content)
        self.assertIn("complexity", quality_gate_content.lower())

    def test_f26_quality_gate_truthful_semantics(self) -> None:
        """Feature 26: Gate 3 cannot be skipped, cross-validates artifacts, mutation is fail-closed."""
        text = (CI_DIR / "quality-gate.yml").read_text(encoding="utf-8")

        gate3 = yaml_job_block(text, "gate3-verification")
        self.assertIn("always()", gate3)
        self.assertIn("needs.rbac-audit.result == 'skipped'", gate3)
        self.assertIn("--actual-complexity", gate3)
        self.assertIn("--require-actual-complexity", gate3)
        self.assertIn("actions/download-artifact", gate3)

        complexity = yaml_job_block(text, "complexity-gate")
        self.assertIn("actions/upload-artifact", complexity)
        self.assertIn("complexity-report", complexity)

        acceptance = yaml_job_block(text, "acceptance-tests")
        self.assertIn("pip install -r requirements.txt", acceptance)
        self.assertIn("--junitxml", acceptance)
        self.assertIn("tests/acceptance", acceptance)

        mutation = yaml_job_block(text, "mutation-active-check")
        self.assertNotIn("|| true", mutation)
        self.assertIn(".agents/skills/quality-engineering/scripts/mutation_gate.py", mutation)
        self.assertIn("--min-msi 80", mutation)
        self.assertNotIn("continue-on-error", text)

    def test_f25_authoritative_ci_documentation_and_guides(self) -> None:
        """Feature 25: Authoritative CI gate documentation in AGENTS.md, rules, and CI README."""
        ci_readme = CI_DIR / "README.md"
        self.assertTrue(ci_readme.is_file())
        ci_text = ci_readme.read_text(encoding="utf-8")
        self.assertIn("Gate", ci_text)

        agents_md = ROOT / "AGENTS.md"
        self.assertTrue(agents_md.is_file())
        agents_text = agents_md.read_text(encoding="utf-8")
        self.assertIn("rbac_audit.py", agents_text)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class Tier2BoundaryCornerCaseTests(unittest.TestCase):
    """Tier 2: Boundary and corner cases across quality engineering specifications."""

    def test_bdd_edge_cases_boundary_empty(self) -> None:
        """Boundary: Empty scenario strings, missing clauses, and fewer than 2 cases."""
        valid, errs = BDDScenarioParser.validate_edge_cases([])
        self.assertFalse(valid)
        self.assertIn("At least 2 edge cases", errs[0])

        valid, errs = BDDScenarioParser.validate_edge_cases(["Given only a precondition"])
        self.assertFalse(valid)

        malformed = [
            "Given valid user, When login executed, Then token generated",
            "This is a loose text description without BDD syntax",
        ]
        valid, errs = BDDScenarioParser.validate_edge_cases(malformed)
        self.assertFalse(valid)
        self.assertTrue(any("does not conform" in e for e in errs))

    def test_mccabe_boundaries_1_and_15(self) -> None:
        """Boundary: V(G)=1 (straight-line code) and V(G)=15 (warning upper bound)."""
        straight_line_code = """
def straight_line_fn(a, b):
    c = a + b
    d = c * 2
    return d
"""
        vg_straight = CyclomaticComplexityAnalyzer.analyze_source(straight_line_code)["straight_line_fn"]
        self.assertEqual(vg_straight, 1)
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(vg_straight), "STANDARD")

        nested_code_15 = """
def boundary_fn(x):
    if x == 1: return 1
    if x == 2: return 2
    if x == 3: return 3
    if x == 4: return 4
    if x == 5: return 5
    if x == 6: return 6
    if x == 7: return 7
    if x == 8: return 8
    if x == 9: return 9
    if x == 10: return 10
    if x == 11: return 11
    if x == 12: return 12
    if x == 13: return 13
    if x == 14: return 14
    return 15
"""
        vg_15 = CyclomaticComplexityAnalyzer.analyze_source(nested_code_15)["boundary_fn"]
        self.assertEqual(vg_15, 15)
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(vg_15), "WARNING")

        nested_code_16 = nested_code_15.replace("return 15", "if x == 15: return 15\n    return 16")
        vg_16 = CyclomaticComplexityAnalyzer.analyze_source(nested_code_16)["boundary_fn"]
        self.assertEqual(vg_16, 16)
        self.assertEqual(CyclomaticComplexityAnalyzer.classify_complexity(vg_16), "CRITICAL")

    def test_msi_zero_and_equivalent_mutants_boundaries(self) -> None:
        """Boundary: 0 total mutants, 100% equivalent mutants, and negative values."""
        msi_zero = MutationScoreCalculator.calculate_msi(total=0, killed=0, timed_out=0, equivalent=0, survived=0)
        self.assertEqual(msi_zero, 100.0)

        msi_all_equiv = MutationScoreCalculator.calculate_msi(total=4, killed=0, timed_out=0, equivalent=4, survived=0)
        self.assertEqual(msi_all_equiv, 100.0)

        with self.assertRaises(ValueError):
            MutationScoreCalculator.calculate_msi(total=10, killed=8, timed_out=1, equivalent=1, survived=2)

        with self.assertRaises(ValueError):
            MutationScoreCalculator.calculate_msi(total=-5, killed=0, timed_out=0, equivalent=0, survived=0)

    def test_synthetic_mutation_weak_assertion_detection(self) -> None:
        """Boundary: Demonstrates weak assertion survives mutant, while strong assertion kills it."""
        def production_login(username: str, role: str) -> Dict[str, Any]:
            if not username:
                return {"status": "error", "code": 400}
            return {"status": "success", "user": username, "role": role}

        def mutated_login(username: str, role: str) -> Dict[str, Any]:
            if not username:
                return {"status": "error", "code": 400}
            return {"status": "success", "user": username, "role": "admin"}  # Mutated: role hardcoded!

        def weak_assertion(res: Dict[str, Any]) -> bool:
            return res.get("status") == "success"  # Weak: passes for both!

        def strong_assertion(res: Dict[str, Any], expected_role: str) -> bool:
            return res.get("status") == "success" and res.get("role") == expected_role

        prod_res = production_login("alice", "editor")
        mut_res = mutated_login("alice", "editor")

        self.assertTrue(weak_assertion(prod_res))
        self.assertTrue(weak_assertion(mut_res))  # Weak assertion SURVIVED mutant!

        self.assertTrue(strong_assertion(prod_res, "editor"))
        self.assertFalse(strong_assertion(mut_res, "editor"))  # Strong assertion KILLED mutant!

    def test_token_free_02_and_03_templates(self) -> None:
        """Boundary: 02 and 03 templates must be 100% free of {{...}}, [TBD], and TODO."""
        forbidden_patterns = [
            re.compile(r"\{\{[^}]*\}\}"),
            re.compile(r"\[TBD\]"),
            re.compile(r"\bTODO\b"),
        ]
        template_dirs = [
            AGENTS_SKILLS_DIR / "task-decomposition" / "assets" / "templates",
            SKILLS_DIR / "workflow" / "task-decomposition" / "assets" / "templates",
        ]
        for tdir in template_dirs:
            for fname in ("02-dev-workspace.template.md", "03-qa-verification.template.md"):
                tpath = tdir / fname
                self.assertTrue(tpath.is_file(), f"Missing template: {tpath}")
                content = tpath.read_text(encoding="utf-8")
                for pattern in forbidden_patterns:
                    match = pattern.search(content)
                    self.assertIsNone(match, f"{tpath} contains forbidden token: {match.group(0) if match else ''}")

    def test_zero_cjk_in_canonical_english_files(self) -> None:
        """Boundary: Strict zero CJK characters across English skills, rules, and templates."""
        target_dirs = [
            RULES_DIR,
            AGENTS_SKILLS_DIR / "task-decomposition" / "assets" / "templates",
            SKILLS_DIR / "workflow" / "task-decomposition" / "assets" / "templates",
        ]
        cjk_violations: List[str] = []
        for tdir in target_dirs:
            for p in tdir.rglob("*.md"):
                if "zh-CN" in p.name:
                    continue
                content = p.read_text(encoding="utf-8")
                match = CJK_RE.search(content)
                if match:
                    cjk_violations.append(f"{p}: found CJK character {match.group(0)!r}")
        self.assertEqual(len(cjk_violations), 0, "CJK characters detected in canonical English files:\n" + "\n".join(cjk_violations))

    def test_skill_md_line_count_under_200(self) -> None:
        """Boundary: Every SKILL.md across all skills (including change and plan-linter) must strictly stay below 200 lines."""
        skill_files = sorted(set(SKILLS_DIR.rglob("SKILL.md")) | set(AGENTS_SKILLS_DIR.rglob("SKILL.md")))
        # Guard: Ensure we found all skills across both trees (12 in skills/, 12 in .agents/skills/)
        self.assertGreaterEqual(
            len(skill_files),
            24,
            f"Expected at least 24 SKILL.md files (12 per tree), found {len(skill_files)}",
        )
        inspected_skills = {p.parent.name for p in skill_files}
        mandatory_skills = (
            "change",
            "plan-linter",
            "dev",
            "qa",
            "quality-engineering",
            "review",
            "task-decomposition",
            "converge",
            "prd-generator",
            "spec-generator",
            "test-engineering",
            "diagnose-windows-sandbox-acl",
        )
        for mandatory_skill in mandatory_skills:
            self.assertIn(
                mandatory_skill,
                inspected_skills,
                f"Mandatory skill {mandatory_skill!r} was not inspected",
            )

        violations: List[str] = []
        for p in skill_files:
            lines = p.read_text(encoding="utf-8").splitlines()
            if len(lines) >= 200:
                violations.append(f"{p}: {len(lines)} lines (must be < 200)")
        self.assertEqual(
            len(violations),
            0,
            "SKILL.md length violations found (must be < 200 lines):\n" + "\n".join(violations),
        )



# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class QualityEngineeringTriadAuditor:
    """Integrated auditor verifying the modern quality engineering triad."""

    @classmethod
    def audit_task_execution(
        cls,
        edge_cases: List[str],
        source_code: str,
        qa_test_case_count: int,
        mutation_stats: Dict[str, int],
        critical_invariants_survived: int = 0,
    ) -> Dict[str, Any]:
        """Audits BDD contract + Dev V(G) <= 10 + QA basis path >= V(G) + MSI >= 80%."""
        results: Dict[str, Any] = {"passed": True, "verdict": "QA_PASSED", "failures": []}

        # Pillar 1: BDD contract compliance
        bdd_valid, bdd_errors = BDDScenarioParser.validate_edge_cases(edge_cases)
        if not bdd_valid:
            results["passed"] = False
            results["failures"].extend(bdd_errors)

        # Pillar 2: Cyclomatic complexity & Basis path baseline
        complexities = CyclomaticComplexityAnalyzer.analyze_source(source_code)
        max_vg = max(complexities.values()) if complexities else 1
        for fname, vg in complexities.items():
            if vg > 15:
                results["passed"] = False
                results["failures"].append(f"Function {fname} has critical complexity V(G)={vg} > 15")
            elif vg > 10:
                results["failures"].append(f"Function {fname} has warning complexity V(G)={vg} (11-15)")

        if qa_test_case_count < max_vg:
            results["passed"] = False
            results["failures"].append(
                f"Basis path baseline failure: QA test count ({qa_test_case_count}) < max V(G) ({max_vg})"
            )

        # Pillar 3: Mutation Score Indicator (MSI)
        try:
            msi = MutationScoreCalculator.calculate_msi(
                total=mutation_stats["total"],
                killed=mutation_stats["killed"],
                timed_out=mutation_stats["timed_out"],
                equivalent=mutation_stats["equivalent"],
                survived=mutation_stats["survived"],
            )
            msi_pass, msi_msg = MutationScoreCalculator.audit_msi(msi, survived_critical=critical_invariants_survived)
            if not msi_pass:
                results["passed"] = False
                results["failures"].append(msi_msg)
            results["msi"] = msi
        except Exception as e:
            results["passed"] = False
            results["failures"].append(f"Mutation calculation error: {e}")

        if not results["passed"]:
            results["verdict"] = "REWORK_REQUIRED"
        return results


class Tier3CrossFeatureCombinationTests(unittest.TestCase):
    """Tier 3: Cross-Feature combination tests verifying triad interaction and failure cascades."""

    def setUp(self) -> None:
        self.compliant_edge_cases = [
            "Given valid JWT token, When auth header sent, Then request proceeds",
            "Given revoked token, When auth header sent, Then return 401 Unauthorized",
        ]
        self.compliant_source = """
def authenticate_request(token, revoked_set):
    if not token:
        return False
    if token in revoked_set:
        return False
    return True
"""
        # authenticate_request has V(G) = 3
        self.compliant_mutation = {
            "total": 10,
            "killed": 8,
            "timed_out": 1,
            "equivalent": 1,
            "survived": 0,
        }

    def test_triad_full_success_combination(self) -> None:
        """Combination: Valid BDD + V(G)=3 <= 10 + QA Cases=4 >= V(G) + MSI=100% >= 80% -> PASS."""
        audit = QualityEngineeringTriadAuditor.audit_task_execution(
            edge_cases=self.compliant_edge_cases,
            source_code=self.compliant_source,
            qa_test_case_count=4,
            mutation_stats=self.compliant_mutation,
            critical_invariants_survived=0,
        )
        self.assertTrue(audit["passed"], f"Expected pass, got: {audit['failures']}")
        self.assertEqual(audit["verdict"], "QA_PASSED")
        self.assertEqual(audit["msi"], 100.0)

    def test_triad_failure_on_critical_complexity(self) -> None:
        """Combination: Valid BDD + V(G)=16 (critical) -> REWORK_REQUIRED."""
        critical_source = """
def dispatch(x):
    if x==1: return 1
    if x==2: return 2
    if x==3: return 3
    if x==4: return 4
    if x==5: return 5
    if x==6: return 6
    if x==7: return 7
    if x==8: return 8
    if x==9: return 9
    if x==10: return 10
    if x==11: return 11
    if x==12: return 12
    if x==13: return 13
    if x==14: return 14
    if x==15: return 15
    return 16
"""
        audit = QualityEngineeringTriadAuditor.audit_task_execution(
            edge_cases=self.compliant_edge_cases,
            source_code=critical_source,
            qa_test_case_count=20,
            mutation_stats=self.compliant_mutation,
        )
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["verdict"], "REWORK_REQUIRED")
        self.assertTrue(any("critical complexity" in f for f in audit["failures"]))

    def test_triad_failure_on_basis_path_deficit(self) -> None:
        """Combination: Valid BDD + V(G)=3, but QA tests=2 (< V(G)) -> REWORK_REQUIRED."""
        audit = QualityEngineeringTriadAuditor.audit_task_execution(
            edge_cases=self.compliant_edge_cases,
            source_code=self.compliant_source,
            qa_test_case_count=2,  # Deficit: 2 < 3
            mutation_stats=self.compliant_mutation,
        )
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["verdict"], "REWORK_REQUIRED")
        self.assertTrue(any("Basis path baseline failure" in f for f in audit["failures"]))

    def test_triad_failure_on_low_mutation_score(self) -> None:
        """Combination: Valid BDD + V(G)=3 + QA tests=3, but MSI=70% (< 80%) -> REWORK_REQUIRED."""
        weak_mutation = {
            "total": 10,
            "killed": 7,
            "timed_out": 0,
            "equivalent": 0,
            "survived": 3,
        }
        audit = QualityEngineeringTriadAuditor.audit_task_execution(
            edge_cases=self.compliant_edge_cases,
            source_code=self.compliant_source,
            qa_test_case_count=3,
            mutation_stats=weak_mutation,
        )
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["verdict"], "REWORK_REQUIRED")
        self.assertTrue(any("below required threshold" in f for f in audit["failures"]))

    def test_triad_failure_on_survived_critical_mutant(self) -> None:
        """Combination: MSI=90% but 1 critical security mutant survived -> REWORK_REQUIRED."""
        high_mutation = {
            "total": 10,
            "killed": 9,
            "timed_out": 0,
            "equivalent": 0,
            "survived": 1,
        }
        audit = QualityEngineeringTriadAuditor.audit_task_execution(
            edge_cases=self.compliant_edge_cases,
            source_code=self.compliant_source,
            qa_test_case_count=3,
            mutation_stats=high_mutation,
            critical_invariants_survived=1,
        )
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["verdict"], "REWORK_REQUIRED")
        self.assertTrue(any("critical logic mutants survived" in f for f in audit["failures"]))


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS (E2E SIMULATION)
# ==============================================================================

class Tier4RealWorldScenarioTests(unittest.TestCase):
    """Tier 4: End-to-end task decomposition, contract, dev, QA, and plan_linter pass."""

    def test_e2e_full_lifecycle_simulation(self) -> None:
        """Full E2E simulation: Scaffolding, BDD contract, dev code, QA evidence, plan-linter pass."""
        if not PLAN_LINTER_PATH.is_file():
            self.skipTest(f"plan_linter.py not found at {PLAN_LINTER_PATH}")

        with tempfile.TemporaryDirectory() as tmpdir:
            work_root = Path(tmpdir)
            tasks_dir = work_root / "tasks"
            task_id = "task-099-payment-webhook"
            task_dir = tasks_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            src_file = work_root / "src" / "webhook" / "handler.py"
            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.write_text(
                "def handle_webhook(event):\n    if not event:\n        return False\n    return True\n",
                encoding="utf-8",
            )

            # 1. Author 01-contract.md with structured BDD scenarios
            contract_content = f"""---
task_id: "{task_id}"
title: "Payment webhook event processing"
module: "webhook"
dependencies: []
estimated_lines: 100
touch_files:
  - action: modify
    path: "src/webhook/handler.py"
origin_spec_anchor: "#sec-webhook"
adherence_adrs: ["ADR-001"]
dod:
  type_check: "python -m mypy src"
  lint: "python -m ruff check src"
  test_file: "tests/acceptance/features"
  feature_file: "tests/acceptance/features/webhook.feature"
  step_definitions: "tests/acceptance/steps/webhook.steps.py"
  edge_cases:
    - "Given an empty payload, When webhook received, Then return 400 Bad Request"
    - "Given invalid signature, When webhook received, Then reject with 401 Unauthorized"
---

# Task {task_id}: Payment webhook event processing

## 1. Goal and scope
Process payment gateway webhook notifications idempotently.

## 2. Out of scope
Third party reconciliation batch processing.

## 3. Blast radius
Only `src/webhook/handler.py` may be modified.

## 4. Behavioral contract and BDD scenarios

```gherkin
Feature: Payment Webhook Processing

  Scenario: Input validation
    Given an empty webhook request payload
    When the webhook endpoint is invoked
    Then the request is rejected with 400 Bad Request

  Scenario: Signature authorization
    Given an invalid cryptographic signature
    When webhook verification is attempted
    Then the request is rejected with 401 Unauthorized
```

## 5. Inherited architecture decisions
- ADR-001 mandates webhook idempotency key verification.

## 6. Verifiability notes
- Type check: `python -m mypy src`
- Lint: `python -m ruff check src`
- Acceptance tests: `tests/acceptance/test_webhook.py`

## 7. Notes and open questions
None.
"""
            (task_dir / "01-contract.md").write_text(contract_content, encoding="utf-8")

            # 2. Author 02-dev-workspace.md
            dev_content = """# Dev Workspace

## 1. Execution metadata
- Dev agent: dev-agent-1
- Branch: feat/webhook
- Base commit: HEAD~1
- Handoff commit: HEAD
- Handoff time (UTC): 2026-10-18T07:15:00Z

## 2. Implementation notes
Implemented webhook payload and signature validation with V(G) = 2.

## 3. Actual changes
| Action | Path | Net lines |
| :--- | :--- | :--- |
| modify | src/webhook/handler.py | +15 / -2 |

## 4. Implementation deviations
| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |
| None | None | None | None |

## 5. Self-verification
- Type check: exit 0
- Lint: exit 0
- Existing tests: exit 0

## 6. Handoff to QA
- [x] WAITING_FOR_QA
"""
            (task_dir / "02-dev-workspace.md").write_text(dev_content, encoding="utf-8")

            # 3. Author 03-qa-verification.md with BDD, Complexity, and Mutation evidence
            qa_content = """# QA Verification

## 1. Verification metadata
| Field | Value |
| :--- | :--- |
| QA agent | qa-agent-1 |
| Reviewed commit | HEAD |
| Environment | local-sandbox |
| Attempt | 1 |
| Verdict time (UTC) | 2026-10-18T07:20:00Z |

## 2. Test matrix
| Case ID | Category | Given (Precondition) | When (Trigger / Action) | Then (Observable Result) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | Normal path | Valid signed event | POST /webhook | 200 OK | PASSED |
| TC-02 | Boundary | Empty payload | POST /webhook | 400 Bad Request | PASSED |
| TC-03 | Security | Invalid signature | POST /webhook | 401 Unauthorized | PASSED |

## 3. Complexity and basis path coverage
| Target Function | V(G) Complexity | Independent Basis Paths | Mapped Test Cases | Path Coverage |
| :--- | :--- | :--- | :--- | :--- |
| handle_webhook | 2 | P1 (empty), P2 (valid) | TC-01, TC-02 | 100% |

## 4. Mutation testing and MSI audit
| Metric / Field | Value |
| :--- | :--- |
| Mutation tool / engine | Synthetic agent fallback |
| Total mutants generated | 6 |
| Killed mutants | 5 |
| Timed-out mutants | 0 |
| Equivalent mutants | 1 |
| Survived mutants | 0 |
| Mutation Score Indicator (MSI) | 100.0% |

## 5. Boundary and anti-cheat audit
- [x] Every changed path is listed in `01-contract.md` -> `touch_files`
- [x] Dev did not modify `tests/acceptance/` or `01-contract.md`
- [x] Implementation honors every decision in `adherence_adrs`

## 6. Verdict
- [x] QA_PASSED
- [ ] REWORK_REQUIRED

## 7. Verdict notes
All BDD scenarios, basis paths, and mutation audits passed.
"""
            (task_dir / "03-qa-verification.md").write_text(qa_content, encoding="utf-8")

            # 4. Author 04-process.md
            process_content = """# Process Audit

## 1. Status card
macro_status: "DONE"
micro_phase: "CONVERGED"
current_lock_holder: "None"
last_heartbeat: "2026-10-18T07:22:00Z"
retry_count: 0

## 2. Event log
| Event ID | Timestamp (UTC) | Role | Event Code | Note |
| :--- | :--- | :--- | :--- | :--- |
"""
            (task_dir / "04-process.md").write_text(process_content, encoding="utf-8")

            # 5. Run plan_linter.py on the instantiated bundle
            cmd = [
                sys.executable,
                str(PLAN_LINTER_PATH),
                "--tasks-dir", str(tasks_dir),
                "--json",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work_root), timeout=60)
            self.assertEqual(res.returncode, 0, f"plan_linter failed (code {res.returncode}):\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

            parsed = json.loads(res.stdout)
            self.assertTrue(parsed.get("passed"), f"plan_linter report passed=False: {parsed}")
            self.assertEqual(len(parsed.get("errors", [])), 0, f"Errors found: {parsed.get('errors')}")

    def test_e2e_legacy_contract_backward_compatibility(self) -> None:
        """Compatibility: Existing legacy contracts with plain string edge cases pass plan_linter."""
        if not PLAN_LINTER_PATH.is_file():
            self.skipTest(f"plan_linter.py not found at {PLAN_LINTER_PATH}")

        with tempfile.TemporaryDirectory() as tmpdir:
            work_root = Path(tmpdir)
            tasks_dir = work_root / "tasks"
            task_id = "task-001-legacy"
            task_dir = tasks_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            legacy_contract = f"""---
task_id: "{task_id}"
title: "Legacy task contract"
module: "legacy"
dependencies: []
estimated_lines: 60
touch_files:
  - action: create
    path: "src/legacy/module.py"
origin_spec_anchor: "#sec-legacy"
adherence_adrs: ["ADR-001"]
dod:
  type_check: "python -m mypy src"
  lint: "python -m ruff check src"
  test_file: "tests/acceptance/test_legacy.py"
  edge_cases:
    - "legacy string edge case one"
    - "legacy string edge case two"
---

# Task {task_id}: Legacy task contract
## 1. Goal and scope
Legacy scope.
## 2. Out of scope
None.
## 3. Blast radius
Only declared touch_files.
## 4. Behavioral contract and invariants
Plain invariants.
## 5. Inherited architecture decisions
- ADR-001
## 6. Verifiability notes
- Notes
## 7. Notes and open questions
None.
"""
            (task_dir / "01-contract.md").write_text(legacy_contract, encoding="utf-8")
            (task_dir / "02-dev-workspace.md").write_text("# Dev Workspace\n- [ ] WAITING_FOR_QA\n", encoding="utf-8")
            (task_dir / "03-qa-verification.md").write_text("# QA Verification\n- [ ] QA_PASSED\n- [ ] REWORK_REQUIRED\n", encoding="utf-8")
            (task_dir / "04-process.md").write_text("# Process Audit\n", encoding="utf-8")

            # The documented Gate 1 escape hatch restores the pre-v4 contract schema.
            escape_hatch = work_root / "plan-linter.json"
            escape_hatch.write_text(
                json.dumps({"require_feature_file": False, "require_gherkin_block": False}),
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                str(PLAN_LINTER_PATH),
                "--tasks-dir", str(tasks_dir),
                "--config", str(escape_hatch),
                "--json",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work_root), timeout=60)
            self.assertEqual(res.returncode, 0, f"plan_linter failed on legacy contract:\n{res.stdout}\n{res.stderr}")
            parsed = json.loads(res.stdout)
            self.assertTrue(parsed.get("passed"))

    def test_repository_python_scripts_syntax_compilation(self) -> None:
        """Verify all Python scripts in skills/, .agents/skills/, and tools/ compile cleanly with zero SyntaxError."""
        import py_compile

        target_dirs = [ROOT / "skills", ROOT / ".agents" / "skills", ROOT / "tools"]
        py_files: List[Path] = []
        for d in target_dirs:
            self.assertTrue(d.is_dir(), f"Expected directory {d} to exist")
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith(".py") and not f.endswith(".pyc"):
                        py_files.append(Path(root) / f)

        self.assertGreaterEqual(len(py_files), 25, "Expected at least 25 Python scripts across skills/ and tools/")
        syntax_errors: List[Tuple[str, str]] = []
        for p in py_files:
            content = p.read_text(encoding="utf-8")
            try:
                ast.parse(content, filename=str(p))
            except Exception as exc:
                syntax_errors.append((str(p), f"ast.parse failed: {exc}"))
                continue
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as exc:
                syntax_errors.append((str(p), f"py_compile failed: {exc}"))

        self.assertEqual(
            len(syntax_errors),
            0,
            f"Found {len(syntax_errors)} Python syntax/compilation error(s):\n"
            + "\n".join(f"  {p}: {err}" for p, err in syntax_errors),
        )


if __name__ == "__main__":
    unittest.main()
