#!/usr/bin/env python3
"""Guards the always-loaded skill-change and git-flow workflow in AGENTS.md."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"

REQUIRED_AGENTS_PHRASES = (
    "## 6. Skill change workflow",
    "Intent and issue (risk-based)",
    "Branch and write scope",
    "Author or optimize",
    "Test and evidence before commit",
    "Pull request and review",
    "Merge, sync and post-merge verification",
    "Tag and release (SemVer)",
    "Definition of done",
    "Prohibited shortcuts",
    "Closes #",
    "standard open-source workflow",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


class AgentsWorkflowTests(unittest.TestCase):
    def test_agents_has_the_skill_change_workflow(self) -> None:
        text = read(AGENTS)
        text_flat = flat(text)
        for phrase in REQUIRED_AGENTS_PHRASES:
            self.assertIn(phrase, text_flat, "AGENTS.md misses workflow phrase: " + phrase)
        self.assertIn("git flow", text.lower())
        self.assertIn("never commit directly to `main`", text_flat.lower())
        self.assertIn("do not force-push", text_flat.lower())
        self.assertIn("Never delete, skip or weaken", text_flat)
        self.assertIn("Never move or delete a published tag", text_flat)
        self.assertIn("independent reviewer", text_flat)
        self.assertIn("disjoint write scopes", text_flat)
        self.assertIn("post-merge", text_flat.lower())

    def test_agents_is_concise_and_scannable(self) -> None:
        text = read(AGENTS)
        self.assertLessEqual(len(text.splitlines()), 150, "AGENTS.md must stay under 150 lines")
        for phrase in (
            "**Purpose.**",
            "**Precedence (highest first).**",
            "**Authority.**",
            "## 1. Repository map",
            "## 2. How to work",
            "### 2.1 Per-task delivery",
            "### 2.2 Skill-suite development",
            "## 7. Commands",
            "always-loaded summary",
        ):
            self.assertIn(phrase, text, "AGENTS.md misses structure phrase: " + phrase)
        self.assertNotIn("v2.0.0", text, "do not pin tool versions in the always-loaded summary")

    def test_contributing_points_to_the_canonical_workflow(self) -> None:
        text = flat(read(CONTRIBUTING))
        self.assertIn("AGENTS.md#skill-change-workflow", text)
        self.assertIn("issue -> branch", text)
        self.assertIn("Closes #<issue>", text)
        self.assertIn("independent reviewer", text)
        self.assertIn("SemVer", text)

    def test_pull_request_template_requires_issue_review_and_release_plan(self) -> None:
        text = flat(read(PR_TEMPLATE))
        for phrase in (
            "Closes #",
            "Risk and rollback",
            "Release / tag",
            "independent reviewer",
            "No secrets",
            "byte-identical",
        ):
            self.assertIn(phrase, text, "PR template misses: " + phrase)


if __name__ == "__main__":
    unittest.main()
