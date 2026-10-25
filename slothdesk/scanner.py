from __future__ import annotations
from pathlib import Path
import hashlib

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".slothdesk"}

def scan_directory(root: Path) -> list[dict]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Selected path is not a directory.")
    rows = []
    for path in sorted(root.rglob("*")):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            stat = path.stat()
            rows.append({
                "relative_path": rel.as_posix(),
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
        except (OSError, ValueError):
            continue
    return rows

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def find_exact_duplicates(root: Path, rows: list[dict]) -> list[list[str]]:
    by_size: dict[int, list[str]] = {}
    for row in rows:
        by_size.setdefault(row["size_bytes"], []).append(row["relative_path"])
    groups = []
    for candidates in by_size.values():
        if len(candidates) < 2:
            continue
        hashes: dict[str, list[str]] = {}
        for rel in candidates:
            try:
                digest = sha256_file(root / rel)
                hashes.setdefault(digest, []).append(rel)
            except OSError:
                continue
        groups.extend(group for group in hashes.values() if len(group) > 1)
    return groups
