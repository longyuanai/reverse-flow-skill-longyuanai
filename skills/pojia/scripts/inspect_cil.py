#!/usr/bin/env python3
"""Independent, zero-external-dependency PE/CLI (.NET) metadata and CIL disassembler.

Extracts CIL method bytecodes, decodes opcodes, resolves tokens (TypeRefs, MemberRefs,
UserStrings), calculates method SHA-256 hashes, MVID, and file offsets without executing
the specimen or requiring external decompiler installations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import uuid
from pathlib import Path


OPCODES: dict[int, tuple[str, str]] = {
    0x00: ("nop", ""),
    0x02: ("ldarg.0", ""),
    0x03: ("ldarg.1", ""),
    0x04: ("ldarg.2", ""),
    0x05: ("ldarg.3", ""),
    0x06: ("ldloc.0", ""),
    0x07: ("ldloc.1", ""),
    0x08: ("ldloc.2", ""),
    0x09: ("ldloc.3", ""),
    0x0A: ("stloc.0", ""),
    0x0B: ("stloc.1", ""),
    0x0C: ("stloc.2", ""),
    0x0D: ("stloc.3", ""),
    0x12: ("ldloca.s", "u1"),
    0x14: ("ldnull", ""),
    0x15: ("ldc.i4.m1", ""),
    0x16: ("ldc.i4.0", ""),
    0x17: ("ldc.i4.1", ""),
    0x18: ("ldc.i4.2", ""),
    0x19: ("ldc.i4.3", ""),
    0x1A: ("ldc.i4.4", ""),
    0x1B: ("ldc.i4.5", ""),
    0x1C: ("ldc.i4.6", ""),
    0x1D: ("ldc.i4.7", ""),
    0x1E: ("ldc.i4.8", ""),
    0x1F: ("ldc.i4.s", "i1"),
    0x20: ("ldc.i4", "i4"),
    0x21: ("ldc.i8", "i8"),
    0x25: ("dup", ""),
    0x26: ("pop", ""),
    0x28: ("call", "token"),
    0x2A: ("ret", ""),
    0x2B: ("br.s", "branch"),
    0x2C: ("brfalse.s", "branch"),
    0x2D: ("brtrue.s", "branch"),
    0x2E: ("beq.s", "branch"),
    0x2F: ("bge.s", "branch"),
    0x30: ("bgt.s", "branch"),
    0x31: ("ble.s", "branch"),
    0x32: ("blt.s", "branch"),
    0x33: ("bne.un.s", "branch"),
    0x38: ("br", "branch4"),
    0x39: ("brfalse", "branch4"),
    0x3A: ("brtrue", "branch4"),
    0x58: ("add", ""),
    0x59: ("sub", ""),
    0x5A: ("mul", ""),
    0x5B: ("div", ""),
    0x5C: ("div.un", ""),
    0x5D: ("rem", ""),
    0x5E: ("rem.un", ""),
    0x5F: ("and", ""),
    0x60: ("or", ""),
    0x61: ("xor", ""),
    0x62: ("shl", ""),
    0x63: ("shr", ""),
    0x64: ("shr.un", ""),
    0x65: ("neg", ""),
    0x66: ("not", ""),
    0x67: ("conv.i1", ""),
    0x68: ("conv.i2", ""),
    0x69: ("conv.i4", ""),
    0x6A: ("conv.i8", ""),
    0x6F: ("callvirt", "token"),
    0x72: ("ldstr", "token"),
    0x73: ("newobj", "token"),
    0x8D: ("newarr", "token"),
    0x8E: ("ldlen", ""),
    0x9A: ("ldelem.ref", ""),
    0x9C: ("ldelem.i4", ""),
    0xA3: ("stelem.i", ""),
    0xA4: ("stelem.i1", ""),
    0xA5: ("stelem.i2", ""),
    0xA6: ("stelem.i4", ""),
    0xA7: ("stelem.i8", ""),
    0xD0: ("ldtoken", "token"),
}


def _inspect_cil(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError(f"Not a valid PE file: {path}")

    def u16(p: int) -> int:
        return struct.unpack_from("<H", data, p)[0]

    def u32(p: int) -> int:
        return struct.unpack_from("<I", data, p)[0]

    def u64(p: int) -> int:
        return struct.unpack_from("<Q", data, p)[0]

    pe = u32(0x3C)
    if data[pe : pe + 4] != b"PE\0\0":
        raise ValueError("Invalid PE signature")
    opt = pe + 24
    opt_magic = u16(opt)
    sec_count = u16(pe + 6)
    sec_header_off = opt + u16(pe + 20)

    sections = []
    for i in range(sec_count):
        p = sec_header_off + 40 * i
        sections.append({
            "name": data[p : p + 8].rstrip(b"\0").decode("ascii", errors="replace"),
            "virtual_size": u32(p + 8),
            "rva": u32(p + 12),
            "raw_size": u32(p + 16),
            "raw_offset": u32(p + 20),
        })

    def rva_to_offset(rva: int) -> int:
        for s in sections:
            d = rva - s["rva"]
            if 0 <= d < s["raw_size"]:
                p = s["raw_offset"] + d
                if p >= len(data):
                    raise ValueError("RVA points beyond EOF")
                return p
        raise ValueError(f"Unmapped RVA: {hex(rva)}")

    # CLI Directory is entry 14 in DataDirectory
    cli_dir_off = opt + (96 + 14 * 8 if opt_magic == 0x10B else 112 + 14 * 8)
    cli_rva = u32(cli_dir_off)
    if cli_rva == 0:
        raise ValueError("Not a .NET managed assembly (no CLI header directory)")

    cli = rva_to_offset(cli_rva)
    md_rva = u32(cli + 8)
    md = rva_to_offset(md_rva)
    if data[md : md + 4] != b"BSJB":
        raise ValueError("Invalid CLR metadata signature (expected BSJB)")

    verlen = u32(md + 12)
    p = md + 16 + verlen
    stream_count = u16(p + 2)
    p += 4
    streams: dict[str, dict] = {}
    for _ in range(stream_count):
        rel, size = u32(p), u32(p + 4)
        end = data.index(b"\0", p + 8)
        sname = data[p + 8 : end].decode("ascii", errors="replace")
        streams[sname] = {"file_offset": md + rel, "size": size}
        p += 8 + ((end - (p + 8) + 1 + 3) // 4) * 4

    if "#~" not in streams:
        raise ValueError("Metadata stream '#~' not found")

    tables = streams["#~"]["file_offset"]
    heapsizes = data[tables + 6]
    ss = 4 if heapsizes & 1 else 2
    gs = 4 if heapsizes & 2 else 2
    bs = 4 if heapsizes & 4 else 2
    valid = u64(tables + 8)
    rows: dict[int, int] = {}
    p = tables + 24
    for i in range(64):
        if valid & (1 << i):
            rows[i] = u32(p)
            p += 4

    def ix(t: int) -> int:
        return 4 if rows.get(t, 0) >= 65536 else 2

    def cx(bits: int, targets: list[int]) -> int:
        return 4 if max([rows.get(t, 0) for t in targets] + [0]) >= (1 << (16 - bits)) else 2

    rs = cx(2, [0, 26, 35, 1])
    tdor = cx(2, [2, 1, 27])
    mrp = cx(3, [2, 1, 26, 6, 27])
    hca = cx(5, [6, 4, 1, 2, 8, 9, 10, 0, 14, 23, 20, 17, 26, 27, 32, 35, 38, 39, 40, 42, 44, 43])
    cat = cx(3, [6, 10])

    sizes = {
        0: 2 + ss + 3 * gs,
        1: rs + 2 * ss,
        2: 4 + 2 * ss + tdor + ix(4) + ix(6),
        6: 8 + ss + bs + ix(8),
        8: 4 + ss,
        10: mrp + ss + bs,
        12: hca + cat + bs,
        17: bs,
        32: 16 + bs + 2 * ss,
        35: 12 + 2 * bs + 2 * ss,
    }

    tableloc: dict[int, int] = {}
    for t, n in rows.items():
        tableloc[t] = p
        p += sizes.get(t, 0) * n

    def index(p_idx: int, size: int) -> int:
        return int.from_bytes(data[p_idx : p_idx + size], "little")

    def string(i: int) -> str:
        b_str = streams["#Strings"]["file_offset"] + i
        e_str = data.index(b"\0", b_str)
        return data[b_str:e_str].decode("utf-8", errors="replace")

    def compressed(p_cmp: int) -> tuple[int, int]:
        a = data[p_cmp]
        if a < 128:
            return a, 1
        if a < 192:
            return ((a & 63) << 8) | data[p_cmp + 1], 2
        return ((a & 31) << 24) | int.from_bytes(data[p_cmp + 1 : p_cmp + 4], "big"), 4

    def blob(i: int) -> dict:
        b_blob = streams["#Blob"]["file_offset"] + i
        n, k = compressed(b_blob)
        return {
            "file_offset": b_blob,
            "payload_offset": b_blob + k,
            "hex": data[b_blob + k : b_blob + k + n].hex(),
        }

    type_refs: dict[int, str] = {}
    for i in range(rows.get(1, 0)):
        p_row = tableloc[1] + i * sizes[1]
        name, ns = string(index(p_row + rs, ss)), string(index(p_row + rs + ss, ss))
        type_refs[0x01000001 + i] = f"{ns}.{name}" if ns else name

    types: dict[int, str] = {}
    for i in range(rows.get(2, 0)):
        p_row = tableloc[2] + i * sizes[2]
        name, ns = string(index(p_row + 4, ss)), string(index(p_row + 4 + ss, ss))
        types[0x02000001 + i] = f"{ns}.{name}" if ns else name

    mrefs: dict[int, dict] = {}
    mr_targets = [2, 1, 26, 6, 27]
    for i in range(rows.get(10, 0)):
        p_row = tableloc[10] + i * sizes[10]
        parent = index(p_row, mrp)
        pt = (mr_targets[parent & 7] << 24) | (parent >> 3)
        name = string(index(p_row + mrp, ss))
        owner = type_refs.get(pt, types.get(pt, hex(pt)))
        mrefs[0x0A000001 + i] = {
            "row_offset": p_row,
            "parent_token": hex(pt),
            "name": f"{owner}.{name}",
            "signature": blob(index(p_row + mrp + ss, bs)),
        }

    user_strings: dict[int, dict] = {}
    if "#US" in streams:
        b_us = streams["#US"]["file_offset"]
        p_us = b_us + 1
        while p_us < b_us + streams["#US"]["size"]:
            n, k = compressed(p_us)
            if not n:
                p_us += k
                continue
            val_bytes = data[p_us + k : p_us + k + n - 1]
            user_strings[0x70000000 | (p_us - b_us)] = {
                "file_offset": p_us,
                "raw_hex": data[p_us : p_us + k + n].hex(),
                "value": val_bytes.decode("utf-16le", errors="replace"),
            }
            p_us += k + n

    methods: list[dict] = []
    for i in range(rows.get(6, 0)):
        p_row = tableloc[6] + i * sizes[6]
        rva = u32(p_row)
        if rva == 0:
            continue
        b_code = rva_to_offset(rva)
        header_byte = data[b_code]
        # Tiny header: 2 bits = 2, size is top 6 bits
        if (header_byte & 3) == 2:
            hsize = 1
            code_size = header_byte >> 2
            local_sig = "0x0"
        elif (header_byte & 3) == 3:  # Fat header
            hsize = (u16(b_code) >> 12) * 4
            code_size = u32(b_code + 4)
            local_sig = hex(u32(b_code + 8))
        else:
            continue

        body = data[b_code + hsize : b_code + hsize + code_size]
        instructions: list[dict] = []
        j = 0
        while j < len(body):
            start = j
            opcode_byte = body[j]
            j += 1
            name, kind = OPCODES.get(opcode_byte, (f"unknown_{hex(opcode_byte)}", ""))
            operand = None
            if kind in ("i1", "u1", "branch"):
                operand = int.from_bytes(body[j : j + 1], "little", signed=(kind != "u1"))
                j += 1
                if kind == "branch":
                    operand += j
            elif kind in ("i4", "token", "branch4"):
                operand = int.from_bytes(body[j : j + 4], "little", signed=(kind == "i4"))
                j += 4
                if kind == "branch4":
                    operand += j
            elif kind == "i8":
                operand = int.from_bytes(body[j : j + 8], "little", signed=True)
                j += 8

            ins: dict = {
                "il_offset": hex(start),
                "file_offset": hex(b_code + hsize + start),
                "bytes": body[start:j].hex(),
                "opcode": name,
            }
            if operand is not None:
                ins["operand"] = hex(operand) if kind in ("branch", "branch4", "token") else operand
                if kind == "token":
                    if operand in mrefs:
                        ins["resolved"] = mrefs[operand]["name"]
                    elif operand in user_strings:
                        ins["resolved"] = repr(user_strings[operand]["value"])
                    elif operand in types:
                        ins["resolved"] = types[operand]

            instructions.append(ins)

        m_name = string(index(p_row + 8, ss))
        methods.append({
            "token": hex(0x06000001 + i),
            "name": m_name,
            "rva": hex(rva),
            "file_offset": hex(b_code),
            "code_start": hex(b_code + hsize),
            "code_size": code_size,
            "code_hex": body.hex(),
            "code_sha256": hashlib.sha256(body).hexdigest(),
            "local_signature_token": local_sig,
            "instructions": instructions,
        })

    guid_idx = index(tableloc[0] + 2 + ss, gs) if 0 in tableloc else 1
    guid_offset = streams["#GUID"]["file_offset"] + (guid_idx - 1) * 16 if "#GUID" in streams else 0
    mvid = str(uuid.UUID(bytes_le=data[guid_offset : guid_offset + 16])) if guid_offset else ""

    return {
        "artifact": str(path.resolve()),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pe_offset": hex(pe),
        "cli_file_offset": hex(cli),
        "metadata_version": data[md + 16 : md + 16 + verlen].rstrip(b"\0").decode("ascii", errors="replace"),
        "mvid": mvid,
        "entry_token": hex(u32(cli + 20)),
        "type_refs": {hex(k): v for k, v in type_refs.items()},
        "member_refs": {hex(k): v["name"] for k, v in mrefs.items()},
        "user_strings": {hex(k): v["value"] for k, v in user_strings.items()},
        "methods": methods,
    }


def inspect_cil(path: Path) -> dict:
    try:
        return _inspect_cil(path)
    except (struct.error, IndexError) as err:
        raise ValueError(f"Truncated or malformed PE structure: {err}") from err


def to_disassembly_text(data: dict, target_method: str | None = None) -> str:
    lines = [
        f"// Assembly: {data['artifact']}",
        f"// Size: {data['size']} bytes | SHA-256: {data['sha256']}",
        f"// CLR Runtime: {data['metadata_version']} | MVID: {data['mvid']}",
        f"// Entry Point Token: {data['entry_token']}",
        "",
    ]
    for m in data["methods"]:
        if target_method and target_method.lower() not in m["name"].lower():
            continue
        lines.append(f"// Method token: {m['token']} | RVA: {m['rva']} | Offset: {m['file_offset']}")
        lines.append(f"// Code size: {m['code_size']} bytes | SHA-256: {m['code_sha256']}")
        lines.append(f".method {m['name']} () cil managed {{")
        for ins in m["instructions"]:
            op = ins["opcode"].ljust(12)
            arg = str(ins.get("operand", ""))
            resolved = f" // {ins['resolved']}" if "resolved" in ins else ""
            lines.append(f"    {ins['il_offset']}: {op} {arg}{resolved}")
        lines.append("}\n")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Path to .NET managed PE binary")
    parser.add_argument("--out", type=Path, help="Output file (JSON or text)")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format (default: text)")
    parser.add_argument("--method", help="Filter disassembly to specific method name")
    args = parser.parse_args()

    try:
        res = inspect_cil(args.artifact)
        if args.format == "json":
            out_str = json.dumps(res, indent=2, ensure_ascii=False)
        else:
            out_str = to_disassembly_text(res, target_method=args.method)

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(out_str, encoding="utf-8")
            print(f"CIL Inspection written to: {args.out}")
        else:
            print(out_str)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
