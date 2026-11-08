"""Tests for inspect_cil module."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inspect_cil",
    ROOT / "skills" / "pojia" / "scripts" / "inspect_cil.py"
)
assert SPEC is not None and SPEC.loader is not None
inspect_cil = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_cil)


class InspectCilTests(unittest.TestCase):
    def setUp(self):
        fixture_path = ROOT / "tests" / "fixtures" / "sample.exe"
        if not fixture_path.exists():
            fixture_path = ROOT / ".validation" / "capture-1" / "sample.exe"
        self.sample = fixture_path
        if not self.sample.exists():
            self.skipTest("sample.exe fixture not present")

    def test_inspect_cil_sample_exe(self):
        res = inspect_cil.inspect_cil(self.sample)
        self.assertEqual(res["size"], 4096)
        self.assertEqual(res["sha256"], "48abddac90d0f023ad5571bcf17914fe3387c04ee2140616e09f7b967d08c96f")
        self.assertEqual(res["metadata_version"], "v4.0.30319")
        self.assertEqual(res["mvid"], "0a9712bb-c098-48d9-977d-e5830475ec8e")
        self.assertEqual(res["entry_token"], "0x6000002")

        # Verify methods
        names = [m["name"] for m in res["methods"]]
        self.assertIn("Transform", names)
        self.assertIn("Main", names)

        transform = next(m for m in res["methods"] if m["name"] == "Transform")
        self.assertEqual(transform["token"], "0x6000001")
        self.assertEqual(transform["code_size"], 28)
        self.assertEqual(transform["code_sha256"], "4884ddd2ff3e3b779069e500059d3537e1f483f212b1d1bb6c9c26541641eab2")

        opcodes = [ins["opcode"] for ins in transform["instructions"]]
        expected_subset = ["ldarg.0", "ldc.i4", "xor", "stloc.0", "ldc.i4.7", "shl", "shr.un", "or", "mul", "add", "ret"]
        for op in expected_subset:
            self.assertIn(op, opcodes)

    def test_disassembly_text_filtering(self):
        res = inspect_cil.inspect_cil(self.sample)
        text = inspect_cil.to_disassembly_text(res, target_method="Transform")
        self.assertIn(".method Transform () cil managed", text)
        self.assertNotIn(".method Main () cil managed", text)
        self.assertIn("xor", text)

    def test_reject_non_dotnet(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".exe", delete=False)
        try:
            tmp.write(b"MZ" + b"\x00" * 200)
            tmp.close()
            with self.assertRaises(ValueError):
                inspect_cil.inspect_cil(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_reject_truncated_pe(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".exe", delete=False)
        try:
            # PE header offset points to EOF boundary so reading PE fields would trigger struct/index error
            tmp.write(b"MZ" + b"\x00" * 58 + b"\x40\x00\x00\x00" + b"PE\x00\x00" + b"\x00" * 5)
            tmp.close()
            with self.assertRaises(ValueError) as ctx:
                inspect_cil.inspect_cil(Path(tmp.name))
            self.assertTrue("Truncated or malformed" in str(ctx.exception) or "Invalid PE" in str(ctx.exception))
        finally:
            Path(tmp.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
