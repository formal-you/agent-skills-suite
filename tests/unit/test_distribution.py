#!/usr/bin/env python3
"""Tests for the distribution layer: tools/quickstart.py and the bundled CI skill assets.

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
QUALITY_ENGINEERING = SKILLS_ROOT / "quality-engineering"
TEMPLATES = QUALITY_ENGINEERING / "assets" / "templates" / "ci"
CI_FILES = ("plan-gate.yml", "quality-gate.yml", "rbac-gate.yml")
GATE_SCRIPTS = (
    "complexity_check.py",
    "verification_linter.py",
    "rbac_audit.py",
    "mutation_gate.py",
)


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

        quality_engineering = skills_dest / "quality-engineering"
        for script in GATE_SCRIPTS:
            self.assertTrue((quality_engineering / "scripts" / script).is_file(), script)
        self.assertTrue((quality_engineering / "assets" / "templates" / "ci" / "quality-gate.yml").is_file())
        self.assertFalse((self.target / "tools").exists(), "install must not create a repo-level tools/ directory")
        self.assertFalse((self.target / ".github").exists())
        self.assertEqual(sorted(path.name for path in self.target.iterdir()), [".agents"])
        self.assertEqual([path.name for path in self.root.iterdir()], ["target"])

    def test_with_ci_installs_both_workflows(self):
        result = self.install("--copy", "--with-ci")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        workflows = self.target / ".github" / "workflows"
        self.assertEqual(sorted(path.name for path in workflows.iterdir()), sorted(CI_FILES))
        self.assertEqual(sorted(path.name for path in self.target.iterdir()), [".agents", ".github"])
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
        payload = self.install_json("--skills", "plan-linter", "--no-with-rules")
        skills_dest = self.target / ".agents" / "skills"
        self.assertEqual(sorted(path.name for path in skills_dest.iterdir()), ["plan-linter"])
        self.assertFalse((self.target / ".agents" / "rules").exists())
        self.assertFalse((self.target / ".agents" / "scripts").exists())
        self.assertFalse((self.target / "tools").exists())
        self.assertEqual(payload["failures"], 0)
        self.assertTrue(payload["ok"])

    def test_with_ci_implies_quality_engineering(self):
        payload = self.install_json("--skills", "plan-linter", "--with-ci")
        skills_dest = self.target / ".agents" / "skills"
        self.assertEqual(sorted(path.name for path in skills_dest.iterdir()), ["plan-linter", "quality-engineering"])
        workflows = self.target / ".github" / "workflows"
        self.assertEqual(sorted(path.name for path in workflows.iterdir()), sorted(CI_FILES))
        self.assertTrue(
            (skills_dest / "quality-engineering" / "scripts" / "rbac_audit.py").is_file()
        )
        self.assertTrue(payload["ok"], payload)

    def test_with_ci_rejects_custom_dest(self):
        result = self.install("--copy", "--with-ci", "--dest", "custom/skills")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--with-ci requires the default --dest", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_installed_quality_engineering_runs_from_a_relocated_copy(self):
        result = self.install("--copy", "--skills", "quality-engineering")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        skill = self.target / ".agents" / "skills" / "quality-engineering"
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        for script in GATE_SCRIPTS:
            help_result = subprocess.run(
                [sys.executable, str(skill / "scripts" / script), "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=120,
            )
            self.assertEqual(help_result.returncode, 0, script + ": " + help_result.stderr)
        for name in CI_FILES:
            self.assertTrue((skill / "assets" / "templates" / "ci" / name).is_file(), name)
        self.assertTrue((skill / "assets" / "templates" / "ci" / "profiles" / "index.json").is_file())

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
            self.assertIn(item["kind"], ("skill", "rule", "ci"), item)
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
        self.assertIn(".agents/skills/quality-engineering/scripts/rbac_audit.py", text)
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

    def test_workflow_templates_have_no_repo_level_tool_paths(self):
        for name, text in self.files.items():
            self.assertNotIn("tools/", text, name)
            self.assertNotIn("templates/ci", text, name)

    def test_readme_documents_both_workflows(self):
        for name in CI_FILES:
            self.assertIn(name, self.readme)
        lowered = self.readme.lower()
        for phrase in (
            "permissions",
            "contents: read",
            "fork",
            "pinning the suite version",
            "authoritative",
            "troubleshooting",
            "fetch-depth",
        ):
            self.assertIn(phrase, lowered, phrase)


class SkillSelfContainmentTests(unittest.TestCase):
    """A skill must keep working when installed alone (plugin / npx / Gemini --path)."""

    SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
    FORBIDDEN_TOKENS = ("docs/", "tools/", ".agents/rules", ".agents/scripts")
    ALLOWED_SIBLING_SKILLS = {"plan-linter"}
    REPO_LEVEL_CI = re.compile(r"(?<!assets/)(?<!skills/)templates/ci")

    def skill_directories(self):
        return sorted(
            path
            for path in self.SKILLS_ROOT.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )

    def test_skill_directories_do_not_reference_suite_files_outside_the_skill(self):
        offenders = []
        for skill in self.skill_directories():
            for path in sorted(skill.rglob("*.md")):
                text = path.read_text(encoding="utf-8", errors="replace")
                relative = path.relative_to(REPO_ROOT).as_posix()
                for token in self.FORBIDDEN_TOKENS:
                    if token in text:
                        offenders.append(relative + " -> " + token)
                if self.REPO_LEVEL_CI.search(text):
                    offenders.append(relative + " -> repo-level templates/ci")
                for match in re.finditer(r"\.agents/skills/([A-Za-z0-9_-]+)/", text):
                    name = match.group(1)
                    if name == skill.name:
                        continue
                    if name in self.ALLOWED_SIBLING_SKILLS and re.search(r"\binstalled\b", text):
                        # A pipeline skill may call Gate 1 from the plan-linter skill when installed.
                        continue
                    offenders.append(relative + " -> .agents/skills/" + name)
        self.assertEqual(
            offenders,
            [],
            "SKILL.md and references must be self-contained; move shared content into the skill",
        )

    def test_skill_docs_never_use_a_bare_relative_script_path(self):
        """`python scripts/x.py` only works if cwd is the skill dir; project-root form must be used."""
        bare = re.compile(
            r"\bpython3?\s+(?:-[A-Za-z]+\s+)*scripts/([A-Za-z0-9_.-]+\.(?:py|ps1))"
        )
        offenders = []
        for skill in self.skill_directories():
            for path in sorted(skill.rglob("*.md")):
                text = path.read_text(encoding="utf-8", errors="replace")
                relative = path.relative_to(REPO_ROOT).as_posix()
                for match in bare.finditer(text):
                    script = match.group(1)
                    if not (skill / "scripts" / script).is_file():
                        offenders.append(relative + " -> scripts/" + script + " is not in this skill")
                    else:
                        offenders.append(
                            relative + " -> bare scripts/" + script
                            + " (use .agents/skills/" + skill.name + "/scripts/" + script + ")"
                        )
        self.assertEqual(
            offenders,
            [],
            "skill commands must resolve from the repository root:\n" + "\n".join(offenders),
        )

    def test_repository_has_no_repo_level_templates_or_gate_scripts(self):
        self.assertFalse((REPO_ROOT / "templates").exists(), "templates must live inside a skill")
        self.assertFalse((REPO_ROOT / "tools" / "rbac_audit.py").exists(), "rbac_audit belongs to quality-engineering")
        self.assertFalse((REPO_ROOT / "tools" / "mutation_gate.py").exists(), "mutation_gate belongs to quality-engineering")
        for script in GATE_SCRIPTS:
            self.assertTrue((QUALITY_ENGINEERING / "scripts" / script).is_file(), script)
        for name in CI_FILES + ("README.md", "quality-gate.config.example.json"):
            self.assertTrue((TEMPLATES / name).is_file(), name)
        self.assertTrue((TEMPLATES / "profiles" / "index.json").is_file())

    def test_skill_markdown_relative_links_stay_inside_the_skill(self):
        broken = []
        link_re = re.compile(r"\]\(([^)]+)\)")
        for skill in self.skill_directories():
            for path in [skill / "SKILL.md"] + sorted((skill / "references").glob("*.md")):
                for raw in link_re.findall(path.read_text(encoding="utf-8", errors="replace")):
                    target = raw.strip().split()[0].strip("<>")
                    if target.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    target = target.split("#", 1)[0].split("?", 1)[0]
                    if not target:
                        continue
                    resolved = (path.parent / target).resolve()
                    if not resolved.exists() or not resolved.is_relative_to(skill.resolve()):
                        broken.append(
                            path.relative_to(REPO_ROOT).as_posix() + " -> " + target
                        )
        self.assertEqual(broken, [], "skill links must resolve inside the skill directory")

    def test_role_skills_bundle_their_boundaries(self):
        for name in ("qa", "dev", "review", "converge"):
            boundaries = self.SKILLS_ROOT / name / "references" / "role-boundaries.md"
            self.assertTrue(boundaries.is_file(), name + " lacks references/role-boundaries.md")
            text = boundaries.read_text(encoding="utf-8")
            self.assertIn("Write scope", text, name)
            self.assertIn("advisory", text, name)


if __name__ == "__main__":
    unittest.main()
