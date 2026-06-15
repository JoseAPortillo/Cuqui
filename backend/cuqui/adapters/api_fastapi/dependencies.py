"""FastAPI dependency-injection wiring.

Provides three ``Depends()``-compatible callables that retrieve
application-level singletons from ``request.app.state``.  The state is
populated by the ``lifespan`` context manager defined in ``routes.py``.

Usage in endpoints::

    @router.post("/commands/text")
    async def post_command(
        ...,
        timer_manager: TimerManager = Depends(get_timer_manager),
        sync_service: SyncService = Depends(get_sync_service),
        intent_parser: IntentParser = Depends(get_intent_parser),
    ):
        ...

``get_timer_manager``, ``get_sync_service``, and ``get_intent_parser``
are the canonical DI functions for production use.  Tests override them
via ``app.dependency_overrides``.
"""

from __future__ import annotations

from starlette.requests import HTTPConnection

from cuqui.adapters.push_webpush import WebPushAdapter
from cuqui.adapters.storage_sqlite import SqliteTimerStore
from cuqui.application.manage_timers import TimerManager
from cuqui.application.sync_state import SyncService
from cuqui.ports.intent_parser import IntentParser
from cuqui.ports.speech_to_text import SpeechToText

__all__ = [
    "get_intent_parser",
    "get_push_service",
    "get_speech_to_text",
    "get_sync_service",
    "get_timer_manager",
    "get_timer_store",
]


def get_timer_manager(conn: HTTPConnection) -> TimerManager:
    """Return the ``TimerManager`` singleton from app state."""
    return conn.app.state.timer_manager


def get_sync_service(conn: HTTPConnection) -> SyncService:
    """Return the ``SyncService`` singleton from app state."""
    return conn.app.state.sync_service


def get_intent_parser(conn: HTTPConnection) -> IntentParser:
    """Return the ``IntentParser`` singleton from app state."""
    return conn.app.state.intent_parser


def get_speech_to_text(conn: HTTPConnection) -> SpeechToText:
    """Return the ``SpeechToText`` singleton from app state."""
    return conn.app.state.speech_to_text


def get_timer_store(conn: HTTPConnection) -> SqliteTimerStore:
    """Return the ``SqliteTimerStore`` singleton from app state."""
    return conn.app.state.timer_store


def get_push_service(conn: HTTPConnection) -> WebPushAdapter | None:
    """Return the ``WebPushAdapter`` singleton from app state (may be None)."""
    return getattr(conn.app.state, "push_service", None)
