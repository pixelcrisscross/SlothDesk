from pathlib import Path
import pytest
from slothdesk.safety import validate_plan_item

def test_rejects_path_traversal(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    with pytest.raises(ValueError):
        validate_plan_item(root, {
            "original_name": "a.txt",
            "suggested_name": "x.txt",
            "category": "../outside",
            "reason": "test",
            "confidence": 0.9,
        })

def test_rejects_missing_source(tmp_path):
    with pytest.raises(ValueError):
        validate_plan_item(tmp_path, {
            "original_name": "missing.txt",
            "suggested_name": "new.txt",
            "category": "Documents",
            "reason": "test",
            "confidence": 0.9,
        })

def test_rejects_existing_destination(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    (root / "Documents").mkdir()
    (root / "Documents" / "new.txt").write_text("occupied")
    with pytest.raises(ValueError):
        validate_plan_item(root, {
            "original_name": "a.txt",
            "suggested_name": "new.txt",
            "category": "Documents",
            "reason": "test",
            "confidence": 0.9,
        })
