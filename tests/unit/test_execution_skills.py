#!/usr/bin/env python3
"""Tests for the dev/qa execution skills (prompt-only, no helpers)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
EXEC_SKILLS = ("dev", "qa")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ABS_PATH_MARKERS = ("D:\\", "C:\\", "/home/", "/Users/")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    return match.group(1)


def markdown_targets(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


class ExecutionSkillStructureTests(unittest.TestCase):
    def test_skill_directories_exist(self) -> None:
        for name in EXEC_SKILLS:
            self.assertTrue((SKILLS / name / "SKILL.md").is_file(), f"missing {name}/SKILL.md")

    def test_frontmatter_is_valid(self) -> None:
        for name in EXEC_SKILLS:
            text = read_text(SKILLS / name / "SKILL.md")
            fm = frontmatter(text)
            self.assertRegex(fm, r"(?m)^name: " + name + r"$")
            self.assertRegex(fm, r'(?m)^description: ".+Use when .+Do not use .+"$')
            self.assertIn("license:", fm)
            self.assertIn("compatibility:", fm)
            self.assertRegex(fm, r'(?m)^\s+version: "2\.0\.0"$')
            self.assertRegex(fm, r"(?m)^\s+category: execution$")

    def test_skills_stay_compact(self) -> None:
        for name in EXEC_SKILLS:
            text = read_text(SKILLS / name / "SKILL.md")
            self.assertLess(len(text.splitlines()), 200, f"{name}/SKILL.md must stay below 200 lines")

    def test_english_canonical(self) -> None:
        for name in EXEC_SKILLS:
            for md in (SKILLS / name).rglob("*.md"):
                self.assertIsNone(CJK_RE.search(read_text(md)), f"non-English CJK content in {md}")

    def test_no_repo_absolute_paths(self) -> None:
        for name in EXEC_SKILLS:
            for md in (SKILLS / name).rglob("*.md"):
                text = read_text(md)
                for marker in ABS_PATH_MARKERS:
                    self.assertNotIn(marker, text, f"absolute path {marker} in {md}")

    def test_relative_links_resolve(self) -> None:
        for name in EXEC_SKILLS:
            for md in (SKILLS / name).rglob("*.md"):
                for target in markdown_targets(read_text(md)):
                    if target.startswith(("http://", "https://", "#", "mailto:")):
                        continue
                    path = (md.parent / target.split("#")[0]).resolve()
                    self.assertTrue(path.exists(), f"broken link in {md}: {target}")

    def test_prompt_only_no_scripts(self) -> None:
        for name in EXEC_SKILLS:
            self.assertFalse((SKILLS / name / "scripts").exists(), f"{name} should not ship scripts")


class ExecutionSkillContentTests(unittest.TestCase):
    def test_dev_documents_contract_and_handoff(self) -> None:
        text = read_text(SKILLS / "dev" / "SKILL.md")
        for needle in (
            "01-contract.md", "touch_files", "dod", "02-dev-workspace.md",
            "WAITING_FOR_QA", "tests/acceptance", "04-process.md",
            "03-qa-verification.md", "REWORK_REQUIRED",
        ):
            self.assertIn(needle, text, "dev skill misses: " + needle)
        self.assertIn("Only when every self-verification item passes", text)

    def test_qa_documents_verdict_and_evidence(self) -> None:
        text = read_text(SKILLS / "qa" / "SKILL.md")
        for needle in (
            "WAITING_FOR_QA", "tests/acceptance", "03-qa-verification.md",
            "QA_PASSED", "REWORK_REQUIRED", "touch_files", "evidence", "exactly one",
        ):
            self.assertIn(needle, text, "qa skill misses: " + needle)
        self.assertIn("Never tick both", text)

    def test_skills_do_not_grant_access(self) -> None:
        for name in EXEC_SKILLS:
            text = read_text(SKILLS / name / "SKILL.md").lower()
            self.assertIn("does not grant write access", text)
            self.assertIn("docs/agent-rules.md", text)

    def test_role_rules_point_to_skills(self) -> None:
        dev_rule = read_text(ROOT / ".agents" / "rules" / "dev.md")
        qa_rule = read_text(ROOT / ".agents" / "rules" / "qa.md")
        self.assertIn("skills/dev/SKILL.md", dev_rule)
        self.assertIn("skills/qa/SKILL.md", qa_rule)

    def test_skill_index_lists_execution_skills(self) -> None:
        text = read_text(SKILLS / "README.md")
        self.assertIn("(dev/SKILL.md)", text)
        self.assertIn("(qa/SKILL.md)", text)


if __name__ == "__main__":
    unittest.main()
