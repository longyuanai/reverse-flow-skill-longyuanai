"""Unit tests for zero-dependency native entry point & opcode disassembler."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "skills" / "pojia" / "scripts" / "inspect_native.py"

import importlib.util

spec = importlib.util.spec_from_file_location("inspect_native", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
native_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_mod)

decode_x86_x64 = native_mod.decode_x86_x64
inspect_native = native_mod.inspect_native


class InspectNativeTests(unittest.TestCase):
    def test_decode_x86_x64_prologue(self) -> None:
        # Standard x64 prologue: push rbp; mov rbp, rsp; sub rsp, 0x20; xor rax, rax; ret
        code = bytes.fromhex("55 4889e5 4883ec20 4831c0 c3")
        instructions = decode_x86_x64(code, base_address=0x1000)

        mnemonics = [i["mnemonic"] for i in instructions]
        self.assertEqual(mnemonics, ["push", "mov", "sub", "xor", "ret"])
        self.assertEqual(instructions[0]["operands"], "rbp")
        self.assertEqual(instructions[1]["operands"], "rbp, rsp")
        self.assertEqual(instructions[2]["operands"], "rsp, 0x20")

    def test_decode_calls_and_jumps(self) -> None:
        # call rel32, jmp rel32, jmp rel8, syscall, nop, int3
        code = bytes.fromhex("e8 05000000 e9 10000000 eb 02 0f05 90 cc")
        instructions = decode_x86_x64(code, base_address=0x2000)

        mnemonics = [i["mnemonic"] for i in instructions]
        self.assertIn("call", mnemonics)
        self.assertIn("jmp", mnemonics)
        self.assertIn("syscall", mnemonics)
        self.assertIn("nop", mnemonics)
        self.assertIn("int3", mnemonics)

    def test_inspect_native_sample_exe(self) -> None:
        sample_path = ROOT / "tests" / "fixtures" / "sample.exe"
        if not sample_path.exists():
            self.skipTest("sample.exe fixture missing")

        res = inspect_native(sample_path)
        self.assertTrue(res["format"].startswith("PE"))
        self.assertIsNotNone(res["entry_point"])
        self.assertIsInstance(res["instructions"], list)
        self.assertGreater(len(res["instructions"]), 0)

    def test_reject_nonexistent_binary(self) -> None:
        with self.assertRaises(FileNotFoundError):
            inspect_native(ROOT / "tests" / "nonexistent.exe")


if __name__ == "__main__":
    unittest.main()
