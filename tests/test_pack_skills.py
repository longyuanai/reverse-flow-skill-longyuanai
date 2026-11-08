"""Tests for pack_skills module."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pack_skills",
    ROOT / "scripts" / "pack_skills.py"
)
assert SPEC is not None and SPEC.loader is not None
pack_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pack_skills)


class PackSkillsTests(unittest.TestCase):
    def test_should_include_filter(self):
        self.assertTrue(pack_skills.should_include(Path("skills/pojia/SKILL.md")))
        self.assertTrue(pack_skills.should_include(Path("skills/reverse-flow/scripts/triage.py")))
        self.assertFalse(pack_skills.should_include(Path("skills/pojia/__pycache__/cache.py")))
        self.assertFalse(pack_skills.should_include(Path("skills/pojia/scripts/test.pyc")))
        self.assertFalse(pack_skills.should_include(Path("skills/pojia/.DS_Store")))

    def test_pack_all_creates_valid_archives(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            results = pack_skills.pack_all(out_dir)

            self.assertIn("reverse-flow", results)
            self.assertIn("pojia", results)

            # Check files exist
            rf_skill = out_dir / "reverse-flow.skill"
            pojia_skill = out_dir / "pojia.skill"
            checksum_file = out_dir / "checksums.sha256"

            self.assertTrue(rf_skill.exists())
            self.assertTrue(pojia_skill.exists())
            self.assertTrue(checksum_file.exists())

            # Verify checksum file contents
            content = checksum_file.read_text(encoding="utf-8")
            self.assertIn("reverse-flow.skill", content)
            self.assertIn("pojia.skill", content)

            # Inspect zip contents
            with zipfile.ZipFile(pojia_skill, "r") as zf:
                names = zf.namelist()
                self.assertIn("pojia/SKILL.md", names)
                self.assertIn("pojia/scripts/inspect_cil.py", names)
                # Ensure no pycache
                for name in names:
                    self.assertNotIn("__pycache__", name)
                    self.assertFalse(name.endswith(".pyc"))


if __name__ == "__main__":
    unittest.main()
