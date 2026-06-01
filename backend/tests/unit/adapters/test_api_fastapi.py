"""Tests for FastAPI REST and WebSocket endpoints.

Covers:
- POST /commands/text: 200 on success, 400 on parse error, 422 on domain error
- POST /commands/text: 422 on missing session_id
- GET /timers: 200 with timers array
- GET /timers: 200 with empty array for unknown session
- GET /timers: 422 on missing session_id
- POST /timers/{timer_id}/pause: 200 on pause, 404 unknown timer, 422 on invalid state
- POST /timers/{timer_id}/resume: 200 on resume, 404 unknown timer, 422 on invalid state
- POST /timers/{timer_id}/cancel: 200 on cancel, 404 unknown timer
- WS /ws/session/{session_id}: connect successfully
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cuqui.application.manage_timers import TimerManager
from cuqui.application.sync_state import SyncService
from cuqui.adapters.parser_rules.adapter import TimerParserAdapter
from cuqui.adapters.api_fastapi.dependencies import (
    get_intent_parser,
    get_sync_service,
    get_timer_manager,
)
from cuqui.adapters.api_fastapi.routes import router


class TestApiRoutesImport:
    """API routes SHALL be importable."""

    def test_router_is_importable(self) -> None:
        """GIVEN the router module WHEN importing it THEN no error."""
        assert router is not None
        assert isinstance(router, type(router))


class TestApiRoutes:
    """FastAPI REST and WebSocket endpoints."""

    def setup_method(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)

        self.timer_manager = TimerManager()
        self.sync_service = SyncService()
        self.parser = TimerParserAdapter(lang="en")

        self.app.dependency_overrides[get_timer_manager] = lambda: self.timer_manager
        self.app.dependency_overrides[get_sync_service] = lambda: self.sync_service
        self.app.dependency_overrides[get_intent_parser] = lambda: self.parser

        self.client = TestClient(self.app)

    # ── POST /commands/text ─────────────────────────────────────────────────

    def test_post_command_valid_creates_timer(self) -> None:
        """GIVEN valid text WHEN POST /commands/text THEN 200 with timer state."""
        response = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "pasta"
        assert data["duration"] == 300
        assert data["remaining"] == 300
        assert data["status"] == "running"
        assert "created_at" in data

    def test_post_command_parse_error_returns_400(self) -> None:
        """GIVEN malformed text WHEN POST /commands/text THEN 400 with parse error."""
        response = self.client.post(
            "/commands/text",
            json={"text": "xyzzy", "session_id": "abc"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"] == "parse_error"
        assert "message" in data
        assert "original_text" in data

    def test_post_command_domain_error_returns_422(self) -> None:
        """GIVEN command causing domain error WHEN POST THEN 422 with domain error."""
        # Create timer — auto-starts → running
        resp = self.client.post(
            "/commands/text",
            json={"text": "set 1 minute timer for pasta", "session_id": "abc"},
        )
        assert resp.status_code == 200

        # Pause first — works because timer is running
        resp = self.client.post(
            "/commands/text",
            json={"text": "pause timer for pasta", "session_id": "abc"},
        )
        assert resp.status_code == 200

        # Try to pause again — already paused → domain error
        resp = self.client.post(
            "/commands/text",
            json={"text": "pause timer for pasta", "session_id": "abc"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"] == "domain_error"
        assert "message" in data

    def test_post_command_missing_session_id_returns_422(self) -> None:
        """GIVEN request without session_id WHEN POST THEN 422 validation error."""
        response = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta"},
        )
        assert response.status_code == 422

    # ── GET /timers ─────────────────────────────────────────────────────────

    def test_get_timers_returns_timer_array(self) -> None:
        """GIVEN session with timers WHEN GET /timers THEN 200 with timer array."""
        self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        response = self.client.get("/timers", params={"session_id": "abc"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "pasta"
        assert data[0]["status"] == "running"

    def test_get_timers_unknown_session_returns_empty(self) -> None:
        """GIVEN non-existent session WHEN GET /timers THEN 200 with empty array."""
        response = self.client.get("/timers", params={"session_id": "nonexistent"})
        assert response.status_code == 200
        assert response.json() == []

    def test_get_timers_missing_session_id_returns_422(self) -> None:
        """GIVEN no session_id WHEN GET /timers THEN 422."""
        response = self.client.get("/timers")
        assert response.status_code == 422

    def test_post_command_query_returns_all(self) -> None:
        """GIVEN two timers in session WHEN POST query command THEN dict with both."""
        # Create two timers
        self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        self.client.post(
            "/commands/text",
            json={"text": "set 10 minute timer for rice", "session_id": "abc"},
        )
        # Query timers
        response = self.client.post(
            "/commands/text",
            json={"text": "how much time left", "session_id": "abc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) >= 2

    def test_get_timers_with_two_timers_returns_both(self) -> None:
        """GIVEN two timers WHEN GET /timers THEN array with both."""
        self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        self.client.post(
            "/commands/text",
            json={"text": "set 10 minute timer for rice", "session_id": "abc"},
        )
        response = self.client.get("/timers", params={"session_id": "abc"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [t["name"] for t in data]
        assert "pasta" in names
        assert "rice" in names

    # ── WS /ws/session/{session_id} ─────────────────────────────────────────

    def test_ws_connect_establishes_connection(self) -> None:
        """GIVEN valid session_id WHEN WS connect THEN accepted without error."""
        with self.client.websocket_connect("/ws/session/abc") as websocket:
            assert websocket is not None

    def test_ws_disconnect_does_not_raise(self) -> None:
        """GIVEN connected WS WHEN disconnected THEN no error."""
        with self.client.websocket_connect("/ws/session/abc") as websocket:
            pass  # exiting the context manager disconnects gracefully

    # ── POST /timers/{timer_id}/pause ───────────────────────────────────────────


    def test_pause_timer_returns_200_and_paused(self) -> None:
        """GIVEN running timer WHEN POST /timers/{id}/pause THEN 200 with paused status."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        assert create.status_code == 200
        timer_id = create.json()["id"]

        response = self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["id"] == timer_id
        assert data["name"] == "pasta"

    def test_pause_unknown_timer_returns_404(self) -> None:
        """GIVEN non-existent timer_id WHEN POST /timers/{id}/pause THEN 404."""
        response = self.client.post(
            "/timers/nonexistent/pause",
            json={"session_id": "abc"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"

    def test_pause_already_paused_timer_returns_422(self) -> None:
        """GIVEN paused timer WHEN POST /timers/{id}/pause THEN 422 domain error."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        # Pause first
        pause = self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )
        assert pause.status_code == 200

        # Pause again → invalid transition
        response = self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )
        assert response.status_code == 422
        assert response.json()["error"] == "domain_error"

    def test_pause_missing_session_id_returns_422(self) -> None:
        """GIVEN no session_id in body WHEN POST /timers/{id}/pause THEN 422."""
        response = self.client.post(
            "/timers/some-id/pause",
            json={},
        )
        assert response.status_code == 422

    # ── POST /timers/{timer_id}/resume ──────────────────────────────────────────


    def test_resume_timer_returns_200_and_running(self) -> None:
        """GIVEN paused timer WHEN POST /timers/{id}/resume THEN 200 with running status."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        # Pause first
        self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )

        # Resume
        response = self.client.post(
            f"/timers/{timer_id}/resume",
            json={"session_id": "abc"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["id"] == timer_id

    def test_resume_unknown_timer_returns_404(self) -> None:
        """GIVEN non-existent timer_id WHEN POST /timers/{id}/resume THEN 404."""
        response = self.client.post(
            "/timers/nonexistent/resume",
            json={"session_id": "abc"},
        )
        assert response.status_code == 404
        assert response.json()["error"] == "not_found"

    def test_resume_running_timer_returns_422(self) -> None:
        """GIVEN running timer WHEN POST /timers/{id}/resume THEN 422 domain error."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        # Resume a running timer → invalid transition
        response = self.client.post(
            f"/timers/{timer_id}/resume",
            json={"session_id": "abc"},
        )
        assert response.status_code == 422
        assert response.json()["error"] == "domain_error"

    # ── POST /timers/{timer_id}/cancel ──────────────────────────────────────────


    def test_cancel_timer_returns_200_and_cancelled(self) -> None:
        """GIVEN running timer WHEN POST /timers/{id}/cancel THEN 200 with cancelled status."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        response = self.client.post(
            f"/timers/{timer_id}/cancel",
            json={"session_id": "abc"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert response.json()["id"] == timer_id

    def test_cancel_unknown_timer_returns_404(self) -> None:
        """GIVEN non-existent timer_id WHEN POST /timers/{id}/cancel THEN 404."""
        response = self.client.post(
            "/timers/nonexistent/cancel",
            json={"session_id": "abc"},
        )
        assert response.status_code == 404
        assert response.json()["error"] == "not_found"

    def test_cancel_paused_timer_returns_200(self) -> None:
        """GIVEN paused timer WHEN POST /timers/{id}/cancel THEN 200 (cancel is a no-op on paused)."""
        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        # Pause first
        self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )

        # Cancel from paused → valid transition
        response = self.client.post(
            f"/timers/{timer_id}/cancel",
            json={"session_id": "abc"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    # ── POST /timers/{timer_id}/* — WS broadcast ──────────────────────────────


    def test_pause_broadcasts_via_websocket(self) -> None:
        """GIVEN running timer WHEN pause via REST THEN WS receives state broadcast."""
        from unittest.mock import MagicMock
        import json

        mock_ws = MagicMock()
        self.sync_service.register(mock_ws, "abc")

        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]
        mock_ws.reset_mock()

        self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )

        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert "timers" in payload
        assert timer_id in payload["timers"]
        assert payload["timers"][timer_id]["status"] == "paused"

    def test_resume_broadcasts_via_websocket(self) -> None:
        """GIVEN paused timer WHEN resume via REST THEN WS receives state broadcast."""
        from unittest.mock import MagicMock
        import json

        mock_ws = MagicMock()
        self.sync_service.register(mock_ws, "abc")

        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]

        # Pause first
        self.client.post(
            f"/timers/{timer_id}/pause",
            json={"session_id": "abc"},
        )
        mock_ws.reset_mock()

        # Resume
        self.client.post(
            f"/timers/{timer_id}/resume",
            json={"session_id": "abc"},
        )

        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert payload["timers"][timer_id]["status"] == "running"

    def test_cancel_broadcasts_via_websocket(self) -> None:
        """GIVEN running timer WHEN cancel via REST THEN WS receives state broadcast."""
        from unittest.mock import MagicMock
        import json

        mock_ws = MagicMock()
        self.sync_service.register(mock_ws, "abc")

        create = self.client.post(
            "/commands/text",
            json={"text": "set 5 minute timer for pasta", "session_id": "abc"},
        )
        timer_id = create.json()["id"]
        mock_ws.reset_mock()

        self.client.post(
            f"/timers/{timer_id}/cancel",
            json={"session_id": "abc"},
        )

        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert payload["timers"][timer_id]["status"] == "cancelled"
