#!/usr/bin/env python3
"""Deterministic skill packaging utility for reverse-flow and pojia.

Packs skill directories into portable .skill zip archives, excludes temporary
and compiled artifacts, and generates SHA256 checksums.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
IGNORED_PARTS = {"__pycache__", ".git", ".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".tmp"}


def should_include(file_path: Path) -> bool:
    """Return True if the file should be included in the skill archive."""
    for part in file_path.parts:
        if part in IGNORED_PARTS:
            return False
    if file_path.suffix.lower() in IGNORED_SUFFIXES:
        return False
    return True


def pack_skill(skill_name: str, skills_root: Path, output_dir: Path) -> tuple[Path, str]:
    """Pack a single skill directory into an output .skill file.

    Returns the output path and its hex SHA256 digest.
    """
    skill_src = skills_root / skill_name
    if not skill_src.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {skill_src}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{skill_name}.skill"

    # Collect files deterministically
    files_to_pack: list[tuple[Path, str]] = []
    for item in sorted(skill_src.rglob("*")):
        if item.is_file() and should_include(item):
            rel_in_archive = f"{skill_name}/{item.relative_to(skill_src).as_posix()}"
            files_to_pack.append((item, rel_in_archive))

    # Write zip file
    with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for disk_path, arc_path in files_to_pack:
            # Set fixed zip time for reproducibility
            zinfo = zipfile.ZipInfo(arc_path, date_time=(2026, 11, 8, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            data = disk_path.read_bytes()
            zf.writestr(zinfo, data)

    digest = hashlib.sha256(out_file.read_bytes()).hexdigest()
    return out_file, digest


def pack_all(output_dir: Path) -> dict[str, dict[str, str]]:
    """Pack all recognized skills and write checksums.sha256."""
    skills = ["reverse-flow", "pojia"]
    results: dict[str, dict[str, str]] = {}
    checksum_lines: list[str] = []

    for name in skills:
        out_path, sha = pack_skill(name, SKILLS_DIR, output_dir)
        results[name] = {"path": str(out_path.resolve()), "sha256": sha}
        checksum_lines.append(f"{sha}  {out_path.name}")

    checksum_file = output_dir / "checksums.sha256"
    checksum_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack reverse-flow and pojia skills.")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dist",
        help="Target output directory for .skill files and checksums (default: ./dist)",
    )
    args = parser.parse_args()

    results = pack_all(args.out)
    for name, info in results.items():
        print(f"[+] Packed {name} -> {info['path']} (SHA256: {info['sha256'][:16]}...)")
    print(f"[+] Checksums saved to: {args.out / 'checksums.sha256'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
