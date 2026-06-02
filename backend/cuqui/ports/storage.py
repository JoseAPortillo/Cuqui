"""Port — Storage protocol.

Defines the contract for persisting timer state per session.
Any adapter that satisfies this Protocol can be swapped in
(e.g., in-memory dict → SQLite → Redis) without changing the
application layer.

See ``cuqui/adapters/storage_memory/`` for the reference implementation.
"""

from __future__ import annotations

import typing

from cuqui.domain.timer import Timer

__all__ = [
    "Storage",
]


class Storage(typing.Protocol):
    """Persist and retrieve timer state for a session.

    Usage::

        store: Storage = InMemoryTimerStore()
        store.save("session-1", {timer.id: timer})
        timers = store.load("session-1")
    """

    def load(self, session_id: str) -> dict[str, Timer]:
        """Return all timers for *session_id* (empty dict if unknown)."""
        ...

    def save(self, session_id: str, timers: dict[str, Timer]) -> None:
        """Persist *timers* dict for *session_id*."""
        ...

    def list_sessions(self) -> list[str]:
        """Return all session IDs that have stored data."""
        ...
