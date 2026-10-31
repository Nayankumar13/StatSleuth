"""SQLite persistence for saved reports (stdlib only, no ORM)."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("STATSLEUTH_DB", Path(__file__).resolve().parents[1] / "data" / "statsleuth.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    title      TEXT NOT NULL,
    source     TEXT NOT NULL,
    text       TEXT NOT NULL,
    summary    TEXT NOT NULL,
    findings   TEXT NOT NULL,
    options    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
"""


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def save(title: str, source: str, text: str, result: dict) -> str:
    rid = uuid.uuid4().hex[:12]
    with conn() as c:
        c.execute(
            "INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)",
            (rid, datetime.now(timezone.utc).isoformat(timespec="seconds"), title, source, text,
             json.dumps(result["summary"]), json.dumps(result["findings"]), json.dumps(result["options"])))
    return rid


def _row(r: sqlite3.Row, full: bool) -> dict:
    d = {"id": r["id"], "created_at": r["created_at"], "title": r["title"], "source": r["source"],
         "summary": json.loads(r["summary"]), "options": json.loads(r["options"])}
    if full:
        d["text"] = r["text"]
        d["findings"] = json.loads(r["findings"])
    return d


def list_reports(limit: int = 100) -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r, False) for r in rows]


def get(rid: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM reports WHERE id = ?", (rid,)).fetchone()
    return _row(r, True) if r else None


def delete(rid: str) -> bool:
    with conn() as c:
        cur = c.execute("DELETE FROM reports WHERE id = ?", (rid,))
        return cur.rowcount > 0
