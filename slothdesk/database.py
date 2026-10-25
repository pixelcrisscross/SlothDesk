from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path.home() / ".slothdesk" / "history.sqlite3"

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                root_path TEXT NOT NULL,
                model TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
        """)

def save_run(root_path: str, model: str, result: dict) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs(created_at, root_path, model, result_json) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), root_path, model, json.dumps(result)),
        )
        return int(cur.lastrowid)

def list_runs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, root_path, model FROM runs ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]

def get_run(run_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, created_at, root_path, model, result_json FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["result"] = json.loads(result.pop("result_json"))
    return result
