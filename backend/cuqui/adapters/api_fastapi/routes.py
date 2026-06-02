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

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, FastAPI, File, Form, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from cuqui.application.manage_timers import TimerManager
from cuqui.application.process_command import process_command
from cuqui.application.sync_state import SyncService
from cuqui.ports.intent_parser import IntentParser
from cuqui.ports.speech_to_text import SpeechToText
from cuqui.domain.commands import CuquiCommand
from cuqui.domain.parser import ParseError
from cuqui.domain.timer import Timer

from cuqui.adapters.api_fastapi.dependencies import (
    get_intent_parser,
    get_speech_to_text,
    get_sync_service,
    get_timer_manager,
)
from cuqui.adapters.api_fastapi.schemas import (
    CommandRequest,
    DomainErrorResponse,
    ParseErrorResponse,
    TimerActionRequest,
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
    await sync_service.broadcast(body.session_id, {"timers": full_state})

    return response_data


# ── POST /commands/audio ─────────────────────────────────────────────────────


@router.post(
    "/commands/audio",
    responses={
        200: {"model": TimerResponse, "description": "Timer state"},
        400: {"description": "Parse or transcription failure"},
        422: {"model": DomainErrorResponse, "description": "Domain error"},
    },
)
async def post_audio_command(
    audio: UploadFile = File(..., description="Audio file (WAV, WebM, etc.)"),
    session_id: str = Form(..., description="Session identifier"),
    timer_manager: TimerManager = Depends(get_timer_manager),
    intent_parser: IntentParser = Depends(get_intent_parser),
    sync_service: SyncService = Depends(get_sync_service),
    speech_to_text: SpeechToText = Depends(get_speech_to_text),
) -> Any:
    """Accept an audio recording, transcribe, parse, and execute.

    Steps
    -----
    1. Read audio bytes from the uploaded file.
    2. Transcribe via ``SpeechToText`` adapter.
    3. Parse the transcribed text via ``IntentParser``.
    4. Route via ``process_command`` → ``TimerManager``.
    5. Broadcast full session state to WS clients.
    6. Return the timer result.
    """
    # 1. Read audio
    audio_bytes = await audio.read()
    if not audio_bytes:
        return JSONResponse(
            status_code=400,
            content={"error": "empty_audio", "message": "No audio data received"},
        )

    # 2. Transcribe
    try:
        text = await speech_to_text.transcribe(audio_bytes, audio.content_type)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": "transcription_failed",
                "message": f"Speech recognition failed: {exc}",
            },
        )

    if not text:
        return JSONResponse(
            status_code=400,
            content={
                "error": "empty_transcription",
                "message": "Speech recognition returned no text",
            },
        )

    # 3. Parse
    parsed = intent_parser.parse(text)
    if isinstance(parsed, ParseError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "parse_error",
                "message": parsed.message,
                "original_text": parsed.original_text,
                "transcribed_text": text,
            },
        )

    # 4. Execute
    try:
        result = process_command(timer_manager, session_id, parsed)
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "domain_error", "message": str(exc)},
        )

    # 5. Build response
    response_data: Any
    if isinstance(result, Timer):
        response_data = _timer_to_dict(result)
    elif isinstance(result, dict):
        response_data = {tid: _timer_to_dict(t) for tid, t in result.items()}
    else:
        response_data = {"status": "ok"}

    # 6. Broadcast
    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(session_id).items()
    }
    await sync_service.broadcast(session_id, {"timers": full_state})

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


# ── POST /timers/{timer_id}/pause ─────────────────────────────────────────────


@router.post(
    "/timers/{timer_id}/pause",
    responses={
        200: {"model": TimerResponse, "description": "Paused timer state"},
        404: {"description": "Timer not found"},
        422: {"model": DomainErrorResponse, "description": "Invalid transition"},
    },
)
async def pause_timer(
    timer_id: str,
    body: TimerActionRequest,
    timer_manager: TimerManager = Depends(get_timer_manager),
    sync_service: SyncService = Depends(get_sync_service),
) -> Any:
    """Pause a running timer, broadcast state, return the updated timer.

    Steps
    -----
    1. Retrieve the timer via ``TimerManager.pause_timer()``.
    2. Catch ``KeyError`` → 404 (timer not found).
    3. Catch ``ValueError`` → 422 (invalid state transition).
    4. Broadcast full session state to all WebSocket clients.
    5. Return the updated timer dict.
    """
    try:
        updated = timer_manager.pause_timer(body.session_id, timer_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": f"Timer {timer_id!r} not found in session {body.session_id!r}",
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "domain_error", "message": str(exc)},
        )

    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(body.session_id).items()
    }
    await sync_service.broadcast(body.session_id, {"timers": full_state})

    return _timer_to_dict(updated)


# ── POST /timers/{timer_id}/resume ────────────────────────────────────────────


@router.post(
    "/timers/{timer_id}/resume",
    responses={
        200: {"model": TimerResponse, "description": "Resumed timer state"},
        404: {"description": "Timer not found"},
        422: {"model": DomainErrorResponse, "description": "Invalid transition"},
    },
)
async def resume_timer(
    timer_id: str,
    body: TimerActionRequest,
    timer_manager: TimerManager = Depends(get_timer_manager),
    sync_service: SyncService = Depends(get_sync_service),
) -> Any:
    """Resume a paused timer, broadcast state, return the updated timer.

    Steps
    -----
    1. Retrieve the timer via ``TimerManager.resume_timer()``.
    2. Catch ``KeyError`` → 404 (timer not found).
    3. Catch ``ValueError`` → 422 (invalid state transition).
    4. Broadcast full session state to all WebSocket clients.
    5. Return the updated timer dict.
    """
    try:
        updated = timer_manager.resume_timer(body.session_id, timer_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": f"Timer {timer_id!r} not found in session {body.session_id!r}",
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "domain_error", "message": str(exc)},
        )

    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(body.session_id).items()
    }
    await sync_service.broadcast(body.session_id, {"timers": full_state})

    return _timer_to_dict(updated)


# ── POST /timers/{timer_id}/cancel ────────────────────────────────────────────


@router.post(
    "/timers/{timer_id}/cancel",
    responses={
        200: {"model": TimerResponse, "description": "Cancelled timer state"},
        404: {"description": "Timer not found"},
        422: {"model": DomainErrorResponse, "description": "Invalid transition"},
    },
)
async def cancel_timer(
    timer_id: str,
    body: TimerActionRequest,
    timer_manager: TimerManager = Depends(get_timer_manager),
    sync_service: SyncService = Depends(get_sync_service),
) -> Any:
    """Cancel an active timer, broadcast state, return the updated timer.

    ``Timer.cancel()`` is a no-op on completed or already-cancelled timers
    (never raises), but we still guard ``ValueError`` for consistency.

    Steps
    -----
    1. Retrieve the timer via ``TimerManager.cancel_timer()``.
    2. Catch ``KeyError`` → 404 (timer not found).
    3. Catch ``ValueError`` → 422 (invalid state transition).
    4. Broadcast full session state to all WebSocket clients.
    5. Return the updated timer dict.
    """
    try:
        updated = timer_manager.cancel_timer(body.session_id, timer_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": f"Timer {timer_id!r} not found in session {body.session_id!r}",
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "domain_error", "message": str(exc)},
        )

    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(body.session_id).items()
    }
    await sync_service.broadcast(body.session_id, {"timers": full_state})

    return _timer_to_dict(updated)


# ── DELETE /timers/{timer_id} ────────────────────────────────────────────────


@router.delete(
    "/timers/{timer_id}",
    responses={
        200: {"description": "Timer removed"},
        404: {"description": "Timer not found"},
    },
)
async def delete_timer(
    timer_id: str,
    session_id: str = Query(..., description="Session identifier"),
    timer_manager: TimerManager = Depends(get_timer_manager),
    sync_service: SyncService = Depends(get_sync_service),
) -> Any:
    """Remove a timer from the session and broadcast the updated state.

    Steps
    -----
    1. Remove via ``TimerManager.remove_timer()``.
    2. 404 if the timer does not exist.
    3. Broadcast full session state to all WebSocket clients.
    4. Return a success marker.
    """
    removed = timer_manager.remove_timer(session_id, timer_id)
    if removed is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": f"Timer {timer_id!r} not found in session {session_id!r}",
            },
        )

    full_state = {
        tid: _timer_to_dict(t)
        for tid, t in timer_manager.get_all_timers(session_id).items()
    }
    await sync_service.broadcast(session_id, {"timers": full_state})

    return {"status": "ok"}


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
    Also starts the background countdown tick.
    """
    import os

    from cuqui.adapters.asr import SpeechToTextRouter
    from cuqui.adapters.asr_faster_whisper import FasterWhisperAdapter
    from cuqui.adapters.asr_openai import OpenAIWhisperAdapter
    from cuqui.adapters.parser_rules.adapter import TimerParserAdapter
    from cuqui.adapters.storage_sqlite import SqliteTimerStore

    store = SqliteTimerStore(db_path="cuqui.db")
    app.state.timer_manager = TimerManager(store=store)
    app.state.sync_service = SyncService()
    app.state.intent_parser = TimerParserAdapter(lang="es")

    faster_whisper = FasterWhisperAdapter(model_size="small", language="es")
    openai_asr = OpenAIWhisperAdapter(
        language="es",
    ) if os.getenv("OPENAI_API_KEY") else None
    app.state.speech_to_text = SpeechToTextRouter(
        primary=faster_whisper,
        fallback=openai_asr,
    )

    tick_task = asyncio.create_task(_run_tick(app))
    yield
    tick_task.cancel()
    try:
        await tick_task
    except asyncio.CancelledError:
        pass


async def _run_tick(app: FastAPI) -> None:
    """Background task: decrement running timers every second and broadcast."""
    while True:
        await asyncio.sleep(1)
        manager: TimerManager = app.state.timer_manager
        sync: SyncService = app.state.sync_service
        changed = manager.tick_all()
        for sid in changed:
            full = {
                tid: _timer_to_dict(t)
                for tid, t in manager.get_all_timers(sid).items()
            }
            await sync.broadcast(sid, {"timers": full})


def create_app() -> FastAPI:
    """Build a fully-wired ``FastAPI`` application.

    Includes the ``lifespan`` context manager and the ``router``.
    This is the production entry point; tests typically bypass it
    and use ``app.dependency_overrides`` instead.
    """
    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app
