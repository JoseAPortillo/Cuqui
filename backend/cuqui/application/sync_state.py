"""SyncService — WebSocket connection registry and state broadcast.

Tracks per-session WebSocket connections and broadcasts timer state
to all connected clients within a session.  Designed to be called
externally (not injected into TimerManager) so that the broadcast
decision lives at the orchestration layer.
"""

from __future__ import annotations

import inspect
import json
from typing import Any

__all__ = [
    "SyncService",
]

# A "connection" can be any object with a ``send_text(text: str)`` method.
# In production this is a FastAPI WebSocket; in tests it is a mock.
# The signature is intentionally loose to support both sync and async.


class SyncService:
    """Manage WebSocket connections and broadcast state per session.

    Usage::

        service = SyncService()
        service.register(ws, "session-1")
        service.broadcast("session-1", {"timers": {...}})
        service.unregister(ws)
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[Any]] = {}

    def register(self, ws: Any, session_id: str) -> None:
        """Track *ws* connection under *session_id*."""
        self._connections.setdefault(session_id, set()).add(ws)

    def unregister(self, ws: Any) -> None:
        """Remove *ws* from all sessions it was registered in."""
        for conns in self._connections.values():
            conns.discard(ws)

    async def broadcast(self, session_id: str, state: dict[str, Any]) -> None:
        """Send JSON-serialised *state* to all connections in *session_id*.

        Broadcast is best-effort: failed sends are silently ignored.
        Supports both async and sync ``send_text`` callables.
        """
        conns = self._connections.get(session_id)
        if not conns:
            return

        payload = json.dumps(state, default=str)
        is_async = inspect.iscoroutinefunction
        for ws in list(conns):
            try:
                send = ws.send_text
                if is_async(send):
                    await send(payload)
                else:
                    send(payload)
            except Exception:
                pass  # Best-effort: ignore send failures
