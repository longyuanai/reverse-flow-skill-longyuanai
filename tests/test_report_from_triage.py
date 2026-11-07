"""Tests for report_from_triage module."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "report_from_triage",
    ROOT / "skills" / "reverse-flow" / "scripts" / "report_from_triage.py"
)
assert SPEC is not None and SPEC.loader is not None
report_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report_mod)


class ReportFromTriageTests(unittest.TestCase):
    def test_risk_hint_high_entropy(self):
        item = {
            "prefix_entropy": 7.8,
            "indicators": {"urls": ["http://test.local"], "suspicious_terms": ["CreateProcess"]},
            "magic_hints": ["PE/Windows executable or DLL"],
        }
        risk, reasons = report_mod.risk_hint(item)
        self.assertEqual(risk, "Medium")
        self.assertTrue(len(reasons) >= 3)

    def test_risk_hint_clean_file(self):
        item = {
            "prefix_entropy": 3.0,
            "indicators": {},
            "magic_hints": [],
        }
        risk, reasons = report_mod.risk_hint(item)
        self.assertEqual(risk, "Unknown/Low")
        self.assertTrue(len(reasons) > 0)

    def test_markdown_report_generation(self):
        tmp_dir = tempfile.mkdtemp(prefix="report_test_")
        try:
            triage_data = {
                "path": "E:/test/sample.exe",
                "name": "sample.exe",
                "size": 4096,
                "hashes": {
                    "md5": "b695521381e446004e5dba7ea21a6a6e",
                    "sha1": "7eb04140d2c70c0d7166edff67b71cd5c216e165",
                    "sha256": "48abddac90d0f023ad5571bcf17914fe3387c04ee2140616e09f7b967d08c96f",
                },
                "magic_hints": ["PE/Windows executable or DLL", ".NET / CLR Managed Assembly"],
                "profiles": ["managed", "dotnet"],
                "prefix_entropy": 3.826,
                "indicators": {},
                "recommended_tools": ["inspect_cil.py", "ilspy"],
                "structure": {
                    "kind": "PE",
                    "format": "PE32",
                    "machine": "x86 (32-bit)",
                    "entry_point_rva": "0x25be",
                    "sections_count": 3,
                },
            }
            json_file = Path(tmp_dir) / "sample.triage.json"
            json_file.write_text(json.dumps(triage_data), encoding="utf-8")
            out_md = Path(tmp_dir) / "report.md"

            # Execute main via mock args
            import sys
            saved_argv = sys.argv
            try:
                sys.argv = [
                    "report_from_triage.py",
                    str(json_file),
                    "--out",
                    str(out_md),
                    "--title",
                    "Test Reverse Report",
                ]
                ret = report_mod.main()
                self.assertEqual(ret, 0)
                self.assertTrue(out_md.exists())
                content = out_md.read_text(encoding="utf-8")
                self.assertIn("# Test Reverse Report", content)
                self.assertIn("Analysis -> Initial report", content)
                self.assertNotIn("Analysis ? Initial report", content)
                self.assertIn("inspect_cil.py", content)
                self.assertIn("format=PE32", content)
            finally:
                sys.argv = saved_argv
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
