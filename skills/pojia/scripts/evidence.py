"""Snapshot selected case files and verify later changes; Python standard library only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def case_file(root: Path, name: str) -> Path:
    relative = Path(name)
    if not name or relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError(f"Expected a relative case path: {name!r}")
    target = (root / relative).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"Not a regular file inside the case: {name!r}")
    return target


def digest(path: Path) -> dict:
    before = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"File changed while hashing: {path.name}")
    return {"size": after.st_size, "sha256": hasher.hexdigest()}


def snapshot(root: Path, names: list[str]) -> dict:
    root = root.resolve(strict=True)
    if not names:
        raise ValueError("Select at least one evidence file")
    entries = {}
    for name in names:
        target = case_file(root, name)
        relative = target.relative_to(root).as_posix()
        entries[relative] = {"path": relative, **digest(target)}
    return {"schema_version": 1, "files": [entries[n] for n in sorted(entries)]}


def verify(root: Path, manifest: dict) -> dict:
    root = root.resolve(strict=True)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Unsupported evidence manifest")
    if not manifest["files"]:
        raise ValueError("Empty evidence manifest")
    failures = []
    seen = set()
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Invalid evidence entry")
        name = entry["path"]
        if name in seen:
            raise ValueError(f"Duplicate evidence path: {name}")
        seen.add(name)
        try:
            actual = digest(case_file(root, name))
            if actual != {"size": entry.get("size"), "sha256": entry.get("sha256")}:
                failures.append({"path": name, "reason": "content-mismatch"})
        except (OSError, ValueError) as error:
            failures.append({"path": name, "reason": str(error)})
    return {"ok": not failures, "checked": len(seen), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    capture = sub.add_parser("snapshot")
    capture.add_argument("--root", type=Path, required=True)
    capture.add_argument("--out", required=True)
    capture.add_argument("files", nargs="+")
    check = sub.add_parser("verify")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if args.action == "snapshot":
            output = (root / args.out).resolve()
            if not output.is_relative_to(root):
                raise ValueError("Manifest must remain inside the case")
            record = snapshot(root, args.files)
            if output.relative_to(root).as_posix() in {e["path"] for e in record["files"]}:
                raise ValueError("Manifest cannot include itself")
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print(json.dumps({"ok": True, "files": len(record["files"])}, ensure_ascii=False))
            return 0
        record = json.loads(case_file(root, args.manifest).read_text(encoding="utf-8"))
        result = verify(root, record)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
