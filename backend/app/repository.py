"""Small SQLite repository for local dataset metadata and analysis history.

This is intentionally single-user/local-first. SQLite gives the portfolio app
real persistence without requiring a separate database server.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("STATE_DB", Path(__file__).resolve().parents[1] / "data" / "datapilot.db"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('demo', 'upload')),
                rows_count INTEGER NOT NULL,
                columns_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                mode TEXT NOT NULL,
                primary_tool TEXT,
                steps_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_dataset_created
            ON analyses(dataset_id, id DESC);
            """
        )


def save_dataset(dataset_id: str, filename: str, source: str, rows: int, columns: int) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO datasets
               (dataset_id, filename, source, rows_count, columns_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dataset_id, filename, source, int(rows), int(columns), _utc_now()),
        )


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
    return dict(row) if row else None


def delete_dataset(dataset_id: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))


def record_analysis(dataset_id: str, question: str, result: dict[str, Any]) -> None:
    init_db()
    steps = result.get("steps") or []
    primary_tool = steps[0].get("tool") if steps else None
    with _connect() as conn:
        conn.execute(
            """INSERT INTO analyses
               (dataset_id, question, answer, mode, primary_tool, steps_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                dataset_id,
                question,
                str(result.get("answer", "")),
                str(result.get("mode", "unknown")),
                primary_tool,
                json.dumps(steps, ensure_ascii=False, default=str),
                _utc_now(),
            ),
        )


def list_history(dataset_id: str, limit: int = 30) -> list[dict[str, Any]]:
    init_db()
    limit = max(1, min(int(limit), 100))
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, question, answer, mode, primary_tool, created_at
               FROM analyses WHERE dataset_id = ? ORDER BY id DESC LIMIT ?""",
            (dataset_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_history(dataset_id: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM analyses WHERE dataset_id = ?", (dataset_id,))