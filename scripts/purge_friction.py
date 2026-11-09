#!/usr/bin/env python3
"""Host Friction Purge & Environment Diagnostic Utility for Claude Code and Codex.

Inspired by host-level patch mechanisms (e.g., dsh-purge):
1. Injects non-destructive auto-approval permissions into Claude Code (.claude/settings.local.json)
   to eliminate repetitive confirmation popups during reverse engineering.
2. Provides snapshot backups (*.friction_purge.bak) and one-click rollback.
3. Diagnoses host runtimes (separates real Python runtimes from Windows Store stubs)
   and verifies toolchain readiness.
4. Synchronizes reverse-flow and pojia skills across Claude Code and Codex platforms.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Default non-destructive tool and reverse-flow / pojia command permissions
DEFAULT_ALLOW_PERMISSIONS = [
    # Python runtimes & skill scripts
    "Bash(python *)",
    "Bash(python3 *)",
    "Bash(py *)",
    "PowerShell(python *)",
    "PowerShell(python3 *)",
    "PowerShell(py *)",
    "PowerShell(py.exe *)",
    # Core reverse tools & scripts
    "Bash(*inspect_cil.py*)",
    "Bash(*diff_verifier.py*)",
    "Bash(*evidence.py*)",
    "Bash(*triage_artifact.py*)",
    "Bash(*create_case.py*)",
    "Bash(*tool_audit.py*)",
    "Bash(*report_from_triage.py*)",
    "PowerShell(*inspect_cil.py*)",
    "PowerShell(*diff_verifier.py*)",
    "PowerShell(*evidence.py*)",
    "PowerShell(*triage_artifact.py*)",
    "PowerShell(*create_case.py*)",
    "PowerShell(*tool_audit.py*)",
    "PowerShell(*report_from_triage.py*)",
    # Craft Anything clean-room recreation engine & MCP CLI
    "Bash(craft-anything-cli *)",
    "Bash(craft-anything *)",
    "Bash(*craft-anything-cli.exe*)",
    "PowerShell(craft-anything-cli *)",
    "PowerShell(craft-anything *)",
    "PowerShell(*craft-anything-cli.exe*)",
    # Read-only standard RE analysis tools
    "Bash(strings *)",
    "Bash(file *)",
    "Bash(xxd *)",
    "Bash(readelf *)",
    "Bash(objdump *)",
    "PowerShell(strings *)",
    "PowerShell(file *)",
    "PowerShell(xxd *)",
]


def find_valid_python_interpreters() -> list[dict[str, Any]]:
    """Scan and return valid Python interpreters, distinguishing real ones from Windows Store stubs."""
    candidates = ["py", "python3", "python"]
    valid_interpreters: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for cmd in candidates:
        try:
            # Check where command points
            where_cmd = "where" if os.name == "nt" else "which"
            proc = subprocess.run([where_cmd, cmd], capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                raw_paths = [p.strip() for p in proc.stdout.splitlines() if p.strip()]
                for path_str in raw_paths:
                    norm = os.path.normcase(os.path.realpath(path_str))
                    if norm in seen_paths:
                        continue
                    seen_paths.add(norm)

                    # Check if Windows Store 0-byte or redirector stub
                    is_store_stub = "WindowsApps" in path_str and not os.path.exists(path_str)

                    # Test execution
                    version = ""
                    usable = False
                    try:
                        v_proc = subprocess.run([path_str, "--version"], capture_output=True, text=True, timeout=5)
                        if v_proc.returncode == 0:
                            version = (v_proc.stdout or v_proc.stderr).strip()
                            usable = True
                    except Exception:
                        usable = False

                    valid_interpreters.append({
                        "command": cmd,
                        "path": path_str,
                        "version": version or "Unknown / Stub",
                        "usable": usable and not is_store_stub,
                        "is_store_stub": is_store_stub or ("WindowsApps" in path_str and not usable)
                    })
        except Exception:
            continue

    return valid_interpreters


def get_claude_settings_path(target_dir: Path | None = None, is_global: bool = False) -> Path:
    """Return project-level .claude/settings.local.json or global ~/.claude/settings.json path."""
    if is_global:
        return Path.home() / ".claude" / "settings.json"
    base = target_dir or Path.cwd()
    return base / ".claude" / "settings.local.json"


def apply_friction_purge(
    target_dir: Path | None = None,
    is_global: bool = False,
    extra_allows: list[str] | None = None
) -> dict[str, Any]:
    """Merge auto-approval permissions into settings with a timestamped backup."""
    settings_path = get_claude_settings_path(target_dir, is_global=is_global)
    settings_dir = settings_path.parent
    settings_dir.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    raw_data: Any = {}

    if settings_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = settings_dir / f"{settings_path.name}.{timestamp}.friction_purge.bak"
        shutil.copy2(settings_path, backup_path)
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception:
            raw_data = {}

    existing_data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}

    perms = existing_data.setdefault("permissions", {})
    if not isinstance(perms, dict):
        perms = {}
        existing_data["permissions"] = perms

    allow_list: list[str] = perms.setdefault("allow", [])
    if not isinstance(allow_list, list):
        allow_list = []
        perms["allow"] = allow_list

    # Merge permissions without duplicates
    merged = list(allow_list)
    to_add = list(DEFAULT_ALLOW_PERMISSIONS) + (extra_allows or [])
    added_count = 0

    for rule in to_add:
        if rule not in merged:
            merged.append(rule)
            added_count += 1

    perms["allow"] = merged

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "status": "success",
        "settings_path": str(settings_path),
        "is_global": is_global,
        "backup_path": str(backup_path) if backup_path else None,
        "added_rules": added_count,
        "total_rules": len(merged)
    }


def rollback_friction_purge(target_dir: Path | None = None, is_global: bool = False) -> dict[str, Any]:
    """Rollback to the latest .friction_purge.bak snapshot."""
    settings_path = get_claude_settings_path(target_dir, is_global=is_global)
    settings_dir = settings_path.parent

    if not settings_dir.exists():
        return {"status": "error", "message": f"Settings directory not found: {settings_dir}"}

    backups = sorted(settings_dir.glob(f"{settings_path.name}.*.friction_purge.bak"))
    if not backups:
        # Fallback to any friction_purge.bak in directory
        backups = sorted(settings_dir.glob("*.friction_purge.bak"))
    if not backups:
        return {"status": "error", "message": "No friction_purge backup found to rollback"}

    latest_backup = backups[-1]
    shutil.copy2(latest_backup, settings_path)

    return {
        "status": "success",
        "restored_from": str(latest_backup),
        "settings_path": str(settings_path)
    }


def sync_skills_to_platforms(repo_root: Path) -> dict[str, Any]:
    """Copy reverse-flow and pojia skills to ~/.claude/skills and ~/.codex/skills."""
    home = Path.home()
    claude_skills = home / ".claude" / "skills"
    codex_skills = home / ".codex" / "skills"

    skills_src = repo_root / "skills"
    results: dict[str, list[str]] = {"claude": [], "codex": []}

    for skill_name in ["reverse-flow", "pojia"]:
        src = skills_src / skill_name
        if not src.is_dir():
            continue

        # Sync to Claude Code
        if claude_skills.parent.exists():
            dest_claude = claude_skills / skill_name
            dest_claude.mkdir(parents=True, exist_ok=True)
            _copy_tree_clean(src, dest_claude)
            results["claude"].append(skill_name)

        # Sync to Codex
        if codex_skills.parent.exists():
            dest_codex = codex_skills / skill_name
            dest_codex.mkdir(parents=True, exist_ok=True)
            _copy_tree_clean(src, dest_codex)
            results["codex"].append(skill_name)

    return {"status": "success", "synced": results}


def _copy_tree_clean(src: Path, dest: Path) -> None:
    """Copy directory while ignoring pycache and git files."""
    dest.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        rel = Path(root).relative_to(src)
        target_dir = dest / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            if f.endswith((".pyc", ".tmp")):
                continue
            shutil.copy2(Path(root) / f, target_dir / f)


def diagnose_environment(
    repo_root: Path,
    target_dir: Path | None = None,
    is_global: bool = False
) -> dict[str, Any]:
    """Perform a holistic diagnostic of host runtimes, permissions, and skill deployments."""
    repo_skills_present = (repo_root / "skills" / "pojia" / "SKILL.md").exists()
    pythons = find_valid_python_interpreters()
    settings_path = get_claude_settings_path(target_dir, is_global=is_global)

    has_settings = settings_path.exists()
    allowed_rules: list[str] = []
    if has_settings:
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                allowed_rules = data.get("permissions", {}).get("allow", [])
        except Exception:
            pass

    home = Path.home()
    claude_installed = (home / ".claude" / "skills" / "pojia" / "SKILL.md").exists()
    codex_installed = (home / ".codex" / "skills" / "pojia" / "SKILL.md").exists()
    cany_available = bool(shutil.which("craft-anything-cli") or shutil.which("craft-anything-cli.exe"))

    usable_py = [p for p in pythons if p["usable"]]

    return {
        "repo_skills_present": repo_skills_present,
        "python_interpreters": pythons,
        "recommended_python": usable_py[0]["command"] if usable_py else None,
        "craft_anything_available": cany_available,
        "claude_settings_path": str(settings_path),
        "is_global": is_global,
        "permissions_active": len(allowed_rules),
        "claude_skill_installed": claude_installed,
        "codex_skill_installed": codex_installed,
        "is_ready_for_frictionless_re": bool(usable_py and allowed_rules and (claude_installed or codex_installed))
    }


def setup_shell_aliases(repo_root: Path) -> dict[str, Any]:
    """Configure convenient 'pojia' and 'rf' terminal shortcuts in PowerShell and Bash."""
    configured: list[str] = []
    py_interpreters = find_valid_python_interpreters()
    usable_py = [p for p in py_interpreters if p["usable"]]
    py_cmd = usable_py[0]["command"] if usable_py else "py"

    triage_script = (repo_root / "skills" / "reverse-flow" / "scripts" / "triage_artifact.py").resolve()
    cil_script = (repo_root / "skills" / "pojia" / "scripts" / "inspect_cil.py").resolve()

    # 1. Windows PowerShell Profiles
    ps_profiles = [
        Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    ]

    ps_block = f"""
# >>> Reverse Flow & Pojia Aliases >>>
function pojia {{
    param([string]$target, [switch]$ai)
    if ($ai) {{
        claude "破甲 $target"
    }} elseif (-not $target) {{
        & {py_cmd} "{triage_script}" --help
    }} else {{
        Write-Host "[*] 启动 Pojia 破甲分析: $target" -ForegroundColor Cyan
        & {py_cmd} "{triage_script}" "$target"
        & {py_cmd} "{cil_script}" "$target" 2>$null
    }}
}}

function rf {{
    param([string]$target, [switch]$ai)
    if ($ai) {{
        claude "真心为你，分析 $target"
    }} elseif (-not $target) {{
        & {py_cmd} "{triage_script}" --help
    }} else {{
        & {py_cmd} "{triage_script}" "$target"
    }}
}}
# <<< Reverse Flow & Pojia Aliases <<<
"""
    for prof in ps_profiles:
        try:
            prof.parent.mkdir(parents=True, exist_ok=True)
            existing = prof.read_text(encoding="utf-8-sig", errors="ignore") if prof.exists() else ""
            start_tag = "# >>> Reverse Flow & Pojia Aliases >>>"
            end_tag = "# <<< Reverse Flow & Pojia Aliases <<<"
            if start_tag in existing and end_tag in existing:
                before = existing.split(start_tag)[0]
                after = existing.split(end_tag)[1]
                new_content = before.rstrip() + "\n" + ps_block.strip() + "\n" + after.lstrip()
            else:
                new_content = existing.rstrip() + "\n" + ps_block.strip() + "\n"
            prof.write_text(new_content, encoding="utf-8-sig")
            configured.append(str(prof))
        except Exception:
            continue

    return {"status": "success", "configured_profiles": configured}


def run_one_click_install(repo_root: Path, target_dir: Path | None = None) -> dict[str, Any]:
    """Perform complete one-click install across platforms and permissions."""
    sync_res = sync_skills_to_platforms(repo_root)
    global_res = apply_friction_purge(is_global=True)
    local_res = apply_friction_purge(target_dir=target_dir, is_global=False)
    alias_res = setup_shell_aliases(repo_root)
    diag = diagnose_environment(repo_root, target_dir=target_dir, is_global=False)

    return {
        "status": "success",
        "synced": sync_res["synced"],
        "global_purge": global_res,
        "local_purge": local_res,
        "aliases": alias_res,
        "diagnostics": diag
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Host Friction Purge & Environment Diagnostic Utility")
    subparsers = parser.add_subparsers(dest="command")

    # install (one-click setup)
    subparsers.add_parser("install", help="Complete one-click install for new PC (sync skills + global & local permissions)")

    # apply
    apply_p = subparsers.add_parser("apply", help="Inject frictionless auto-approval rules into Claude settings")
    apply_p.add_argument("--global", "-g", dest="is_global", action="store_true", help="Apply to global ~/.claude/settings.json")

    # rollback
    roll_p = subparsers.add_parser("rollback", help="Restore previous Claude settings from backup")
    roll_p.add_argument("--global", "-g", dest="is_global", action="store_true", help="Rollback global ~/.claude/settings.json")

    # diagnose
    diag_p = subparsers.add_parser("diagnose", help="Check Python runtimes, permissions, and skill deployments")
    diag_p.add_argument("--global", "-g", dest="is_global", action="store_true", help="Diagnose global settings")

    # sync-skills
    subparsers.add_parser("sync-skills", help="Synchronize skills to ~/.claude/skills and ~/.codex/skills")

    # alias
    subparsers.add_parser("alias", help="Configure 'pojia' and 'rf' terminal shortcuts in PowerShell and Bash")

    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.command == "install":
        print("=" * 65)
        print(" [🚀] 正在执行 Reverse Flow & Pojia (破甲) 全局一键安装...")
        print("=" * 65)
        res = run_one_click_install(repo_root)
        print(f"✓ 技能同步成功:")
        print(f"  - Claude Code: {', '.join(res['synced']['claude']) or '已跳过'}")
        print(f"  - Codex:       {', '.join(res['synced']['codex']) or '已跳过'}")
        print(f"✓ 全局免扰白名单生效: {res['global_purge']['settings_path']} ({res['global_purge']['total_rules']} 条规则)")
        print(f"✓ 本地工作区白名单生效: {res['local_purge']['settings_path']}")
        if res["aliases"]["configured_profiles"]:
            print(f"✓ 终端快捷指令已注入: {', '.join(res['aliases']['configured_profiles'])}")
        diag = res["diagnostics"]
        print(f"\n推荐 Python 解释器: {diag['recommended_python'] or '未检测到，建议安装 Python 3.10+'}")
        print(f"无障碍逆向就绪状态: {'✓ 100% 准备就绪' if diag['is_ready_for_frictionless_re'] else '✗ 部分环境待配置'}")
        print("=" * 65)
        print("使用方式：在 Claude Code 或 Codex 终端直接输入【真心为你】或【破甲】！")
        print("系统终端快捷命令：直接输入 pojia <file> 或 rf <file> 快速分析！")
        print("=" * 65)
        return 0

    elif args.command == "alias":
        res = setup_shell_aliases(repo_root)
        print("✓ Shell aliases configured:")
        for prof in res["configured_profiles"]:
            print(f"  - {prof}")
        print("\nNow you can type 'pojia <target>' or 'rf <target>' directly in PowerShell!")
        return 0

    elif args.command == "apply":
        is_glob = getattr(args, "is_global", False)
        res = apply_friction_purge(is_global=is_glob)
        scope = "Global (~/.claude/settings.json)" if is_glob else "Local (.claude/settings.local.json)"
        print(f"✓ Host Friction Purge Applied Successfully ({scope})!")
        print(f"  Target: {res['settings_path']}")
        if res['backup_path']:
            print(f"  Backup: {res['backup_path']}")
        print(f"  Added {res['added_rules']} new rules (Total: {res['total_rules']} active rules)")
        return 0

    elif args.command == "rollback":
        is_glob = getattr(args, "is_global", False)
        res = rollback_friction_purge(is_global=is_glob)
        if res["status"] == "success":
            print(f"✓ Rollback successful! Restored from: {res['restored_from']}")
            return 0
        else:
            print(f"✗ Rollback failed: {res['message']}")
            return 1

    elif args.command == "diagnose":
        is_glob = getattr(args, "is_global", False)
        diag = diagnose_environment(repo_root, is_global=is_glob)
        print("=" * 60)
        print("  Host Runtime & Friction Purge Diagnostic Report")
        print("=" * 60)
        print(f"Python Interpreters Detected:")
        for p in diag["python_interpreters"]:
            status = "✓ Ready" if p["usable"] else ("✗ Windows Store Stub" if p["is_store_stub"] else "✗ Broken")
            print(f"  - [{status}] {p['command']} -> {p['path']} ({p['version']})")
        print(f"\nRecommended Python: {diag['recommended_python'] or 'None found (Please install Python 3.10+)'}")
        scope_str = "Global" if is_glob else "Local"
        print(f"Claude Code {scope_str} Permissions: {diag['permissions_active']} rules active")
        print(f"Claude Code Skill (pojia): {'✓ Installed' if diag['claude_skill_installed'] else '✗ Missing'}")
        print(f"Codex Skill (pojia): {'✓ Installed' if diag['codex_skill_installed'] else '✗ Missing'}")
        print(f"Frictionless Execution Ready: {'✓ YES' if diag['is_ready_for_frictionless_re'] else '✗ Incomplete setup'}")
        print("=" * 60)
        return 0

    elif args.command == "sync-skills":
        res = sync_skills_to_platforms(repo_root)
        print("✓ Skills synchronized to platforms:")
        print(f"  Claude Code: {', '.join(res['synced']['claude']) or 'skipped'}")
        print(f"  Codex:       {', '.join(res['synced']['codex']) or 'skipped'}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
