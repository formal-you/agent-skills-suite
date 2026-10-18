#!/usr/bin/env python3
"""Tests for task-decomposition templates, SKILL/rules docs and scaffold_task.py.

These tests intentionally avoid third-party packages (no PyYAML): the templates
are checked structurally, and the real plan-linter v2 CLI is used as the
integration signal when it is available.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".agents" / "skills" / "task-decomposition"
TEMPLATES_DIR = SKILL_DIR / "assets" / "templates"
TEMPLATE_README = TEMPLATES_DIR / "README.md"
SKILL_MD = SKILL_DIR / "SKILL.md"
RULES_DIR = ROOT / ".agents" / "rules"
AGENTS_MD = ROOT / "AGENTS.md"
AGENT_RULES_MD = ROOT / ".agents" / "rules" / "enforcement.md"
SCAFFOLD = SKILL_DIR / "scripts" / "scaffold_task.py"
LINTER = ROOT / ".agents" / "skills" / "plan-linter" / "scripts" / "plan_linter.py"

TEMPLATE_NAMES = (
    "01-contract.template.md",
    "02-dev-workspace.template.md",
    "03-qa-verification.template.md",
    "04-process.template.md",
)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
UNCHECKED_BOX_RE = re.compile(r"^\s*-\s*\[\s\]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ISO_DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}")

FILL_MAP = {
    "TASK_ID": "task-001-auth",
    "TASK_TITLE": "User authentication",
    "MODULE_NAME": "auth",
    "ESTIMATED_LINES": "120",
    "TOUCH_FILE_1": "src/auth/service.py",
    "TOUCH_FILE_2": "src/auth/routes.py",
    "MODULE_SLUG": "auth",
    "ADR_ID_1": "ADR-001",
    "TYPE_CHECK_COMMAND": "python -m mypy src",
    "LINT_COMMAND": "python -m ruff check src",
    "TEST_FILE_PATH": "tests/acceptance/test_auth.py",
    "EDGE_CASE_1": "Given empty credentials, When login is attempted, Then return 400 Bad Request",
    "EDGE_CASE_2": "Given expired token, When authentication is checked, Then return 401 Unauthorized",
    "GOAL_AND_SCOPE": "Implement authentication for the existing service.",
    "OUT_OF_SCOPE": "SSO and external identity providers.",
    "INVARIANT_INPUT_VALIDATION_GIVEN": "an unauthenticated request with malformed credentials",
    "INVARIANT_INPUT_VALIDATION_WHEN": "credentials validation is executed",
    "INVARIANT_INPUT_VALIDATION_THEN": "the request is rejected with 400 before database lookup",
    "INVARIANT_STATE_TRANSITIONS_GIVEN": "a user session in pending state",
    "INVARIANT_STATE_TRANSITIONS_WHEN": "successful verification occurs",
    "INVARIANT_STATE_TRANSITIONS_THEN": "the session transitions to active and cannot return to pending",
    "INVARIANT_IDEMPOTENCY_GIVEN": "an existing active token",
    "INVARIANT_IDEMPOTENCY_WHEN": "a duplicate creation request with the same idempotency key is received",
    "INVARIANT_IDEMPOTENCY_THEN": "the original token is returned without creating duplicate state",
    "INVARIANT_INPUT_VALIDATION": "Malformed credentials are rejected before any lookup.",
    "INVARIANT_STATE_TRANSITIONS": "A session moves from pending to active once, never back.",
    "INVARIANT_IDEMPOTENCY": "Repeated create requests with the same key return the first result.",
    "INHERITED_ADR_SUMMARY": "ADR-001 mandates opaque session tokens.",
    "NOTES": "No open questions.",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def template_text(name: str) -> str:
    return read_text(TEMPLATES_DIR / name)


def extract_frontmatter(text: str) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("document does not start with a YAML frontmatter block")
    return match.group(1)


def fill_contract(text: str) -> str:
    filled = text
    for token, value in FILL_MAP.items():
        filled = filled.replace("{{" + token + "}}", value)
    leftovers = PLACEHOLDER_RE.findall(filled)
    if leftovers:
        raise AssertionError("unmapped placeholders in the contract template: " + repr(sorted(set(leftovers))))
    return filled


def run_script(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCAFFOLD)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        cwd=str(cwd) if cwd else None,
    )


class TemplateStructureTests(unittest.TestCase):
    def test_all_templates_and_readme_exist(self) -> None:
        for name in TEMPLATE_NAMES:
            self.assertTrue((TEMPLATES_DIR / name).is_file(), "missing template: " + name)
        self.assertTrue(TEMPLATE_README.is_file(), "missing assets/templates/README.md")

    def test_no_checked_token_inside_an_unchecked_box(self) -> None:
        for name in TEMPLATE_NAMES:
            for lineno, line in enumerate(template_text(name).splitlines(), start=1):
                if UNCHECKED_BOX_RE.match(line):
                    self.assertNotIn("[x]", line.lower(), f"{name}:{lineno} unchecked box contains [x]: {line}")

    def test_dev_and_qa_templates_have_no_placeholder_tokens(self) -> None:
        forbidden = (re.compile(r"\{\{[^}]*\}\}"), re.compile(r"\[TBD\]"), re.compile(r"\bTODO\b"))
        for name in ("02-dev-workspace.template.md", "03-qa-verification.template.md"):
            text = template_text(name)
            for pattern in forbidden:
                match = pattern.search(text)
                if match:
                    self.fail(name + " must stay token-free; found: " + match.group(0))

    def test_handoff_and_verdict_boxes_are_unchecked(self) -> None:
        dev = template_text("02-dev-workspace.template.md")
        qa = template_text("03-qa-verification.template.md")
        self.assertIn("- [ ] WAITING_FOR_QA", dev)
        self.assertIn("- [ ] QA_PASSED", qa)
        self.assertIn("- [ ] REWORK_REQUIRED", qa)
        for text, markers in ((dev, ("WAITING_FOR_QA",)), (qa, ("QA_PASSED", "REWORK_REQUIRED"))):
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("<!--"):
                    continue  # instructions may name the marker without being a checkbox
                for marker in markers:
                    if marker in line:
                        self.assertTrue(stripped.startswith("- [ ]"), f"unexpected marker line: {line}")

    def test_process_event_table_is_header_and_separator_only(self) -> None:
        text = template_text("04-process.template.md")
        lines = text.splitlines()
        heading = next((i for i, line in enumerate(lines) if re.match(r"^##\s+2[.\s)]", line)), None)
        self.assertIsNotNone(heading, "04-process has no '## 2' event-log section")
        end = next((i for i in range(heading + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        rows = [line for line in lines[heading:end] if line.strip().startswith("|")]
        self.assertEqual(len(rows), 2, "event table must contain exactly header + separator, got: " + repr(rows))
        self.assertRegex(rows[1].strip(), r"^\|[\s:|-]+\|$")

    def test_process_has_no_sample_events_or_fake_timestamps(self) -> None:
        text = template_text("04-process.template.md")
        for code in ("HANDOFF_QA_REQUESTED", "TASK_TERMINATED_DONE", "REWORK_TRIGGERED"):
            self.assertNotIn(code, text, "sample event code must not ship in the template: " + code)
        self.assertIsNone(ISO_DATE_RE.search(text), "fake ISO date found in 04-process template")
        self.assertNotIn("EV-0", text)
        lowered = text.lower()
        for phrase in ("three templates", "three documents", "3 templates"):
            self.assertNotIn(phrase, lowered)
        self.assertIn("derived", lowered)
        self.assertIn("authoritative", lowered)

    def test_process_status_card_has_real_retry_count(self) -> None:
        text = template_text("04-process.template.md")
        self.assertIn("retry_count: 0", text)
        self.assertNotIn("{{RETRY_COUNT}}", text)
        for key in ("macro_status:", "micro_phase:", "current_lock_holder:", "last_heartbeat:"):
            self.assertIn(key, text)

    def test_process_status_card_starts_initialized(self) -> None:
        text = template_text("04-process.template.md")
        self.assertIn('macro_status: "TODO"', text)
        self.assertIn('micro_phase: "UNASSIGNED"', text)
        self.assertIn('current_lock_holder: "None"', text)
        self.assertIn('last_heartbeat: ""', text)
        for token in ("{{MACRO_STATUS}}", "{{MICRO_PHASE}}", "{{LOCK_HOLDER}}", "{{LAST_HEARTBEAT}}", "{{NOTES}}"):
            self.assertNotIn(token, text, "04 status card must be initialized, not placeholder-filled: " + token)

    def test_templates_have_no_domain_examples(self) -> None:
        banned = ("ecommerce", "e-commerce", "shopping", "cart", "checkout", "inventory", "sku", "payment", "tenant")
        for name in ("02-dev-workspace.template.md", "03-qa-verification.template.md", "04-process.template.md"):
            lowered = template_text(name).lower()
            for word in banned:
                self.assertNotIn(word, lowered, f"domain example {word!r} found in {name}")

    def test_english_canonical_content(self) -> None:
        paths = [TEMPLATES_DIR / name for name in TEMPLATE_NAMES] + [
            TEMPLATE_README, SKILL_MD,
            SKILL_DIR / "references" / "decomposition-rules.md",
            SKILL_DIR / "references" / "role-lifecycle.md",
            AGENTS_MD, AGENT_RULES_MD,
        ] + sorted(RULES_DIR.glob("*.md"))
        for path in paths:
            self.assertIsNone(CJK_RE.search(read_text(path)), "non-English CJK content in " + str(path))


class ContractFrontmatterTests(unittest.TestCase):
    def test_contract_starts_with_authoritative_frontmatter(self) -> None:
        text = template_text("01-contract.template.md")
        self.assertTrue(text.startswith("---\n"), "01-contract must start with YAML frontmatter")
        frontmatter = extract_frontmatter(text)
        for key in (
            "task_id", "title", "module", "dependencies", "estimated_lines", "touch_files",
            "origin_spec_anchor", "adherence_adrs", "dod",
        ):
            self.assertRegex(frontmatter, r"(?m)^" + key + r":", "missing frontmatter key: " + key)
        for nested in ("type_check", "lint", "test_file", "edge_cases"):
            self.assertRegex(frontmatter, r"(?m)^\s+" + nested + r":", "missing dod key: " + nested)
        self.assertRegex(frontmatter, r"(?m)^\s+- action: (?:create|modify)\s*(?:#.*)?$")
        self.assertRegex(frontmatter, r"(?m)^\s+path:")

    def test_filled_frontmatter_matches_linter_schema(self) -> None:
        frontmatter = extract_frontmatter(fill_contract(template_text("01-contract.template.md")))
        self.assertRegex(frontmatter, r'(?m)^task_id: "task-001-auth"$')
        self.assertRegex(frontmatter, r'(?m)^estimated_lines: 120$')
        self.assertRegex(frontmatter, r'(?m)^origin_spec_anchor: "#sec-auth"$')
        self.assertIn('adherence_adrs: ["ADR-001"]', frontmatter)
        self.assertIn("dependencies: []", frontmatter)
        actions = re.findall(r"(?m)^\s+- action: (create|modify)\s*(?:#.*)?$", frontmatter)
        self.assertGreaterEqual(len(actions), 1)
        self.assertLessEqual(len(actions), 3)
        edge_cases = re.findall(r"(?m)^\s{4}- \"", frontmatter)
        self.assertGreaterEqual(len(edge_cases), 2)
        for command_key in ("type_check", "lint", "test_file"):
            self.assertRegex(frontmatter, r"(?m)^\s+" + command_key + r': "\S')

    def test_every_template_placeholder_is_documented(self) -> None:
        tokens: set[str] = set()
        for name in TEMPLATE_NAMES:
            tokens.update(PLACEHOLDER_RE.findall(template_text(name)))
        self.assertTrue(tokens, "templates contain no placeholders")
        readme = read_text(TEMPLATE_README)
        documented = set(PLACEHOLDER_RE.findall(readme))
        self.assertLessEqual(tokens, documented, "undocumented placeholders: " + repr(sorted(tokens - documented)))
        for token in tokens:
            self.assertIn(token, readme, "placeholder not documented in README: " + token)
        extras = documented - tokens
        self.assertLessEqual(extras, {"{{UPPER_SNAKE}}"}, "README documents unknown placeholders: " + repr(sorted(extras)))

    def test_filled_contract_passes_plan_linter_v2_when_available(self) -> None:
        if not LINTER.is_file():
            self.skipTest("plan-linter is not available")
        help_result = subprocess.run(
            [sys.executable, str(LINTER), "--help"],
            capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=str(ROOT),
        )
        if "--json" not in (help_result.stdout or ""):
            self.skipTest("plan-linter v2 (YAML frontmatter + --json) is not available yet")
        with tempfile.TemporaryDirectory() as tmp:
            tasks = Path(tmp) / "tasks"
            scaffold = subprocess.run(
                [sys.executable, str(SCAFFOLD), "--task-id", "task-001-auth",
                 "--title", "User authentication", "--tasks-dir", str(tasks)],
                capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=str(ROOT),
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            task_dir = tasks / "task-001-auth"
            # A planner fills 01; 02/03/04 stay exactly as scaffolded (blank role forms).
            (task_dir / "01-contract.md").write_text(
                fill_contract(read_text(task_dir / "01-contract.md")), encoding="utf-8"
            )
            for doc_name in ("02-dev-workspace.md", "03-qa-verification.md"):
                doc_text = read_text(task_dir / doc_name)
                self.assertNotIn("{{", doc_text, "fresh " + doc_name + " must stay token-free")
            result = subprocess.run(
                [sys.executable, str(LINTER), "--tasks-dir", str(tasks), "--json"],
                capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=str(ROOT),
            )
            self.assertEqual(
                result.returncode, 0,
                "plan-linter rejected the filled template\nstdout: " + result.stdout + "\nstderr: " + result.stderr,
            )
            payload = json.loads(result.stdout)
            self.assertTrue(payload.get("passed"), "plan-linter JSON reports failure: " + result.stdout)


class ScaffoldTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.tasks = self.root / "tasks"

    def scaffold(self, *extra: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        args = ["--task-id", "task-001-auth", "--title", "User authentication", "--tasks-dir", str(self.tasks)]
        return run_script(args + list(extra), cwd=cwd)

    def test_help_and_version(self) -> None:
        help_result = run_script(["--help"])
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("usage", help_result.stdout.lower())
        version_result = run_script(["--version"])
        self.assertEqual(version_result.returncode, 0)
        self.assertIn("2.0.0", version_result.stdout)

    def test_creates_four_documents_with_substitutions(self) -> None:
        result = self.scaffold()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.tasks / "task-001-auth"
        for name in ("01-contract.md", "02-dev-workspace.md", "03-qa-verification.md", "04-process.md"):
            self.assertTrue((target / name).is_file(), "missing scaffolded file: " + name)
        contract = read_text(target / "01-contract.md")
        self.assertTrue(contract.startswith("---\n"))
        self.assertIn('task_id: "task-001-auth"', contract)
        self.assertIn('title: "User authentication"', contract)
        self.assertNotIn("{{TASK_ID}}", contract)
        self.assertNotIn("{{TASK_TITLE}}", contract)
        self.assertIn("{{MODULE_NAME}}", contract, "non-scaffold placeholders must be preserved")
        dev_text = read_text(target / "02-dev-workspace.md")
        qa_text = read_text(target / "03-qa-verification.md")
        for doc_text in (dev_text, qa_text):
            self.assertNotIn("{{", doc_text)
            self.assertNotIn("[TBD]", doc_text)
            self.assertNotRegex(doc_text, r"\bTODO\b")
        self.assertIn("- [ ] WAITING_FOR_QA", dev_text)
        self.assertIn("- [ ] QA_PASSED", qa_text)
        self.assertIn("retry_count: 0", read_text(target / "04-process.md"))
        self.assertIn("remaining placeholders", result.stdout.lower())

    def test_dry_run_writes_nothing(self) -> None:
        result = self.scaffold("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.tasks.exists(), "--dry-run must not create the tasks directory")
        self.assertIn("would create", result.stdout.lower())

    def test_refuses_overwrite_without_force(self) -> None:
        first = self.scaffold()
        self.assertEqual(first.returncode, 0, first.stderr)
        contract_path = self.tasks / "task-001-auth" / "01-contract.md"
        before = read_text(contract_path)
        second = self.scaffold()
        self.assertEqual(second.returncode, 1, "overwrite without --force must exit 1")
        self.assertIn("--force", second.stderr)
        self.assertEqual(read_text(contract_path), before)

    def test_force_overwrites_existing_files(self) -> None:
        self.assertEqual(self.scaffold().returncode, 0)
        other = ["--task-id", "task-001-auth", "--title", "Renamed title", "--tasks-dir", str(self.tasks), "--force"]
        result = run_script(other)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('title: "Renamed title"', read_text(self.tasks / "task-001-auth" / "01-contract.md"))

    def test_invalid_task_id_is_usage_error(self) -> None:
        result = run_script(["--task-id", "../escape", "--title", "x", "--tasks-dir", str(self.tasks)])
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "escape").exists())
        self.assertFalse(self.tasks.exists())

    def test_works_from_an_unrelated_working_directory(self) -> None:
        result = self.scaffold(cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.tasks / "task-001-auth" / "04-process.md").is_file())


class SkillAndRulesTests(unittest.TestCase):
    def test_skill_frontmatter_and_size(self) -> None:
        text = read_text(SKILL_MD)
        frontmatter = extract_frontmatter(text)
        for key in ("name", "description", "license", "compatibility", "metadata"):
            self.assertRegex(frontmatter, r"(?m)^" + key + r":", "missing SKILL frontmatter key: " + key)
        self.assertRegex(frontmatter, r"(?m)^name: task-decomposition$")
        self.assertIn("Use when", frontmatter)
        self.assertIn("Do not use when", frontmatter)
        self.assertRegex(frontmatter, r'(?m)^\s+version: "2\.0\.0"$')
        self.assertRegex(frontmatter, r"(?m)^\s+category: spec-pipeline$")
        self.assertLess(len(text.splitlines()), 200, "SKILL.md must stay below 200 lines")

    def test_skill_has_no_repo_absolute_paths(self) -> None:
        text = read_text(SKILL_MD)
        for marker in ("D:\\", "C:\\", "/home/", "/Users/"):
            self.assertNotIn(marker, text, "repo-absolute path in SKILL.md: " + marker)

    def test_skill_relative_links_resolve(self) -> None:
        text = read_text(SKILL_MD)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#")):
                continue
            path = (SKILL_DIR / target.split("#")[0]).resolve()
            self.assertTrue(path.exists(), "broken SKILL.md link: " + target)

    def test_all_rules_have_model_decision_frontmatter(self) -> None:
        names = sorted(path.name for path in RULES_DIR.glob("*.md"))
        self.assertEqual(
            names,
            ["architect.md", "dev.md", "enforcement.md", "orchestrator.md", "planner.md", "pm.md", "qa.md", "reviewer.md"],
        )
        self.assertFalse(
            (RULES_DIR / "README.md").exists(),
            "rules README must move to .agents/rules/enforcement.md",
        )
        for name in names:
            text = read_text(RULES_DIR / name)
            frontmatter = extract_frontmatter(text)
            self.assertRegex(frontmatter, r"(?m)^trigger: model_decision$", name + " lacks model_decision trigger")
            self.assertRegex(frontmatter, r'(?m)^description: "\S.+\"$', name + " lacks a description")

    def test_reviewer_and_orchestrator_rules(self) -> None:
        reviewer = read_text(RULES_DIR / "reviewer.md")
        for needle in ("Write scope:** none", "Gate 2", "hallucination", "ADR", "Must not"):
            self.assertIn(needle, reviewer, "reviewer rule misses: " + needle)
        orchestrator = read_text(RULES_DIR / "orchestrator.md")
        for needle in ("PRD → spec → task bundles", "Gate 1", "Gate 2", "one owner", "Must not"):
            self.assertIn(needle, orchestrator, "orchestrator rule misses: " + needle)

    def test_agent_rules_documents_enforcement_layers(self) -> None:
        text = read_text(AGENT_RULES_MD)
        for layer in ("L0", "L1", "L2"):
            self.assertIn(layer, text)
        self.assertIn("tools/rbac_audit.py", text)
        self.assertIn("not** physical enforcement", text)
        self.assertIn("derived", text.lower())
        self.assertIn("Reviewer (Gate 2)", text)
        self.assertIn("Orchestrator", text)

    def test_agents_md_points_to_details(self) -> None:
        text = read_text(AGENTS_MD)
        for needle in (".agents/rules/enforcement.md", "01-contract.md", "02-dev-workspace.md",
                       "03-qa-verification.md", "04-process.md", "Goldilocks", "skills/README.md"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
