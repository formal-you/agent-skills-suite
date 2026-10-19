#!/usr/bin/env python3
"""Guards the always-loaded skill-change and git-flow workflow in AGENTS.md."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
RULES = ROOT / ".agents" / "rules"
QE_SKILL = ROOT / ".agents" / "skills" / "quality-engineering"
BRANCH_GUARD = QE_SKILL / "scripts" / "branch_guard.py"
BRANCH_ISOLATION = QE_SKILL / "references" / "branch-isolation.md"
RBAC_GATE = QE_SKILL / "assets" / "templates" / "ci" / "rbac-gate.yml"
BRANCH_GUARD_COMMAND = (
    "python .agents/skills/quality-engineering/scripts/branch_guard.py check"
)

REQUIRED_AGENTS_PHRASES = (
    "## 4. Skill change workflow",
    "Intent and issue (user-triggered, batched)",
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

    def test_agents_batches_issue_and_pr_work(self) -> None:
        text = flat(read(AGENTS))
        self.assertIn("Do not open an issue or PR for every change", text)
        self.assertIn("one issue/PR", text)
        self.assertIn("never create issues or PRs on your own initiative", text)

    def test_agents_is_concise_and_scannable(self) -> None:
        text = read(AGENTS)
        self.assertLessEqual(len(text.splitlines()), 155, "AGENTS.md must stay at most 155 lines")
        for phrase in (
            "**Purpose.**",
            "**Precedence (highest first).**",
            "**Authority.**",
            "## 1. Repository map",
            "## 2. Work types",
            "### 2.1 Discovery and specification",
            "### 2.2 Per-task delivery",
            "### 2.3 Skill-suite development",
            "## 5. Commands",
            "always-loaded summary",
        ):
            self.assertIn(phrase, text, "AGENTS.md misses structure phrase: " + phrase)
        for phrase in ("prd-generator", "spec-generator", "task-decomposition", "plan-linter"):
            self.assertIn(phrase, text, "AGENTS.md misses discovery-stage phrase: " + phrase)
        self.assertIn("Never commit secrets/PII", text)
        self.assertIn("Bounded brownfield changes", text)
        self.assertIn("enforcement.md#role-matrix", text)
        self.assertIn("**Evidence and freshness:**", text)
        self.assertIn("Archived notes explain history only", text)
        self.assertIn("never establish a current gap", text)
        self.assertNotIn("| Role | Rule |", text, "do not duplicate the role matrix")
        self.assertNotIn("| Gate | Owner |", text, "do not duplicate the gate matrix")
        self.assertNotIn("v2.0.0", text, "do not pin tool versions in the always-loaded summary")

    def test_agents_role_rules_and_pipeline_skills_exist(self) -> None:
        text = read(AGENTS)
        for name in (
            "pm",
            "architect",
            "planner",
            "dev",
            "qa",
            "test-engineering",
            "reviewer",
            "orchestrator",
        ):
            self.assertTrue(
                (ROOT / ".agents" / "rules" / (name + ".md")).is_file(),
                "AGENTS references a missing role rule: " + name,
            )
        for name in (
            "prd-generator",
            "spec-generator",
            "task-decomposition",
            "plan-linter",
            "quality-engineering",
        ):
            self.assertTrue(
                (ROOT / ".agents" / "skills" / name / "SKILL.md").is_file(),
                "AGENTS references a missing pipeline skill: " + name,
            )
            self.assertIn(name, text)

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


class BranchIsolationRuleTests(unittest.TestCase):
    """Guards the branch-isolation guard, its CI wiring and the role rules."""

    def test_branch_guard_script_and_reference_exist(self) -> None:
        self.assertTrue(BRANCH_GUARD.is_file(), "missing branch guard script")
        self.assertTrue(BRANCH_ISOLATION.is_file(), "missing branch isolation reference")
        script = read(BRANCH_GUARD)
        self.assertTrue(script.startswith("#!/usr/bin/env python3"), "branch guard needs a shebang")
        self.assertIn('VERSION = "1.0.0"', script)
        for code in (
            "BRANCH_PROTECTED",
            "BRANCH_PATTERN_INVALID",
            "BRANCH_DETACHED",
            "BRANCH_DECLARED_MISSING",
            "BRANCH_MISMATCH",
            "TASK_DOC_MISSING",
        ):
            self.assertIn(code, script, "branch guard does not emit " + code)
        self.assertIn("rev-parse", script)
        self.assertIn("--abbrev-ref", script)

    def test_dev_rule_requires_a_dedicated_task_branch(self) -> None:
        text = flat(read(RULES / "dev.md"))
        self.assertIn("git rev-parse --abbrev-ref HEAD", text)
        self.assertIn("feat/<task-id>", text)
        self.assertIn("02-dev-workspace.md", text)
        self.assertIn("`main`/`master`", text)
        self.assertIn(BRANCH_GUARD_COMMAND, text)
        self.assertIn("Record the branch", text)
        self.assertIn("Switch branches in the middle of a task", text)

    def test_qa_rule_verifies_the_recorded_branch(self) -> None:
        text = flat(read(RULES / "qa.md"))
        self.assertIn("git rev-parse --abbrev-ref HEAD", text)
        self.assertIn("git merge-base --is-ancestor", text)
        self.assertIn("`main`/`master`", text)
        self.assertIn("02-dev-workspace.md", text)
        self.assertIn(BRANCH_GUARD_COMMAND, text)
        self.assertIn("CI gates", text)

    def test_orchestrator_rule_blocks_protected_branch_dispatch(self) -> None:
        text = flat(read(RULES / "orchestrator.md"))
        for phrase in (
            "Never dispatch Dev or QA work onto a protected branch",
            "`main`/`master`",
            "every Dev/QA dispatch prompt",
            "02-dev-workspace.md",
            "branch_guard.py",
        ):
            self.assertIn(phrase, text)

    def test_enforcement_documents_branch_isolation_and_honest_limits(self) -> None:
        text = flat(read(RULES / "enforcement.md"))
        for phrase in (
            "## Branch isolation",
            "branch_guard.py",
            "branch-isolation.md",
            "advisory",
            "authoritative",
            "Branch protection",
            "not** physical enforcement",
            "never commits or hands off on a protected trunk",
        ):
            self.assertIn(phrase, text)

    def test_ci_template_runs_the_branch_guard_before_the_audit(self) -> None:
        text = read(RBAC_GATE)
        self.assertIn(BRANCH_GUARD_COMMAND, text)
        self.assertIn('--branch "${{ github.head_ref || github.ref_name }}"', text)
        self.assertIn("--protected main master", text)
        self.assertIn("--json", text)
        self.assertIn('exit "$status"', text)
        self.assertIn("rbac_audit.py", text)
        self.assertLess(
            text.index("branch_guard.py"),
            text.index("rbac_audit.py"),
            "the branch guard must run before the RBAC diff audit",
        )

    def test_reference_covers_lifecycle_ci_and_migration(self) -> None:
        text = flat(read(BRANCH_ISOLATION))
        for phrase in (
            "## 1. Lifecycle",
            "feat/<task-id>",
            "--require-declared",
            "BRANCH_PROTECTED",
            "## 3. How CI consumes it",
            "## 4. Migration runbook",
            "branch protection",
            "advisory",
            "authoritative",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
