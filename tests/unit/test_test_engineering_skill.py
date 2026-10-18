#!/usr/bin/env python3
"""Tests for the test-engineering skill and role rule (prompt-only, global test system)."""
from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
SKILL = SKILLS / "test-engineering"
MIRROR = ROOT / "skills" / "workflow" / "test-engineering"
RULE = ROOT / ".agents" / "rules" / "test-engineering.md"

REQUIRED_FILES = (
    "SKILL.md",
    "references/test-strategy.md",
    "references/test-design-review.md",
    "references/role-boundaries.md",
    "assets/templates/test-strategy.template.md",
)
FORBIDDEN_TOKENS = ("docs/", "tools/", ".agents/rules", ".agents/scripts", "templates/ci")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ABS_PATH_MARKERS = ("D:\\", "C:\\", "/home/", "/Users/")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    return match.group(1)


def markdown_files(root: Path):
    return sorted(root.rglob("*.md"))


def markdown_targets(text: str):
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_files(root: Path):
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


class TestEngineeringStructureTests(unittest.TestCase):
    def test_skill_and_references_exist(self) -> None:
        for relative in REQUIRED_FILES:
            self.assertTrue((SKILL / relative).is_file(), "missing " + relative)

    def test_prompt_only_no_scripts(self) -> None:
        self.assertFalse((SKILL / "scripts").exists(), "test-engineering should stay prompt-only")

    def test_frontmatter_is_valid(self) -> None:
        text = read_text(SKILL / "SKILL.md")
        fm = frontmatter(text)
        self.assertRegex(fm, r"(?m)^name: test-engineering$")
        self.assertRegex(fm, r'(?m)^description: ".+Use when .+Do not use .+"$')
        self.assertRegex(fm, r"(?m)^license: MIT$")
        self.assertIn(
            'compatibility: "Harness-agnostic prompt workflow. No scripts, no runtime dependency."',
            fm,
        )
        self.assertRegex(fm, r'(?m)^\s+version: "1\.0\.0"$')
        self.assertRegex(fm, r"(?m)^\s+category: execution$")

    def test_skill_stays_compact(self) -> None:
        self.assertLess(
            len(read_text(SKILL / "SKILL.md").splitlines()),
            200,
            "SKILL.md must stay below 200 lines",
        )

    def test_english_canonical(self) -> None:
        for md in markdown_files(SKILL):
            self.assertIsNone(CJK_RE.search(read_text(md)), "non-English CJK content in " + str(md))
        self.assertIsNone(CJK_RE.search(read_text(RULE)), "non-English CJK content in the role rule")

    def test_no_repo_absolute_paths(self) -> None:
        for md in markdown_files(SKILL):
            text = read_text(md)
            for marker in ABS_PATH_MARKERS:
                self.assertNotIn(marker, text, "absolute path " + marker + " in " + str(md))

    def test_no_forbidden_external_tokens(self) -> None:
        for md in markdown_files(SKILL):
            text = read_text(md)
            for token in FORBIDDEN_TOKENS:
                self.assertNotIn(
                    token,
                    text,
                    str(md.relative_to(ROOT)) + " must stay self-contained; found " + token,
                )

    def test_relative_links_resolve_inside_the_skill(self) -> None:
        skill_root = SKILL.resolve()
        for md in markdown_files(SKILL):
            for target in markdown_targets(read_text(md)):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.strip().split()[0].strip("<>")
                target = target.split("#", 1)[0].split("?", 1)[0]
                if not target:
                    continue
                resolved = (md.parent / target).resolve()
                self.assertTrue(resolved.exists(), "broken link in " + str(md) + ": " + target)
                self.assertTrue(
                    resolved.is_relative_to(skill_root),
                    "link escapes the skill in " + str(md) + ": " + target,
                )


class TestEngineeringMirrorTests(unittest.TestCase):
    def test_mirror_tree_exists(self) -> None:
        self.assertTrue(MIRROR.is_dir(), "missing skills/workflow/test-engineering")

    def test_every_file_is_byte_identical(self) -> None:
        canonical = relative_files(SKILL)
        mirrored = relative_files(MIRROR)
        self.assertEqual(
            sorted(mirrored),
            sorted(canonical),
            "mirror file sets differ from the canonical skill tree",
        )
        for relative, source in canonical.items():
            self.assertEqual(
                sha256(mirrored[relative]),
                sha256(source),
                "mirror mismatch: " + relative,
            )


class TestEngineeringContentTests(unittest.TestCase):
    def test_skill_is_global_only_and_never_accepts_tasks(self) -> None:
        text = read_text(SKILL / "SKILL.md")
        lowered = text.lower()
        self.assertIn("global-only", lowered)
        self.assertIn("never accepts", lowered)
        self.assertIn("QA_PASSED", text)
        self.assertIn("REWORK_REQUIRED", text)
        self.assertIn("not task acceptance", lowered)
        self.assertIn("defers", lowered)

    def test_skill_defers_to_qa_and_quality_engineering(self) -> None:
        text = read_text(SKILL / "SKILL.md")
        self.assertIn("`qa`", text)
        self.assertIn("`quality-engineering`", text)
        self.assertIn("`review`", text)
        self.assertIn("## Boundaries", text)

    def test_workflow_covers_all_phases(self) -> None:
        text = read_text(SKILL / "SKILL.md")
        for phase in ("Assess", "Formulate the strategy", "Define design standards", "review", "Hand off"):
            self.assertIn(phase, text, "workflow misses phase: " + phase)

    def test_design_markers_are_documented_and_not_verdicts(self) -> None:
        skill_text = read_text(SKILL / "SKILL.md")
        review_text = read_text(SKILL / "references" / "test-design-review.md")
        for marker in ("DESIGN_READY", "DESIGN_GAPS"):
            self.assertIn(marker, skill_text, "SKILL.md misses " + marker)
            self.assertIn(marker, review_text, "test-design-review misses " + marker)
        self.assertIn("never replaces", review_text.lower())
        self.assertIn("not acceptance", review_text.lower())

    def test_review_reference_covers_required_checklist(self) -> None:
        text = read_text(SKILL / "references" / "test-design-review.md")
        for needle in (
            "Contract traceability",
            "Risk coverage",
            "Technique coverage",
            "Boundary and negative cases",
            "State, replay, and idempotency",
            "Contract and property coverage",
            "Determinism and data control",
            "Test-double policy",
            "Oracle strength",
            "Test independence and isolation",
            "Flakiness resistance",
            "Evidence and provenance",
            "Out-of-scope",
            "blocker",
            "major",
            "minor",
            "observation",
        ):
            self.assertIn(needle, text, "test-design-review misses: " + needle)

    def test_strategy_reference_covers_required_sections(self) -> None:
        text = read_text(SKILL / "references" / "test-strategy.md")
        for needle in (
            "Quality attributes",
            "Risk matrix",
            "Test levels",
            "Technique selection",
            "Test data policy",
            "Environment policy",
            "Test-double policy",
            "Flakiness policy",
            "Automation and CI handoff",
            "Metrics and thresholds",
            "RACI",
            "Adoption roadmap",
            "equivalence",
            "boundary",
            "decision table",
            "state transition",
            "pairwise",
        ):
            self.assertIn(needle.lower(), text.lower(), "test-strategy misses: " + needle)

    def test_role_boundaries_reference(self) -> None:
        text = read_text(SKILL / "references" / "role-boundaries.md")
        for needle in ("Write scope", "Read-only", "Never", "Invariants", "advisory"):
            self.assertIn(needle, text, "role-boundaries misses: " + needle)
        self.assertIn("never accepts", text.lower())

    def test_strategy_template_has_sections_and_placeholders(self) -> None:
        text = read_text(SKILL / "assets" / "templates" / "test-strategy.template.md")
        self.assertIn("{{", text, "template must stay fillable")
        for needle in (
            "Risk matrix",
            "Test levels",
            "Technique policy",
            "Test data policy",
            "Environment policy",
            "Test-double policy",
            "Flakiness policy",
            "Metrics and thresholds",
            "Adoption roadmap",
        ):
            self.assertIn(needle, text, "template misses: " + needle)


class TestEngineeringRuleTests(unittest.TestCase):
    def test_rule_exists_with_frontmatter(self) -> None:
        self.assertTrue(RULE.is_file(), "missing test-engineering role rule")
        fm = frontmatter(read_text(RULE))
        self.assertRegex(fm, r"(?m)^trigger: ")
        self.assertRegex(fm, r"(?m)^description: ")

    def test_rule_declares_scope_and_no_task_acceptance(self) -> None:
        text = read_text(RULE)
        self.assertIn("**Write scope:**", text)
        self.assertIn("**Read-only:**", text)
        self.assertIn("skills/test-engineering/SKILL.md", text)
        lowered = text.lower()
        self.assertIn("never accept", lowered)
        self.assertIn("QA_PASSED", text)
        self.assertIn("REWORK_REQUIRED", text)
        self.assertIn("quality-engineering", text)

    def test_rule_no_forbidden_external_tokens(self) -> None:
        # The self-containment scanner only covers skill files, but the rule should not
        # accidentally reference suite internals either.
        text = read_text(RULE)
        for token in FORBIDDEN_TOKENS:
            self.assertNotIn(token, text, "role rule leaks suite internals: " + token)


if __name__ == "__main__":
    unittest.main()
