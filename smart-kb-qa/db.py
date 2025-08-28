# db.py
# Simple SQLite logger for requests/responses
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = "logs.sqlite3"

def init_db():
    """Create logs table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        command_text TEXT,
        response_text TEXT,
        sources_json TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_entry(user_id: str, command_text: str, response_text: str, sources: List[Dict[str, Any]]):
    """Insert a log entry."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO logs (user_id, command_text, response_text, sources_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, command_text, response_text, json.dumps(sources), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def fetch_recent(limit: int = 100):
    """Return most recent logs as list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, command_text, response_text, sources_json, created_at FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "user_id": r[1],
            "command_text": r[2],
            "response_text": r[3],
            "sources": json.loads(r[4]) if r[4] else [],
            "created_at": r[5]
        })
    return result

# initialize DB on module import (idempotent)
init_db()
