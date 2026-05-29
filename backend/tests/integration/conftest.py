"""Integration test fixtures — full-stack FastAPI with real dependencies.

Provides:
- ``timer_manager`` — new ``TimerManager()``
- ``sync_service``   — new ``SyncService()``
- ``intent_parser``  — ``TimerParserAdapter(lang="es")``
- ``app``            — ``FastAPI`` with test dependencies injected
- ``client``         — ``TestClient(app)``
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


@pytest.fixture
def timer_manager() -> TimerManager:
    """Return a fresh ``TimerManager`` per test."""
    return TimerManager()


@pytest.fixture
def sync_service() -> SyncService:
    """Return a fresh ``SyncService`` per test."""
    return SyncService()


@pytest.fixture
def intent_parser() -> TimerParserAdapter:
    """Return a Spanish ``TimerParserAdapter`` per test."""
    return TimerParserAdapter(lang="es")


@pytest.fixture
def app(
    timer_manager: TimerManager,
    intent_parser: TimerParserAdapter,
    sync_service: SyncService,
) -> FastAPI:
    """Build a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_timer_manager] = lambda: timer_manager
    app.dependency_overrides[get_intent_parser] = lambda: intent_parser
    app.dependency_overrides[get_sync_service] = lambda: sync_service
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a ``TestClient`` bound to the test ``app``."""
    return TestClient(app)
