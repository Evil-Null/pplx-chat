import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import Message, Role, Session

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Database operation failed."""
    pass


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(str(db_path))
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.row_factory = sqlite3.Row
            self._create_tables()
        except sqlite3.Error as e:
            logger.exception("Failed to initialize database")
            raise DatabaseError(f"Cannot open database: {e}") from e

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT 'sonar',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                total_cost REAL NOT NULL DEFAULT 0.0,
                total_tokens INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                usage_json TEXT DEFAULT '{}',
                cost_json TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
        """)
        self.conn.commit()

    def create_session(self, model: str, name: str = "") -> int:
        now = datetime.now().isoformat()
        try:
            cursor = self.conn.execute(
                "INSERT INTO sessions (name, model, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (name, model, now, now),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.exception("Failed to create session")
            raise DatabaseError(f"Cannot create session: {e}") from e

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        citations: list[str] | None = None,
        usage_json: str = "{}",
        cost_json: str = "{}",
    ) -> int:
        """Add a message and return its row ID."""
        now = datetime.now().isoformat()
        try:
            cursor = self.conn.execute(
                """INSERT INTO messages
                   (session_id, role, content, timestamp, citations, usage_json, cost_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, role, content, now, json.dumps(citations or []), usage_json, cost_json),
            )
            self.conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.exception("Failed to add message")
            raise DatabaseError(f"Cannot save message: {e}") from e

    def delete_last_message(self, session_id: int) -> bool:
        """Delete the most recent message in a session. Used for rollback on API failure."""
        try:
            cursor = self.conn.execute(
                """DELETE FROM messages WHERE id = (
                    SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1
                )""",
                (session_id,),
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.exception("Failed to delete last message")
            return False

    def update_session_cost(self, session_id: int, cost: float, tokens: int):
        try:
            self.conn.execute(
                """UPDATE sessions
                   SET total_cost = total_cost + ?, total_tokens = total_tokens + ?
                   WHERE id = ?""",
                (cost, tokens, session_id),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.exception("Failed to update session cost")

    def get_session(self, session_id: int) -> Session | None:
        try:
            row = self.conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            messages = self._get_messages(session_id)
            return Session(
                id=row["id"],
                name=row["name"],
                model=row["model"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=messages,
                total_cost=row["total_cost"],
                total_tokens=row["total_tokens"],
            )
        except sqlite3.Error as e:
            logger.exception("Failed to get session")
            return None

    def _get_messages(self, session_id: int) -> list[Message]:
        rows = self.conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [
            Message(
                role=Role(r["role"]),
                content=r["content"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]

    def list_sessions(self, limit: int = 20) -> list[dict]:
        try:
            rows = self.conn.execute(
                """SELECT id, name, model, created_at, updated_at, total_cost, total_tokens,
                          (SELECT COUNT(*) FROM messages WHERE session_id = sessions.id) as msg_count
                   FROM sessions ORDER BY updated_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            logger.exception("Failed to list sessions")
            return []

    def delete_session(self, session_id: int) -> bool:
        try:
            cursor = self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.exception("Failed to delete session")
            return False

    def rename_session(self, session_id: int, name: str):
        try:
            self.conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.exception("Failed to rename session")

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass
