"""Command schema — Intent enum and CuquiCommand frozen dataclasses.

Provides:
    Intent:             IntEnum of 8 voice intents (SYNC_FINISH_TIME deferred).
    {Verb}TimerCommand: Per-intent frozen dataclass with ``__post_init__`` validation.
    CuquiCommand:       ``Union`` type alias for type narrowing.

Zero framework dependencies — only Python stdlib.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Union

__all__ = [
    "CancelTimerCommand",
    "CuquiCommand",
    "ExtendTimerCommand",
    "Intent",
    "PauseTimerCommand",
    "QueryTimerCommand",
    "ReduceTimerCommand",
    "RenameTimerCommand",
    "ResumeTimerCommand",
    "SetTimerCommand",
]

# ── Intents ────────────────────────────────────────────────────────────────────


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


# ── Validation helpers ─────────────────────────────────────────────────────────

_VALID_UNITS = frozenset({"seconds", "minutes", "hours"})


def _validate_name(name: str | None) -> None:
    """Raise ``ValueError`` if *name* exceeds 50 characters."""
    if name is not None and len(name) > 50:
        raise ValueError("name too long")


def _validate_duration_positive(duration: int) -> None:
    """Raise ``ValueError`` if *duration* is not positive."""
    if duration <= 0:
        raise ValueError("duration must be positive")


def _validate_unit(unit: str | None) -> None:
    """Raise ``ValueError`` if *unit* is not None or one of seconds/minutes/hours."""
    if unit is not None and unit not in _VALID_UNITS:
        raise ValueError(f"invalid unit: {unit!r}")


# ── Per-Intent Commands ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SetTimerCommand:
    """Create a new timer with duration, optional unit, optional label."""

    duration: int
    unit: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        _validate_duration_positive(self.duration)
        _validate_unit(self.unit)
        _validate_name(self.name)


@dataclass(frozen=True)
class CancelTimerCommand:
    """Cancel an active timer (defaults to ``"last"`` if no name given)."""

    name: str = "last"

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class PauseTimerCommand:
    """Pause a running timer."""

    name: str | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class ResumeTimerCommand:
    """Resume a paused timer."""

    name: str | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class ExtendTimerCommand:
    """Add time to an existing timer (or create one if no target exists)."""

    duration: int
    unit: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        _validate_duration_positive(self.duration)
        _validate_unit(self.unit)
        _validate_name(self.name)


@dataclass(frozen=True)
class ReduceTimerCommand:
    """Subtract time from an existing timer."""

    duration: int
    unit: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        _validate_duration_positive(self.duration)
        _validate_unit(self.unit)
        _validate_name(self.name)


@dataclass(frozen=True)
class RenameTimerCommand:
    """Rename an active timer (name is required)."""

    name: str

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class QueryTimerCommand:
    """Query the status of a timer. Without a name, returns all / last."""

    name: str | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


# ── Type Alias ─────────────────────────────────────────────────────────────────


CuquiCommand = Union[
    SetTimerCommand,
    CancelTimerCommand,
    PauseTimerCommand,
    ResumeTimerCommand,
    ExtendTimerCommand,
    ReduceTimerCommand,
    RenameTimerCommand,
    QueryTimerCommand,
]
"""A voice command that can represent any of the 8 intents.

Usage::

    from cuqui.domain.commands import CuquiCommand, SetTimerCommand

    cmd: CuquiCommand = SetTimerCommand(duration=300, name="Pasta")
    isinstance(cmd, SetTimerCommand)  # True — type-narrowed
"""
