#!/usr/bin/env python3
"""Guards the user-facing docs index, links and archived-document boundary."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DocsIndexTests(unittest.TestCase):
    def test_docs_index_and_archive_index_exist(self) -> None:
        self.assertTrue((DOCS / "README.md").is_file())
        self.assertTrue((ARCHIVE / "README.md").is_file())
        self.assertTrue((ARCHIVE / "skills-remediation.zh-CN.md").is_file())

    def test_index_lists_every_current_doc(self) -> None:
        index = read(DOCS / "README.md")
        for path in sorted(DOCS.glob("*.md")):
            if path.name == "README.md":
                continue
            self.assertIn(path.name, index, "docs index misses: " + path.name)

    def test_current_docs_do_not_link_to_root_remediation(self) -> None:
        for path in DOCS.rglob("*.md"):
            if ARCHIVE in path.parents:
                continue
            text = read(path)
            self.assertNotIn("(skills-remediation.zh-CN.md)", text, str(path))
            for match in re.findall(r"\(([^)]*skills-remediation[^)]*)\)", text):
                self.assertIn("archive/skills-remediation.zh-CN.md", match, str(path))

    def test_current_docs_relative_links_resolve(self) -> None:
        for path in DOCS.rglob("*.md"):
            if ARCHIVE in path.parents:
                continue
            for target in LINK_RE.findall(read(path)):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (path.parent / target.split("#")[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken docs link in {path}: {target}")

    def test_gate3_guide_documents_authority_and_exit_codes(self) -> None:
        text = read(DOCS / "gate3-precheck.zh-CN.md")
        for phrase in ("CI 的 Gate 3 才是权威", "退出码", "不执行测试", "本地预检通过 ≠ 任务通过"):
            self.assertIn(phrase, text)

    def test_benchmark_is_marked_as_baseline_and_current(self) -> None:
        text = read(DOCS / "skills-benchmark.zh-CN.md")
        self.assertIn("v3.1.0 基线", text)
        self.assertIn("415 passed, 1 skipped", text)


if __name__ == "__main__":
    unittest.main()
