"""Tests for demo_quickstart module."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "demo_quickstart",
    ROOT / "demo_quickstart.py"
)
assert SPEC is not None and SPEC.loader is not None
demo_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo_mod)


class DemoQuickstartTests(unittest.TestCase):
    def test_run_demo_executes_cleanly(self):
        exit_code = demo_mod.run_demo()
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
