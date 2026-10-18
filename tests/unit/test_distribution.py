#!/usr/bin/env python3
"""Tests for the distribution layer: tools/quickstart.py and templates/ci/*.

Run from the repository root:
    python -m unittest tests.unit.test_distribution -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = REPO_ROOT / "tools" / "quickstart.py"
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
RULES_ROOT = REPO_ROOT / ".agents" / "rules"
SCRIPTS_ROOT = REPO_ROOT / ".agents" / "scripts"
TEMPLATES = REPO_ROOT / "templates" / "ci"
CI_FILES = ("rbac-gate.yml", "plan-gate.yml")


def run_quickstart(*arguments, cwd=None):
    command = [sys.executable, str(QUICKSTART)] + [str(item) for item in arguments]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        command,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=180,
    )


def source_skill_names():
    return sorted(
        path.name
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file() and path.name not in ("__pycache__", ".git")
    )


class QuickstartTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.target = self.root / "target"
        self.target.mkdir()

    def install(self, *arguments):
        return run_quickstart("--target", self.target, *arguments)

    def install_json(self, *arguments):
        result = self.install("--copy", "--json", *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    # -- metadata and CLI surface -------------------------------------------

    def test_quickstart_has_pep723_metadata(self):
        text = QUICKSTART.read_text(encoding="utf-8")
        header = text[:400]
        self.assertEqual(text.splitlines()[0], "#!/usr/bin/env python3")
        self.assertIn("# /// script", header)
        self.assertIn('requires-python = ">=3.9"', header)
        self.assertIn("dependencies = []", header)
        self.assertIn("# ///", text[text.index("# /// script") + 1 :])

    def test_help_and_version(self):
        help_result = run_quickstart("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)
        self.assertIn("usage", help_result.stdout.lower())
        self.assertIn("--target", help_result.stdout)
        version_result = run_quickstart("--version")
        self.assertEqual(version_result.returncode, 0, version_result.stdout + version_result.stderr)
        self.assertIn("quickstart", version_result.stdout)
        self.assertRegex(version_result.stdout, r"\d+\.\d+\.\d+")

    def test_target_is_required(self):
        result = run_quickstart("--copy")
        self.assertEqual(result.returncode, 2)
        self.assertIn("target", result.stderr.lower())

    # -- happy path ---------------------------------------------------------

    def test_install_full_suite(self):
        result = self.install("--copy")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        skill_names = source_skill_names()
        self.assertTrue(skill_names, "the suite must contain at least one skill")
        skills_dest = self.target / ".agents" / "skills"
        for name in skill_names:
            self.assertTrue((skills_dest / name / "SKILL.md").is_file(), name)
        self.assertEqual(sorted(path.name for path in skills_dest.iterdir()), skill_names)

        expected_rules = sorted(path.name for path in RULES_ROOT.glob("*.md"))
        installed_rules = sorted(path.name for path in (self.target / ".agents" / "rules").glob("*.md"))
        self.assertEqual(installed_rules, expected_rules)

        expected_scripts = sorted(path.name for path in SCRIPTS_ROOT.glob("*.py"))
        installed_scripts = sorted(
            path.name for path in (self.target / ".agents" / "scripts").glob("*.py")
        )
        self.assertEqual(installed_scripts, expected_scripts)

        self.assertTrue((self.target / ".agents" / "hooks.json").is_file())
        self.assertTrue((self.target / "tools" / "rbac_audit.py").is_file())
        self.assertFalse((self.target / ".github").exists())
        self.assertEqual([path.name for path in self.root.iterdir()], ["target"])

    def test_with_ci_installs_both_workflows(self):
        result = self.install("--copy", "--with-ci")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        workflows = self.target / ".github" / "workflows"
        self.assertEqual(sorted(path.name for path in workflows.iterdir()), sorted(CI_FILES))
        for name in CI_FILES:
            self.assertEqual(
                (workflows / name).read_text(encoding="utf-8"),
                (TEMPLATES / name).read_text(encoding="utf-8"),
                name,
            )

    def test_dry_run_writes_nothing(self):
        result = self.install("--copy", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertEqual([path.name for path in self.root.iterdir()], ["target"])
        self.assertIn("planned", result.stdout.lower())

    def test_second_run_without_force_skips_identical_items(self):
        first = self.install("--copy", "--json")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.install("--copy", "--json")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        payload = json.loads(second.stdout)
        self.assertEqual(payload["failures"], 0)
        self.assertEqual(payload["installed"], 0)
        self.assertEqual(payload["skipped"], len(payload["results"]))
        for item in payload["results"]:
            self.assertEqual(item["status"], "skipped", item)

    def test_default_symlink_mode_survives_a_second_run(self):
        first = self.install("--json")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.install("--json")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        payload = json.loads(second.stdout)
        self.assertEqual(payload["failures"], 0)
        for item in payload["results"]:
            self.assertEqual(item["status"], "skipped", item)

    def test_force_replaces_existing_items(self):
        first = self.install("--copy")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        skill_file = self.target / ".agents" / "skills" / "review" / "SKILL.md"
        original = skill_file.read_text(encoding="utf-8")
        skill_file.write_text("# tampered\n", encoding="utf-8")
        extra = skill_file.parent / "extra-file.md"
        extra.write_text("stale\n", encoding="utf-8")

        result = self.install("--copy", "--force", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(extra.exists())
        self.assertEqual(skill_file.read_text(encoding="utf-8"), original)

    def test_skills_subset_and_optional_layers(self):
        payload = self.install_json(
            "--skills", "plan-linter", "--no-with-rules", "--no-with-audit"
        )
        skills_dest = self.target / ".agents" / "skills"
        self.assertEqual(sorted(path.name for path in skills_dest.iterdir()), ["plan-linter"])
        self.assertFalse((self.target / ".agents" / "rules").exists())
        self.assertFalse((self.target / ".agents" / "scripts").exists())
        self.assertFalse((self.target / "tools").exists())
        self.assertEqual(payload["failures"], 0)
        self.assertTrue(payload["ok"])

    def test_quickstart_is_self_contained(self):
        portable = self.root / "portable"
        (portable / "tools").mkdir(parents=True)
        shutil.copy2(str(QUICKSTART), str(portable / "tools" / "quickstart.py"))
        demo = portable / ".agents" / "skills" / "demo"
        demo.mkdir(parents=True)
        (demo / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")

        isolated_target = self.root / "isolated-target"
        isolated_target.mkdir()
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(
            [
                sys.executable,
                str(portable / "tools" / "quickstart.py"),
                "--target",
                str(isolated_target),
                "--copy",
                "--no-with-rules",
                "--no-with-audit",
            ],
            cwd=str(portable),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((isolated_target / ".agents" / "skills" / "demo" / "SKILL.md").is_file())

    def test_unknown_skill_is_usage_error(self):
        result = self.install("--copy", "--skills", "does-not-exist")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown skill", result.stderr.lower())
        self.assertEqual(list(self.target.iterdir()), [])

    # -- path containment ---------------------------------------------------

    def test_dest_with_dotdot_is_refused(self):
        result = self.install("--copy", "--dest", "../outside")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("..", result.stderr)
        self.assertFalse((self.root / "outside").exists())
        self.assertEqual(list(self.target.iterdir()), [])

    def test_dest_with_embedded_dotdot_is_refused(self):
        result = self.install("--copy", "--dest", ".agents/../skills")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_absolute_dest_is_refused(self):
        result = self.install("--copy", "--dest", str(self.root / "outside"))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((self.root / "outside").exists())

    def test_skill_name_traversal_is_refused(self):
        result = self.install("--copy", "--skills", "../evil")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_symlinked_skills_root_escape_is_refused(self):
        agents = self.target / ".agents"
        agents.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        link = agents / "skills"
        try:
            os.symlink(str(outside), str(link), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlinks are not available on this platform")

        result = self.install("--copy")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertIn("outside --target", result.stdout + result.stderr)

    # -- machine-readable output -------------------------------------------

    def test_json_output_is_valid_and_contained(self):
        payload = self.install_json("--with-ci")
        for key in (
            "tool",
            "version",
            "source",
            "target",
            "dest",
            "copy",
            "dry_run",
            "results",
            "installed",
            "skipped",
            "failures",
            "ok",
        ):
            self.assertIn(key, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failures"], 0)
        self.assertEqual(payload["installed"], len(payload["results"]))
        target = Path(payload["target"])
        for item in payload["results"]:
            self.assertIn(item["status"], ("linked", "copied"), item)
            self.assertIn(item["kind"], ("skill", "rule", "script", "hooks", "audit", "ci"), item)
            self.assertTrue(Path(item["destination"]).is_relative_to(target), item)

    def test_print_oneliner(self):
        without_target = run_quickstart("--print-oneliner", "--copy", "--with-ci")
        self.assertEqual(without_target.returncode, 0, without_target.stdout + without_target.stderr)
        lines = without_target.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, without_target.stdout)
        self.assertIn("quickstart.py", lines[0])
        self.assertIn("--with-ci", lines[0])
        self.assertIn("--copy", lines[0])

        with_target = run_quickstart(
            "--print-oneliner", "--target", self.target, "--copy"
        )
        self.assertEqual(with_target.returncode, 0, with_target.stdout + with_target.stderr)
        lines = with_target.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, with_target.stdout)
        self.assertIn(str(self.target), lines[0])


class CiTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {
            name: (TEMPLATES / name).read_text(encoding="utf-8") for name in CI_FILES
        }
        cls.readme = (TEMPLATES / "README.md").read_text(encoding="utf-8")

    def test_templates_exist(self):
        for name in CI_FILES:
            self.assertTrue((TEMPLATES / name).is_file(), name)
        self.assertTrue((TEMPLATES / "README.md").is_file())

    def test_no_tab_indentation(self):
        for name, text in self.files.items():
            self.assertNotIn("\t", text, name)

    def test_workflows_start_with_name(self):
        for name, text in self.files.items():
            self.assertTrue(text.startswith("name:"), name)

    def test_common_workflow_structure(self):
        for name, text in self.files.items():
            self.assertIn("on:", text, name)
            self.assertIn("on:\n  pull_request", text, name)
            self.assertIn("pull_request", text, name)
            self.assertIn("permissions:", text, name)
            self.assertIn("contents: read", text, name)
            self.assertIn("jobs:", text, name)
            self.assertIn("runs-on: ubuntu-latest", text, name)
            self.assertIn('python-version: "3.12"', text, name)
            self.assertIn("actions/checkout@v4", text, name)

    def test_rbac_gate_invokes_audit_with_event_shas(self):
        text = self.files["rbac-gate.yml"]
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("tools/rbac_audit.py", text)
        self.assertIn("--base", text)
        self.assertIn("--head", text)
        self.assertIn("--tasks-dir tasks", text)
        self.assertIn("--json", text)
        self.assertIn("github.event.pull_request.base.sha", text)
        self.assertIn("github.event.pull_request.head.sha", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)
        self.assertIn("vars.RBAC_ROLE", text)

    def test_plan_gate_invokes_plan_linter(self):
        text = self.files["plan-gate.yml"]
        self.assertIn(".agents/skills/plan-linter/scripts/plan_linter.py", text)
        self.assertIn("--tasks-dir tasks", text)
        self.assertIn("--spec .specs/02-tech-spec.md", text)
        self.assertIn("--json", text)
        self.assertIn("tasks/**", text)
        self.assertIn(".specs/**", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)

    def test_workflows_fail_the_job_on_nonzero(self):
        for name, text in self.files.items():
            self.assertIn('exit "$status"', text, name)
            self.assertIn("GITHUB_STEP_SUMMARY", text, name)

    def test_workflow_templates_have_no_placeholder_tokens(self):
        for name, text in self.files.items():
            for token in ("TODO", "TBD"):
                self.assertNotIn(token, text, name)
        for token in ("TODO", "TBD", "{{"):
            self.assertNotIn(token, self.readme)

    def test_readme_documents_both_workflows(self):
        for name in CI_FILES:
            self.assertIn(name, self.readme)
        lowered = self.readme.lower()
        for phrase in (
            "permissions",
            "contents: read",
            "fork",
            "pinning the suite version",
            "hooks",
            "authoritative",
            "troubleshooting",
            "fetch-depth",
        ):
            self.assertIn(phrase, lowered, phrase)


if __name__ == "__main__":
    unittest.main()
