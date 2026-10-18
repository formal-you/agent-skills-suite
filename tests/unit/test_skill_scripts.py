"""Tests for the prd-generator / spec-generator bundled skill scripts.

Run from the repository root:
    python -m unittest tests.unit.test_skill_scripts -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRD_SKILL = REPO_ROOT / ".agents" / "skills" / "prd-generator"
SPEC_SKILL = REPO_ROOT / ".agents" / "skills" / "spec-generator"
INSTALL_TOOL = REPO_ROOT / "tools" / "install_skills.py"

VALID_PRD = """# PRD: Demo

## 1. Summary
A demo product.

## 2. Functional requirements
### REQ-001: Sign in
- Scope: users can sign in.
- Acceptance criteria: valid credentials succeed.
- Anchor: #sec-sign-in

## 3. Constraints
- CON-001: credentials are never logged.

## 4. Non-functional requirements
- NFR-001 (Latency): 200 ms p99.
  - Verification: load test.

## 5. Forks
### FORK-001: Session storage
- Context: choose a session store.
- Candidate options:
  - Option A: signed cookie.
  - Option B: server-side session.
- Decision drivers: simplicity, revocation.
"""

VALID_SPEC = """# Tech Spec: Demo

## 1. Architecture overview
Single service.

| ID | Dimension | Target | Verification |
| :--- | :--- | :--- | :--- |
| NFR-001 | Latency | 200 ms p99 | load test |

## 2. System topology

~~~mermaid
flowchart TD
    User["User"] --> Service["Service"]
    Service --> Store["Data store"]
~~~

## 3. Components
| Component | Responsibility | Anchor |
| :--- | :--- | :--- |
| Service | Handles sign in | #sec-sign-in |

## 6. Invariants
| ID | Category | Invariant | Enforcement | Anchor |
| :--- | :--- | :--- | :--- | :--- |
| INV-001 | Security | Credentials are never logged | redaction test | #sec-sign-in |

## 7. Modular index
- [02-tech-spec/01-topology.md](02-tech-spec/01-topology.md)
"""

VALID_TOPOLOGY = """# Topology: Demo

Reuses #sec-sign-in.
"""

VALID_ADR = """# ADR-001: Session storage

## Status
Accepted

## Context and problem statement
We need a session store.

## Considered options
1. Signed cookie.
2. Server-side session.

## Decision
Use server-side sessions.

## Consequences
Extra store to operate.
"""


def run(script: Path, *arguments, cwd=None, flags=()):
    command = [sys.executable, *flags, str(script), *[str(item) for item in arguments]]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )


def write_valid_prd(root: Path) -> Path:
    path = root / "01-prd.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VALID_PRD, encoding="utf-8")
    return path


def write_valid_spec_bundle(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "02-tech-spec.md").write_text(VALID_SPEC, encoding="utf-8")
    modular = root / "02-tech-spec"
    modular.mkdir(parents=True, exist_ok=True)
    (modular / "01-topology.md").write_text(VALID_TOPOLOGY, encoding="utf-8")
    adr = root / "adr"
    adr.mkdir(parents=True, exist_ok=True)
    (adr / "001-session.md").write_text(VALID_ADR, encoding="utf-8")
    return root / "02-tech-spec.md"


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="skill-scripts-")
        self.temp = Path(self._temp.name)

    def tearDown(self):
        self._temp.cleanup()


class ScaffoldTests(TempDirTestCase):
    def test_prd_dry_run_writes_nothing(self):
        out = self.temp / "specs"
        result = run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would create", result.stdout)
        self.assertFalse(out.exists(), "dry-run must not create the output tree")

    def test_prd_scaffold_creates_bundle(self):
        out = self.temp / "specs"
        result = run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "scaffold")
        self.assertGreater(payload["created"], [])
        self.assertTrue((out / "01-prd.md").is_file())
        self.assertTrue((out / "01-prd" / "00-overview.md").is_file())
        names = [path.name for path in out.rglob("*") if path.is_file()]
        self.assertFalse([name for name in names if ".template" in name])

    def test_spec_scaffold_creates_bundle_and_adr_dir(self):
        out = self.temp / "specs"
        result = run(SPEC_SKILL / "scripts" / "scaffold.py", "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((out / "02-tech-spec.md").is_file())
        self.assertTrue((out / "02-tech-spec" / "01-topology.md").is_file())
        self.assertTrue((out / "02-tech-spec" / "02-database-schema.sql").is_file())
        self.assertTrue((out / "adr").is_dir())
        self.assertFalse((out / "adr.md").exists())

    def test_scaffold_is_idempotent_and_refuses_overwrite(self):
        out = self.temp / "specs"
        self.assertEqual(run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out).returncode, 0)
        target = out / "01-prd.md"
        target.write_text("USER EDIT", encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["created"], [])
        self.assertTrue(payload["skipped"])
        self.assertEqual(target.read_text(encoding="utf-8"), "USER EDIT")

    def test_force_overwrites_existing_files(self):
        out = self.temp / "specs"
        self.assertEqual(run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out).returncode, 0)
        target = out / "01-prd.md"
        target.write_text("USER EDIT", encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "scaffold.py", "--out", out, "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(target.read_text(encoding="utf-8"), "USER EDIT")
        self.assertIn("{{PROJECT_TITLE}}", target.read_text(encoding="utf-8"))


class LintPrdTests(TempDirTestCase):
    def test_valid_prd_passes(self):
        bundle = self.temp / "specs"
        path = write_valid_prd(bundle)
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_placeholder_fails(self):
        bundle = self.temp / "specs"
        path = write_valid_prd(bundle)
        path.write_text(path.read_text(encoding="utf-8").replace("users can sign in.", "{{SCOPE}}"), encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("PLACEHOLDER", result.stdout)

    def test_missing_required_identifier_fails(self):
        bundle = self.temp / "specs"
        path = write_valid_prd(bundle)
        text = path.read_text(encoding="utf-8").replace("FORK-001", "NOTE")
        path.write_text(text, encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING_SECTION", result.stdout)

    def test_dangling_link_fails(self):
        bundle = self.temp / "specs"
        path = write_valid_prd(bundle)
        path.write_text(path.read_text(encoding="utf-8") + "\n[missing](does-not-exist.md)\n", encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("DANGLING_LINK", result.stdout)

    def test_json_output(self):
        bundle = self.temp / "specs"
        path = write_valid_prd(bundle)
        path.write_text(path.read_text(encoding="utf-8") + "\nTODO: finish\n", encoding="utf-8")
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", path, "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "lint_prd")
        self.assertFalse(payload["passed"])
        self.assertTrue(any(item["code"].startswith("PLACEHOLDER") for item in payload["errors"]))

    def test_missing_target_returns_usage_error(self):
        result = run(PRD_SKILL / "scripts" / "lint_prd.py", self.temp / "absent")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)


class LintSpecTests(TempDirTestCase):
    def test_valid_spec_bundle_passes(self):
        bundle = self.temp / "specs"
        write_valid_spec_bundle(bundle)
        result = run(SPEC_SKILL / "scripts" / "lint_spec.py", bundle)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_unbalanced_mermaid_fails(self):
        bundle = self.temp / "specs"
        write_valid_spec_bundle(bundle)
        path = bundle / "02-tech-spec.md"
        text = path.read_text(encoding="utf-8").replace(
            '    Service --> Store["Data store"]', '    Service --> Store["Data store"'
        )
        path.write_text(text, encoding="utf-8")
        result = run(SPEC_SKILL / "scripts" / "lint_spec.py", bundle)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MERMAID_BRACKET", result.stdout)

    def test_adr_missing_sections_fails(self):
        bundle = self.temp / "specs"
        write_valid_spec_bundle(bundle)
        (bundle / "adr" / "002-broken.md").write_text(
            "# ADR-002: Broken\n\n## Context\nOnly context.\n", encoding="utf-8"
        )
        result = run(SPEC_SKILL / "scripts" / "lint_spec.py", bundle)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ADR_SECTION_MISSING", result.stdout)

    def test_json_output(self):
        bundle = self.temp / "specs"
        write_valid_spec_bundle(bundle)
        (bundle / "02-tech-spec.md").write_text(
            (bundle / "02-tech-spec.md").read_text(encoding="utf-8") + "\n[TBD]\n", encoding="utf-8"
        )
        result = run(SPEC_SKILL / "scripts" / "lint_spec.py", bundle, "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "lint_spec")
        self.assertFalse(payload["passed"])


class EngineProxyTests(TempDirTestCase):
    def test_help_works_without_engine(self):
        result = run(
            PRD_SKILL / "scripts" / "engine.py",
            "--help",
            cwd=self.temp,
            flags=("-S",),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("optional engine", result.stdout.lower())
        self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_check_exits_2_without_engine(self):
        result = run(
            SPEC_SKILL / "scripts" / "engine.py",
            "--check",
            cwd=self.temp,
            flags=("-S",),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not installed", result.stderr)

    def test_forwarded_arguments_exit_2_when_engine_absent(self):
        result = run(
            PRD_SKILL / "scripts" / "engine.py",
            "run",
            "--idea",
            "demo",
            cwd=self.temp,
            flags=("-S",),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("scaffold.py", result.stderr)

    def test_check_zero_when_engine_available(self):
        probe = subprocess.run(
            [sys.executable, "-c", "import importlib.util; print(bool(importlib.util.find_spec('prd_generator')))"],
            capture_output=True,
            text=True,
            cwd=str(self.temp),
        )
        available = probe.stdout.strip() == "True"
        if not available:
            self.skipTest("optional engine is not installed in this environment")
        result = run(PRD_SKILL / "scripts" / "engine.py", "--check", cwd=self.temp)
        self.assertEqual(result.returncode, 0, result.stderr)


class RelocationTests(TempDirTestCase):
    def test_copied_prd_skill_scaffolds_and_lints(self):
        relocated = self.temp / "relocated" / "prd-generator"
        shutil.copytree(PRD_SKILL, relocated, ignore=shutil.ignore_patterns("__pycache__"))
        out = self.temp / "out"
        scaffold = run(relocated / "scripts" / "scaffold.py", "--out", out, cwd=self.temp)
        self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
        self.assertTrue((out / "01-prd.md").is_file())
        help_result = run(relocated / "scripts" / "lint_prd.py", "--help", cwd=self.temp)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)

    def test_copied_spec_skill_scaffolds_and_lints(self):
        relocated = self.temp / "relocated" / "spec-generator"
        shutil.copytree(SPEC_SKILL, relocated, ignore=shutil.ignore_patterns("__pycache__"))
        out = self.temp / "out"
        scaffold = run(relocated / "scripts" / "scaffold.py", "--out", out, cwd=self.temp)
        self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
        self.assertTrue((out / "02-tech-spec.md").is_file())
        help_result = run(relocated / "scripts" / "lint_spec.py", "--help", cwd=self.temp)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)


class InstallSkillsToolTests(TempDirTestCase):
    def test_dry_run_plans_without_writing(self):
        destination = self.temp / "skills"
        result = run(
            INSTALL_TOOL,
            "--dest",
            destination,
            "--skills",
            "prd-generator",
            "--dry-run",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool"], "install_skills")
        self.assertTrue(payload["results"])
        self.assertFalse(destination.exists())

    def test_unknown_skill_is_usage_error(self):
        result = run(INSTALL_TOOL, "--skills", "no-such-skill", "--dry-run")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown skill", result.stderr)


if __name__ == "__main__":
    unittest.main()
