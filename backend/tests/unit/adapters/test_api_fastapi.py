"""Tests for FastAPI REST and WebSocket endpoints.

Covers:
- POST /commands/text: 200 on success, 400 on parse error, 422 on domain error
- POST /commands/text: 422 on missing session_id
- GET /timers: 200 with timers array
- GET /timers: 200 with empty array for unknown session
- GET /timers: 422 on missing session_id
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
        assert data["status"] == "pending"
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
        # Create a pending timer
        resp = self.client.post(
            "/commands/text",
            json={"text": "set 1 minute timer for pasta", "session_id": "abc"},
        )
        assert resp.status_code == 200

        # Try to pause it — PENDING cannot pause, domain error
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
        assert data[0]["status"] == "pending"

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
