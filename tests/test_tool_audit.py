"""Tests for tool_audit module."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tool_audit",
    ROOT / "skills" / "reverse-flow" / "scripts" / "tool_audit.py"
)
assert SPEC is not None and SPEC.loader is not None
tool_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool_audit)


class ToolAuditTests(unittest.TestCase):
    def test_check_module_standard_library(self):
        self.assertTrue(tool_audit.check_module("sys"))
        self.assertTrue(tool_audit.check_module("json"))

    def test_check_module_non_existent(self):
        self.assertFalse(tool_audit.check_module("definitely_non_existent_module_12345"))

    def test_audit_catalog_profile_managed(self):
        res = tool_audit.audit(profile="managed")
        self.assertEqual(res["profile"], "managed")
        names = [r["name"] for r in res["tools"]]
        self.assertIn("ILSpy", names)
        self.assertIn("dnSpy", names)
        self.assertIn("de4dot", names)

    def test_markdown_formatting_no_broken_arrows(self):
        res = tool_audit.audit(profile="managed")
        md = tool_audit.to_markdown(res)
        self.assertNotIn(" ? ", md)  # Ensure no corrupted encoding markers
        self.assertIn("| Tool | Stars | Purpose | Found | Repo |", md)


if __name__ == "__main__":
    unittest.main()
