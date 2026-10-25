from __future__ import annotations
from pathlib import Path
import re
from .schemas import PlanItem

INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')

def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (ValueError, OSError):
        return False

def validate_plan_item(root: Path, raw: dict) -> dict:
    root = root.resolve(strict=True)
    item = PlanItem.model_validate(raw)
    source = root / item.original_name
    # MVP plan operates on files directly in the selected root only. This avoids ambiguity
    # when category folders and nested source folders overlap.
    if source.parent.resolve() != root or source.is_symlink() or not source.is_file():
        raise ValueError(f"Source is missing, nested, or unsafe: {item.original_name}")
    if INVALID_CHARS.search(item.suggested_name):
        raise ValueError(f"Filename contains unsupported characters: {item.suggested_name}")
    if item.suggested_name in {".", ".."}:
        raise ValueError("Invalid destination filename.")
    dest_dir = root / item.category
    dest = dest_dir / item.suggested_name
    if not _inside(root, dest_dir) or not _inside(root, dest):
        raise ValueError("Destination escapes selected folder.")
    if dest.exists() and dest.resolve() != source.resolve():
        raise ValueError(f"Destination already exists: {dest.relative_to(root)}")
    return {
        "original_name": item.original_name,
        "suggested_name": item.suggested_name,
        "category": item.category,
        "reason": item.reason,
        "confidence": item.confidence,
    }
