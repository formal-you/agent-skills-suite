#!/usr/bin/env python3
"""Tests for the multi-language CI profile catalog."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_DIR = ROOT / "templates" / "ci"
PROFILES_DIR = CI_DIR / "profiles"
INDEX = PROFILES_DIR / "index.json"
CONFIG_EXAMPLE = CI_DIR / "quality-gate.config.example.json"
README = CI_DIR / "README.md"
GUIDE = ROOT / "docs" / "ci-stack-profiles.zh-CN.md"
SKILL = ROOT / ".agents" / "skills" / "quality-engineering" / "SKILL.md"

EXPECTED_STACKS = ["python", "node", "go", "java", "rust", "dotnet", "cpp"]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
REQUIRED_PROFILE_LINES = [
    "stack:",
    "display_name:",
    "toolchain:",
    "install:",
    "acceptance:",
    "junit:",
    "mutation:",
    "report:",
    "complexity:",
    "services:",
    "notes:",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CiProfileCatalogTests(unittest.TestCase):
    def test_index_is_valid_json_and_lists_every_profile(self) -> None:
        data = json.loads(read(INDEX))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["normalized_mutation_report"], "artifacts/mutation-report.json")
        entries = data["profiles"]
        self.assertEqual([entry["stack"] for entry in entries], EXPECTED_STACKS)
        for entry in entries:
            path = PROFILES_DIR / entry["file"]
            self.assertTrue(path.is_file(), "missing profile: " + str(path))
            self.assertTrue(entry["display_name"])
            self.assertTrue(entry["acceptance"])
            self.assertTrue(entry["mutation"])

    def test_profiles_are_reference_fragments_with_required_sections(self) -> None:
        for stack in EXPECTED_STACKS:
            path = PROFILES_DIR / (stack + ".yml")
            self.assertTrue(path.is_file(), "missing profile: " + str(path))
            text = read(path)
            for needle in REQUIRED_PROFILE_LINES:
                self.assertIn(needle, text, "%s misses %s" % (path.name, needle))
            self.assertIn('report: "artifacts/mutation-report.json"', text, path.name)
            self.assertIn("services: []", text, path.name)
            self.assertNotIn("|| true", text, path.name)
            self.assertNotIn("continue-on-error", text, path.name)
            self.assertIsNone(CJK_RE.search(text), "%s must be English-only" % path.name)

    def test_profiles_parse_as_yaml_when_pyyaml_is_available(self) -> None:
        try:
            import yaml  # type: ignore
        except ImportError:
            self.skipTest("PyYAML not installed; text-level assertions already cover the catalog")
        for stack in EXPECTED_STACKS:
            path = PROFILES_DIR / (stack + ".yml")
            data = yaml.safe_load(read(path))
            self.assertIsInstance(data, dict, path.name)
            self.assertEqual(data["stack"], stack, path.name)
            self.assertIn("mutation", data, path.name)
            self.assertEqual(data["mutation"]["report"], "artifacts/mutation-report.json", path.name)

    def test_config_example_is_valid_and_matches_profile_shape(self) -> None:
        data = json.loads(read(CONFIG_EXAMPLE))
        for key in ("schema_version", "mode", "stack", "source", "install", "acceptance",
                    "mutation", "complexity", "services"):
            self.assertIn(key, data, key)
        self.assertEqual(data["mutation"]["report"], "artifacts/mutation-report.json")
        self.assertEqual(data["mutation"]["min_msi"], 80)
        self.assertEqual(data["complexity"]["standard"], 10)
        self.assertEqual(data["complexity"]["warning"], 15)

    def test_docs_and_index_reference_every_stack(self) -> None:
        docs = read(GUIDE)
        for stack in EXPECTED_STACKS:
            self.assertIn(stack, docs, "docs/ci-stack-profiles.zh-CN.md misses " + stack)
            self.assertIn(stack + ".yml", docs, "docs misses " + stack + ".yml")
        self.assertIn("变异报告 adapter", docs)
        self.assertIn("services:", docs)

    def test_ci_readme_and_skill_point_to_profiles(self) -> None:
        readme = read(README)
        self.assertIn("profiles", readme.lower())
        self.assertIn("ci-stack-profiles.zh-CN.md", readme)
        skill = read(SKILL)
        self.assertIn("profile", skill.lower())
        self.assertNotIn("templates/ci", skill, "skill docs must stay self-contained")


if __name__ == "__main__":
    unittest.main()
