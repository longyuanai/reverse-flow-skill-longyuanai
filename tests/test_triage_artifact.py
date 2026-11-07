"""Tests for triage_artifact module."""
from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "triage_artifact",
    ROOT / "skills" / "reverse-flow" / "scripts" / "triage_artifact.py"
)
assert SPEC is not None and SPEC.loader is not None
triage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(triage)


class TriageArtifactTests(unittest.TestCase):
    def test_entropy_calculation(self):
        self.assertEqual(triage.entropy(b""), 0.0)
        # Uniform bytes -> 0 entropy
        self.assertEqual(triage.entropy(b"A" * 100), 0.0)
        # High entropy: all 256 byte values present uniformly
        all_bytes = bytes(range(256)) * 10
        ent = triage.entropy(all_bytes)
        self.assertAlmostEqual(ent, 8.0, places=2)

    def test_detect_magic_dot_net(self):
        data = b"MZ\x90\x00" + b"\x00" * 60 + b"BSJB\x00\x00" + b"_CorExeMain"
        hints = triage.detect_magic(data)
        self.assertIn("PE/Windows executable or DLL", hints)
        self.assertIn(".NET / CLR Managed Assembly", hints)

    def test_detect_magic_upx_and_go(self):
        pe_upx = b"MZ" + b"\x00" * 20 + b"UPX0\x00\x00" + b"Go buildinf:\x00"
        hints = triage.detect_magic(pe_upx)
        self.assertIn("UPX packed executable", hints)
        self.assertIn("Go runtime binary", hints)

    def test_parse_pe_brief_valid(self):
        # Construct minimal synthetic PE header
        pe_offset = 0x80
        data = bytearray(b"MZ" + b"\x00" * (pe_offset - 2))
        struct.pack_into("<I", data, 0x3C, pe_offset)
        data.extend(b"PE\0\0")
        opt_size = 0xF0
        data.extend(struct.pack("<HHIIIHH", 0x8664, 2, 0x60000000, 0, 0, opt_size, 0x0002))
        opt_hdr = bytearray(opt_size)
        struct.pack_into("<H", opt_hdr, 0, 0x20B)  # PE32+ (64-bit)
        struct.pack_into("<I", opt_hdr, 16, 0x1000)  # entry point RVA
        struct.pack_into("<H", opt_hdr, 68, 3)  # subsystem = Console
        data.extend(opt_hdr)
        # Section 1: .text
        data.extend(b".text\0\0\0" + struct.pack("<IIII", 0x500, 0x1000, 0x600, 0x200) + b"\x00" * 16)
        # Section 2: .data
        data.extend(b".data\0\0\0" + struct.pack("<IIII", 0x200, 0x2000, 0x200, 0x800) + b"\x00" * 16)
        data.extend(b"\x00" * 1024)

        parsed = triage.parse_pe_brief(bytes(data))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["kind"], "PE")
        self.assertEqual(parsed["format"], "PE32+")
        self.assertEqual(parsed["machine"], "x86_64 (64-bit)")
        self.assertEqual(parsed["subsystem"], "Windows CUI (Console)")
        self.assertEqual(parsed["entry_point_rva"], "0x1000")
        self.assertEqual(parsed["sections_count"], 2)
        self.assertEqual(parsed["sections"][0]["name"], ".text")
        self.assertEqual(parsed["sections"][1]["name"], ".data")

    def test_parse_elf_brief_valid(self):
        # Minimal synthetic ELF64 header
        # EI_MAG: \x7fELF, EI_CLASS: 2 (64-bit), EI_DATA: 1 (little-endian), EI_VERSION: 1
        hdr = bytearray(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8)
        # e_type: 2 (EXEC), e_machine: 0x3E (x86_64), e_version: 1, e_entry: 0x401000
        hdr.extend(struct.pack("<HHIQ", 2, 0x3E, 1, 0x401000))
        hdr.extend(b"\x00" * 32)

        parsed = triage.parse_elf_brief(bytes(hdr))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["kind"], "ELF")
        self.assertEqual(parsed["format"], "ELF64")
        self.assertEqual(parsed["endian"], "little")
        self.assertEqual(parsed["type"], "EXEC (Executable)")
        self.assertEqual(parsed["machine"], "x86_64")
        self.assertEqual(parsed["entry_point"], "0x401000")

    def test_indicator_sanitization(self):
        strings = [
            "Assembly Version 1.0.0.0",
            "File 0.0.0.0",
            "Connect to 192.168.1.100 now",
            "Broadcast 255.255.255.255",
            "Loopback 127.0.0.1",
            "Suspicious: IsDebuggerPresent",
            "VirtualAlloc",
        ]
        inds = triage.indicators(strings)
        self.assertIn("192.168.1.100", inds.get("ipv4", []))
        self.assertNotIn("1.0.0.0", inds.get("ipv4", []))
        self.assertNotIn("0.0.0.0", inds.get("ipv4", []))
        self.assertNotIn("127.0.0.1", inds.get("ipv4", []))
        self.assertIn("suspicious_terms", inds)
        self.assertIn("IsDebuggerPresent", inds["suspicious_terms"])
        self.assertIn("VirtualAlloc", inds["suspicious_terms"])

    def test_sample_exe_triage(self):
        sample = ROOT / "tests" / "fixtures" / "sample.exe"
        if not sample.exists():
            sample = ROOT / ".validation" / "capture-1" / "sample.exe"
        if not sample.exists():
            self.skipTest("sample.exe not present")
        data = sample.read_bytes()
        hints = triage.detect_magic(data)
        self.assertIn(".NET / CLR Managed Assembly", hints)
        parsed = triage.parse_pe_brief(data)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["format"], "PE32")
        self.assertEqual(parsed["machine"], "x86 (32-bit)")
        self.assertEqual(len(parsed["sections"]), 3)


if __name__ == "__main__":
    unittest.main()
