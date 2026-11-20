from __future__ import annotations

import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


class PackageTest(unittest.TestCase):
    def test_index_matches_version_and_files(self) -> None:
        index = json.loads((DIST / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index["skills"]), 1)
        entry = index["skills"][0]
        self.assertEqual(entry["name"], "skill-manager")
        self.assertEqual(entry["version"], VERSION)
        self.assertIn("SKILL.md", entry["files"])
        for rel in entry["files"]:
            self.assertTrue((DIST / "skill-manager" / rel).is_file(), rel)

    def test_zip_contains_the_same_files(self) -> None:
        index = json.loads((DIST / "index.json").read_text(encoding="utf-8"))
        expected = {
            f"skill-manager/{rel}" for rel in index["skills"][0]["files"]
        }
        archive_path = DIST / f"opencode-skill-manager-{VERSION}.zip"
        self.assertTrue(archive_path.is_file())
        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(set(archive.namelist()), expected)


if __name__ == "__main__":
    unittest.main()
