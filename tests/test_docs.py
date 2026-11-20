from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "GUIDE.md"
README = ROOT / "README.md"
CTL = ROOT / "skills" / "skill-manager" / "scripts" / "skillctl"

SUBCOMMANDS = [
    "source add", "source list", "source remove",
    "topic add", "topic list", "topic remove", "topic search",
]

ENV_VARS = [
    "OPENCODE_SKILLS_DIR", "OPENCODE_SKILLS_DISABLED",
    "OPENCODE_SKILL_MANAGER_STATE", "OPENCODE_SKILL_CATALOG_DIR",
    "OPENCODE_SESSION_ID", "GITHUB_TOKEN", "GITHUB_TOPIC_LIMIT",
]


def top_level_commands() -> list[str]:
    source = CTL.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'cmd == "([a-z][a-z-]*)"', source)))


class DocumentationCoverageTest(unittest.TestCase):
    def test_guide_documents_every_command(self) -> None:
        guide = GUIDE.read_text(encoding="utf-8")
        missing = [cmd for cmd in top_level_commands() if f"### `{cmd}" not in guide]
        self.assertEqual(missing, [], f"comandos sin sección en GUIDE.md: {missing}")

    def test_guide_documents_every_subcommand(self) -> None:
        guide = GUIDE.read_text(encoding="utf-8")
        missing = [cmd for cmd in SUBCOMMANDS if f"### `{cmd}" not in guide]
        self.assertEqual(missing, [], f"subcomandos sin sección en GUIDE.md: {missing}")

    def test_guide_documents_dry_run(self) -> None:
        self.assertIn("### `sync` y `sync --dry-run`", GUIDE.read_text(encoding="utf-8"))

    def test_guide_documents_every_env_var(self) -> None:
        guide = GUIDE.read_text(encoding="utf-8")
        missing = [var for var in ENV_VARS if var not in guide]
        self.assertEqual(missing, [], f"variables sin documentar: {missing}")

    def test_readme_links_the_guide(self) -> None:
        self.assertIn("](GUIDE.md)", README.read_text(encoding="utf-8"))

    def test_readme_mentions_every_command(self) -> None:
        readme = README.read_text(encoding="utf-8")
        missing = [cmd for cmd in top_level_commands() if f"`{cmd}" not in readme]
        self.assertEqual(missing, [], f"comandos ausentes en README.md: {missing}")


if __name__ == "__main__":
    unittest.main()
