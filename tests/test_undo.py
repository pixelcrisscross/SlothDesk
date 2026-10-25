from pathlib import Path
from slothdesk.executor import apply_plan
from slothdesk.undo import undo_run

def test_apply_and_undo(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "receipt.pdf").write_text("synthetic receipt")
    result = apply_plan(root, [{
        "original_name": "receipt.pdf",
        "suggested_name": "2026_receipt.pdf",
        "category": "Documents/Receipts",
        "reason": "test",
        "confidence": 0.8,
    }])
    assert result["success_count"] == 1
    assert (root / "Documents/Receipts/2026_receipt.pdf").exists()
    undone = undo_run(str(root), result)
    assert undone["restored"] == 1
    assert (root / "receipt.pdf").exists()
