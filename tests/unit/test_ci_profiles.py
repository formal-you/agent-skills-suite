#!/usr/bin/env python3
"""Tests for the multi-language CI profile catalog."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".agents" / "skills" / "quality-engineering"
CI_DIR = SKILL_DIR / "assets" / "templates" / "ci"
PROFILES_DIR = CI_DIR / "profiles"
INDEX = PROFILES_DIR / "index.json"
CONFIG_EXAMPLE = CI_DIR / "quality-gate.config.example.json"
README = CI_DIR / "README.md"
PROFILES_README = PROFILES_DIR / "README.md"
GUIDE = ROOT / "docs" / "ci-stack-profiles.zh-CN.md"
SKILL = SKILL_DIR / "SKILL.md"

EXPECTED_STACKS = ["python", "node", "go", "java", "rust", "dotnet", "cpp"]
# Stacks that ship a ready-to-copy, executable quality-gate.config.json.
STACK_CONFIGS = ["python", "node", "go", "java"]
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
        skill = read(SKILL)
        self.assertIn("profile", skill.lower())
        self.assertIn("assets/templates/ci/", skill, "skill must point at its own bundled CI assets")
        self.assertNotIn("../", skill, "skill docs must stay self-contained")


class StackConfigTests(unittest.TestCase):
    """The four config-bearing stacks ship real, executable per-stack configs."""

    def config(self, stack: str) -> dict:
        path = PROFILES_DIR / (stack + ".config.json")
        self.assertTrue(path.is_file(), "missing ready-to-copy config: " + str(path))
        return json.loads(read(path))

    def test_stack_configs_are_valid_and_actionable(self) -> None:
        for stack in STACK_CONFIGS:
            path = PROFILES_DIR / (stack + ".config.json")
            text = read(path)
            data = json.loads(text)

            self.assertEqual(data["schema_version"], 1, path.name)
            self.assertEqual(data["mode"], "spec-driven", path.name)
            self.assertEqual(data["stack"], stack, path.name)
            self.assertTrue(data["display_name"], path.name)

            source = data["source"]
            self.assertIsInstance(source["dirs"], list, path.name)
            self.assertTrue(source["dirs"], path.name)
            self.assertIsInstance(source["languages"], list, path.name)
            self.assertTrue(source["languages"], path.name)

            install = data["install"]
            self.assertIsInstance(install, list, path.name)
            self.assertTrue(install, path.name)
            for command in install:
                self.assertTrue(command.strip(), path.name)

            acceptance = data["acceptance"]
            self.assertTrue(acceptance["command"].strip(), path.name)
            self.assertTrue(acceptance["junit"].strip(), path.name)
            self.assertNotIn("|| true", acceptance["command"], path.name)
            for alternative in acceptance.get("alternatives", []):
                self.assertTrue(alternative.strip(), path.name)

            mutation = data["mutation"]
            self.assertTrue(mutation["tool"].strip(), path.name)
            self.assertTrue(mutation["command"].strip(), path.name)
            self.assertTrue(mutation["raw_report"].strip(), path.name)
            self.assertTrue(mutation["adapter"].strip(), path.name)
            self.assertEqual(
                mutation["report"], "artifacts/mutation-report.json", path.name
            )
            self.assertEqual(mutation["min_msi"], 80, path.name)
            self.assertEqual(mutation["core_min_msi"], 90, path.name)
            self.assertNotIn("|| true", mutation["command"], path.name)

            complexity = data["complexity"]
            self.assertIn("complexity_check.py", complexity["command"], path.name)
            self.assertTrue(complexity["engines"], path.name)
            self.assertEqual(complexity["standard"], 10, path.name)
            self.assertEqual(complexity["warning"], 15, path.name)

            self.assertEqual(data["services"], [], path.name)
            self.assertTrue(data["notes"], path.name)
            self.assertNotIn("continue-on-error", text, path.name)
            self.assertIsNone(CJK_RE.search(text), "%s must be English-only" % path.name)

    def test_stack_configs_use_industry_standard_tools(self) -> None:
        expected = {
            "python": {"acceptance": "pytest", "mutation": "mutmut"},
            "node": {"acceptance": "cucumber-js", "mutation": "stryker"},
            "go": {"acceptance": "godog", "mutation": "go-mutesting"},
            "java": {"acceptance": "cucumber", "mutation": "pitest"},
        }
        for stack, tools in expected.items():
            data = self.config(stack)
            self.assertIn(
                tools["acceptance"], data["acceptance"]["command"].lower(), stack
            )
            self.assertIn(
                tools["mutation"], data["mutation"]["command"].lower(), stack
            )
            self.assertIn("complexity_check.py", data["complexity"]["command"], stack)

    def test_index_references_ready_to_copy_config_for_config_stacks(self) -> None:
        data = json.loads(read(INDEX))
        entries = {entry["stack"]: entry for entry in data["profiles"]}
        for stack in EXPECTED_STACKS:
            self.assertIn(stack, entries, "index misses " + stack)
        for stack in STACK_CONFIGS:
            entry = entries[stack]
            self.assertIn("config", entry, "%s index entry misses config" % stack)
            self.assertEqual(entry["config"], stack + ".config.json", stack)
            self.assertTrue(
                (PROFILES_DIR / entry["config"]).is_file(),
                "index points at a missing config: " + entry["config"],
            )

    def test_readmes_document_tool_matrix_and_fail_closed_floor(self) -> None:
        profiles_readme = read(PROFILES_README)
        ci_readme = read(README)
        for stack in STACK_CONFIGS:
            config_name = stack + ".config.json"
            self.assertIn(config_name, profiles_readme, "profiles/README.md misses " + config_name)
            self.assertIn(config_name, ci_readme, "ci/README.md misses " + config_name)
        for text, label in (
            (profiles_readme, "profiles/README.md"),
            (ci_readme, "ci/README.md"),
        ):
            self.assertIn("industry standard", text.lower(), label)
            self.assertIn("fail-closed", text.lower(), label)
            self.assertIn("min_msi", text, label)
            self.assertIn("core_min_msi", text, label)
            self.assertIn("80", text, label)
            self.assertIn("90", text, label)
            self.assertIn("mutation-report.json", text, label)
            self.assertIn("Tree-sitter", text, label)
            self.assertIn("Lizard", text, label)
            self.assertIsNone(CJK_RE.search(text), "%s must be English-only" % label)
        self.assertIn("branch_guard.py", ci_readme)


if __name__ == "__main__":
    unittest.main()
