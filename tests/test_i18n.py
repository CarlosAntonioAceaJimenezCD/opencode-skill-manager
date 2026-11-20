from __future__ import annotations

import importlib.util
import io
import contextlib
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
LOCALES = CTL.parents[1] / "locales"

_loader = SourceFileLoader("skillctl_i18n", str(CTL))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
skillctl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skillctl)

LANGS = ["es", "en", "pt-BR", "fr", "de"]


class CatalogTest(unittest.TestCase):
    def test_all_locales_have_the_same_non_empty_keys(self) -> None:
        catalogs = {lang: json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
                    for lang in LANGS}
        baseline = set(catalogs["es"])
        self.assertTrue(baseline)
        for lang, data in catalogs.items():
            self.assertEqual(set(data), baseline, f"claves distintas en {lang}")
            empty = [key for key, value in data.items() if not value]
            self.assertEqual(empty, [], f"valores vacíos en {lang}: {empty}")

    def test_description_has_multilingual_triggers(self) -> None:
        text = (CTL.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        description = text.splitlines()[2]
        self.assertLessEqual(len(description), 1024)
        for word in ("session", "sessão", "session", "Sitzung"):
            self.assertIn(word, description)

    def test_normalize_language(self) -> None:
        cases = {
            "es": "es", "EN": "en", "pt": "pt-BR", "pt_br": "pt-BR",
            "english": "en", "fr": "fr", "de": "de", "xx": "",
        }
        for value, expected in cases.items():
            self.assertEqual(skillctl.normalize_language(value), expected)

    def test_detect_language(self) -> None:
        cases = {
            "Inicia la sesión y activa las skills de la tarea": "es",
            "Start the session and activate the skills for this task": "en",
            "Inicie a sessão e ative as skills da tarefa": "pt-BR",
            "Démarre la session et active les compétences de la tâche": "fr",
            "Starte die Sitzung und aktiviere die Skills der Aufgabe": "de",
        }
        for sample, expected in cases.items():
            result = skillctl.detect_language(sample)
            self.assertEqual(result["language"], expected, sample)
            self.assertGreater(result["confidence"], 0)
        self.assertEqual(skillctl.detect_language("xyz qwerty")["language"], "other")


class LanguageCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="skillctl-i18n-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skills = self.tmp / "skills"
        self.skill_dir = self.skills / "skill-manager"
        (self.skill_dir / "scripts").mkdir(parents=True)
        shutil.copy2(CTL, self.skill_dir / "scripts" / "skillctl")
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: skill-manager\ndescription: test\n---\n", encoding="utf-8"
        )
        shutil.copytree(LOCALES, self.skill_dir / "locales")
        self.env = {
            **os.environ,
            "OPENCODE_SESSION_ID": "ses_i18n",
            "OPENCODE_SKILLS_DIR": str(self.skills),
        }

    def run_ctl(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, str(self.skill_dir / "scripts" / "skillctl"), *args],
            capture_output=True, text=True, env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout

    def test_default_language_is_spanish(self) -> None:
        state = json.loads((self.tmp / "skill-manager" / "state.json").read_text()) \
            if (self.tmp / "skill-manager" / "state.json").exists() else {}
        self.run_ctl("language", "list")
        saved = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(saved["language"], "es")
        self.assertIn("idioma: es", self.run_ctl("language", "list"))

    def test_set_language_localizes_status(self) -> None:
        confirmation = self.run_ctl("language", "set", "en")
        self.assertIn("en", confirmation)
        self.assertNotIn("language.set", confirmation)
        output = self.run_ctl("status")
        self.assertIn("language: en", output)
        self.assertIn("session:", output)
        saved = json.loads((self.tmp / "skill-manager" / "state.json").read_text())
        self.assertEqual(saved["language"], "en")

    def test_detect_json_schema(self) -> None:
        output = self.run_ctl("language", "detect", "Start the session", "--json")
        data = json.loads(output)
        self.assertEqual(data["language"], "en")
        self.assertEqual(set(data), {"language", "confidence", "supported"})

    def test_search_lang_validates_tag(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.skill_dir / "scripts" / "skillctl"),
             "search", "pandas", "--lang", "xx"],
            capture_output=True, text=True, env=self.env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("idioma no soportado", result.stderr)


class SearchLocalizationTest(unittest.TestCase):
    def test_header_follows_active_language(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td)
            (catalog / "index.tsv").write_text(
                "demo\tDemo\tWrit\ttag\tdesc\ttrig\thttps://ejemplo.com/x.zip\topencodeskills\n",
                encoding="utf-8",
            )
            (catalog / ".stamp").write_text(str(int(time.time())), encoding="utf-8")
            originals = (skillctl.CATALOG_DIR, skillctl.INDEX, skillctl.STAMP, skillctl._LANG_CACHE)
            skillctl.CATALOG_DIR = catalog
            skillctl.INDEX = catalog / "index.tsv"
            skillctl.STAMP = catalog / ".stamp"
            skillctl._LANG_CACHE = "en"
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    skillctl.search("demo trigger", "en")
                self.assertIn("name", output.getvalue())
                self.assertIn("source", output.getvalue())
                self.assertNotIn("nombre", output.getvalue())
            finally:
                (skillctl.CATALOG_DIR, skillctl.INDEX, skillctl.STAMP,
                 skillctl._LANG_CACHE) = originals


if __name__ == "__main__":
    unittest.main()
