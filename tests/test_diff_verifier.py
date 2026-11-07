"""Tests for diff_verifier module."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "diff_verifier",
    ROOT / "skills" / "pojia" / "scripts" / "diff_verifier.py"
)
assert SPEC is not None and SPEC.loader is not None
diff_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diff_verifier)


class DiffVerifierTests(unittest.TestCase):
    def test_corpus_generation_int(self):
        corpus = diff_verifier.generate_default_corpus(kind="int", count=20)
        self.assertIn("0", corpus)
        self.assertIn("1", corpus)
        self.assertIn("2147483647", corpus)  # 0x7FFFFFFF
        self.assertIn("4294967295", corpus)  # 0xFFFFFFFF
        self.assertTrue(len(corpus) >= 20)

    def test_corpus_generation_str(self):
        corpus = diff_verifier.generate_default_corpus(kind="str", count=10)
        self.assertIn("", corpus)
        self.assertIn("A", corpus)
        self.assertIn("admin", corpus)

    def test_verify_differential_success(self):
        # Target script that doubles integer input
        target_code = "import sys\nfor line in sys.stdin:\n    line = line.strip()\n    if line:\n        print(int(line) * 2)\n"
        tmp_target = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        try:
            tmp_target.write(target_code.encode("utf-8"))
            tmp_target.close()

            # Python implementation
            def recon_func(x: int) -> int:
                return x * 2

            corpus = ["0", "1", "10", "100", "999"]
            cmd = [sys.executable, tmp_target.name]
            report = diff_verifier.verify_differential(cmd, recon_func, corpus, input_mode="stdin")
            self.assertEqual(report["total_cases"], 5)
            self.assertEqual(report["passed"], 5)
            self.assertEqual(report["failed"], 0)
            self.assertEqual(report["accuracy"], 1.0)
            self.assertEqual(report["confidence"], 1.0)
            self.assertEqual(len(report["mismatches"]), 0)
        finally:
            Path(tmp_target.name).unlink(missing_ok=True)

    def test_verify_differential_mismatch_detected(self):
        # Target doubles input
        target_code = "import sys\nfor line in sys.stdin:\n    line = line.strip()\n    if line:\n        print(int(line) * 2)\n"
        tmp_target = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        try:
            tmp_target.write(target_code.encode("utf-8"))
            tmp_target.close()

            # Faulty Python implementation
            def faulty_func(x: int) -> int:
                return x * 2 + 1  # Mutant

            corpus = ["0", "1", "10"]
            cmd = [sys.executable, tmp_target.name]
            report = diff_verifier.verify_differential(cmd, faulty_func, corpus, input_mode="stdin")
            self.assertEqual(report["passed"], 0)
            self.assertEqual(report["failed"], 3)
            self.assertEqual(report["accuracy"], 0.0)
            self.assertEqual(report["confidence"], 0.0)
            self.assertTrue(len(report["mismatches"]) > 0)
        finally:
            Path(tmp_target.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
