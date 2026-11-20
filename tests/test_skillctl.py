from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLCTL = ROOT / "skills" / "skill-manager" / "scripts" / "skillctl"


class SkillctlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="skillctl-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skills = self.tmp / "skills"
        self.skill_dir = self.skills / "skill-manager"
        (self.skill_dir / "scripts").mkdir(parents=True)
        shutil.copy2(SKILLCTL, self.skill_dir / "scripts" / "skillctl")
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: skill-manager\ndescription: test\n---\n", encoding="utf-8"
        )
        shutil.copytree(ROOT / "skills" / "skill-manager" / "locales",
                        self.skill_dir / "locales")
        for slug in ("alpha", "beta", "gamma"):
            directory = self.skills / slug
            directory.mkdir()
            (directory / "SKILL.md").write_text(
                f"---\nname: {slug}\ndescription: {slug}\n---\n", encoding="utf-8"
            )

    @property
    def state_path(self) -> Path:
        return self.tmp / "skill-manager" / "state.json"

    def state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def run_ctl(
        self,
        *args: str,
        session: str = "ses_test",
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OPENCODE_SESSION_ID"] = session
        env["OPENCODE_SKILLS_DIR"] = str(self.skills)
        env.pop("OPENCODE_SKILL_MANAGER_STATE", None)
        env.pop("OPENCODE_SKILLS_DISABLED", None)
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [sys.executable, str(self.skill_dir / "scripts" / "skillctl"), *args],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def test_session_begin_initializes_state(self) -> None:
        self.run_ctl("session-begin")
        state = self.state()
        self.assertEqual(state["session_id"], "ses_test")
        self.assertEqual(state["session_core"], ["skill-manager"])
        self.assertEqual(state["active"], [])

    def test_task_lifecycle_deactivates_and_restores(self) -> None:
        self.run_ctl("session-begin")
        self.run_ctl("begin", "tarea de prueba")
        self.run_ctl("ensure", "alpha", "beta")

        state = self.state()
        self.assertEqual(state["active"], ["alpha", "beta"])

        self.run_ctl("sync")
        self.assertTrue((self.skills / "alpha").is_dir())
        self.assertTrue((self.skills / "beta").is_dir())
        self.assertTrue((self.skills / "skill-manager").is_dir())
        self.assertFalse((self.skills / "gamma").exists())
        self.assertTrue((self.tmp / "skills-disabled" / "gamma").is_dir())

        self.run_ctl("end")
        self.assertEqual(self.state()["active"], [])

        self.run_ctl("restore")
        self.assertTrue((self.skills / "gamma").is_dir())
        self.assertFalse((self.tmp / "skills-disabled" / "gamma").exists())

    def test_dry_run_does_not_move_directories(self) -> None:
        self.run_ctl("session-begin")
        result = self.run_ctl("sync", "--dry-run")
        self.assertIn("gamma", result.stdout)
        self.assertTrue((self.skills / "gamma").is_dir())

    def test_pinned_skill_survives_new_task_and_sync(self) -> None:
        self.run_ctl("pin", "gamma")
        self.run_ctl("session-begin")
        self.run_ctl("begin", "otra tarea")
        self.run_ctl("sync")
        self.assertTrue((self.skills / "gamma").is_dir())

        self.run_ctl("unpin", "gamma")
        self.run_ctl("sync")
        self.assertFalse((self.skills / "gamma").exists())

    def test_new_session_resets_task_and_session_pins(self) -> None:
        self.run_ctl("session-begin", "alpha")
        self.run_ctl("begin", "tarea vieja")
        self.run_ctl("ensure", "beta")
        self.assertIn("beta", self.state()["active"])

        self.run_ctl("status", session="ses_otra")
        state = self.state()
        self.assertEqual(state["session_id"], "ses_otra")
        self.assertEqual(state["active"], [])
        self.assertEqual(state["session_core"], ["skill-manager"])

    def test_state_path_can_be_overridden(self) -> None:
        custom = self.tmp / "custom" / "state.json"
        self.run_ctl(
            "status",
            extra_env={"OPENCODE_SKILL_MANAGER_STATE": str(custom)},
        )
        self.assertTrue(custom.is_file())
        self.assertEqual(json.loads(custom.read_text(encoding="utf-8"))["session_id"], "ses_test")


if __name__ == "__main__":
    unittest.main()
