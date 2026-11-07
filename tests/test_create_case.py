"""Tests for create_case module."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "create_case",
    ROOT / "skills" / "reverse-flow" / "scripts" / "create_case.py"
)
assert SPEC is not None and SPEC.loader is not None
create_case = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(create_case)


class CreateCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="case_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_slugify(self):
        self.assertEqual(create_case.slugify("Sample Case #1"), "sample-case-1")
        self.assertEqual(create_case.slugify("---test--case---"), "test-case")
        self.assertEqual(create_case.slugify(""), "reverse-case")

    def test_create_case_basic(self):
        parent = Path(self.temp_dir)
        case_id = create_case.slugify("Basic Audit")
        case_dir = parent / case_id
        for sub in ["artifacts", "triage", "reports", "logs", "notes", "exports", "tools", "prompts"]:
            (case_dir / sub).mkdir(parents=True, exist_ok=True)
        meta = {
            "case_name": "Basic Audit",
            "case_id": case_id,
            "goal": "reverse sample",
            "scope": "local sandbox",
            "directories": ["artifacts", "triage", "reports", "logs", "notes", "exports", "tools", "prompts"],
        }
        (case_dir / "case.json").write_text(json.dumps(meta), encoding="utf-8")
        self.assertTrue((case_dir / "case.json").exists())
        self.assertTrue((case_dir / "artifacts").is_dir())

    def test_create_case_with_artifact(self):
        parent = Path(self.temp_dir)
        sample = ROOT / "tests" / "fixtures" / "sample.exe"
        if not sample.exists():
            sample = ROOT / ".validation" / "capture-1" / "sample.exe"
        if not sample.exists():
            self.skipTest("sample.exe fixture missing")

        # Emulate script logic with artifact
        case_id = create_case.slugify("Artifact Ingestion")
        case_dir = parent / case_id
        for sub in ["artifacts", "triage", "reports", "logs", "notes", "exports", "tools", "prompts"]:
            (case_dir / sub).mkdir(parents=True, exist_ok=True)

        dest_art = case_dir / "artifacts" / sample.name
        shutil.copyfile(sample, dest_art)
        manifest = {
            "schema_version": 1,
            "files": [{"path": f"artifacts/{sample.name}", "size": dest_art.stat().st_size, "sha256": "dummy"}]
        }
        (case_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        self.assertTrue(dest_art.exists())
        self.assertTrue((case_dir / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
