"""In-memory implementation of the ``Storage`` protocol.

Stores timer state in a ``dict[str, dict[str, Timer]]`` keyed by
session ID.  Data is lost on process restart — acceptable for MVP.

Usage::

    from cuqui.adapters.storage_memory.adapter import InMemoryTimerStore

    store = InMemoryTimerStore()
    store.save("session-1", {timer.id: timer})
    timers = store.load("session-1")
"""

from __future__ import annotations

from cuqui.domain.timer import Timer

__all__ = [
    "InMemoryTimerStore",
]


class InMemoryTimerStore:
    """Dict-backed store for timer state per session.

    Thread-safety is **not** guaranteed — this is an MVP reference
    implementation intended for single-process, single-event-loop use.
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Timer]] = {}

    def load(self, session_id: str) -> dict[str, Timer]:
        """Return all timers for *session_id* (empty dict if unknown)."""
        return dict(self._data.get(session_id, {}))

    def save(self, session_id: str, timers: dict[str, Timer]) -> None:
        """Persist *timers* dict for *session_id*."""
        self._data[session_id] = dict(timers)

    def list_sessions(self) -> list[str]:
        """Return all session IDs that have stored data."""
        return list(self._data.keys())
