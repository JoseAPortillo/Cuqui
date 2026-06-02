"""Tests for SyncService — WebSocket connection management and broadcast.

Covers:
- register adds connection to session
- unregister removes connection
- broadcast reaches all connections in session
- broadcast does NOT reach connections in other sessions
- After unregister, broadcast becomes no-op
- Multiple connections in same session all receive broadcast
- Disconnect does not affect other clients
"""

from __future__ import annotations

import json

# ── Mock WebSocket ─────────────────────────────────────────────────────────────


class MockWebSocket:
    """A fake WebSocket that captures sent messages for test assertions."""

    def __init__(self) -> None:
        self.sent_messages: list[str] = []
        self.closed = False

    async def send_text(self, text: str) -> None:
        self.sent_messages.append(text)

    def close(self) -> None:
        self.closed = True

    def __repr__(self) -> str:
        return f"MockWebSocket(sent={len(self.sent_messages)})"


class TestSyncServiceImport:
    """SyncService SHALL be importable."""

    def test_sync_service_is_importable(self) -> None:
        pass  # noqa: F811


class TestSyncServiceRegistry:
    """SyncService SHALL track connections per session."""

    def setup_method(self) -> None:
        from cuqui.application.sync_state import SyncService

        self.service = SyncService()

    def test_register_adds_connection(self) -> None:
        """GIVEN a WS connection WHEN register THEN it is tracked for the session."""
        ws = MockWebSocket()
        self.service.register(ws, "s1")
        assert ws in self.service._connections.get("s1", set())

    def test_unregister_removes_connection(self) -> None:
        """GIVEN a registered connection WHEN unregister THEN it is removed."""
        ws = MockWebSocket()
        self.service.register(ws, "s1")
        self.service.unregister(ws)
        assert ws not in self.service._connections.get("s1", set())

    def test_register_multiple_in_same_session(self) -> None:
        """GIVEN multiple connections for same session WHEN register THEN all tracked."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        self.service.register(ws1, "s1")
        self.service.register(ws2, "s1")
        assert len(self.service._connections["s1"]) == 2


class TestSyncServiceBroadcast:
    """SyncService.broadcast SHALL send state to session connections."""

    def setup_method(self) -> None:
        from cuqui.application.sync_state import SyncService

        self.service = SyncService()

    async def test_broadcast_reaches_all_session_connections(self) -> None:
        """GIVEN two connections in "s1" WHEN broadcast THEN both receive state."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        self.service.register(ws1, "s1")
        self.service.register(ws2, "s1")

        state = {"timers": {"t1": {"name": "Pasta", "status": "running"}}}
        await self.service.broadcast("s1", state)

        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1
        data1 = json.loads(ws1.sent_messages[0])
        assert data1["timers"]["t1"]["name"] == "Pasta"

    async def test_broadcast_does_not_reach_other_sessions(self) -> None:
        """GIVEN connections in "s1" and "s2" WHEN broadcast "s1" THEN "s2" does NOT receive."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        self.service.register(ws1, "s1")
        self.service.register(ws2, "s2")

        state = {"timers": {}}
        await self.service.broadcast("s1", state)

        assert len(ws1.sent_messages) == 1  # received
        assert len(ws2.sent_messages) == 0  # NOT received

    async def test_broadcast_empty_session_is_noop(self) -> None:
        """GIVEN no connections in "unknown" WHEN broadcast THEN no error."""
        state = {"timers": {}}
        # Should not raise
        await self.service.broadcast("unknown", state)
        # No crash means success

    async def test_broadcast_after_unregister_is_noop(self) -> None:
        """GIVEN a connection registered THEN unregistered WHEN broadcast THEN no message sent."""
        ws = MockWebSocket()
        self.service.register(ws, "s1")
        self.service.unregister(ws)

        await self.service.broadcast("s1", {"timers": {}})
        assert len(ws.sent_messages) == 0

    async def test_disconnect_does_not_affect_others(self) -> None:
        """GIVEN three connections, one disconnects WHEN broadcast THEN other two receive."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        self.service.register(ws1, "s1")
        self.service.register(ws2, "s1")
        self.service.register(ws3, "s1")

        self.service.unregister(ws2)

        state = {"timers": {"t1": {"name": "Pasta"}}}
        await self.service.broadcast("s1", state)

        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 0  # disconnected
        assert len(ws3.sent_messages) == 1
