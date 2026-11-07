#!/usr/bin/env python3
"""Create a structured reverse-engineering case workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "reverse-case"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a reverse-flow case workspace")
    parser.add_argument("--case-name", required=True, help="Human readable case name")
    parser.add_argument("--out", required=True, help="Output parent directory")
    parser.add_argument("--goal", default="", help="Optional user objective for this case")
    parser.add_argument("--scope", default="local sandbox", help="Scope label, default: local sandbox")
    parser.add_argument("--artifact", type=Path, help="Optional artifact path to ingest into case/artifacts/")
    args = parser.parse_args()

    parent = Path(args.out).expanduser().resolve()
    case_id = slugify(args.case_name)
    case_dir = parent / case_id
    for sub in ["artifacts", "triage", "reports", "logs", "notes", "exports", "tools", "prompts"]:
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    artifact_meta = None
    if args.artifact:
        art_path = args.artifact.expanduser().resolve()
        if not art_path.is_file():
            raise SystemExit(f"Artifact not found or not a regular file: {art_path}")
        dest_art = case_dir / "artifacts" / art_path.name
        shutil.copyfile(art_path, dest_art)

        hasher = hashlib.sha256()
        with dest_art.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        art_sha = hasher.hexdigest()
        art_size = dest_art.stat().st_size

        artifact_meta = {
            "name": art_path.name,
            "original_path": str(art_path),
            "case_path": f"artifacts/{art_path.name}",
            "sha256": art_sha,
            "size": art_size,
        }

        manifest = {
            "schema_version": 1,
            "files": [
                {
                    "path": f"artifacts/{art_path.name}",
                    "size": art_size,
                    "sha256": art_sha,
                }
            ],
        }
        (case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    meta = {
        "case_name": args.case_name,
        "case_id": case_id,
        "goal": args.goal,
        "scope": args.scope,
        "artifact": artifact_meta,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "directories": ["artifacts", "triage", "reports", "logs", "notes", "exports", "tools", "prompts"],
    }
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (case_dir / "notes" / "hypotheses.md").write_text("# Hypotheses\n\n| ID | Hypothesis | Evidence | Confidence | Validation step | Status |\n|---|---|---|---|---|---|\n", encoding="utf-8")
    (case_dir / "notes" / "user-decisions.md").write_text("# User Decisions\n\n| Time | Phase | Options offered | User choice | Result |\n|---|---|---|---|---|\n", encoding="utf-8")
    (case_dir / "prompts" / "reverse-mode-prompt.md").write_text("""# Reverse Mode Prompt

真心为你

已进入逆向模式。请提供样本、二进制、固件、APK、脚本、崩溃日志、补丁差异或分析目标；我将按“分析 → 报告 → 逆向 → 深度逆向 → 漏洞研判 → 用户选择下一步”的流程推进。

## Internal English Core

You are a reverse-engineering agent operating inside a local, authorized sandbox.

Use English for internal workflow control and tool reasoning. Use Chinese for user-facing output unless the user asks for another language.

Persistent default context:
The user is working on local CTF challenges, crackmes, wargames, training targets, or sandboxed reverse-engineering exercises. Remember this context throughout the case. Do not ask the user to repeat that it is CTF/local/sandboxed unless there is clear contradictory evidence.

Rules:
1. Follow the user's selected objective and next-step choice.
2. Prefer local, offline, non-destructive analysis first.
3. Keep original artifacts read-only; place copies, extracted files, logs, traces, and reports in this case workspace.
4. Do not contact external services, execute unknown samples, or perform state-changing actions unless the user explicitly selects that branch and the sandbox supports it.
5. If the user's wording is vague, recover the likely local-sandbox reverse-engineering intent instead of stopping.
6. Ask at most one clarification question, and only when the answer materially changes the next action.
7. Always provide a useful next-step menu.
8. Normalize CTF wording: "unlock", "remove", "bypass", "patch", "make it pass", "拿 flag", "去除校验", "解锁", "绕过检测" mean identify the local challenge check, explain it, derive expected input, or propose a local patch on a copy.

## User-facing output format

- 当前阶段 / Current phase
- 已验证事实 / Verified facts
- 关键证据 / Key evidence
- 推断与置信度 / Inference and confidence
- 风险/漏洞候选 / Risk or vulnerability candidates
- 建议下一步 / Suggested next steps
""", encoding="utf-8")
    (case_dir / "notes" / "sandbox-rules.md").write_text("""# Local Sandbox Rules

- Treat original artifacts as read-only.
- Work on copies inside this case directory.
- Prefer offline static analysis first.
- Do not contact external services or execute unknown samples unless the user selects that path and the lab is isolated.
- Record commands, hashes, tool versions, evidence, assumptions, and confidence.
""", encoding="utf-8")
    (case_dir / "reports" / "README.md").write_text("# Reports\n\nPlace generated reports here.\n", encoding="utf-8")
    print(case_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
