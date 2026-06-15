"""Persistent ``Storage`` backend backed by SQLite.

Stores timer state in a ``timers`` table keyed by ``(session_id, timer_id)``.
Each timer is serialised to a JSON blob for schema-free evolution.

Usage::

    from cuqui.adapters.storage_sqlite import SqliteTimerStore

    store = SqliteTimerStore("data/cuqui.db")
    store.save("session-1", {timer.id: timer})
    timers = store.load("session-1")
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from cuqui.domain.timer import Timer, TimerStatus

__all__ = [
    "SqliteTimerStore",
]


def _timer_to_row(timer: Timer) -> dict[str, Any]:
    return {
        "id": timer.id,
        "name": timer.name,
        "duration": timer.duration,
        "remaining": timer.remaining,
        "status": timer.status.value,
        "created_at": timer.created_at.isoformat(),
        "completed_at": timer.completed_at.isoformat() if timer.completed_at else None,
    }


def _row_to_timer(data: dict[str, Any]) -> Timer:
    return Timer(
        id=data["id"],
        name=data["name"],
        duration=data["duration"],
        remaining=data["remaining"],
        status=TimerStatus(data["status"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
    )


class SqliteTimerStore:
    """SQLite-persisted store for timer state and API keys per session.

    Creates the ``timers`` and ``api_keys`` tables on first use.  Single-file,
    no external dependencies beyond Python's stdlib ``sqlite3`` module.

    Thread-safety is **not** guaranteed — this adapter assumes
    single-process, single-event-loop usage (the same as
    ``InMemoryTimerStore``).
    """

    def __init__(self, db_path: str = "cuqui.db") -> None:
        self._db_path = db_path
        parent = Path(db_path).parent
        if parent != Path("."):
            parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS timers (
                session_id TEXT NOT NULL,
                timer_id   TEXT NOT NULL,
                data       TEXT NOT NULL,
                PRIMARY KEY (session_id, timer_id)
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS api_keys (
                session_id TEXT PRIMARY KEY,
                api_key    TEXT NOT NULL
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS push_subscriptions (
                session_id TEXT NOT NULL,
                endpoint   TEXT NOT NULL,
                auth       TEXT NOT NULL,
                p256dh     TEXT NOT NULL,
                PRIMARY KEY (session_id, endpoint)
            )"""
        )
        self._conn.commit()

    def load(self, session_id: str) -> dict[str, Timer]:
        cursor = self._conn.execute(
            "SELECT data FROM timers WHERE session_id = ?",
            (session_id,),
        )
        timers: dict[str, Timer] = {}
        for (json_data,) in cursor:
            data = json.loads(json_data)
            timer = _row_to_timer(data)
            timers[timer.id] = timer
        return timers

    def save(self, session_id: str, timers: dict[str, Timer]) -> None:
        self._conn.execute(
            "DELETE FROM timers WHERE session_id = ?",
            (session_id,),
        )
        for timer in timers.values():
            self._conn.execute(
                "INSERT INTO timers (session_id, timer_id, data) VALUES (?, ?, ?)",
                (session_id, timer.id, json.dumps(_timer_to_row(timer))),
            )
        self._conn.commit()

    def save_api_key(self, session_id: str, api_key: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO api_keys (session_id, api_key) VALUES (?, ?)",
            (session_id, api_key),
        )
        self._conn.commit()

    def get_api_key(self, session_id: str) -> str | None:
        cursor = self._conn.execute(
            "SELECT api_key FROM api_keys WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def save_push_subscription(self, session_id: str, endpoint: str, auth: str, p256dh: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO push_subscriptions (session_id, endpoint, auth, p256dh) VALUES (?, ?, ?, ?)",
            (session_id, endpoint, auth, p256dh),
        )
        self._conn.commit()

    def remove_push_subscription(self, session_id: str, endpoint: str) -> None:
        self._conn.execute(
            "DELETE FROM push_subscriptions WHERE session_id = ? AND endpoint = ?",
            (session_id, endpoint),
        )
        self._conn.commit()

    def load_push_subscriptions(self, session_id: str) -> list[dict[str, str]]:
        cursor = self._conn.execute(
            "SELECT endpoint, auth, p256dh FROM push_subscriptions WHERE session_id = ?",
            (session_id,),
        )
        return [
            {"endpoint": row[0], "auth": row[1], "p256dh": row[2]}
            for row in cursor
        ]

    def list_sessions(self) -> list[str]:
        cursor = self._conn.execute("SELECT DISTINCT session_id FROM timers")
        return [row[0] for row in cursor]
