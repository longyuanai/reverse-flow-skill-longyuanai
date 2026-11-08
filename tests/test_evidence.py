"""Tests for evidence module."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evidence",
    ROOT / "skills" / "pojia" / "scripts" / "evidence.py"
)
assert SPEC is not None and SPEC.loader is not None
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "sample.bin").write_bytes(b"original\x00bytes")

    def tearDown(self):
        self.temp.cleanup()

    def test_verifies_original_and_detects_changed_same_length(self):
        record = evidence.snapshot(self.root, ["sample.bin"])
        self.assertTrue(evidence.verify(self.root, record)["ok"])
        (self.root / "sample.bin").write_bytes(b"modified\x00bytes")
        self.assertFalse(evidence.verify(self.root, record)["ok"])

    def test_missing_file_is_failure(self):
        record = evidence.snapshot(self.root, ["sample.bin"])
        (self.root / "sample.bin").unlink()
        self.assertFalse(evidence.verify(self.root, record)["ok"])

    def test_case_can_be_relocated(self):
        record = evidence.snapshot(self.root, ["sample.bin"])
        relocated = self.root / "relocated"
        relocated.mkdir()
        shutil.copyfile(self.root / "sample.bin", relocated / "sample.bin")
        self.assertTrue(evidence.verify(relocated, record)["ok"])

    def test_parent_escape_rejected(self):
        with self.assertRaises(ValueError):
            evidence.snapshot(self.root, ["../outside.bin"])

    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):
            evidence.snapshot(self.root, [str(self.root / "sample.bin")])

    def test_malicious_manifest_cannot_read_outside_case(self):
        record = {"schema_version": 1, "files": [{"path": "../outside.bin"}]}
        self.assertFalse(evidence.verify(self.root, record)["ok"])

    def test_empty_manifest_is_not_success(self):
        with self.assertRaises(ValueError):
            evidence.verify(self.root, {"schema_version": 1, "files": []})


if __name__ == "__main__":
    unittest.main()
