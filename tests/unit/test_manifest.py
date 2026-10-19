#!/usr/bin/env python3
"""Guards the distributable SHA-256 manifest against stale release artifacts."""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "MANIFEST.sha256"
TOOL = ROOT / "tools" / "gen_manifest.py"
LINE_RE = re.compile(r"^[0-9a-f]{64}  \S.*$")


class ManifestTests(unittest.TestCase):
    def test_manifest_exists_and_is_well_formed(self) -> None:
        self.assertTrue(MANIFEST.is_file())
        lines = MANIFEST.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines, "manifest must not be empty")
        for line in lines:
            self.assertRegex(line, LINE_RE)
        paths = [line.split("  ", 1)[1] for line in lines]
        self.assertEqual(paths, sorted(paths, key=str.lower), "manifest must be sorted")
        self.assertNotIn("MANIFEST.sha256", paths)

    def test_manifest_matches_the_tracked_tree(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--check"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
