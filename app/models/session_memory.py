from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
from threading import Lock
from uuid import uuid4

from app.core.config import get_settings


@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str


@dataclass(slots=True)
class ConversationSession:
    session_id: str
    summary: str = ""
    turns: list[ConversationTurn] = field(default_factory=list)


class SessionMemoryStore:
    """Session store backed by SQLite persistence."""

    def __init__(self, max_turns: int = 6, storage_path: str | None = None) -> None:
        self.max_turns = max_turns
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = Lock()
        self.storage_path = Path(storage_path or get_settings().session_store_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
        self._load()

    def get_or_create(self, session_id: str | None) -> ConversationSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]

            new_session_id = session_id or f"session-{uuid4().hex[:10]}"
            session = ConversationSession(session_id=new_session_id)
            self._sessions[new_session_id] = session
            self._persist_session(session)
            return session

    def append_turn(self, session_id: str, role: str, content: str) -> ConversationSession:
        with self._lock:
            session = self._sessions[session_id]
            session.turns.append(ConversationTurn(role=role, content=content.strip()))
            session.turns = session.turns[-self.max_turns :]
            session.summary = self._build_summary(session.turns)
            self._persist_session(session)
            return session

    def get_session(self, session_id: str) -> ConversationSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def _build_summary(self, turns: list[ConversationTurn]) -> str:
        if not turns:
            return ""

        summary_parts = [f"{turn.role}: {turn.content[:120]}" for turn in turns[-4:]]
        return " | ".join(summary_parts)

    def _initialize_db(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
                """
            )
            connection.commit()

    def _persist_session(self, session: ConversationSession) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            connection.execute(
                """
                INSERT INTO sessions(session_id, summary)
                VALUES(?, ?)
                ON CONFLICT(session_id) DO UPDATE SET summary = excluded.summary
                """,
                (session.session_id, session.summary),
            )
            connection.execute("DELETE FROM turns WHERE session_id = ?", (session.session_id,))
            connection.executemany(
                """
                INSERT INTO turns(session_id, turn_index, role, content)
                VALUES(?, ?, ?, ?)
                """,
                [
                    (session.session_id, index, turn.role, turn.content)
                    for index, turn in enumerate(session.turns)
                ],
            )
            connection.commit()

    def _load(self) -> None:
        with sqlite3.connect(self.storage_path) as connection:
            session_rows = connection.execute(
                "SELECT session_id, summary FROM sessions"
            ).fetchall()

            for session_id, summary in session_rows:
                turn_rows = connection.execute(
                    """
                    SELECT role, content
                    FROM turns
                    WHERE session_id = ?
                    ORDER BY turn_index ASC
                    """,
                    (session_id,),
                ).fetchall()
                turns = [
                    ConversationTurn(role=role, content=content)
                    for role, content in turn_rows
                ]
                self._sessions[session_id] = ConversationSession(
                    session_id=session_id,
                    summary=summary,
                    turns=turns,
                )


session_memory_store = SessionMemoryStore()
