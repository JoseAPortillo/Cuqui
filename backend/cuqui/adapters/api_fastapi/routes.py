"""FastAPI REST and WebSocket routes for the Cuqui timer API.

Provides three public endpoints:

* ``POST /commands/text`` — accept natural-language text, route through
  the application layer, return and broadcast the result.
* ``GET  /timers`` — return all timers for a session as a JSON array.
* ``WS   /ws/session/{session_id}`` — real-time state broadcast channel.

Lifespan
--------
The ``lifespan()`` context manager creates and wires the three
application-layer singletons (``TimerManager``, ``SyncService``,
``IntentParser``) into ``app.state``.  Endpoints retrieve them via the
``Depends()`` functions in ``dependencies.py``.

Error handling
--------------
* ``ParseError`` → HTTP 400 with ``ParseErrorResponse`` payload.
* ``ValueError`` (domain) → HTTP 422 with ``DomainErrorResponse`` payload.
* All other exceptions → HTTP 500 with a generic error message.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from cuqui.application.manage_timers import TimerManager
from cuqui.application.process_command import process_command
from cuqui.application.sync_state import SyncService
from cuqui.ports.intent_parser import IntentParser
from cuqui.domain.commands import CuquiCommand
from cuqui.domain.parser import ParseError
from cuqui.domain.timer import Timer

from cuqui.adapters.api_fastapi.dependencies import (
    get_intent_parser,
    get_sync_service,
    get_timer_manager,
)
from cuqui.adapters.api_fastapi.schemas import (
    CommandRequest,
    DomainErrorResponse,
    ParseErrorResponse,
    TimerResponse,
)

__all__ = [
    "create_app",
    "router",
]

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────────


def _timer_to_dict(timer: Timer) -> dict[str, Any]:
    """Convert a domain ``Timer`` to a JSON-compatible dictionary.

    The output matches ``TimerResponse`` model structure so FastAPI
    can validate or document the response.
    """
    return {
        "id": timer.id,
        "name": timer.name,
        "duration": timer.duration,
        "remaining": timer.remaining,
        "status": timer.status.value,
        "created_at": timer.created_at.isoformat(),
    }


# ── POST /commands/text ───────────────────────────────────────────────────────


@router.post(
    "/commands/text",
    responses={
        200: {"model": TimerResponse, "description": "Timer state"},
        400: {"model": ParseErrorResponse, "description": "Parse failure"},
        422: {"model": DomainErrorResponse, "description": "Domain error"},
    },
)
async def post_command(
    body: CommandRequest,
    timer_manager: TimerManager = Depends(get_timer_manager),
    intent_parser: IntentParser = Depends(get_intent_parser),
    sync_service: SyncService = Depends(get_sync_service),
) -> Any:
    """Accept natural-language *text*, execute the command, broadcast state.

    Steps
    -----
    1. Parse *text* via ``IntentParser``.
    2. Route via ``process_command`` → ``TimerManager``.
    3. Convert result to a JSON dict.
    4. Broadcast the full session state to all connected WS clients.
    5. Return the result (timer dict, timer dict map, or success marker).
    """
    # 1. Parse
    parsed = intent_parser.parse(body.text)
    if isinstance(parsed, ParseError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "parse_error",
                "message": parsed.message,
                "original_text": parsed.original_text,
            },
        )

    # 2. Execute
    try:
        result = process_command(timer_manager, body.session_id, parsed)
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "domain_error", "message": str(exc)},
        )

    # 3. Build response data
    response_data: Any
    if isinstance(result, Timer):
        response_data = _timer_to_dict(result)
    elif isinstance(result, dict):
        response_data = {tid: _timer_to_dict(t) for tid, t in result.items()}
    else:
        response_data = {"status": "ok"}

    # 4. Broadcast full session state
    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(body.session_id).items()
    }
    sync_service.broadcast(body.session_id, {"timers": full_state})

    return response_data


# ── GET /timers ───────────────────────────────────────────────────────────────


@router.get(
    "/timers",
    responses={
        200: {
            "model": list[TimerResponse],
            "description": "Array of timer states (empty if session unknown)",
        },
    },
)
async def get_timers(
    session_id: str = Query(..., description="Session identifier"),
    timer_manager: TimerManager = Depends(get_timer_manager),
) -> list[dict[str, Any]]:
    """Return all timers for *session_id* as a JSON array.

    Unknown sessions return an empty array (never an error).
    """
    timers = timer_manager.get_all_timers(session_id)
    return [_timer_to_dict(t) for t in timers.values()]


# ── WS /ws/session/{session_id} ───────────────────────────────────────────────


@router.websocket("/ws/session/{session_id}")
async def ws_session(
    websocket: WebSocket,
    session_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> None:
    """Real-time channel for *session_id* state broadcasts.

    On connect the client is registered with ``SyncService``.  The
    server does **not** require incoming messages — it only broadcasts
    state on timer mutations.  Disconnect is handled gracefully.
    """
    await websocket.accept()
    sync_service.register(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        sync_service.unregister(websocket)


# ── Lifespan & App factory ────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and wire application-layer singletons.

    Runs once at startup — stores ``TimerManager``, ``SyncService``,
    and ``IntentParser`` in ``app.state`` so that ``Depends()``
    functions in ``dependencies.py`` can retrieve them.
    """
    from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

    app.state.timer_manager = TimerManager()
    app.state.sync_service = SyncService()
    app.state.intent_parser = TimerParserAdapter(lang="es")
    yield


def create_app() -> FastAPI:
    """Build a fully-wired ``FastAPI`` application.

    Includes the ``lifespan`` context manager and the ``router``.
    This is the production entry point; tests typically bypass it
    and use ``app.dependency_overrides`` instead.
    """
    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app
