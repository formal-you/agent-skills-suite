#!/usr/bin/env python3
"""Tests for the repository test-strategy wiring.

The strategy document is owned by the test-engineering role; this module only reads it and the
wiring points that consume it (role rule, QA test design, the 03 template, quality-engineering CI
mapping, review boundaries, docs and version). Standard library only: markdown and JSON are checked
structurally, deliberately without PyYAML.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
MIRROR_SKILLS = ROOT / "skills"
DOCS = ROOT / "docs"
STRATEGY = DOCS / "testing-strategy.md"
RULE = ROOT / ".agents" / "rules" / "test-engineering.md"
QA_SKILL = SKILLS / "qa" / "SKILL.md"
QA_PROTOCOL = SKILLS / "qa" / "references" / "qa-protocol.md"
QA_TEMPLATE = SKILLS / "task-decomposition" / "assets" / "templates" / "03-qa-verification.template.md"
QE_SKILL = SKILLS / "quality-engineering" / "SKILL.md"
QE_PROTOCOL = SKILLS / "quality-engineering" / "references" / "verification-protocol.md"
REVIEW_SKILL = SKILLS / "review" / "SKILL.md"
TE_SKILL = SKILLS / "test-engineering" / "SKILL.md"
SKILL_INDEX = SKILLS / "README.md"

FORBIDDEN_TOKENS = ("docs/", "tools/", ".agents/rules", ".agents/scripts", "templates/ci")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")
TBD_RE = re.compile(r"\[TBD\]|\bTODO\b")
H2_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.M)
VERSION_RE = re.compile(r"(?m)^\s+version: \"([^\"]+)\"$")

# One entry per required strategy theme; an entry matches when any alternative appears in an H2.
REQUIRED_STRATEGY_SECTIONS = (
    ("purpose",),
    ("scope",),
    ("quality attributes",),
    ("risk matrix",),
    ("test levels",),
    ("technique",),
    ("data",),
    ("environment",),
    ("flakiness",),
    ("metrics",),
    ("raci",),
    ("review cadence", "cadence"),
)

# The five test-design fields, matched tolerantly so the wording may carry parenthetical detail.
TEST_DESIGN_FIELDS = (
    "Strategy reference",
    "Risk level",
    "Technique",
    "Environment",
    "Out of scope",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def h2_titles(text: str) -> list[str]:
    return [match.group(1).strip().lower() for match in H2_RE.finditer(text)]


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    return match.group(1)


def markdown_files(root: Path):
    return sorted(root.rglob("*.md"))


class StrategyDocumentTests(unittest.TestCase):
    def test_strategy_document_exists_and_is_filled(self) -> None:
        self.assertTrue(STRATEGY.is_file(), "missing docs/testing-strategy.md")
        text = read_text(STRATEGY)
        self.assertTrue(text.startswith("# "), "the strategy needs a top-level title")
        self.assertIsNone(PLACEHOLDER_RE.search(text), "unresolved placeholder in the strategy")
        self.assertIsNone(TBD_RE.search(text), "unresolved [TBD]/TODO marker in the strategy")

    def test_strategy_declares_required_sections(self) -> None:
        title_blob = "\n".join(h2_titles(read_text(STRATEGY)))
        missing = [
            alternatives[0]
            for alternatives in REQUIRED_STRATEGY_SECTIONS
            if not any(needle in title_blob for needle in alternatives)
        ]
        self.assertEqual(missing, [], "strategy misses section headings: " + repr(missing))

    def test_strategy_is_english_canonical(self) -> None:
        self.assertIsNone(CJK_RE.search(read_text(STRATEGY)), "the strategy must be English-only")


class RoleRuleTests(unittest.TestCase):
    def test_rule_names_the_default_strategy_path(self) -> None:
        self.assertIn("docs/testing-strategy.md", read_text(RULE))

    def test_rule_documents_the_adopter_override(self) -> None:
        text = read_text(RULE).lower()
        self.assertIn("override", text, "the role rule must document the adopters' override")
        self.assertIn("default", text, "the role rule must name the default output location")
        self.assertIn("template", text, "the role rule must create the strategy from the bundled template")
        self.assertIn("create", text, "the role rule must not assume the strategy file already exists")

    def test_skill_ships_template_and_is_standalone(self) -> None:
        text = read_text(TE_SKILL)
        lowered = text.lower()
        self.assertIn("assets/templates/test-strategy.template.md", text)
        self.assertIn("template", lowered)
        self.assertIn("create", lowered, "the skill must say to create the strategy when absent")
        self.assertIn("depends on a suite-level strategy file", lowered)
        self.assertIn("never", lowered)
        self.assertNotIn("docs/", text, "skill docs must not depend on a repository docs path")

    def test_strategy_seed_is_not_an_install_dependency(self) -> None:
        text = read_text(STRATEGY).lower()
        self.assertIn("not an install dependency", text)
        self.assertIn("template", text)

    def test_rule_keeps_global_only_and_no_task_verdict(self) -> None:
        text = read_text(RULE)
        lowered = text.lower()
        self.assertIn("never accept", lowered)
        self.assertIn("QA_PASSED", text)
        self.assertIn("REWORK_REQUIRED", text)


class QaWiringTests(unittest.TestCase):
    def test_qa_skill_reads_the_strategy_and_marks_baseline(self) -> None:
        text = read_text(QA_SKILL)
        lowered = text.lower()
        self.assertIn("test strategy", lowered, "qa/SKILL.md must mention the repository test strategy")
        self.assertIn("baseline", lowered, "qa/SKILL.md must state the baseline fallback")
        self.assertIn("Test design summary", text, "qa/SKILL.md must name the test design summary")

    def test_qa_protocol_documents_the_test_design_summary(self) -> None:
        text = read_text(QA_PROTOCOL)
        self.assertIn("Test design summary", text)
        summary = text.split("Test design summary", 1)[1]
        for field in TEST_DESIGN_FIELDS:
            self.assertIn(field, summary, "qa-protocol test design summary misses: " + field)

    def test_qa_protocol_handles_strategy_conflicts(self) -> None:
        text = read_text(QA_PROTOCOL)
        self.assertIn("SPEC_AMBIGUITY", text, "strategy conflicts must escalate, never silently override")
        lowered = text.lower()
        self.assertIn("escalat", lowered)


class TemplateWiringTests(unittest.TestCase):
    def test_template_has_the_test_design_summary_block(self) -> None:
        text = read_text(QA_TEMPLATE)
        self.assertIn("### 2.1 Test design summary", text)
        self.assertIn("### 2.2 Test matrix", text)
        self.assertLess(
            text.index("### 2.1 Test design summary"),
            text.index("### 2.2 Test matrix"),
            "the test design summary must precede the matrix",
        )
        summary = text.split("### 2.1 Test design summary", 1)[1].split("### 2.2 Test matrix", 1)[0]
        for field in TEST_DESIGN_FIELDS:
            self.assertIn(field, summary, "03 template test design summary misses: " + field)

    def test_template_summary_stays_token_free(self) -> None:
        text = read_text(QA_TEMPLATE)
        self.assertIsNone(PLACEHOLDER_RE.search(text), "03 template must stay token-free")
        self.assertIsNone(TBD_RE.search(text), "03 template must stay token-free")

    def test_qa_template_is_english_canonical(self) -> None:
        self.assertIsNone(CJK_RE.search(read_text(QA_TEMPLATE)))


class QualityEngineeringWiringTests(unittest.TestCase):
    def test_skill_consumes_the_test_strategy(self) -> None:
        text = read_text(QE_SKILL)
        lowered = text.lower()
        self.assertIn("test strategy", lowered, "quality-engineering must declare the strategy input")
        self.assertIn("test-engineering", text, "quality-engineering must name the defining role")
        self.assertIn("Map the approved test strategy", text)
        self.assertIn("do not invent test standards", lowered)

    def test_skill_declares_version_and_stays_compact(self) -> None:
        text = read_text(QE_SKILL)
        self.assertRegex(frontmatter(text), VERSION_RE)
        versions = VERSION_RE.findall(frontmatter(text))
        self.assertEqual(versions, ["2.1.0"], "quality-engineering metadata.version must be 2.1.0")
        self.assertLess(len(text.splitlines()), 200, "SKILL.md must stay below 200 lines")

    def test_protocol_contains_the_strategy_to_ci_mapping(self) -> None:
        text = read_text(QE_PROTOCOL)
        self.assertIn("### Strategy-to-CI mapping", text)
        mapping = text.split("### Strategy-to-CI mapping", 1)[1]
        for needle in ("Risk class", "Test levels", "Data and environment", "Flakiness", "Metrics"):
            self.assertIn(needle, mapping, "strategy-to-CI table misses: " + needle)
        lowered = mapping.lower()
        self.assertIn("test-engineering", mapping)
        self.assertIn("implements", lowered, "quality-engineering implements the strategy")
        self.assertIn("defines", lowered, "test-engineering defines the strategy")
        self.assertIn("never hide a failure", lowered, "flakiness reruns must never hide failures")


class ReviewBoundaryTests(unittest.TestCase):
    def test_review_defers_test_design_review_to_test_engineering(self) -> None:
        text = read_text(REVIEW_SKILL)
        lowered = text.lower()
        self.assertIn("test-engineering", text)
        self.assertIn("test-design", lowered.replace("test design", "test-design"))
        self.assertIn("semantic", lowered, "review must stay semantic plan/change review")

    def test_review_does_not_link_to_the_other_skill(self) -> None:
        text = read_text(REVIEW_SKILL)
        self.assertNotIn("test-engineering/", text, "review must not carry a cross-skill path")
        self.assertNotIn(".agents/skills", text)


class SkillSelfContainmentTests(unittest.TestCase):
    def test_skill_markdown_has_no_suite_internal_tokens(self) -> None:
        # The suite-level skill index (skills/README.md) is repository context, not a skill
        # directory, so it may legitimately name suite paths. Only skill directories are scanned.
        offenders: list[str] = []
        for tree in (SKILLS, MIRROR_SKILLS):
            for skill in sorted(path for path in tree.iterdir() if path.is_dir()):
                if not (skill / "SKILL.md").is_file():
                    continue
                for path in markdown_files(skill):
                    text = read_text(path)
                    relative = path.relative_to(ROOT).as_posix()
                    for token in FORBIDDEN_TOKENS:
                        if token in text:
                            offenders.append(relative + " -> " + token)
        self.assertEqual(
            offenders,
            [],
            "skill .md files must stay self-contained; offenders:\n" + "\n".join(offenders),
        )

    def test_skill_index_lists_test_engineering(self) -> None:
        self.assertIn("test-engineering", read_text(SKILL_INDEX))


class DocsAndVersionTests(unittest.TestCase):
    def test_readme_links_the_strategy(self) -> None:
        text = read_text(ROOT / "README.md")
        self.assertIn("docs/testing-strategy.md", text)
        self.assertIn("strategy", text.lower())

    def test_skills_guide_wires_the_strategy(self) -> None:
        text = read_text(DOCS / "skills-guide.zh-CN.md")
        self.assertIn("testing-strategy.md", text, "the guide must link the strategy document")
        self.assertIn("测试策略", text)

    def test_compatibility_doc_mentions_the_strategy(self) -> None:
        text = read_text(DOCS / "skills-compatibility.md")
        self.assertIn("testing-strategy.md", text)

    def test_version_files_agree(self) -> None:
        version = read_text(ROOT / "VERSION").strip()
        self.assertEqual(version, "3.4.2")
        plugin = json.loads(read_text(ROOT / ".claude-plugin" / "plugin.json"))
        self.assertEqual(plugin["version"], "3.4.2")
        self.assertIn("eleven", plugin["description"].lower())
        marketplace = json.loads(read_text(ROOT / ".claude-plugin" / "marketplace.json"))
        plugins = marketplace["plugins"]
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["version"], "3.4.2")
        self.assertIn("eleven", plugins[0]["description"].lower())

    def test_changelog_has_the_release_section(self) -> None:
        text = read_text(ROOT / "CHANGELOG.md")
        self.assertIn("## [3.4.2] - 2026-10-19", text)
        section = text.split("## [3.4.2] - 2026-10-19", 1)[1].split("\n## [", 1)[0]
        for heading in ("### Changed", "### Fixed"):
            self.assertIn(heading, section, "3.4.2 changelog misses: " + heading)


if __name__ == "__main__":
    unittest.main()
