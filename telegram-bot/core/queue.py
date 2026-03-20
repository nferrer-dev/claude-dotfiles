"""SQLite message queue and session history."""

import sqlite3
import threading
import time

from config import DB_PATH

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Get thread-local SQLite connection."""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            session_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            response TEXT,
            created_at REAL DEFAULT (unixepoch('now')),
            processed_at REAL
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp REAL DEFAULT (unixepoch('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_queue_session_status
            ON queue(session_name, status);
        CREATE INDEX IF NOT EXISTS idx_history_session
            ON history(session_name, timestamp);
    """)
    conn.commit()


class MessageQueue:
    """FIFO message queue with per-session ordering."""

    def enqueue(self, chat_id: int, text: str, session_name: str) -> int:
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO queue (chat_id, text, session_name) VALUES (?, ?, ?)",
            (chat_id, text, session_name),
        )
        conn.commit()
        return cur.lastrowid

    def dequeue(self, session_name: str) -> dict | None:
        conn = get_conn()
        # Atomic: UPDATE+RETURNING prevents two threads grabbing the same row
        row = conn.execute(
            """UPDATE queue SET status = 'processing', processed_at = ?
               WHERE id = (
                   SELECT id FROM queue
                   WHERE session_name = ? AND status = 'pending'
                   ORDER BY id LIMIT 1
               ) RETURNING *""",
            (time.time(), session_name),
        ).fetchone()
        conn.commit()
        return dict(row) if row else None

    def complete(self, msg_id: int, response: str):
        conn = get_conn()
        conn.execute(
            "UPDATE queue SET status = 'done', response = ?, processed_at = ? WHERE id = ?",
            (response, time.time(), msg_id),
        )
        conn.commit()

    def fail(self, msg_id: int, error: str):
        conn = get_conn()
        conn.execute(
            "UPDATE queue SET status = 'failed', response = ?, processed_at = ? WHERE id = ?",
            (error, time.time(), msg_id),
        )
        conn.commit()

    def pending_count(self, session_name: str) -> int:
        conn = get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM queue WHERE session_name = ? AND status = 'pending'",
            (session_name,),
        ).fetchone()
        return row["cnt"] if row else 0

    def cleanup(self, max_age_days: int = 7) -> int:
        """Delete completed/failed messages older than max_age_days."""
        conn = get_conn()
        cutoff = time.time() - (max_age_days * 86400)
        cur = conn.execute(
            "DELETE FROM queue WHERE status IN ('done', 'failed') AND processed_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount

    def pending_all(self) -> dict[str, int]:
        conn = get_conn()
        rows = conn.execute(
            "SELECT session_name, COUNT(*) as cnt FROM queue WHERE status = 'pending' GROUP BY session_name",
        ).fetchall()
        return {r["session_name"]: r["cnt"] for r in rows}

    def requeue_stale(self, max_age_seconds: float = 600) -> int:
        """Reset messages stuck in 'processing' back to 'pending'.

        Called on startup to recover from crashes. Returns count reset.
        """
        conn = get_conn()
        cutoff = time.time() - max_age_seconds
        cur = conn.execute(
            "UPDATE queue SET status = 'pending', processed_at = NULL "
            "WHERE status = 'processing' AND (processed_at IS NULL OR processed_at < ?)",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount


class SessionHistory:
    """Conversation history per session."""

    def add(self, session_name: str, role: str, text: str):
        conn = get_conn()
        conn.execute(
            "INSERT INTO history (session_name, role, text) VALUES (?, ?, ?)",
            (session_name, role, text),
        )
        conn.commit()

    def recent(self, session_name: str, limit: int = 20) -> list[dict]:
        conn = get_conn()
        rows = conn.execute(
            "SELECT role, text, timestamp FROM history WHERE session_name = ? ORDER BY id DESC LIMIT ?",
            (session_name, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def count(self, session_name: str) -> int:
        conn = get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM history WHERE session_name = ?",
            (session_name,),
        ).fetchone()
        return row["cnt"] if row else 0

    def cleanup(self, max_age_days: int = 30):
        """Delete history entries older than max_age_days."""
        conn = get_conn()
        cutoff = time.time() - (max_age_days * 86400)
        conn.execute("DELETE FROM history WHERE timestamp < ?", (cutoff,))
        conn.commit()
