#!/usr/bin/env python3
"""Independent, zero-external-dependency Native PE/ELF Entry Point & x86/x64 Opcode Disassembler.

Decodes entry point opcodes, function prologues, calls, and jumps for native PE (x86/x64)
and ELF binaries without external debuggers or disassemblers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any


def rva_to_file_offset(data: bytes, rva: int) -> int | None:
    """Calculate file offset from RVA using PE Section Headers."""
    try:
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        num_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
        opt_header_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
        section_offset = pe_offset + 24 + opt_header_size

        for i in range(num_sections):
            sec = section_offset + i * 40
            vsize = struct.unpack_from("<I", data, sec + 8)[0]
            vaddr = struct.unpack_from("<I", data, sec + 12)[0]
            raw_size = struct.unpack_from("<I", data, sec + 16)[0]
            raw_ptr = struct.unpack_from("<I", data, sec + 20)[0]

            size_to_check = max(vsize, raw_size)
            if vaddr <= rva < vaddr + size_to_check:
                return raw_ptr + (rva - vaddr)
    except Exception:
        pass
    return None


def elf_vaddr_to_file_offset(data: bytes, vaddr: int) -> int | None:
    """Calculate file offset from virtual address using ELF Program Headers."""
    try:
        ei_class = data[4]
        ei_data = data[5]
        endian = "<" if ei_data == 1 else ">"
        is_64 = ei_class == 2

        if is_64:
            e_phoff = struct.unpack_from(endian + "Q", data, 32)[0]
            e_phentsize = struct.unpack_from(endian + "H", data, 54)[0]
            e_phnum = struct.unpack_from(endian + "H", data, 56)[0]
        else:
            e_phoff = struct.unpack_from(endian + "I", data, 28)[0]
            e_phentsize = struct.unpack_from(endian + "H", data, 42)[0]
            e_phnum = struct.unpack_from(endian + "H", data, 44)[0]

        for i in range(e_phnum):
            ph = e_phoff + i * e_phentsize
            p_type = struct.unpack_from(endian + "I", data, ph)[0]
            if p_type == 1:  # PT_LOAD
                if is_64:
                    p_offset = struct.unpack_from(endian + "Q", data, ph + 8)[0]
                    p_vaddr = struct.unpack_from(endian + "Q", data, ph + 16)[0]
                    p_memsz = struct.unpack_from(endian + "Q", data, ph + 40)[0]
                else:
                    p_offset = struct.unpack_from(endian + "I", data, ph + 4)[0]
                    p_vaddr = struct.unpack_from(endian + "I", data, ph + 8)[0]
                    p_memsz = struct.unpack_from(endian + "I", data, ph + 20)[0]

                if p_vaddr <= vaddr < p_vaddr + p_memsz:
                    return p_offset + (vaddr - p_vaddr)
    except Exception:
        pass
    return None


def decode_x86_x64(code_bytes: bytes, base_address: int = 0, max_insts: int = 16) -> list[dict[str, Any]]:
    """Lightweight zero-dependency x86/x64 instruction stream decoder."""
    instructions: list[dict[str, Any]] = []
    idx = 0
    n = len(code_bytes)

    reg64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"]

    while idx < n and len(instructions) < max_insts:
        pc = base_address + idx
        b = code_bytes[idx]

        # 1-byte instructions
        if b == 0x90:
            instructions.append({"address": hex(pc), "bytes": "90", "mnemonic": "nop", "operands": ""})
            idx += 1
        elif b == 0xCC:
            instructions.append({"address": hex(pc), "bytes": "cc", "mnemonic": "int3", "operands": ""})
            idx += 1
        elif b == 0xC3:
            instructions.append({"address": hex(pc), "bytes": "c3", "mnemonic": "ret", "operands": ""})
            idx += 1
        elif 0x50 <= b <= 0x57:
            r = reg64[b - 0x50]
            instructions.append({"address": hex(pc), "bytes": f"{b:02x}", "mnemonic": "push", "operands": r})
            idx += 1
        elif 0x58 <= b <= 0x5F:
            r = reg64[b - 0x58]
            instructions.append({"address": hex(pc), "bytes": f"{b:02x}", "mnemonic": "pop", "operands": r})
            idx += 1
        elif b == 0x31 and idx + 1 < n:
            modrm = code_bytes[idx + 1]
            if modrm == 0xC0:
                instructions.append({"address": hex(pc), "bytes": "31 c0", "mnemonic": "xor", "operands": "eax, eax"})
            elif modrm == 0xED:
                instructions.append({"address": hex(pc), "bytes": "31 ed", "mnemonic": "xor", "operands": "ebp, ebp"})
            else:
                instructions.append({"address": hex(pc), "bytes": f"31 {modrm:02x}", "mnemonic": "xor", "operands": "reg, reg"})
            idx += 2
        elif b == 0x89 and idx + 1 < n and code_bytes[idx + 1] == 0xE5:
            instructions.append({"address": hex(pc), "bytes": "89 e5", "mnemonic": "mov", "operands": "ebp, esp"})
            idx += 2
        elif b == 0x83 and idx + 2 < n and code_bytes[idx + 1] == 0xEC:
            imm = code_bytes[idx + 2]
            instructions.append({"address": hex(pc), "bytes": f"83 ec {imm:02x}", "mnemonic": "sub", "operands": f"esp, {hex(imm)}"})
            idx += 3
        # REX prefix instructions (0x48 x64)
        elif b == 0x48 and idx + 1 < n:
            b2 = code_bytes[idx + 1]
            if b2 == 0x89 and idx + 2 < n and code_bytes[idx + 2] == 0xE5:
                instructions.append({"address": hex(pc), "bytes": "48 89 e5", "mnemonic": "mov", "operands": "rbp, rsp"})
                idx += 3
            elif b2 == 0x83 and idx + 3 < n and code_bytes[idx + 2] == 0xEC:
                imm = code_bytes[idx + 3]
                instructions.append({"address": hex(pc), "bytes": f"48 83 ec {imm:02x}", "mnemonic": "sub", "operands": f"rsp, {hex(imm)}"})
                idx += 4
            elif b2 == 0x83 and idx + 3 < n and code_bytes[idx + 2] == 0xC4:
                imm = code_bytes[idx + 3]
                instructions.append({"address": hex(pc), "bytes": f"48 83 c4 {imm:02x}", "mnemonic": "add", "operands": f"rsp, {hex(imm)}"})
                idx += 4
            elif b2 == 0x31 and idx + 2 < n and code_bytes[idx + 2] == 0xC0:
                instructions.append({"address": hex(pc), "bytes": "48 31 c0", "mnemonic": "xor", "operands": "rax, rax"})
                idx += 3
            elif b2 == 0x8B and idx + 2 < n:
                instructions.append({"address": hex(pc), "bytes": f"48 8b {code_bytes[idx+2]:02x}", "mnemonic": "mov", "operands": "reg, [mem]"})
                idx += 3
            else:
                instructions.append({"address": hex(pc), "bytes": f"48 {b2:02x}", "mnemonic": "rex.w", "operands": f"0x{b2:02x}"})
                idx += 2
        # Jumps and calls
        elif b == 0xE8 and idx + 4 < n:
            rel = struct.unpack_from("<i", code_bytes, idx + 1)[0]
            target = pc + 5 + rel
            bstr = " ".join(f"{x:02x}" for x in code_bytes[idx : idx + 5])
            instructions.append({"address": hex(pc), "bytes": bstr, "mnemonic": "call", "operands": hex(target)})
            idx += 5
        elif b == 0xE9 and idx + 4 < n:
            rel = struct.unpack_from("<i", code_bytes, idx + 1)[0]
            target = pc + 5 + rel
            bstr = " ".join(f"{x:02x}" for x in code_bytes[idx : idx + 5])
            instructions.append({"address": hex(pc), "bytes": bstr, "mnemonic": "jmp", "operands": hex(target)})
            idx += 5
        elif b == 0xEB and idx + 1 < n:
            rel8 = struct.unpack_from("<b", code_bytes, idx + 1)[0]
            target = pc + 2 + rel8
            instructions.append({"address": hex(pc), "bytes": f"eb {code_bytes[idx+1]:02x}", "mnemonic": "jmp", "operands": hex(target)})
            idx += 2
        # Syscall / Interrupts
        elif b == 0x0F and idx + 1 < n and code_bytes[idx + 1] == 0x05:
            instructions.append({"address": hex(pc), "bytes": "0f 05", "mnemonic": "syscall", "operands": ""})
            idx += 2
        elif b == 0xCD and idx + 1 < n and code_bytes[idx + 1] == 0x80:
            instructions.append({"address": hex(pc), "bytes": "cd 80", "mnemonic": "int", "operands": "0x80"})
            idx += 2
        else:
            # Fallback 1 raw byte
            instructions.append({"address": hex(pc), "bytes": f"{b:02x}", "mnemonic": "db", "operands": hex(b)})
            idx += 1

    return instructions


def inspect_native(target_path: str | Path) -> dict[str, Any]:
    """Inspect native PE/ELF binary and extract entry point assembly."""
    p = Path(target_path)
    if not p.is_file():
        raise FileNotFoundError(f"Target binary not found: {target_path}")

    data = p.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()

    result: dict[str, Any] = {
        "file_name": p.name,
        "file_size": len(data),
        "sha256": sha256,
        "format": "UNKNOWN",
        "entry_point": None,
        "entry_point_file_offset": None,
        "raw_bytes": "",
        "instructions": [],
    }

    if data.startswith(b"MZ"):
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        magic = struct.unpack_from("<H", data, pe_offset + 24)[0]
        is_pe32_plus = (magic == 0x20B)
        entry_rva = struct.unpack_from("<I", data, pe_offset + 40)[0]
        image_base = struct.unpack_from("<Q" if is_pe32_plus else "<I", data, pe_offset + (48 if not is_pe32_plus else 48))[0]

        file_off = rva_to_file_offset(data, entry_rva) or entry_rva
        code_slice = data[file_off : file_off + 64] if file_off < len(data) else b""

        result["format"] = "PE32+" if is_pe32_plus else "PE32"
        result["entry_point"] = hex(entry_rva)
        result["entry_point_file_offset"] = hex(file_off)
        result["raw_bytes"] = code_slice.hex()
        result["instructions"] = decode_x86_x64(code_slice, base_address=image_base + entry_rva)

    elif data.startswith(b"\x7fELF"):
        ei_class = data[4]
        ei_data = data[5]
        endian = "<" if ei_data == 1 else ">"
        is_64 = ei_class == 2
        entry_vaddr = struct.unpack_from(endian + ("Q" if is_64 else "I"), data, 24)[0]

        file_off = elf_vaddr_to_file_offset(data, entry_vaddr) or (entry_vaddr if entry_vaddr < len(data) else 0)
        code_slice = data[file_off : file_off + 64] if file_off < len(data) else b""

        result["format"] = "ELF64" if is_64 else "ELF32"
        result["entry_point"] = hex(entry_vaddr)
        result["entry_point_file_offset"] = hex(file_off)
        result["raw_bytes"] = code_slice.hex()
        result["instructions"] = decode_x86_x64(code_slice, base_address=entry_vaddr)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-dependency Native PE/ELF entry point disassembler")
    parser.add_argument("specimen", help="Path to native PE or ELF executable")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    res = inspect_native(args.specimen)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print(f"Format: {res['format']} | Entry Point: {res['entry_point']} (Offset: {res['entry_point_file_offset']})")
    print("-" * 60)
    for inst in res.get("instructions", []):
        ops = f" {inst['operands']}" if inst["operands"] else ""
        print(f"  {inst['address']:>12}:  {inst['bytes']:<12} {inst['mnemonic']}{ops}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
