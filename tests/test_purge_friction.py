"""Tests for purge_friction module."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "purge_friction",
    ROOT / "scripts" / "purge_friction.py"
)
assert SPEC is not None and SPEC.loader is not None
purge_friction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(purge_friction)


class PurgeFrictionTests(unittest.TestCase):
    def test_apply_friction_purge_creates_new_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            res = purge_friction.apply_friction_purge(target_dir=temp_path)

            self.assertEqual(res["status"], "success")
            self.assertIsNone(res["backup_path"])
            self.assertGreater(res["added_rules"], 0)

            settings_file = temp_path / ".claude" / "settings.local.json"
            self.assertTrue(settings_file.exists())

            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("permissions", data)
            self.assertIn("allow", data["permissions"])
            rules = data["permissions"]["allow"]
            self.assertIn("Bash(python *)", rules)
            self.assertIn("PowerShell(py *)", rules)
            self.assertIn("PowerShell(*diff_verifier.py*)", rules)

    def test_apply_friction_purge_merges_and_backups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_dir = temp_path / ".claude"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.local.json"

            initial_data = {
                "permissions": {
                    "allow": [
                        "WebFetch(domain:github.com)",
                        "PowerShell(Get-ChildItem *)"
                    ]
                }
            }
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # Apply
            res = purge_friction.apply_friction_purge(target_dir=temp_path)
            self.assertEqual(res["status"], "success")
            self.assertIsNotNone(res["backup_path"])
            self.assertTrue(Path(res["backup_path"]).exists())

            with open(settings_file, "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            rules = updated_data["permissions"]["allow"]
            # Preserved existing
            self.assertIn("WebFetch(domain:github.com)", rules)
            self.assertIn("PowerShell(Get-ChildItem *)", rules)
            # Added new
            self.assertIn("PowerShell(*inspect_cil.py*)", rules)

    def test_rollback_friction_purge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_dir = temp_path / ".claude"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.local.json"

            initial_data = {"version": "original"}
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            # Apply purge (creates backup)
            purge_friction.apply_friction_purge(target_dir=temp_path)

            # Change file
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({"version": "corrupted"}, f)

            # Rollback
            roll_res = purge_friction.rollback_friction_purge(target_dir=temp_path)
            self.assertEqual(roll_res["status"], "success")

            with open(settings_file, "r", encoding="utf-8") as f:
                restored = json.load(f)
            self.assertEqual(restored.get("version"), "original")

    def test_diagnose_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            diag = purge_friction.diagnose_environment(repo_root=ROOT, target_dir=temp_path)

            self.assertIn("python_interpreters", diag)
            self.assertIn("claude_settings_path", diag)
            self.assertIn("permissions_active", diag)
            self.assertIn("is_ready_for_frictionless_re", diag)
            self.assertTrue(diag["repo_skills_present"])

    def test_setup_shell_aliases(self):
        res = purge_friction.setup_shell_aliases(repo_root=ROOT)
        self.assertEqual(res["status"], "success")
        self.assertIsInstance(res["configured_profiles"], list)


if __name__ == "__main__":
    unittest.main()
