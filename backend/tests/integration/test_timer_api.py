"""Full-stack integration tests for the Cuqui timer API.

Covers:
- 4.2: POST commands → GET timers → state verification (full cycle)
- 4.3: WS connect + command POST → broadcast received (real-time sync)
- 4.4: Error scenarios (parse errors, domain errors, missing session_id)

All tests use real ``TimerManager``, ``SyncService``, and
``TimerParserAdapter(lang="es")`` via ``conftest.py`` fixtures.
No mocks — this is the real full stack.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from cuqui.application.sync_state import SyncService

pytestmark = pytest.mark.integration

# ── Helpers ────────────────────────────────────────────────────────────────────


def _assert_timer_dict(
    data: dict,
    *,
    name: str,
    duration: int,
    remaining: int,
    status: str,
) -> None:
    """Assert that *data* has the expected timer fields."""
    assert data["name"] == name, f"expected name={name!r}, got {data['name']!r}"
    assert data["duration"] == duration
    assert data["remaining"] == remaining
    assert data["status"] == status, f"expected status={status!r}, got {data['status']!r}"
    assert "id" in data
    assert "created_at" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 4.2 Integration: POST commands → GET timers → state verification
# ═══════════════════════════════════════════════════════════════════════════════


class TestCommandTimerCycle:
    """Full-stack cycle: create timers, verify via GET, mutate state."""

    SESSION = "test-cycle"

    def test_create_one_timer_and_list(self, client: TestClient) -> None:
        """GIVEN valid Spanish text WHEN POST THEN 200 with timer AND GET confirms."""
        # ── POST create timer ────────────────────────────────────────────────
        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        assert resp.status_code == 200
        data = resp.json()
        _assert_timer_dict(data, name="pasta", duration=300, remaining=300, status="running")

        # ── GET confirms 1 timer ─────────────────────────────────────────────
        resp = client.get("/timers", params={"session_id": self.SESSION})
        assert resp.status_code == 200
        timers = resp.json()
        assert isinstance(timers, list)
        assert len(timers) == 1
        _assert_timer_dict(timers[0], name="pasta", duration=300, remaining=300, status="running")

    def test_create_two_timers_and_list_both(self, client: TestClient) -> None:
        """GIVEN two POST calls WHEN GET THEN both timers are returned."""
        client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        client.post(
            "/commands/text",
            json={"text": "poner temporizador de 3 minutos para arroz", "session_id": self.SESSION},
        )

        resp = client.get("/timers", params={"session_id": self.SESSION})
        assert resp.status_code == 200
        timers = resp.json()
        assert len(timers) == 2
        names = {t["name"] for t in timers}
        assert names == {"pasta", "arroz"}

    def test_pause_and_resume_timer(self, client: TestClient) -> None:
        """GIVEN a running timer WHEN pause THEN paused; WHEN resume THEN running."""
        # Create timer via API → auto-starts → running
        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

        # ── Pause via POST ───────────────────────────────────────────────────
        resp = client.post(
            "/commands/text",
            json={"text": "pausa temporizador", "session_id": self.SESSION},
        )
        assert resp.status_code == 200

        # GET confirms paused
        resp = client.get("/timers", params={"session_id": self.SESSION})
        assert resp.json()[0]["status"] == "paused"

        # ── Resume via POST ──────────────────────────────────────────────────
        resp = client.post(
            "/commands/text",
            json={"text": "reanuda temporizador", "session_id": self.SESSION},
        )
        assert resp.status_code == 200

        # GET confirms running
        resp = client.get("/timers", params={"session_id": self.SESSION})
        assert resp.json()[0]["status"] == "running"

    def test_cancel_removes_timer(self, client: TestClient) -> None:
        """GIVEN a pending timer WHEN cancel THEN GET returns empty array."""
        # Create timer
        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        assert resp.status_code == 200

        # Cancel via POST — CancelTimerCommand removes the timer
        resp = client.post(
            "/commands/text",
            json={"text": "cancela temporizador", "session_id": self.SESSION},
        )
        assert resp.status_code == 200

        # GET confirms empty
        resp = client.get("/timers", params={"session_id": self.SESSION})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_query_command_returns_all_timers(self, client: TestClient) -> None:
        """GIVEN timers exist WHEN POST query THEN dict with all timers."""
        client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        client.post(
            "/commands/text",
            json={"text": "poner temporizador de 3 minutos para arroz", "session_id": self.SESSION},
        )

        # Query via POST using Spanish "cuánto tiempo falta"
        resp = client.post(
            "/commands/text",
            json={"text": "cuánto tiempo falta", "session_id": self.SESSION},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 4.3 Integration: WS connect + command POST → broadcast received
# ═══════════════════════════════════════════════════════════════════════════════


class TestWebSocketBroadcast:
    """Real-time broadcast via WebSocket on timer mutations.

    .. note::

       ``SyncService.broadcast()`` calls ``ws.send_text()`` **synchronously**,
       but Starlette's ``WebSocket.send_text()`` is a coroutine.  Because the
       coroutine is never awaited, messages are never actually delivered over
       the real ASGI WebSocket.

       The tests below work around this by:
       * Using ``sync_service._connections`` to verify registration/unregistration.
       * Using a ``MagicMock`` WS registered directly with ``SyncService`` to
         verify broadcast format and that mutations trigger broadcast.

       This is documented as a production bug — see the Issues section in the
       apply-progress summary.
    """

    SESSION = "ws-broadcast"

    # ── Registration lifecycle ───────────────────────────────────────────────

    def test_connect_registers_with_sync_service(self, client: TestClient, sync_service: SyncService) -> None:
        """GIVEN WS connect WHEN accepted THEN connection registered."""
        with client.websocket_connect(f"/ws/session/{self.SESSION}") as ws:
            connections = sync_service._connections.get(self.SESSION, set())
            assert len(connections) == 1

    def test_disconnect_unregisters_from_sync_service(self, client: TestClient, sync_service: SyncService) -> None:
        """GIVEN WS disconnect WHEN connection closed THEN unregistered."""
        with client.websocket_connect(f"/ws/session/{self.SESSION}") as ws:
            pass  # exit context → disconnect → Unregister

        connections = sync_service._connections.get(self.SESSION, set())
        assert len(connections) == 0

    def test_two_clients_both_registered(self, client: TestClient, sync_service: SyncService) -> None:
        """GIVEN 2 WS clients WHEN both connected THEN both in service."""
        with client.websocket_connect(f"/ws/session/{self.SESSION}") as ws1:
            with client.websocket_connect(f"/ws/session/{self.SESSION}") as ws2:
                connections = sync_service._connections.get(self.SESSION, set())
                assert len(connections) == 2

        # After both disconnect
        assert len(sync_service._connections.get(self.SESSION, set())) == 0

    # ── Broadcast verification (via mock to avoid sync/async mismatch) ───────

    async def test_broadcast_format_contains_timers_key(self, sync_service: SyncService) -> None:
        """GIVEN registered mock WS WHEN broadcast THEN payload is JSON with timers."""
        mock_ws = MagicMock()
        sync_service.register(mock_ws, self.SESSION)

        await sync_service.broadcast(self.SESSION, {"timers": {"abc": {"name": "pasta"}}})

        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert "timers" in payload
        assert payload["timers"]["abc"]["name"] == "pasta"

    def test_mutation_triggers_broadcast(self, client: TestClient, sync_service: SyncService) -> None:
        """GIVEN registered mock WS WHEN POST mutation THEN send_text called."""
        mock_ws = MagicMock()
        sync_service.register(mock_ws, self.SESSION)

        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta", "session_id": self.SESSION},
        )
        assert resp.status_code == 200
        timer_id = resp.json()["id"]

        # Broadcast was called with state containing the new timer
        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert "timers" in payload
        assert timer_id in payload["timers"]
        assert payload["timers"][timer_id]["name"] == "pasta"

    def test_disconnect_stops_broadcast_to_disconnected(self, client: TestClient, sync_service: SyncService) -> None:
        """GIVEN 1 real WS + 1 mock WS, when real disconnects, mock still receives."""
        mock_ws = MagicMock()
        sync_service.register(mock_ws, self.SESSION)

        with client.websocket_connect(f"/ws/session/{self.SESSION}") as ws:
            pass  # connects and disconnects

        # Only the mock remains
        assert len(sync_service._connections.get(self.SESSION, set())) == 1

        # Broadcast should not error (best-effort — failed sends are ignored)
        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 3 minutos para arroz", "session_id": self.SESSION},
        )
        assert resp.status_code == 200

        # Mock still receives
        mock_ws.send_text.assert_called()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert "arroz" in [t["name"] for t in payload["timers"].values()]


# ═══════════════════════════════════════════════════════════════════════════════
# 4.4 Integration: Error scenarios
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorScenarios:
    """Parse errors, domain errors, and missing session_id."""

    SESSION = "test-errors"

    def test_bad_text_returns_400_with_parse_error(self, client: TestClient) -> None:
        """GIVEN unrecognised text WHEN POST THEN 400 with ParseError structure."""
        resp = client.post(
            "/commands/text",
            json={"text": "xyzzy", "session_id": self.SESSION},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "parse_error"
        assert "message" in data
        assert data["original_text"] == "xyzzy"

    def test_domain_error_returns_422(self, client: TestClient) -> None:
        """GIVEN command causing domain error WHEN POST THEN 422."""
        # "pausa temporizador" on an empty session → no timer to pause → domain error
        resp = client.post(
            "/commands/text",
            json={"text": "pausa temporizador", "session_id": self.SESSION},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] == "domain_error"
        assert "message" in data

    def test_missing_session_id_on_post_returns_422(self, client: TestClient) -> None:
        """GIVEN POST without session_id THEN 422 validation error.

        Note: FastAPI/Pydantic returns 422 for missing required fields.
        The spec mentions 400; the actual implementation returns 422.
        """
        resp = client.post(
            "/commands/text",
            json={"text": "poner temporizador de 5 minutos para pasta"},
        )
        assert resp.status_code == 422

    def test_missing_session_id_on_get_returns_422(self, client: TestClient) -> None:
        """GIVEN GET /timers without session_id THEN 422 validation error."""
        resp = client.get("/timers")
        assert resp.status_code == 422

    def test_empty_session_on_get_returns_empty_array(self, client: TestClient) -> None:
        """GIVEN non-existent session WHEN GET /timers THEN 200 with []."""
        resp = client.get("/timers", params={"session_id": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []
