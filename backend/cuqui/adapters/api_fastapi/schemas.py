"""Pydantic models for the FastAPI adapter.

Defines the request/response/error schemas for the Cuqui timer API.
All models use Pydantic v2 for validation and serialization.

Schemas
-------
CommandRequest:
    Body for ``POST /commands/text`` — text and session_id.
TimerResponse:
    Serialised timer state returned by REST endpoints.
ParseErrorResponse:
    400-level error — the input text could not be parsed.
DomainErrorResponse:
    422-level error — the command was parsed but the domain rejected it.
TimerListResponse:
    ``list[TimerResponse]`` — returned by ``GET /timers``.
"""

from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "ApiKeyRequest",
    "ApiKeyResponse",
    "CommandRequest",
    "DomainErrorResponse",
    "ParseErrorResponse",
    "TimerActionRequest",
    "TimerListResponse",
    "TimerResponse",
]


class CommandRequest(BaseModel):
    """Body contract for ``POST /commands/text``."""

    text: str
    session_id: str


class TimerActionRequest(BaseModel):
    """Body contract for timer control endpoints (pause/resume/cancel)."""

    session_id: str


class TimerResponse(BaseModel):
    """Serialised timer state returned to the client."""

    id: str
    name: str
    duration: int
    remaining: int
    status: str
    created_at: str


class ParseErrorResponse(BaseModel):
    """Error payload when the input text cannot be parsed."""

    error: str = "parse_error"
    message: str
    original_text: str


class DomainErrorResponse(BaseModel):
    """Error payload when the domain rejects a parsed command."""

    error: str = "domain_error"
    message: str


class ApiKeyRequest(BaseModel):
    """Body contract for ``POST /settings/api-key``."""

    session_id: str
    api_key: str


class ApiKeyResponse(BaseModel):
    """Response for API key status."""

    has_key: bool
    masked_key: str | None = None


TimerListResponse = list[TimerResponse]
"""``GET /timers`` returns an array of ``TimerResponse``."""
