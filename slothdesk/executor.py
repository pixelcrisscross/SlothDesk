from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import os
import uuid
from .safety import validate_plan_item

def apply_plan(root: Path, items: list[dict]) -> dict:
    root = root.resolve(strict=True)
    run_id = str(uuid.uuid4())
    operations = []
    errors = []
    # Revalidate the complete approved plan and detect destination collisions within it.
    validated = [validate_plan_item(root, item) for item in items]
    destinations = set()
    for item in validated:
        dest_rel = (Path(item["category"]) / item["suggested_name"]).as_posix()
        if dest_rel in destinations:
            raise ValueError(f"Two approved files target the same destination: {dest_rel}")
        destinations.add(dest_rel)

    for item in validated:
        source = root / item["original_name"]
        dest_dir = root / item["category"]
        dest = dest_dir / item["suggested_name"]
        if source.resolve() == dest.resolve():
            continue
        try:
            # Recheck just before mutation to reduce collision/race risk.
            if source.is_symlink() or not source.is_file():
                raise ValueError("Source changed or is no longer a regular file.")
            if dest.exists() or dest.is_symlink():
                raise FileExistsError(f"Destination appeared during execution: {dest}")
            dest_dir.mkdir(parents=True, exist_ok=True)
            if not dest_dir.resolve().is_relative_to(root):
                raise ValueError("Destination directory escaped selected root.")
            os.replace(source, dest)
            operations.append({
                "source": item["original_name"],
                "destination": dest.relative_to(root).as_posix(),
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            errors.append(f"{item['original_name']}: {exc}")
            operations.append({
                "source": item["original_name"],
                "destination": (Path(item["category"]) / item["suggested_name"]).as_posix(),
                "status": "error",
                "error": str(exc),
            })
    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root_path": str(root),
        "operations": operations,
        "success_count": sum(op["status"] == "success" for op in operations),
        "errors": errors,
    }
