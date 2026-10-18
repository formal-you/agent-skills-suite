#!/usr/bin/env python3
"""Tests for the review skill (plan/Gate 2 + change review, prompt-only)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
REVIEW = SKILLS / "review"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ABS_PATH_MARKERS = ("D:\\", "C:\\", "/home/", "/Users/")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    return match.group(1)


class ReviewSkillStructureTests(unittest.TestCase):
    def test_skill_files_exist(self) -> None:
        self.assertTrue((REVIEW / "SKILL.md").is_file())
        self.assertTrue((REVIEW / "references" / "plan-review.md").is_file())
        self.assertTrue((REVIEW / "references" / "code-review.md").is_file())

    def test_frontmatter_is_valid(self) -> None:
        text = read_text(REVIEW / "SKILL.md")
        fm = frontmatter(text)
        self.assertRegex(fm, r"(?m)^name: review$")
        self.assertRegex(fm, r'(?m)^description: ".+Use when .+Do not use .+"$')
        self.assertIn("license:", fm)
        self.assertIn("compatibility:", fm)
        self.assertRegex(fm, r'(?m)^\s+version: "2\.0\.0"$')
        self.assertRegex(fm, r"(?m)^\s+category: review$")

    def test_skill_stays_compact(self) -> None:
        self.assertLess(len(read_text(REVIEW / "SKILL.md").splitlines()), 200)

    def test_english_canonical(self) -> None:
        for md in REVIEW.rglob("*.md"):
            self.assertIsNone(CJK_RE.search(read_text(md)), f"non-English CJK content in {md}")

    def test_no_repo_absolute_paths(self) -> None:
        for md in REVIEW.rglob("*.md"):
            text = read_text(md)
            for marker in ABS_PATH_MARKERS:
                self.assertNotIn(marker, text, f"absolute path {marker} in {md}")

    def test_relative_links_resolve(self) -> None:
        for md in REVIEW.rglob("*.md"):
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read_text(md)):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                path = (md.parent / target.split("#")[0]).resolve()
                self.assertTrue(path.exists(), f"broken link in {md}: {target}")

    def test_prompt_only_no_scripts(self) -> None:
        self.assertFalse((REVIEW / "scripts").exists(), "review skill should not ship scripts")


class ReviewSkillContentTests(unittest.TestCase):
    def test_documents_both_modes(self) -> None:
        text = read_text(REVIEW / "SKILL.md")
        for needle in (
            "Plan / Gate 2", "Change / code", "Gate 1", "reviewer", "independence",
            "blocker", "major", "minor", "nit", "PASS", "REQUEST CHANGES", "BLOCKED",
        ):
            self.assertIn(needle, text, "review skill misses: " + needle)

    def test_read_only_and_no_gate_bypass(self) -> None:
        text = read_text(REVIEW / "SKILL.md").lower()
        for needle in ("never edits", "no edits", "bypass gate 1", "own work"):
            self.assertIn(needle, text, "review skill misses: " + needle)
        self.assertNotIn("write scope:", text)

    def test_plan_review_reference_covers_gate_2(self) -> None:
        text = read_text(REVIEW / "references" / "plan-review.md")
        for needle in ("completeness", "anti-hallucination", "ADR", "Output format", "BLOCKED"):
            self.assertIn(needle, text, "plan-review reference misses: " + needle)

    def test_code_review_reference_covers_scope_and_security(self) -> None:
        text = read_text(REVIEW / "references" / "code-review.md")
        for needle in ("Contract and scope", "Correctness", "Tests and evidence", "Security", "Verdict"):
            self.assertIn(needle, text, "code-review reference misses: " + needle)

    def test_plan_linter_points_to_review_skill(self) -> None:
        text = read_text(SKILLS / "plan-linter" / "SKILL.md")
        self.assertIn("review", text)
        self.assertIn("references/gate-2-review.md", text, "fallback prompt must remain")

    def test_skill_index_and_reviewer_rule_link_review(self) -> None:
        self.assertIn("(review/SKILL.md)", read_text(SKILLS / "README.md"))
        reviewer_rule = read_text(ROOT / ".agents" / "rules" / "reviewer.md")
        self.assertIn("skills/review/SKILL.md", reviewer_rule)


if __name__ == "__main__":
    unittest.main()
