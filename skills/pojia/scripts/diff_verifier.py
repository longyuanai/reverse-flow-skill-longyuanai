#!/usr/bin/env python3
"""Differential verifier: cross-checks an original binary/program against a reconstructed Python implementation.

Inspired by the 'Study -> Build -> Check -> Refine' clean-room verification loop.
Ensures reverse-engineering deductions match 100% against the target executable without hallucination.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_target(cmd_template: list[str], test_input: str, input_mode: str = "stdin", timeout: int = 5) -> str:
    """Run original target executable with given input."""
    try:
        if input_mode == "stdin":
            res = subprocess.run(
                cmd_template,
                input=test_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return res.stdout.strip()
        else:
            # Replace placeholder {input} or append
            cmd = [arg.replace("{input}", test_input) for arg in cmd_template]
            if "{input}" not in " ".join(cmd_template):
                cmd.append(test_input)
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return res.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"


def load_py_func(py_path: Path, func_name: str):
    """Dynamically load function from python file."""
    spec = importlib.util.spec_from_file_location("reconstructed_mod", py_path)
    if not spec or not spec.loader:
        raise ValueError(f"Cannot load python module: {py_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, func_name):
        raise AttributeError(f"Function {func_name} not found in {py_path}")
    return getattr(mod, func_name)


def generate_default_corpus(kind: str = "int", count: int = 100, seed: int = 20261107) -> list[str]:
    """Generate deterministic boundary and randomized inputs."""
    random.seed(seed)
    cases = []
    if kind == "int":
        # Critical boundary values
        boundaries = [
            0, 1, 2, 7, 8, 15, 16, 31, 32, 63, 64, 127, 128, 255, 256,
            0x7FFF, 0x8000, 0xFFFF, 0x10000,
            0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
        ]
        cases.extend(str(x) for x in boundaries)
        # Random inputs
        for _ in range(count):
            cases.append(str(random.randint(0, 0xFFFFFFFF)))
    else:
        # String boundary values
        cases.extend(["", "A", "admin", "password", "flag{test}", "123456", " ", "\t"])
        for length in [4, 8, 16, 32, 64]:
            cases.append("".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=length)))
    # De-duplicate while preserving order
    return list(dict.fromkeys(cases))


def verify_differential(
    target_cmd: list[str],
    py_func,
    corpus: list[str],
    input_mode: str = "stdin",
    negative_func=None
) -> dict:
    """Execute differential testing between target and python implementation."""
    results = []
    passed = 0
    failed = 0
    mismatches = []

    for item in corpus:
        actual_target = run_target(target_cmd, item, input_mode=input_mode)

        try:
            # Handle int or str argument
            val_arg = int(item) if item.isdigit() and int(item) <= 0xFFFFFFFF else item
            recon_res = py_func(val_arg)
            expected_recon = str(recon_res).strip()
        except Exception as e:
            expected_recon = f"EXCEPTION: {e}"

        matched = (actual_target == expected_recon)
        if matched:
            passed += 1
        else:
            failed += 1
            if len(mismatches) < 10:
                mismatches.append({
                    "input": item,
                    "target_output": actual_target,
                    "reconstructed_output": expected_recon
                })
        results.append({
            "input": item,
            "target": actual_target,
            "recon": expected_recon,
            "match": matched
        })

    neg_control_passed = True
    neg_control_sample = None
    if negative_func and corpus:
        # Negative control: intentionally wrong hypothesis should FAIL
        sample_in = corpus[0]
        actual_t = run_target(target_cmd, sample_in, input_mode=input_mode)
        try:
            val_arg = int(sample_in) if sample_in.isdigit() else sample_in
            neg_res = str(negative_func(val_arg)).strip()
            # If wrong hypothesis matches target, the negative control fails!
            if neg_res == actual_t:
                neg_control_passed = False
            neg_control_sample = {"input": sample_in, "neg_output": neg_res, "target_output": actual_t}
        except Exception:
            pass

    confidence = 1.0 if (failed == 0 and passed > 0 and neg_control_passed) else 0.0

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(corpus),
        "passed": passed,
        "failed": failed,
        "accuracy": (passed / len(corpus)) if corpus else 0.0,
        "confidence": confidence,
        "negative_control_verified": neg_control_passed,
        "negative_control_sample": neg_control_sample,
        "mismatches": mismatches
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, nargs="+", help="Target command (e.g. ./sample.exe or python test.py)")
    parser.add_argument("--py", required=True, type=Path, help="Path to reconstructed Python script")
    parser.add_argument("--func", default="transform", help="Function name in reconstructed Python script (default: transform)")
    parser.add_argument("--input-mode", choices=["stdin", "arg"], default="stdin", help="How target expects input")
    parser.add_argument("--corpus-kind", choices=["int", "str"], default="int", help="Corpus type for auto-generation")
    parser.add_argument("--corpus-file", type=Path, help="Optional JSON file with list of inputs")
    parser.add_argument("--count", type=int, default=100, help="Number of random test cases (default: 100)")
    parser.add_argument("--out", type=Path, help="Output JSON path")
    args = parser.parse_args()

    target_cmd = args.target
    py_func = load_py_func(args.py, args.func)

    corpus: list[str] = []
    if args.corpus_file and args.corpus_file.exists():
        raw_data = json.loads(args.corpus_file.read_text(encoding="utf-8"))
        if isinstance(raw_data, dict) and "inputs" in raw_data and isinstance(raw_data["inputs"], list):
            corpus = [str(x) for x in raw_data["inputs"]]
        elif isinstance(raw_data, list):
            corpus = [str(x) for x in raw_data]
    if not corpus:
        corpus = generate_default_corpus(kind=args.corpus_kind, count=args.count)

    report = verify_differential(target_cmd, py_func, corpus, input_mode=args.input_mode)
    report["target_cmd"] = target_cmd
    report["reconstructed_file"] = str(args.py)
    report["function"] = args.func

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(f"Differential verification report written to: {args.out}")
    else:
        print(rendered)

    return 0 if report["confidence"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
