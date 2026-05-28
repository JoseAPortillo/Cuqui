"""Command schema — Intent enum and CuquiCommand discriminated union.

Provides:
    Intent:         IntEnum of 8 voice intents (SYNC_FINISH_TIME deferred).
    {Intent}Payload: Per-intent Pydantic v2 validation models.
    CuquiCommand:   Discriminated union keyed by ``intent`` field.

Zero framework dependencies — only Pydantic v2 for validation.
"""

import enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CancelTimerPayload",
    "CuquiCommand",
    "ExtendTimerPayload",
    "Intent",
    "PauseTimerPayload",
    "QueryTimerPayload",
    "ReduceTimerPayload",
    "RenameTimerPayload",
    "ResumeTimerPayload",
    "SetTimerPayload",
]


class _CommandBase(BaseModel):
    """Base class enforcing strict schema — no extra fields allowed."""

    model_config = ConfigDict(extra="forbid")


class Intent(enum.IntEnum):
    """Canonical voice intents for Cuqui cooking timer.

    Members are ordered by expected frequency of use.
    ``SYNC_FINISH_TIME`` is deferred — not yet part of the MVP.
    """

    SET_TIMER = 1
    CANCEL_TIMER = 2
    PAUSE_TIMER = 3
    RESUME_TIMER = 4
    EXTEND_TIMER = 5
    REDUCE_TIMER = 6
    RENAME_TIMER = 7
    QUERY_TIMER = 8


# ── Per-Intent Payloads ────────────────────────────────────────────────────────

_UnitLiteral = Literal["seconds", "minutes", "hours"]


class SetTimerPayload(_CommandBase):
    """Create a new timer with duration, optional unit, optional label."""

    intent: Literal[Intent.SET_TIMER]
    duration: int = Field(gt=0)
    unit: _UnitLiteral | None = None
    name: str | None = Field(default=None, max_length=50)


class CancelTimerPayload(_CommandBase):
    """Cancel an active timer (defaults to "last" if no name given)."""

    intent: Literal[Intent.CANCEL_TIMER]
    name: str = Field(default="last", max_length=50)


class PauseTimerPayload(_CommandBase):
    """Pause a running timer."""

    intent: Literal[Intent.PAUSE_TIMER]
    name: str | None = Field(default=None, max_length=50)


class ResumeTimerPayload(_CommandBase):
    """Resume a paused timer."""

    intent: Literal[Intent.RESUME_TIMER]
    name: str | None = Field(default=None, max_length=50)


class ExtendTimerPayload(_CommandBase):
    """Add time to an existing timer."""

    intent: Literal[Intent.EXTEND_TIMER]
    duration: int = Field(gt=0)
    unit: _UnitLiteral | None = None


class ReduceTimerPayload(_CommandBase):
    """Subtract time from an existing timer."""

    intent: Literal[Intent.REDUCE_TIMER]
    duration: int = Field(gt=0)
    unit: _UnitLiteral | None = None


class RenameTimerPayload(_CommandBase):
    """Rename an active timer (name is required)."""

    intent: Literal[Intent.RENAME_TIMER]
    name: str = Field(max_length=50)


class QueryTimerPayload(_CommandBase):
    """Query the status of a timer. Without a name, returns all / last."""

    intent: Literal[Intent.QUERY_TIMER]
    name: str | None = Field(default=None, max_length=50)


# ── Discriminated Union ────────────────────────────────────────────────────────

CuquiCommand = Annotated[
    Union[
        SetTimerPayload,
        CancelTimerPayload,
        PauseTimerPayload,
        ResumeTimerPayload,
        ExtendTimerPayload,
        ReduceTimerPayload,
        RenameTimerPayload,
        QueryTimerPayload,
    ],
    Field(discriminator="intent"),
]
"""A validated voice command that can represent any of the 8 intents.

Usage::

    from cuqui.domain.commands import CuquiCommand, Intent
    from pydantic import TypeAdapter

    adapter = TypeAdapter(CuquiCommand)
    cmd = adapter.validate_python({"intent": 1, "duration": 300, "name": "Pasta"})
    isinstance(cmd, SetTimerPayload)  # True — type-narrowed
"""
