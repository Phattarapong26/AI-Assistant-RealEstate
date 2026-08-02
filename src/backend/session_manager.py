"""Conversation sessions with durable storage.

Chat history is what makes follow-up questions ("แล้วถูกกว่านี้มีไหม") work,
so it is stored on disk instead of only in memory: a restart of the API must
not wipe an ongoing customer conversation.
"""

import json
import logging
import secrets
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import DATA_DIR, MAX_HISTORY_TURNS

logger = logging.getLogger(__name__)

SESSIONS_PATH = DATA_DIR / "sessions.json"


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._load()

    # --- Persistence --------------------------------------------------------
    def _load(self) -> None:
        try:
            if SESSIONS_PATH.exists():
                self.sessions = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
                logger.info("Loaded %d sessions", len(self.sessions))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Could not load sessions, starting empty: %s", exc)
            self.sessions = {}

    def _save(self) -> None:
        try:
            SESSIONS_PATH.write_text(
                json.dumps(self.sessions, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Could not save sessions: %s", exc)

    # --- Sessions -----------------------------------------------------------
    def ensure_session(self, session_id: Optional[str] = None) -> str:
        with self._lock:
            sid = session_id or f"session_{secrets.token_hex(8)}"
            if sid not in self.sessions:
                now = datetime.utcnow().isoformat()
                self.sessions[sid] = {
                    "session_id": sid,
                    "created_at": now,
                    "last_activity": now,
                    "messages": [],
                }
                self._save()
            return sid

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        properties: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return
            message: Dict[str, Any] = {
                "role": role,
                "content": content,
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
            }
            if properties:
                message["properties"] = properties
            session["messages"].append(message)
            session["last_activity"] = datetime.utcnow().isoformat()
            self._save()

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        return list(session.get("messages", [])) if session else []

    def get_history(self, session_id: str, max_turns: int = MAX_HISTORY_TURNS) -> List[Dict[str, str]]:
        """Recent turns in the {role, content} shape the model expects."""
        messages = self.get_messages(session_id)[-(max_turns * 2) :]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def clean_old_sessions(self, max_age_hours: int = 24 * 30) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0
        with self._lock:
            for sid in list(self.sessions.keys()):
                try:
                    last = datetime.fromisoformat(self.sessions[sid]["last_activity"])
                except (KeyError, ValueError):
                    continue
                if last < cutoff:
                    del self.sessions[sid]
                    removed += 1
            if removed:
                self._save()
        return removed


session_manager = SessionManager()
