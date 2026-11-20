from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTL = ROOT / "skills" / "skill-manager" / "scripts" / "skillctl"

_loader = SourceFileLoader("skillctl_under_test", str(CTL))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
skillctl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skillctl)


class GithubSourceParsingTest(unittest.TestCase):
    def test_formats(self) -> None:
        cases = {
            "owner/repo": "owner/repo@main",
            "owner/repo.git": "owner/repo@main",
            "https://github.com/owner/repo": "owner/repo@main",
            "https://github.com/owner/repo/": "owner/repo@main",
            "https://github.com/owner/repo/tree/dev": "owner/repo@dev",
            "owner/repo@feature/x": "owner/repo@feature/x",
            "git@github.com:owner/repo.git": "owner/repo@main",
        }
        for value, expected in cases.items():
            parsed = skillctl.parse_github_source(value)
            self.assertIsNotNone(parsed, value)
            self.assertEqual(parsed["id"], expected)

    def test_invalid(self) -> None:
        for value in ("skill-manager", "https://ejemplo.com/owner/repo", "owner/repo/../x", ""):
            self.assertIsNone(skillctl.parse_github_source(value), value)

    def test_old_index_rows_are_padded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td)
            (catalog / "index.tsv").write_text(
                "demo\tDemo\tWrit\t tag \tdesc\ttrig\thttps://ejemplo.com/x.zip\n",
                encoding="utf-8",
            )
            (catalog / ".stamp").write_text(str(int(time.time())), encoding="utf-8")
            original = skillctl.CATALOG_DIR, skillctl.INDEX, skillctl.STAMP
            skillctl.CATALOG_DIR, skillctl.INDEX, skillctl.STAMP = (
                catalog, catalog / "index.tsv", catalog / ".stamp"
            )
            try:
                row = skillctl.read_index()[0]
                self.assertEqual(len(row), 8)
                self.assertEqual(row[7], "")
            finally:
                skillctl.CATALOG_DIR, skillctl.INDEX, skillctl.STAMP = original


class GithubSourceCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="skillctl-gh-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skills = self.tmp / "skills"
        self.skill_dir = self.skills / "skill-manager"
        (self.skill_dir / "scripts").mkdir(parents=True)
        shutil.copy2(CTL, self.skill_dir / "scripts" / "skillctl")
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: skill-manager\ndescription: test\n---\n", encoding="utf-8"
        )
        self.env = {
            **os.environ,
            "OPENCODE_SESSION_ID": "ses_gh_test",
            "OPENCODE_SKILLS_DIR": str(self.skills),
        }

    def run_ctl(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(self.skill_dir / "scripts" / "skillctl"), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def test_add_list_remove(self) -> None:
        self.run_ctl("source", "add", "owner/repo", "https://github.com/otro/repo/tree/dev")
        state = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(state["sources"], ["owner/repo@main", "otro/repo@dev"])
        self.assertIn("otro/repo@dev", self.run_ctl("source", "list").stdout)
        self.run_ctl("source", "remove", "owner/repo")
        state = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(state["sources"], ["otro/repo@dev"])

    def test_topic_add_list_remove(self) -> None:
        self.run_ctl("topic", "add", "#OpenCode-Skills", "otro-tag")
        state = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(state["topics"], ["opencode-skills", "otro-tag"])
        self.assertIn("opencode-skills", self.run_ctl("topic", "list").stdout)
        self.run_ctl("topic", "remove", "otro-tag")
        state = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(state["topics"], ["opencode-skills"])


class RawCatalogInstallTest(unittest.TestCase):
    def test_installs_files_from_catalog_spec(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = root / "payload"
            payload.mkdir()
            (payload / "SKILL.md").write_text(
                "---\nname: demo\ndescription: demo skill\n---\n\n# Demo\n",
                encoding="utf-8",
            )
            skills = root / "skills"
            original = skillctl.SKILLS, skillctl.DISABLED, skillctl.download, skillctl.github_headers
            skillctl.SKILLS = skills
            skillctl.DISABLED = root / "disabled"
            skillctl.github_headers = lambda accept="": {}
            skillctl.download = lambda url, dest, headers=None: shutil.copy2(payload / "SKILL.md", dest)
            try:
                ok, msg = skillctl.install_raw_catalog(
                    "demo", "raw-catalog|https://raw.githubusercontent.com/o/r/main/docs/demo/|SKILL.md"
                )
                self.assertTrue(ok, msg)
                self.assertTrue((skills / "demo" / "SKILL.md").is_file())
            finally:
                skillctl.SKILLS, skillctl.DISABLED, skillctl.download, skillctl.github_headers = original


class GithubTopicSearchTest(unittest.TestCase):
    def test_topic_query_uses_default_branch(self) -> None:
        captured = {}

        def fake_http_json(url: str) -> dict:
            captured["url"] = url
            return {
                "items": [{
                    "full_name": "owner/repo",
                    "default_branch": "develop",
                    "topics": ["opencode-skills"],
                    "html_url": "https://github.com/owner/repo",
                }]
            }

        original = skillctl.http_json
        skillctl.http_json = fake_http_json
        try:
            repos = skillctl.github_topic_repos("opencode-skills")
        finally:
            skillctl.http_json = original
        self.assertIn("topic%3Aopencode-skills", captured["url"])
        self.assertEqual(repos[0][0]["id"], "owner/repo@develop")

    def test_discover_filters_repos_without_skills(self) -> None:
        repos = [
            ({"owner": "a", "repo": "con-skill", "branch": "main", "id": "a/con-skill@main"},
             {"topics": ["opencode-skills"], "html_url": "https://github.com/a/con-skill"}),
            ({"owner": "b", "repo": "sin-skill", "branch": "main", "id": "b/sin-skill@main"},
             {"topics": [], "html_url": "https://github.com/b/sin-skill"}),
        ]
        originals = (skillctl.github_topic_repos, skillctl.github_rows, skillctl.load_state)
        skillctl.github_topic_repos = lambda topic: repos
        skillctl.github_rows = lambda src: [["demo", "Demo", "GitHub", "", "", "", "url", ""]] \
            if src["repo"] == "con-skill" else []
        skillctl.load_state = lambda: {"sources": [], "topics": []}
        try:
            import io
            import contextlib
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                skillctl.discover_topics(["opencode-skills"])
            text = output.getvalue()
            self.assertIn("a/con-skill", text)
            self.assertNotIn("b/sin-skill", text)
        finally:
            skillctl.github_topic_repos, skillctl.github_rows, skillctl.load_state = originals


if __name__ == "__main__":
    unittest.main()
