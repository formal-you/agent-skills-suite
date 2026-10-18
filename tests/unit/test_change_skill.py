"""Tests for the brownfield change skill: proposal -> one task bundle -> archive.

Black-box via subprocess and temporary directories. Run from the repository root:

    python -m unittest tests.unit.test_change_skill -v
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGE_SKILL = REPO_ROOT / ".agents" / "skills" / "change"
SCRIPTS = CHANGE_SKILL / "scripts"
SCAFFOLD_CHANGE = SCRIPTS / "scaffold_change.py"
STANDARDS_EXTRACT = SCRIPTS / "standards_extract.py"
LINT_CHANGE = SCRIPTS / "lint_change.py"
SKILL_MD = CHANGE_SKILL / "SKILL.md"
PROTOCOL = CHANGE_SKILL / "references" / "brownfield-protocol.md"
PROPOSAL_TEMPLATE = CHANGE_SKILL / "assets" / "templates" / "proposal.template.md"
TASK_SCAFFOLD = REPO_ROOT / ".agents" / "skills" / "task-decomposition" / "scripts" / "scaffold_task.py"
PLAN_LINTER = REPO_ROOT / ".agents" / "skills" / "plan-linter" / "scripts" / "plan_linter.py"

PLACEHOLDER_RE = re.compile(r"\{\{[^}\n]+\}\}")
ANCHOR_TOKEN_RE = re.compile(r"#sec-[a-z0-9-]+")
ISO_DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

CHANGE_ID = "CHG-001-rate-limit"
ANCHOR = "#sec-auth-tokens"

BASE_SPEC = """# 02-tech-spec: Demo

## 1. Authentication

Opaque tokens are issued by the identity service. #sec-auth-tokens

Sessions are stored server-side. #sec-auth-session
"""

REMAINING_CONTRACT_TOKENS = {
    "MODULE_NAME": "auth",
    "ADR_ID_1": "ADR-001",
    "TYPE_CHECK_COMMAND": "python -m mypy src",
    "LINT_COMMAND": "python -m ruff check src",
    "TEST_FILE_PATH": "tests/acceptance/test_rate_limit.py",
    "EDGE_CASE_1": "Given a sixth request within the window, When rate limit checked, Then return 429",
    "EDGE_CASE_2": "Given a request for an unknown user, When profile requested, Then return 404",
    "INVARIANT_INPUT_VALIDATION_GIVEN": "an unauthenticated request with malformed identity",
    "INVARIANT_INPUT_VALIDATION_WHEN": "identity validation is executed",
    "INVARIANT_INPUT_VALIDATION_THEN": "the request is rejected before any token lookup",
    "INVARIANT_STATE_TRANSITIONS_GIVEN": "a token in active state",
    "INVARIANT_STATE_TRANSITIONS_WHEN": "expiry duration elapses",
    "INVARIANT_STATE_TRANSITIONS_THEN": "the token transitions to expired and is never valid again",
    "INVARIANT_IDEMPOTENCY_GIVEN": "an existing valid token",
    "INVARIANT_IDEMPOTENCY_WHEN": "repeated requests with the same token are received",
    "INVARIANT_IDEMPOTENCY_THEN": "the requests do not extend the window",
    "INVARIANT_INPUT_VALIDATION": "Malformed identities are rejected before any token lookup.",
    "INVARIANT_STATE_TRANSITIONS": "A token is either valid or expired, never both.",
    "INVARIANT_IDEMPOTENCY": "Repeated valid requests with the same token do not extend the window.",
    "INHERITED_ADR_SUMMARY": "ADR-001 keeps tokens opaque and server-validated.",
}


def read_text(path):
    return path.read_text(encoding="utf-8")


def run(script, *arguments, cwd=None):
    command = [sys.executable, str(script)] + [str(argument) for argument in arguments]
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def extract_frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("document does not start with a YAML frontmatter block")
    return match.group(1)


def frontmatter_key(frontmatter, key):
    match = re.search(r"(?m)^" + re.escape(key) + r":\s*(.+?)\s*$", frontmatter)
    if not match:
        raise AssertionError("missing frontmatter key: " + key)
    value = match.group(1)
    if value.startswith("[") and value.endswith("]"):
        return value
    return value.strip('"')


def fill_contract_tokens(text):
    filled = text
    for token, value in REMAINING_CONTRACT_TOKENS.items():
        filled = filled.replace("{{" + token + "}}", value)
    leftovers = PLACEHOLDER_RE.findall(filled)
    if leftovers:
        raise AssertionError("unmapped placeholders in the contract: " + repr(sorted(set(leftovers))))
    return filled


class TempRepoTestCase(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="change-skill-")
        self.addCleanup(self._temp.cleanup)
        self.temp = Path(self._temp.name)

    def make_repo(self, spec_text=BASE_SPEC):
        repo = self.temp / "repo"
        specs = repo / ".specs"
        specs.mkdir(parents=True, exist_ok=True)
        (specs / "02-tech-spec.md").write_text(spec_text, encoding="utf-8")
        return repo

    def scaffold(self, repo, *extra):
        arguments = [
            "--change-id",
            CHANGE_ID,
            "--title",
            "Rate limit login attempts",
            "--anchor",
            ANCHOR,
            "--repo-root",
            str(repo),
        ]
        return run(SCAFFOLD_CHANGE, *(arguments + list(extra)))

    def scaffold_happy(self, repo, *extra):
        extra_arguments = (
            "--kind",
            "modify",
            "--size-class",
            "micro",
            "--estimated-lines",
            "40",
            "--touch-files",
            "modify:src/auth/rate_limit.py",
        )
        result = self.scaffold(repo, *(extra_arguments + tuple(extra)))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def proposal_path(self, repo):
        return repo / ".specs" / "changes" / CHANGE_ID / "proposal.md"

    def bundle_dir(self, repo):
        return repo / "tasks" / CHANGE_ID

    def assert_token_free_role_forms(self, bundle):
        for name in ("02-dev-workspace.md", "03-qa-verification.md", "04-process.md"):
            text = read_text(bundle / name)
            self.assertIsNone(PLACEHOLDER_RE.search(text), name + " must not contain template tokens")
            self.assertNotIn("[TBD]", text, name + " must not contain [TBD]")
            if name != "04-process.md":
                self.assertNotRegex(text, r"\bTODO\b", name + " must stay token-free")


class ScaffoldChangeTests(TempRepoTestCase):
    def test_happy_path_proposal_and_bundle(self):
        repo = self.make_repo()
        (repo / "src" / "auth").mkdir(parents=True)
        (repo / "src" / "auth" / "rate_limit.py").write_text("# implementation\n", encoding="utf-8")
        result = self.scaffold_happy(repo, "--dependencies", "task-000-bootstrap")
        self.assertEqual(result.returncode, 0, result.stderr)

        proposal = self.proposal_path(repo)
        self.assertTrue(proposal.is_file())
        frontmatter = extract_frontmatter(read_text(proposal))
        self.assertEqual(frontmatter_key(frontmatter, "change_id"), CHANGE_ID)
        self.assertEqual(frontmatter_key(frontmatter, "title"), "Rate limit login attempts")
        self.assertEqual(frontmatter_key(frontmatter, "status"), "proposed")
        self.assertEqual(frontmatter_key(frontmatter, "kind"), "modify")
        self.assertEqual(frontmatter_key(frontmatter, "base_spec"), ".specs/02-tech-spec.md")
        expected_sha = hashlib.sha256((repo / ".specs" / "02-tech-spec.md").read_bytes()).hexdigest()
        self.assertEqual(frontmatter_key(frontmatter, "base_spec_sha256"), expected_sha)
        self.assertIn(ANCHOR, frontmatter)
        created = frontmatter_key(frontmatter, "created")
        self.assertRegex(created, r"^\d{4}-\d{2}-\d{2}$")
        proposal_body = read_text(proposal)
        self.assertIsNone(
            PLACEHOLDER_RE.search(proposal_body), "the scaffolded proposal must be token-free"
        )
        self.assertIn("### [CHG-1] " + ANCHOR, proposal_body)
        self.assertIn("- Before:", proposal_body)
        self.assertIn("- After:", proposal_body)
        self.assertIn("src/auth/rate_limit.py", proposal_body)

        bundle = self.bundle_dir(repo)
        for name in ("01-contract.md", "02-dev-workspace.md", "03-qa-verification.md", "04-process.md"):
            self.assertTrue((bundle / name).is_file(), "missing bundle document: " + name)
        contract = read_text(bundle / "01-contract.md")
        contract_frontmatter = extract_frontmatter(contract)
        self.assertEqual(frontmatter_key(contract_frontmatter, "task_id"), CHANGE_ID)
        self.assertEqual(frontmatter_key(contract_frontmatter, "change_id"), CHANGE_ID)
        self.assertEqual(frontmatter_key(contract_frontmatter, "size_class"), "micro")
        self.assertEqual(frontmatter_key(contract_frontmatter, "origin_spec_anchor"), ANCHOR)
        self.assertIn("estimated_lines: 40", contract_frontmatter)
        self.assertIn('["task-000-bootstrap"]', contract_frontmatter)
        self.assertIn("action: modify", contract_frontmatter)
        self.assertIn('path: "src/auth/rate_limit.py"', contract_frontmatter)
        self.assertNotIn("{{GOAL_AND_SCOPE}}", contract)
        self.assertNotIn("{{OUT_OF_SCOPE}}", contract)
        self.assertNotIn("{{NOTES}}", contract)
        self.assertIn("{{MODULE_NAME}}", contract, "Planner-only placeholders must stay")
        self.assert_token_free_role_forms(bundle)
        self.assertIn("### Feature: Rate limit login attempts", contract)
        self.assertIn("#### Scenario 1: Input validation", contract)
        self.assertIn("- **Given** {{INVARIANT_INPUT_VALIDATION_GIVEN}}", contract)
        self.assertIn("- **When** {{INVARIANT_INPUT_VALIDATION_WHEN}}", contract)
        self.assertIn("- **Then** {{INVARIANT_INPUT_VALIDATION_THEN}}", contract)
        self.assertIn("#### Scenario 2: State transitions", contract)
        self.assertIn("#### Scenario 3: Idempotency and data consistency", contract)

    def test_missing_base_spec_exits_2(self):
        repo = self.temp / "repo"
        repo.mkdir()
        result = self.scaffold(repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("base spec", result.stderr.lower())
        self.assertFalse((repo / ".specs" / "changes").exists())
        self.assertFalse((repo / "tasks").exists())

    def test_invalid_anchor_format_exits_2(self):
        repo = self.make_repo()
        result = self.scaffold(repo, "--anchor", "sec-auth-tokens")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--anchor", result.stderr)

    def test_unknown_anchor_is_refused(self):
        repo = self.make_repo()
        result = self.scaffold(repo, "--anchor", "#sec-invented-anchor")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not present", result.stderr)
        self.assertFalse((repo / ".specs" / "changes").exists())

    def test_dry_run_writes_nothing(self):
        repo = self.make_repo()
        result = self.scaffold(repo, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would create", result.stdout.lower())
        self.assertFalse((repo / ".specs" / "changes").exists())
        self.assertFalse((repo / "tasks").exists())

    def test_refuses_existing_change_and_force_overwrites(self):
        repo = self.make_repo()
        self.assertEqual(self.scaffold(repo).returncode, 0)
        second = self.scaffold(repo)
        self.assertEqual(second.returncode, 2, "an existing change directory must exit 2")
        self.assertIn("--force", second.stderr)
        forced = self.scaffold(repo, "--force", "--title", "Rate limit login attempts v2")
        self.assertEqual(forced.returncode, 0, forced.stderr)
        self.assertIn('title: "Rate limit login attempts v2"', read_text(self.proposal_path(repo)))

    def test_path_containment_is_refused(self):
        repo = self.make_repo()
        result = self.scaffold(repo, "--change-id", "../escape")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.temp / "escape").exists())
        self.assertFalse((repo / "tasks").exists())
        result = self.scaffold(repo, "--change-id", "nested/escape")
        self.assertEqual(result.returncode, 2)

    def test_json_output_contract(self):
        repo = self.make_repo()
        result = self.scaffold(repo, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "scaffold_change")
        self.assertEqual(payload["change_id"], CHANGE_ID)
        self.assertEqual(payload["base_spec"], ".specs/02-tech-spec.md")
        self.assertEqual(payload["proposal"], ".specs/changes/" + CHANGE_ID + "/proposal.md")
        self.assertEqual(payload["task_bundle"], "tasks/" + CHANGE_ID)
        self.assertIn("{{MODULE_NAME}}", payload["remaining_placeholders"])

    def test_unknown_repo_root_is_usage_error(self):
        result = run(
            SCAFFOLD_CHANGE,
            "--change-id",
            CHANGE_ID,
            "--title",
            "Rate limit login attempts",
            "--anchor",
            ANCHOR,
            "--repo-root",
            self.temp / "absent",
        )
        self.assertEqual(result.returncode, 2)

    def test_fallback_bundle_when_sibling_scaffolder_absent(self):
        repo = self.make_repo()
        relocated = self.temp / "relocated" / "skills" / "change"
        shutil.copytree(CHANGE_SKILL, relocated, ignore=shutil.ignore_patterns("__pycache__"))
        result = run(
            relocated / "scripts" / "scaffold_change.py",
            "--change-id",
            CHANGE_ID,
            "--title",
            "Rate limit login attempts",
            "--anchor",
            ANCHOR,
            "--repo-root",
            str(repo),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fallback", (result.stderr + result.stdout).lower())
        bundle = repo / "tasks" / CHANGE_ID
        for name in ("01-contract.md", "02-dev-workspace.md", "03-qa-verification.md", "04-process.md"):
            self.assertTrue((bundle / name).is_file(), "fallback bundle missing: " + name)
        contract = read_text(bundle / "01-contract.md")
        self.assertIn('change_id: "' + CHANGE_ID + '"', contract)
        self.assertIn('size_class: "standard"', contract)
        self.assertIn('origin_spec_anchor: "' + ANCHOR + '"', contract)
        self.assert_token_free_role_forms(bundle)
        self.assertIn("### Feature: Rate limit login attempts", contract)
        self.assertIn("#### Scenario 1: Input validation", contract)
        self.assertIn("- **Given** {{INVARIANT_INPUT_VALIDATION_GIVEN}}", contract)
        self.assertIn("- **When** {{INVARIANT_INPUT_VALIDATION_WHEN}}", contract)
        self.assertIn("- **Then** {{INVARIANT_INPUT_VALIDATION_THEN}}", contract)
        self.assertIn("#### Scenario 2: State transitions", contract)
        self.assertIn("#### Scenario 3: Idempotency and data consistency", contract)
        lint = run(
            relocated / "scripts" / "lint_change.py",
            "--change-id",
            CHANGE_ID,
            "--repo-root",
            str(repo),
            "--json",
        )
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        self.assertTrue(json.loads(lint.stdout)["passed"])


class StandardsExtractTests(TempRepoTestCase):
    def make_synthetic_repo(self):
        repo = self.make_repo()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nrequires-python = ">=3.9"\n\n'
            "[tool.ruff]\nline-length = 100\n\n"
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )
        (repo / "package.json").write_text(
            json.dumps(
                {
                    "name": "demo",
                    "engines": {"node": ">=18"},
                    "scripts": {"test": "vitest run", "lint": "eslint ."},
                }
            ),
            encoding="utf-8",
        )
        (repo / "tsconfig.json").write_text("{}", encoding="utf-8")
        (repo / ".eslintrc.json").write_text("{}", encoding="utf-8")
        (repo / "tests" / "unit").mkdir(parents=True)
        (repo / "tests" / "acceptance").mkdir(parents=True)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        return repo

    def test_detects_config_layout_runtime_and_commands(self):
        repo = self.make_synthetic_repo()
        result = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("pyproject.toml", payload["config_files"])
        self.assertIn("package.json", payload["config_files"])
        self.assertIn(".eslintrc.json", payload["config_files"])
        self.assertIn("tsconfig.json", payload["config_files"])
        self.assertIn("tests/unit/", payload["test_layout"]["directories"])
        self.assertIn("tests/acceptance/", payload["test_layout"]["directories"])
        self.assertIn("src/", payload["source_dirs"])
        runtime = {(item["name"], item["version"]) for item in payload["runtime"]}
        self.assertIn(("Python", ">=3.9"), runtime)
        self.assertIn(("Node.js", ">=18"), runtime)
        commands = {item["command"] for item in payload["commands"]}
        self.assertIn("python -m pytest", commands)
        self.assertIn("python -m ruff check .", commands)
        self.assertIn("npm test", commands)
        self.assertIn(ANCHOR, {item["anchor"] for item in payload["anchors"]})

        report = read_text(repo / ".specs" / "change-context" / "standards.md")
        for needle in (
            "pyproject.toml",
            "requires-python",
            ">=3.9",
            "Node.js",
            ">=18",
            "tests/unit",
            "src/",
            ANCHOR,
            "python -m pytest",
            "## 7. Implicit constraints",
        ):
            self.assertIn(needle, report, "standards report misses: " + needle)
        self.assertIsNone(ISO_DATE_RE.search(report), "standards report must stay timestamp-free")

    def test_check_detects_staleness_and_write_is_idempotent(self):
        repo = self.make_synthetic_repo()
        out = repo / ".specs" / "change-context" / "standards.md"
        first = run(STANDARDS_EXTRACT, "--repo-root", str(repo))
        self.assertEqual(first.returncode, 0, first.stderr)
        original = read_text(out)
        run(STANDARDS_EXTRACT, "--repo-root", str(repo))
        self.assertEqual(read_text(out), original, "standards report must be idempotent")
        current = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--check")
        self.assertEqual(current.returncode, 0, current.stderr)

        pyproject = repo / "pyproject.toml"
        pyproject.write_text(
            read_text(pyproject).replace('requires-python = ">=3.9"', 'requires-python = ">=3.10"'),
            encoding="utf-8",
        )
        stale = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--check")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("stale", stale.stderr.lower())
        self.assertEqual(read_text(out), original, "check must not rewrite the report")

        rewritten = run(STANDARDS_EXTRACT, "--repo-root", str(repo))
        self.assertEqual(rewritten.returncode, 0, rewritten.stderr)
        self.assertIn(">=3.10", read_text(out))
        self.assertEqual(run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--check").returncode, 0)

    def test_dry_run_writes_nothing(self):
        repo = self.make_synthetic_repo()
        result = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((repo / ".specs" / "change-context").exists())

    def test_missing_repo_root_is_usage_error(self):
        result = run(STANDARDS_EXTRACT, "--repo-root", str(self.temp / "absent"))
        self.assertEqual(result.returncode, 2)

    def test_nested_workspace_manifest_commands_and_runtime(self):
        repo = self.make_repo()
        package = repo / "pkg"
        package.mkdir()
        (package / "package.json").write_text(
            json.dumps(
                {
                    "name": "nested",
                    "engines": {"node": ">=22"},
                    "scripts": {"test": "vitest run", "typecheck": "tsc --noEmit"},
                }
            ),
            encoding="utf-8",
        )
        (package / "tsconfig.json").write_text("{}", encoding="utf-8")
        (package / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
        result = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("pkg/package.json", payload["config_files"])
        commands = {item["command"] for item in payload["commands"]}
        self.assertIn("cd pkg && pnpm test", commands, "nested manifest commands must be prefixed")
        self.assertIn("cd pkg && pnpm run typecheck", commands)
        runtime = {(item["name"], item["version"], item["source"]) for item in payload["runtime"]}
        self.assertIn(("Node.js", ">=22", "pkg/package.json engines.node"), runtime)

    def test_generated_tasks_and_changes_do_not_invalidate_report(self):
        repo = self.make_synthetic_repo()
        out = repo / ".specs" / "change-context" / "standards.md"
        self.assertEqual(run(STANDARDS_EXTRACT, "--repo-root", str(repo)).returncode, 0)
        original = read_text(out)

        bundle = repo / "tasks" / "CHG-001-demo"
        bundle.mkdir(parents=True)
        (bundle / "01-contract.md").write_text("# placeholder\n", encoding="utf-8")
        proposal = repo / ".specs" / "changes" / "CHG-001-demo" / "proposal.md"
        proposal.parent.mkdir(parents=True)
        proposal.write_text("# Change\n\nReuses " + ANCHOR + "\n", encoding="utf-8")

        current = run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--check")
        self.assertEqual(
            current.returncode, 0, "generated tasks/ and .specs/changes must not stale the report"
        )
        self.assertEqual(read_text(out), original)
        payload = json.loads(run(STANDARDS_EXTRACT, "--repo-root", str(repo), "--json").stdout)
        self.assertNotIn("tasks/", payload["source_dirs"])
        anchor_files = next(
            item["files"] for item in payload["anchors"] if item["anchor"] == ANCHOR
        )
        self.assertFalse(
            any("changes/" in path for path in anchor_files),
            "in-flight proposals must not be treated as specification sources",
        )


class LintChangeTests(TempRepoTestCase):
    def test_passes_after_scaffold(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["changes"][0]["change_id"], CHANGE_ID)
        codes = {warning["code"] for warning in payload["changes"][0]["warnings"]}
        self.assertIn("GUIDANCE_REMAINS", codes)

    def test_detects_base_spec_drift(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        spec = repo / ".specs" / "02-tech-spec.md"
        spec.write_text(read_text(spec) + "\nChanged after scaffolding.\n", encoding="utf-8")
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        codes = {error["code"] for error in payload["changes"][0]["errors"]}
        self.assertIn("BASE_SPEC_DRIFT", codes)

    def test_archived_proposal_is_exempt_from_drift(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        proposal = self.proposal_path(repo)
        proposal.write_text(
            read_text(proposal).replace('status: "proposed"', 'status: "archived"'), encoding="utf-8"
        )
        spec = repo / ".specs" / "02-tech-spec.md"
        spec.write_text(read_text(spec) + "\nConverged change appended.\n", encoding="utf-8")
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        codes = {warning["code"] for warning in payload["changes"][0]["warnings"]}
        self.assertIn("ARCHIVED_DRIFT_SKIPPED", codes)

    def test_rejects_invented_anchor(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        proposal = self.proposal_path(repo)
        text = read_text(proposal)
        text = text.replace('- "' + ANCHOR + '"', '- "#sec-invented-anchor"')
        text = text.replace("### [CHG-1] " + ANCHOR, "### [CHG-1] #sec-invented-anchor")
        proposal.write_text(text, encoding="utf-8")
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        codes = {error["code"] for error in payload["changes"][0]["errors"]}
        self.assertTrue({"UNKNOWN_ANCHOR", "BLOCK_ANCHOR_UNKNOWN"} & codes, codes)

    def test_requires_matching_task_bundle(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        shutil.rmtree(self.bundle_dir(repo))
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        codes = {error["code"] for error in payload["changes"][0]["errors"]}
        self.assertIn("TASK_BUNDLE_MISSING", codes)

    def test_default_invocation_scans_all_changes(self):
        repo = self.make_repo()
        self.scaffold_happy(repo)
        result = run(LINT_CHANGE, "--change-id", CHANGE_ID, "--repo-root", str(repo))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)


class ScaffoldTaskBrownfieldTests(TempRepoTestCase):
    def test_change_fields_only_when_supplied(self):
        tasks = self.temp / "tasks"
        plain = run(
            TASK_SCAFFOLD,
            "--task-id",
            "task-001-auth",
            "--title",
            "User authentication",
            "--tasks-dir",
            str(tasks),
        )
        self.assertEqual(plain.returncode, 0, plain.stderr)
        plain_contract = read_text(tasks / "task-001-auth" / "01-contract.md")
        self.assertNotIn("change_id:", plain_contract)
        self.assertNotIn("size_class:", plain_contract)

        changed = run(
            TASK_SCAFFOLD,
            "--task-id",
            CHANGE_ID,
            "--title",
            "Rate limit login attempts",
            "--tasks-dir",
            str(tasks),
            "--change-id",
            CHANGE_ID,
            "--size-class",
            "micro",
        )
        self.assertEqual(changed.returncode, 0, changed.stderr)
        contract = read_text(tasks / CHANGE_ID / "01-contract.md")
        self.assertIn('change_id: "' + CHANGE_ID + '"', contract)
        self.assertIn('size_class: "micro"', contract)
        self.assertIn('task_id: "' + CHANGE_ID + '"', contract)

    def test_invalid_change_id_and_size_class_are_usage_errors(self):
        tasks = self.temp / "tasks"
        bad_id = run(
            TASK_SCAFFOLD,
            "--task-id",
            "task-001-auth",
            "--title",
            "User authentication",
            "--tasks-dir",
            str(tasks),
            "--change-id",
            "../escape",
        )
        self.assertEqual(bad_id.returncode, 2)
        bad_size = run(
            TASK_SCAFFOLD,
            "--task-id",
            "task-001-auth",
            "--title",
            "User authentication",
            "--tasks-dir",
            str(tasks),
            "--change-id",
            "CHG-001-auth",
            "--size-class",
            "huge",
        )
        self.assertEqual(bad_size.returncode, 2)


class SkillPackageTests(unittest.TestCase):
    def test_skill_frontmatter_matches_directory_name(self):
        text = read_text(SKILL_MD)
        frontmatter = extract_frontmatter(text)
        self.assertRegex(frontmatter, r"(?m)^name: change$")
        self.assertEqual(CHANGE_SKILL.name, "change")
        for key in ("description", "license", "compatibility", "metadata"):
            self.assertRegex(frontmatter, r"(?m)^" + key + r":", "missing SKILL frontmatter key: " + key)
        self.assertIn("Use when", frontmatter)
        self.assertIn("Do not use", frontmatter)
        description = frontmatter_key(frontmatter, "description")
        for needle in (
            "existing spec",
            "incremental change",
            "full PRD is overkill",
            "greenfield requirements (use prd-generator)",
            "architecture decisions (use spec-generator)",
            "task slicing (use task-decomposition)",
        ):
            self.assertIn(needle, description, "description misses: " + needle)
        self.assertRegex(frontmatter, r'(?m)^\s+version: "3\.\d+\.\d+"$')
        self.assertRegex(frontmatter, r"(?m)^\s+category: spec-pipeline$")
        self.assertIn("license: MIT", frontmatter)

    def test_skill_assets_and_protocol_exist(self):
        self.assertTrue(PROTOCOL.is_file(), "missing brownfield-protocol.md")
        self.assertTrue(PROPOSAL_TEMPLATE.is_file(), "missing proposal.template.md")
        self.assertTrue((CHANGE_SKILL / "references").is_dir())
        self.assertTrue((CHANGE_SKILL / "assets" / "templates").is_dir())
        protocol = read_text(PROTOCOL)
        for needle in ("proposed", "applied", "archived", "micro", "standard", "implicit constraints"):
            self.assertIn(needle.lower(), protocol.lower(), "protocol misses: " + needle)
        template = read_text(PROPOSAL_TEMPLATE)
        for key in (
            "change_id",
            "title",
            "status",
            "kind",
            "base_spec",
            "base_spec_sha256",
            "impact_anchors",
            "created",
        ):
            self.assertRegex(template, r"(?m)^" + key + r":", "proposal template misses: " + key)
        for section in ("## 1. Motivation", "## 2. Incremental diff", "## 3. Affected code paths",
                        "## 4. Invariants and NFR impact", "## 5. Rollback", "## 6. Verification"):
            self.assertIn(section, template, "proposal template misses section: " + section)

    def test_skill_docs_are_english_canonical(self):
        for path in (
            SKILL_MD,
            PROTOCOL,
            PROPOSAL_TEMPLATE,
            SCAFFOLD_CHANGE,
            STANDARDS_EXTRACT,
            LINT_CHANGE,
        ):
            self.assertIsNone(CJK_RE.search(read_text(path)), "non-English CJK content in " + path.name)

    def test_skill_has_no_absolute_repository_paths(self):
        for path in (SKILL_MD, PROTOCOL, PROPOSAL_TEMPLATE):
            text = read_text(path)
            for marker in ("D:\\", "C:\\", "/home/", "/Users/"):
                self.assertNotIn(marker, text, "absolute path in " + path.name)

    def test_every_script_help_and_version_exits_zero(self):
        scripts = sorted(SCRIPTS.glob("*.py"))
        self.assertTrue(scripts, "the change skill ships no scripts")
        self.assertEqual(
            sorted(script.name for script in scripts),
            ["lint_change.py", "scaffold_change.py", "standards_extract.py"],
        )
        for script in scripts:
            help_result = run(script, "--help")
            self.assertEqual(help_result.returncode, 0, script.name + ": " + help_result.stderr)
            self.assertIn("usage", help_result.stdout.lower())
            version_result = run(script, "--version")
            self.assertEqual(version_result.returncode, 0, script.name + ": " + version_result.stderr)
            self.assertRegex(version_result.stdout, r"\d+\.\d+\.\d+")

    def test_scaffold_change_help_documents_required_flags(self):
        help_result = run(SCAFFOLD_CHANGE, "--help")
        self.assertEqual(help_result.returncode, 0)
        for flag in (
            "--change-id",
            "--title",
            "--anchor",
            "--touch-files",
            "--estimated-lines",
            "--dependencies",
            "--size-class",
            "--kind",
            "--spec",
            "--changes-dir",
            "--tasks-dir",
            "--repo-root",
            "--force",
            "--dry-run",
            "--json",
        ):
            self.assertIn(flag, help_result.stdout, "scaffold_change --help misses: " + flag)

    def test_standards_extract_help_documents_flags(self):
        help_result = run(STANDARDS_EXTRACT, "--help")
        self.assertEqual(help_result.returncode, 0)
        for flag in ("--repo-root", "--out", "--check", "--dry-run", "--json"):
            self.assertIn(flag, help_result.stdout, "standards_extract --help misses: " + flag)


class PlanLinterCompatibilityTests(TempRepoTestCase):
    def test_filled_change_bundle_passes_gate_1(self):
        if not PLAN_LINTER.is_file():
            self.skipTest("plan-linter is not available")
        help_result = run(PLAN_LINTER, "--help")
        if "--changes-dir" not in (help_result.stdout or ""):
            self.skipTest("plan-linter does not support brownfield changes yet")
        repo = self.make_repo()
        (repo / "src" / "auth").mkdir(parents=True)
        (repo / "src" / "auth" / "rate_limit.py").write_text("# implementation\n", encoding="utf-8")
        self.scaffold_happy(repo)
        contract_path = self.bundle_dir(repo) / "01-contract.md"
        contract_path.write_text(fill_contract_tokens(read_text(contract_path)), encoding="utf-8")
        result = run(
            PLAN_LINTER,
            "--tasks-dir",
            "tasks",
            "--changes-dir",
            ".specs/changes",
            "--spec",
            ".specs/02-tech-spec.md",
            "--repo-root",
            ".",
            "--json",
            cwd=repo,
        )
        self.assertEqual(
            result.returncode,
            0,
            "plan-linter rejected the filled change bundle:\n" + result.stdout + "\n" + result.stderr,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], result.stdout)
        change_codes = {
            error["code"]
            for error in payload["errors"]
            if "CHANGE" in error["code"] or "SIZE" in error["code"] or "MICRO" in error["code"]
        }
        self.assertFalse(change_codes, "unexpected brownfield Gate 1 errors: " + repr(change_codes))

    def test_filled_fallback_bundle_passes_gate_1(self):
        if not PLAN_LINTER.is_file():
            self.skipTest("plan-linter is not available")
        help_result = run(PLAN_LINTER, "--help")
        if "--changes-dir" not in (help_result.stdout or ""):
            self.skipTest("plan-linter does not support brownfield changes yet")
        repo = self.make_repo()
        (repo / "src" / "auth").mkdir(parents=True)
        (repo / "src" / "auth" / "rate_limit.py").write_text("# implementation\n", encoding="utf-8")
        relocated = self.temp / "relocated" / "skills" / "change"
        shutil.copytree(CHANGE_SKILL, relocated, ignore=shutil.ignore_patterns("__pycache__"))
        result = run(
            relocated / "scripts" / "scaffold_change.py",
            "--change-id",
            CHANGE_ID,
            "--title",
            "Rate limit login attempts",
            "--anchor",
            ANCHOR,
            "--kind",
            "modify",
            "--size-class",
            "micro",
            "--estimated-lines",
            "40",
            "--touch-files",
            "modify:src/auth/rate_limit.py",
            "--repo-root",
            str(repo),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        contract_path = self.bundle_dir(repo) / "01-contract.md"
        contract_path.write_text(fill_contract_tokens(read_text(contract_path)), encoding="utf-8")
        linter_result = run(
            PLAN_LINTER,
            "--tasks-dir",
            "tasks",
            "--changes-dir",
            ".specs/changes",
            "--spec",
            ".specs/02-tech-spec.md",
            "--repo-root",
            ".",
            "--json",
            cwd=repo,
        )
        self.assertEqual(
            linter_result.returncode,
            0,
            "plan-linter rejected the filled fallback change bundle:\n"
            + linter_result.stdout
            + "\n"
            + linter_result.stderr,
        )
        payload = json.loads(linter_result.stdout)
        self.assertTrue(payload["passed"], linter_result.stdout)


if __name__ == "__main__":
    unittest.main()
