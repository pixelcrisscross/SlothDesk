from __future__ import annotations
from pathlib import Path
import os

def undo_run(root_path: str, result: dict) -> dict:
    root = Path(root_path).resolve(strict=True)
    restored = 0
    errors = []
    # Reverse order to handle plans where one operation affects another destination.
    for op in reversed(result.get("operations", [])):
        if op.get("status") != "success":
            continue
        source = root / op["destination"]
        dest = root / op["source"]
        try:
            source_resolved = source.resolve(strict=True)
            source_resolved.relative_to(root)
            if source.is_symlink() or not source.is_file():
                raise ValueError("Moved file is missing or unsafe.")
            if dest.exists() or dest.is_symlink():
                raise FileExistsError(f"Cannot restore because original path exists: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.parent.resolve().is_relative_to(root):
                raise ValueError("Restore destination escapes selected root.")
            os.replace(source, dest)
            restored += 1
        except Exception as exc:
            errors.append(f"{op['destination']} → {op['source']}: {exc}")
    return {"restored": restored, "errors": errors}
