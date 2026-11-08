#!/usr/bin/env python3
"""Collect safe, offline triage facts for an artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{4,}")
UTF16_RE = re.compile((rb"(?:[\x20-\x7e]\x00){4,}"))

MAGIC_HINTS = [
    (b"MZ", "PE/Windows executable or DLL"),
    (b"\x7fELF", "ELF executable/shared object"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit"),
    (b"\xca\xfe\xba\xbe", "Java class or Mach-O universal/fat"),
    (b"PK\x03\x04", "ZIP/APK/JAR/Office container"),
    (b"%PDF", "PDF document"),
    (b"\x1f\x8b", "gzip stream"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    (b"Rar!", "RAR archive"),
    (b"dex\n", "Android DEX"),
    (b"SQLite format 3\x00", "SQLite database"),
    (b"ustar", "TAR archive marker"),
    (b"hsqs", "SquashFS little-endian filesystem"),
    (b"sqsh", "SquashFS big-endian filesystem"),
]

EXTENSION_HINTS = {
    ".apk": "Android APK",
    ".dex": "Android DEX",
    ".jar": "Java archive",
    ".class": "Java class",
    ".exe": "Windows PE executable",
    ".dll": "Windows PE DLL",
    ".sys": "Windows driver",
    ".elf": "ELF binary",
    ".so": "ELF shared object",
    ".dylib": "Mach-O dynamic library",
    ".ipa": "iOS app archive",
    ".bin": "raw binary/firmware candidate",
    ".img": "disk or firmware image candidate",
    ".pcap": "packet capture",
    ".pcapng": "packet capture",
}

INDICATOR_PATTERNS = {
    "urls": re.compile(r"https?://[^\s'\"<>]+", re.I),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "windows_paths": re.compile(r"[A-Za-z]:\\[^\s'\"]+"),
    "unix_paths": re.compile(r"/(?:bin|sbin|etc|usr|var|tmp|home|opt)/[^\s'\"]*"),
    "registry": re.compile(r"\bHKEY_(?:LOCAL_MACHINE|CURRENT_USER|CLASSES_ROOT|USERS|CURRENT_CONFIG)\\[^\s'\"]+", re.I),
    "emails": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I),
}

SUSPICIOUS_TERMS = [
    "CreateProcess", "VirtualAlloc", "WriteProcessMemory", "LoadLibrary", "GetProcAddress",
    "socket", "connect", "InternetOpen", "WinHttp", "Crypt", "OpenSSL",
    "powershell", "cmd.exe", "/bin/sh", "chmod", "wget", "curl", "base64",
    "IsDebuggerPresent", "CheckRemoteDebuggerPresent", "NtQueryInformationProcess", "ptrace",
    "OutputDebugString", "CryptAcquireContext", "BCryptEncrypt"
]


def read_prefix(path: Path, limit: int = 8 * 1024 * 1024) -> bytes:
    with path.open("rb") as f:
        return f.read(limit)


def hash_file(path: Path) -> dict[str, str]:
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h_md5.update(chunk)
            h_sha1.update(chunk)
            h_sha256.update(chunk)
    return {"md5": h_md5.hexdigest(), "sha1": h_sha1.hexdigest(), "sha256": h_sha256.hexdigest()}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def strings_from(data: bytes, max_count: int) -> list[str]:
    out: list[str] = []
    for m in PRINTABLE_RE.finditer(data):
        out.append(m.group().decode("utf-8", errors="replace"))
        if len(out) >= max_count:
            return out
    for m in UTF16_RE.finditer(data):
        out.append(m.group().decode("utf-16le", errors="replace"))
        if len(out) >= max_count:
            return out
    return out


def detect_magic(data: bytes) -> list[str]:
    hints = [name for magic, name in MAGIC_HINTS if data.startswith(magic)]
    # Secondary runtime/packer detection
    if data.startswith(b"MZ"):
        if b"BSJB" in data or b"_CorExeMain" in data or b"_CorDllMain" in data or b"mscoree.dll" in data:
            hints.append(".NET / CLR Managed Assembly")
        if b"UPX!" in data or b"UPX0" in data or b"UPX1" in data:
            hints.append("UPX packed executable")
    elif data.startswith(b"\x7fELF"):
        if b"UPX!" in data:
            hints.append("UPX packed ELF")
    if b"Go buildinf:" in data or b"runtime.goexit" in data:
        hints.append("Go runtime binary")
    if b"rust_begin_unwind" in data or b"rustc/" in data:
        hints.append("Rust compiled binary")
    return hints or ["unknown"]


def parse_pe_brief(data: bytes) -> dict | None:
    try:
        if len(data) < 64 or data[:2] != b"MZ":
            return None
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_off + 24 > len(data) or data[pe_off : pe_off + 4] != b"PE\0\0":
            return None
        machine_id = struct.unpack_from("<H", data, pe_off + 4)[0]
        num_sections = struct.unpack_from("<H", data, pe_off + 6)[0]
        timestamp = struct.unpack_from("<I", data, pe_off + 8)[0]
        opt_size = struct.unpack_from("<H", data, pe_off + 20)[0]
        opt_magic = struct.unpack_from("<H", data, pe_off + 24)[0] if opt_size >= 2 else 0
        entry = struct.unpack_from("<I", data, pe_off + 40)[0] if opt_size >= 20 else 0
        subsys = struct.unpack_from("<H", data, pe_off + 92)[0] if opt_size >= 70 else 0

        machines = {0x14C: "x86 (32-bit)", 0x8664: "x86_64 (64-bit)", 0xAA64: "ARM64", 0x1C0: "ARM"}
        subsystems = {1: "Native", 2: "Windows GUI", 3: "Windows CUI (Console)"}

        sec_off = pe_off + 24 + opt_size
        sections = []
        for i in range(min(num_sections, 64)):
            p = sec_off + i * 40
            if p + 40 > len(data):
                break
            s_name = data[p : p + 8].rstrip(b"\0").decode("latin1", errors="replace")
            vsize = struct.unpack_from("<I", data, p + 8)[0]
            vrva = struct.unpack_from("<I", data, p + 12)[0]
            rsize = struct.unpack_from("<I", data, p + 16)[0]
            roff = struct.unpack_from("<I", data, p + 20)[0]
            sec_data = data[roff : roff + rsize] if roff + rsize <= len(data) else b""
            sections.append({
                "name": s_name,
                "virtual_size": vsize,
                "rva": hex(vrva),
                "raw_size": rsize,
                "raw_offset": hex(roff),
                "entropy": round(entropy(sec_data), 3) if sec_data else 0.0,
            })

        return {
            "kind": "PE",
            "format": "PE32" if opt_magic == 0x10B else ("PE32+" if opt_magic == 0x20B else "PE"),
            "machine": machines.get(machine_id, hex(machine_id)),
            "subsystem": subsystems.get(subsys, hex(subsys)),
            "entry_point_rva": hex(entry),
            "timestamp": timestamp,
            "sections_count": num_sections,
            "sections": sections,
        }
    except Exception:
        return None


def parse_elf_brief(data: bytes) -> dict | None:
    try:
        if len(data) < 52 or data[:4] != b"\x7fELF":
            return None
        ei_class = data[4]
        ei_data = data[5]
        endian = "<" if ei_data == 1 else ">"
        types = {1: "REL (Relocatable)", 2: "EXEC (Executable)", 3: "DYN (Shared object / PIE)", 4: "CORE"}
        machines = {0x03: "x86", 0x3E: "x86_64", 0x28: "ARM", 0xB7: "AArch64", 0x08: "MIPS", 0xF3: "RISC-V"}
        e_type = struct.unpack_from(endian + "H", data, 16)[0]
        e_machine = struct.unpack_from(endian + "H", data, 18)[0]
        e_entry = struct.unpack_from(endian + ("Q" if ei_class == 2 else "I"), data, 24)[0]
        return {
            "kind": "ELF",
            "format": "ELF64" if ei_class == 2 else "ELF32",
            "endian": "little" if ei_data == 1 else "big",
            "type": types.get(e_type, hex(e_type)),
            "machine": machines.get(e_machine, hex(e_machine)),
            "entry_point": hex(e_entry),
        }
    except Exception:
        return None


def extract_structure(data: bytes) -> dict | None:
    if data.startswith(b"MZ"):
        return parse_pe_brief(data)
    if data.startswith(b"\x7fELF"):
        return parse_elf_brief(data)
    return None


def profile_and_tools(path: Path, magic_hints: list[str], inds: dict[str, list[str]]) -> tuple[list[str], list[str], list[str]]:
    ext = path.suffix.lower()
    joined = " ".join(magic_hints + [EXTENSION_HINTS.get(ext, "")]).lower()
    profiles: list[str] = []
    tools: list[str] = []
    steps: list[str] = []

    if any(x in joined for x in [".net", "clr", "managed assembly", "cil"]):
        profiles += ["managed", "dotnet"]
        tools += [
            "inspect_cil.py (zero-dependency CIL disassembler)",
            "ilspy",
            "dnspy",
            "de4dot",
            "rea (inspect-managed-artifact/members)",
        ]
        steps += [
            "Decompile CIL methods with inspect_cil.py or ILSpy/dnSpy",
            "Inspect CLI metadata, MVID, and type definitions",
        ]
    elif any(x in joined for x in ["pe", "elf", "mach-o", "executable", "shared object", "dll"]):
        profiles += ["native"]
        tools += ["ghidra", "radare2/rizin", "detect-it-easy", "capa", "floss", "yara", "debugger"]
        steps += ["Map imports/exports/strings to candidate functions", "Open the artifact in a decompiler and label entry points"]

    if any(x in joined for x in ["upx packed"]):
        profiles += ["packed"]
        tools += ["upx -d"]
        steps += ["Unpack artifact with 'upx -d' on a copy before disassembly"]

    if any(x in joined for x in ["apk", "dex", "android"]):
        profiles += ["android", "mobile"]
        tools += ["jadx", "apktool", "frida", "adb", "ghidra for native libraries"]
        steps += ["Decode APK/DEX with jadx/apktool", "Review manifest, exported components, permissions, endpoints, and native libraries"]
    if any(x in joined for x in ["firmware", "raw binary", "filesystem", "squashfs"]) or ext in {".bin", ".img"}:
        profiles += ["firmware"]
        tools += ["binwalk", "unblob", "ghidra", "qiling/unicorn", "yara"]
        steps += ["Attempt filesystem/container extraction on a copy", "Identify CPU/OS/service startup scripts"]
    if any(x in joined for x in ["packet capture"]) or ext in {".pcap", ".pcapng"}:
        profiles += ["network"]
        tools += ["wireshark", "tshark", "zeek", "network protocol parsers"]
        steps += ["Summarize conversations, endpoints, protocols, and suspicious payloads"]
    if inds.get("urls") or inds.get("ipv4"):
        profiles += ["network-indicators"]
        steps += ["Correlate network indicators with code references before drawing behavior conclusions"]
    if inds.get("suspicious_terms"):
        profiles += ["malware-triage"]
        tools += ["capa", "floss", "yara", "sandbox trace if authorized"]
        steps += ["Run capability detection and validate suspicious terms with xrefs"]
    # stable de-duplication
    dedup = lambda xs: list(dict.fromkeys(xs))
    return dedup(profiles) or ["generic"], dedup(tools), dedup(steps) or ["Continue static triage with strings, metadata, and file-format analysis"]


def indicators(strings: list[str]) -> dict[str, list[str]]:
    joined = "\n".join(strings)
    result: dict[str, list[str]] = {}
    for name, pat in INDICATOR_PATTERNS.items():
        vals = sorted(set(pat.findall(joined)))[:50]
        if name == "ipv4":
            # Filter out generic loopback, broadcast, all-zeros, and assembly/software version false positives
            clean_ips = []
            for ip in vals:
                parts = ip.split(".")
                if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                    if ip not in {"0.0.0.0", "1.0.0.0", "2.0.0.0", "127.0.0.1", "255.255.255.255"}:
                        clean_ips.append(ip)
            vals = clean_ips
        if vals:
            result[name] = vals
    suspicious = sorted({term for term in SUSPICIOUS_TERMS if term.lower() in joined.lower()})
    if suspicious:
        result["suspicious_terms"] = suspicious
    return result


def markdown_report(data: dict) -> str:
    lines = [
        "# Artifact Triage",
        "",
        f"- Path: `{data['path']}`",
        f"- Size: {data['size']} bytes",
        f"- SHA-256: `{data['hashes']['sha256']}`",
        f"- Extension hint: {data.get('extension_hint') or '-'}",
        f"- Magic hints: {', '.join(data['magic_hints'])}",
        f"- Prefix entropy: {data['prefix_entropy']:.3f}",
        f"- Suggested profiles: {', '.join(data.get('profiles', []))}",
        f"- Generated UTC: {data['generated_utc']}",
        "",
        "## Recommended local tools",
    ]
    if data.get("recommended_tools"):
        for tool in data["recommended_tools"]:
            lines.append(f"- {tool}")
    else:
        lines.append("- No specific tool recommendation yet.")
    lines += [
        "",
        "## Recommended next steps",
    ]
    for step in data.get("recommended_next_steps", []):
        lines.append(f"- {step}")
    lines += [
        "",
        "## Indicators",
    ]
    if data["indicators"]:
        for k, vals in data["indicators"].items():
            lines.append(f"### {k}")
            for v in vals[:20]:
                lines.append(f"- `{v}`")
    else:
        lines.append("No high-signal indicators found in extracted strings.")

    if data.get("structure"):
        lines += ["", "## Binary structure", ""]
        struct_info = data["structure"]
        lines.append(f"- Kind: {struct_info.get('kind', 'unknown')}")
        lines.append(f"- Format: {struct_info.get('format', 'unknown')}")
        lines.append(f"- Machine: {struct_info.get('machine', 'unknown')}")
        if "subsystem" in struct_info:
            lines.append(f"- Subsystem: {struct_info['subsystem']}")
        lines.append(f"- Entry point: `{struct_info.get('entry_point_rva') or struct_info.get('entry_point', '-')}`")
        if struct_info.get("sections"):
            lines += [
                "",
                "### Sections",
                "| Name | Virtual size | RVA | Raw size | Raw offset | Entropy |",
                "|---|---:|---|---:|---|---:|",
            ]
            for sec in struct_info["sections"]:
                lines.append(
                    f"| `{sec['name']}` | {sec['virtual_size']} | `{sec['rva']}` | {sec['raw_size']} | `{sec['raw_offset']}` | {sec['entropy']} |"
                )

    lines += ["", "## Sample strings", ""]
    for s in data["strings"][:80]:
        safe = s.replace("`", "'")
        lines.append(f"- `{safe}`")
    return "\n".join(lines) + "\n"


def triage(path: Path, max_strings: int = 500) -> dict:
    """Perform safe offline triage on a single artifact and return structured dict."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    prefix = read_prefix(path)
    strs = strings_from(prefix, max_strings)
    inds = indicators(strs)
    profiles, recommended_tools, next_steps = profile_and_tools(path, detect_magic(prefix), inds)
    return {
        "path": str(path),
        "name": path.name,
        "size": os.path.getsize(path),
        "hashes": hash_file(path),
        "extension_hint": EXTENSION_HINTS.get(path.suffix.lower(), ""),
        "magic_hints": detect_magic(prefix),
        "structure": extract_structure(prefix),
        "prefix_entropy": entropy(prefix),
        "strings": strs,
        "indicators": inds,
        "profiles": profiles,
        "recommended_tools": recommended_tools,
        "recommended_next_steps": next_steps,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "notes": "Offline triage only; artifact was not executed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage one artifact without executing it")
    parser.add_argument("artifact", help="Path to artifact")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--max-strings", type=int, default=500, help="Maximum strings to store")
    args = parser.parse_args()

    path = Path(args.artifact).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        raise SystemExit(f"not a file: {path}")

    data = triage(path, args.max_strings)
    stem = path.name.replace(os.sep, "_")
    json_path = out / f"{stem}.triage.json"
    md_path = out / f"{stem}.triage.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown_report(data), encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
