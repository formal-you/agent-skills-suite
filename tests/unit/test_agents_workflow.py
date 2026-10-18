#!/usr/bin/env python3
"""Guards the always-loaded skill-change and git-flow workflow in AGENTS.md."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"

REQUIRED_AGENTS_PHRASES = (
    "## Skill change workflow",
    "Issue first",
    "Branch from `main`",
    "Author or optimize",
    "Test before commit",
    "Pull request",
    "Merge and sync",
    "Tag and release",
    "Definition of done",
    "Prohibited shortcuts",
    "Closes #",
    "standard open-source workflow",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AgentsWorkflowTests(unittest.TestCase):
    def test_agents_has_the_skill_change_workflow(self) -> None:
        text = read(AGENTS)
        for phrase in REQUIRED_AGENTS_PHRASES:
            self.assertIn(phrase, text, "AGENTS.md misses workflow phrase: " + phrase)
        self.assertIn("git flow", text.lower())
        self.assertIn("Never commit directly to `main`", text)
        self.assertIn("Do not force-push", text)
        self.assertIn("Never delete, skip or weaken a test", text)
        self.assertIn("Never tag an unmerged or WIP", text)

    def test_contributing_points_to_the_canonical_workflow(self) -> None:
        text = read(CONTRIBUTING)
        self.assertIn("AGENTS.md#skill-change-workflow", text)
        self.assertIn("issue -> branch", text)
        self.assertIn("Closes #<issue>", text)


if __name__ == "__main__":
    unittest.main()
