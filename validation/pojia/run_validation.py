"""Compile an owned fixture, exercise real REA interfaces, and cross-check evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MASK = (1 << 32) - 1


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def oracle(value: int, xor_constant: int = 0xA53C91E7) -> int:
    mixed = value ^ xor_constant
    rotated = ((mixed << 7) | (mixed >> 25)) & MASK
    return (rotated * 2654435761 + 17) & MASK


def main() -> int:
    if sys.flags.optimize:
        raise RuntimeError("Run validation without -O; verification assertions must remain enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatcher", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--node", default=shutil.which("node"))
    parser.add_argument("--csc", type=Path, default=Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    dispatcher = args.dispatcher.resolve(strict=True)
    if not args.node:
        raise ValueError("A working Node executable is required")
    commands = []

    def write(name: str, value) -> None:
        with (out / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")

    def run(label: str, command: list, input_text: str | None = None, expected: int | None = 0):
        command = [str(part) for part in command]
        result = subprocess.run(command, input=None if input_text is None else input_text.encode("utf-8"), capture_output=True, timeout=60, cwd=out)
        (out / (label + ".stdout")).write_bytes(result.stdout)
        (out / (label + ".stderr")).write_bytes(result.stderr)
        commands.append({"label": label, "argv": command, "exit_code": result.returncode})
        if expected is not None and result.returncode != expected:
            raise RuntimeError(f"{label}: exit {result.returncode}; see raw stdout/stderr")
        return result

    def cli(label: str, operation: str, sample: Path):
        result = run(label, [args.node, dispatcher, operation, sample, "--json"])
        record = json.loads(result.stdout.decode("utf-8-sig"))
        write(label + ".json", record)
        return record

    try:
        source = out / "fixture-source.cs"
        shutil.copyfile(HERE / "Fixture.cs", source)
        sample = out / "sample.exe"
        run("compile", [args.csc, "/nologo", "/optimize+", "/debug-", "/out:" + str(sample), source])
        package_root = dispatcher.parents[1]
        package = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
        lock_path = package_root.parents[1] / "package-lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        locked = lock["packages"]["node_modules/rea-agents"]
        assert package["version"] == locked["version"] == "6.4.0"
        assert lock["packages"][""]["dependencies"]["rea-agents"] == "6.4.0"
        zod_version = json.loads((package_root.parents[1] / "node_modules/zod/package.json").read_text())["version"]
        assert zod_version == "4.6.6", "Use the patched Zod override from the runtime manifests"
        shutil.copyfile(lock_path, out / "npm-package-lock.json")
        version = run("version", [args.node, dispatcher, "--version"]).stdout.decode().strip()
        assert version == package["version"]
        artifact = cli("cli-artifact", "inspect-managed-artifact", sample)
        members = cli("cli-members", "inspect-managed-members", sample)
        run("mcp-probe", [args.node, HERE / "mcp_probe.mjs", "--dispatcher", dispatcher, "--sample", sample, "--out", out / "mcp"])
        mcp_artifact = json.loads((out / "mcp/inspect_managed_artifact.json").read_text())["structuredContent"]
        mcp_members = json.loads((out / "mcp/inspect_managed_members.json").read_text())["structuredContent"]
        for left, right in [(artifact, mcp_artifact), (members, mcp_members)]:
            assert left["normalized_result"] == right["normalized_result"]
            assert left["subject"]["digest"]["sha256"] == sha(sample.read_bytes())
        normalized = members["normalized_result"]
        assert normalized["coverage"]["state"] == "complete"
        methods = [m for m in normalized["methods"] if m["declaring_type"] == "PojiaFixture" and m["name"] == "Transform"]
        assert len(methods) == 1
        method = methods[0]
        assert method["signature"]["return_type"] == "u4"
        assert method["signature"]["parameter_types"] == ["u4"]
        assert any(e["target_token"] == method["token"] and e["caller"] == "PojiaFixture.Main" for e in normalized["call_edges"])
        body = method["body"]
        assert body["status"] == "present" and body["truncated_instructions"] == 0
        raw = sample.read_bytes()
        offset = body["file_offset"]
        header = int.from_bytes(raw[offset:offset + 2], "little")
        header_size = (header >> 12) * 4 if header & 3 == 3 else 1
        il = raw[offset + header_size:offset + header_size + body["il_size"]]
        reflection = bytes.fromhex(run("clr-reflection-il", [sample, "--il"]).stdout.decode().strip())
        assert len(il) == body["il_size"]
        assert il == reflection and sha(il) == body["il_sha256"]
        (out / "transform-il.hex").write_text(il.hex() + "\n", encoding="ascii")
        expected_opcodes = {"xor", "shl", "shr.un", "or", "mul", "add", "ret"}
        assert expected_opcodes.issubset(body["opcode_counts"])

        values = {0, 1, 2, 7, 0x7F, 0x80, 0xFFFF, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF}
        for bit in range(32):
            values.update({1 << bit, (1 << bit) - 1})
        generator = random.Random(20261026)
        values.update(generator.getrandbits(32) for _ in range(256))
        corpus = sorted(values)
        expected = [oracle(value) for value in corpus]
        actual = [int(line) for line in run("runtime-corpus", [sample], "\n".join(map(str, corpus)) + "\n").stdout.decode().splitlines()]
        assert actual == expected
        mutant_failures = [value for value, observed in zip(corpus, actual) if oracle(value, 0xA53C91E6) != observed]
        assert mutant_failures, "A wrong reconstruction must be detected"
        invalid = run("runtime-invalid", [sample], "-1\n4294967296\nhello\n\n").stdout.decode().splitlines()
        assert invalid == ["INVALID"] * 4
        write("corpus.json", {"seed": 20261026, "inputs": corpus, "expected": expected, "actual": actual})
        write("negative-control.json", {"mutation": "XOR constant A53C91E7 -> A53C91E6", "rejected_inputs": mutant_failures, "count": len(mutant_failures)})

        truncated = out / "truncated.exe"
        truncated.write_bytes(raw[:256])
        rejected = run("truncated-inspection", [args.node, dispatcher, "inspect-managed-members", truncated, "--json"], expected=None)
        assert rejected.returncode != 0, "Truncated target must not be reported as recovered"
        catalog = json.loads((out / "mcp/tools-list.json").read_text())
        summary = {
            "ok": True, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(), "python": platform.python_version(),
            "node": run("node-version", [args.node, "--version"]).stdout.decode().strip(),
            "rea_version": version, "zod_version": zod_version, "npm_integrity": locked["integrity"],
            "npm_lock_sha256": sha(lock_path.read_bytes()), "dispatcher": str(dispatcher),
            "sample_sha256": sha(raw), "source_sha256": sha(source.read_bytes()),
            "classification": artifact["normalized_result"]["classification"],
            "mvid": normalized["module"]["mvid"], "method_token": method["token"],
            "method_file_offset": offset, "il_file_offset": offset + header_size,
            "il_size": len(il), "il_sha256": sha(il), "il_hex": il.hex(),
            "mcp_tool_count": len(catalog["tools"]), "cli_mcp_normalized_equal": True,
            "clr_reflection_il_equal": True, "differential_cases": len(corpus),
            "invalid_input_cases": 4, "negative_control_rejected": len(mutant_failures),
            "truncated_exit_code": rejected.returncode,
            "not_verified": ["native Ghidra/IDA/Hopper analysis", "all uint32 inputs", "live Codex chat MCP reconnection"],
        }
        write("summary.json", summary)
        write("commands.json", commands)
        spec = importlib.util.spec_from_file_location("pojia_evidence", PROJECT / "skills/pojia/scripts/evidence.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        names = [p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()]
        manifest = module.snapshot(out, names)
        write("manifest.json", manifest)
        assert module.verify(out, manifest)["ok"]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        if not (out / "commands.json").exists():
            write("commands.json", commands)


if __name__ == "__main__":
    raise SystemExit(main())
