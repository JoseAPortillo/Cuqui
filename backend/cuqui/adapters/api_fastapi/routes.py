"""FastAPI REST and WebSocket routes for the Cuqui timer API.

Provides three public endpoints:

* ``POST /commands/text`` — accept natural-language text, route through
  the application layer, return and broadcast the result.
* ``GET  /timers`` — return all timers for a session as a JSON array.
* ``WS   /ws/session/{session_id}`` — real-time state broadcast channel.
* ``GET  /health`` — healthcheck for monitoring / Docker.

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
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from cuqui.adapters.api_fastapi.dependencies import (
    get_intent_parser,
    get_push_service,
    get_speech_to_text,
    get_sync_service,
    get_timer_manager,
    get_timer_store,
)
from cuqui.adapters.api_fastapi.schemas import (
    ApiKeyRequest,
    ApiKeyResponse,
    CommandRequest,
    DomainErrorResponse,
    ParseErrorResponse,
    PushSubscriptionRequest,
    TimerActionRequest,
    TimerResponse,
)
from cuqui.adapters.push_webpush import WebPushAdapter
from cuqui.adapters.storage_sqlite import SqliteTimerStore
from cuqui.application.manage_timers import TimerManager
from cuqui.application.process_command import process_command
from cuqui.application.sync_state import SyncService
from cuqui.domain.parser import ParseError
from cuqui.domain.timer import Timer, TimerStatus
from cuqui.ports.intent_parser import IntentParser
from cuqui.ports.speech_to_text import SpeechToText

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
        "completed_at": timer.completed_at.isoformat() if timer.completed_at else None,
    }


# ── GET /health ───────────────────────────────────────────────────────────────


@router.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck endpoint for monitoring and Docker HEALTHCHECK."""
    return {"status": "ok"}


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
    store: SqliteTimerStore = Depends(get_timer_store),
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
    # 1. Read audio with size limit (10 MB max)
    MAX_AUDIO_SIZE = 10 * 1024 * 1024
    audio_bytes = await audio.read()
    if not audio_bytes:
        return JSONResponse(
            status_code=400,
            content={"error": "empty_audio", "message": "No audio data received"},
        )
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        return JSONResponse(
            status_code=413,
            content={"error": "audio_too_large", "message": "Audio exceeds 10 MB limit"},
        )

    # 2. Transcribe
    session_api_key = store.get_api_key(session_id)
    try:
        text = await speech_to_text.transcribe(
            audio_bytes, audio.content_type, session_api_key=session_api_key,
        )
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


# ── POST /settings/api-key ─────────────────────────────────────────────────────


@router.post(
    "/settings/api-key",
    responses={
        200: {"description": "API key saved"},
    },
)
async def set_api_key(
    body: ApiKeyRequest,
    store: SqliteTimerStore = Depends(get_timer_store),
) -> dict[str, str]:
    """Save or update the OpenAI API key for *session_id*."""
    store.save_api_key(body.session_id, body.api_key)
    return {"status": "ok"}


# ── GET /settings/api-key ─────────────────────────────────────────────────────


@router.get(
    "/settings/api-key",
    responses={
        200: {"model": ApiKeyResponse, "description": "API key status"},
    },
)
async def get_api_key(
    session_id: str = Query(..., description="Session identifier"),
    store: SqliteTimerStore = Depends(get_timer_store),
) -> ApiKeyResponse:
    """Check whether *session_id* has a saved API key.

    Returns ``has_key`` boolean and a masked version of the key if set.
    """
    key = store.get_api_key(session_id)
    if not key:
        return ApiKeyResponse(has_key=False, masked_key=None)
    masked = key[:4] + "…" + key[-4:] if len(key) > 8 else "…"
    return ApiKeyResponse(has_key=True, masked_key=masked)


# ── Push notification endpoints ────────────────────────────────────────────────


@router.get("/push/vapid-public-key")
async def get_vapid_public_key(
    push_service: WebPushAdapter | None = Depends(get_push_service),
) -> dict[str, str | None]:
    """Return the VAPID public key for push subscription (or null if push is disabled)."""
    key = push_service.vapid_public_key() if push_service else None
    return {"public_key": key}


@router.post("/push/subscribe")
async def subscribe_push(
    body: PushSubscriptionRequest,
    push_service: WebPushAdapter | None = Depends(get_push_service),
) -> dict[str, str]:
    """Save a push subscription for *session_id*."""
    if push_service is None:
        return {"status": "push_disabled"}
    push_service.save_subscription(
        body.session_id,
        {"endpoint": body.endpoint, "p256dh": body.p256dh, "auth": body.auth},
    )
    return {"status": "ok"}


@router.delete("/push/subscribe")
async def unsubscribe_push(
    session_id: str = Query(..., description="Session identifier"),
    endpoint: str = Query(..., description="Push endpoint to remove"),
    push_service: WebPushAdapter | None = Depends(get_push_service),
) -> dict[str, str]:
    """Remove a push subscription for *session_id*."""
    if push_service is None:
        return {"status": "push_disabled"}
    push_service.remove_subscription(session_id, endpoint)
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
    import logging
    import os

    from cuqui.adapters.api_fastapi.security import SafeFormatter
    from cuqui.adapters.asr import SpeechToTextRouter
    from cuqui.adapters.asr_faster_whisper import FasterWhisperAdapter
    from cuqui.adapters.asr_openai import OpenAIWhisperAdapter
    from cuqui.adapters.parser_rules.adapter import TimerParserAdapter
    from cuqui.adapters.push_webpush import WebPushAdapter
    from cuqui.adapters.storage_sqlite import SqliteTimerStore

    # Protect all logs against accidental credential leaks
    root = logging.getLogger()
    for handler in root.handlers:
        fmt = handler.formatter._fmt if handler.formatter else "%(message)s"
        handler.setFormatter(SafeFormatter(fmt))

    store = SqliteTimerStore(db_path="data/cuqui.db")
    app.state.timer_store = store
    app.state.timer_manager = TimerManager(store=store)
    app.state.sync_service = SyncService()
    app.state.intent_parser = TimerParserAdapter(lang="es")

    faster_whisper = FasterWhisperAdapter(model_size="tiny", language="es")
    openai_asr = OpenAIWhisperAdapter(
        language="es",
    ) if os.getenv("OPENAI_API_KEY") else None
    app.state.speech_to_text = SpeechToTextRouter(
        primary=faster_whisper,
        fallback=openai_asr,
    )

    app.state.push_service = WebPushAdapter(store=store)

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
        push_service: WebPushAdapter | None = getattr(app.state, "push_service", None)
        changed = manager.tick_all()
        for sid in changed:
            full = {
                tid: _timer_to_dict(t)
                for tid, t in manager.get_all_timers(sid).items()
            }
            await sync.broadcast(sid, {"timers": full})
            if push_service:
                for tid, timer in changed[sid].items():
                    if timer.status == TimerStatus.COMPLETED:
                        seq = int(time.time() * 1000)
                        asyncio.create_task(push_service.send(
                            sid,
                            title="\u23F0 \u00a1Tiempo cumplido!",
                            body=f'"{timer.name}" — el temporizador termin\u00f3.',
                            tag=f"timer-{tid}",
                            data={"timerId": tid, "timerName": timer.name},
                        ))


def create_app(serve_frontend: bool = False, frontend_dir: str | None = None) -> FastAPI:
    """Build a fully-wired ``FastAPI`` application.

    Includes the ``lifespan`` context manager, CORS middleware,
    and (optionally) static file serving for a production frontend build.

    Parameters
    ----------
    serve_frontend:
        If ``True``, mount the static frontend build at ``/`` so the same
        server handles both API and UI (single-container deploy).
    frontend_dir:
        Path to the directory containing the production frontend build
        (e.g. ``/app/frontend/dist``).  Falls back to ``frontend/dist``
        relative to the current working directory.
    """
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    # ── CORS — allow the Vite dev server (or any frontend origin) ──────────
    # In production (same-origin static files) CORS is not needed.
    # allow_credentials=False avoids the dangerous * + credentials anti-pattern.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # ── Production static frontend ─────────────────────────────────────────
    # NOTE: we use a catch‑all HTTP route instead of app.mount("/", StaticFiles(...))
    # because Starlette checks mounts *before* routes — a StaticFiles mount at "/"
    # would intercept WebSocket upgrade requests and close them, breaking the
    # real‑time connection that enables the microphone button.
    if serve_frontend:
        import os

        dist = frontend_dir or os.path.join(os.getcwd(), "frontend", "dist")
        if os.path.isdir(dist):

            @app.get("/{full_path:path}")
            async def spa_fallback(full_path: str) -> FileResponse:
                file_path = os.path.join(dist, full_path or "index.html")
                if os.path.isdir(file_path):
                    file_path = os.path.join(file_path, "index.html")
                if os.path.isfile(file_path):
                    return FileResponse(file_path)
                return FileResponse(os.path.join(dist, "index.html"))

    return app
