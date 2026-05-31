"""Pure domain timer entity with state machine — zero framework dependencies.

Provides:
    TimerStatus:    Enum of lifecycle states (pending, running, paused, completed, cancelled).
    Timer:          Frozen dataclass with pure state-transition methods.
    create_timer(): Factory to build a new pending Timer with validation.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NoReturn

__all__ = [
    "Timer",
    "TimerStatus",
    "create_timer",
]


class TimerStatus(enum.StrEnum):
    """Lifecycle states for a cooking timer."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = frozenset({TimerStatus.COMPLETED, TimerStatus.CANCELLED})


def _raise(message: str) -> NoReturn:
    raise ValueError(message)


@dataclass(frozen=True, slots=True)
class Timer:
    """Immutable cooking timer with a full state machine.

    Every state-transition method returns a *new* ``Timer`` instance, leaving
    the original untouched.  Terminal-state rules are enforced transparently:

    * ``COMPLETED`` → ``cancel()`` returns ``self`` (no-op).
    * ``CANCELLED`` → every transition method returns ``self`` (no-op).
    * All other invalid transitions raise ``ValueError``.
    """

    id: str
    name: str
    duration: int
    remaining: int
    status: TimerStatus
    created_at: datetime

    # ── state transitions ──────────────────────────────────────────────────

    def start(self) -> Timer:
        """pending → running."""
        if self.status == TimerStatus.CANCELLED:
            return self
        if self.status != TimerStatus.PENDING:
            _raise(f"Cannot start timer in {self.status.value} state")
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration,
            remaining=self.remaining,
            status=TimerStatus.RUNNING,
            created_at=self.created_at,
        )

    def pause(self) -> Timer:
        """running → paused."""
        if self.status == TimerStatus.CANCELLED:
            return self
        if self.status != TimerStatus.RUNNING:
            _raise(f"Cannot pause timer in {self.status.value} state")
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration,
            remaining=self.remaining,
            status=TimerStatus.PAUSED,
            created_at=self.created_at,
        )

    def resume(self) -> Timer:
        """paused → running."""
        if self.status == TimerStatus.CANCELLED:
            return self
        if self.status != TimerStatus.PAUSED:
            _raise(f"Cannot resume timer in {self.status.value} state")
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration,
            remaining=self.remaining,
            status=TimerStatus.RUNNING,
            created_at=self.created_at,
        )

    def complete(self) -> Timer:
        """running → completed (remaining → 0)."""
        if self.status == TimerStatus.CANCELLED:
            return self
        if self.status != TimerStatus.RUNNING:
            _raise(f"Cannot complete timer in {self.status.value} state")
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration,
            remaining=0,
            status=TimerStatus.COMPLETED,
            created_at=self.created_at,
        )

    def cancel(self) -> Timer:
        """active → cancelled.  completed → no-op.  cancelled → no-op."""
        if self.status in (TimerStatus.COMPLETED, TimerStatus.CANCELLED):
            return self
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration,
            remaining=self.remaining,
            status=TimerStatus.CANCELLED,
            created_at=self.created_at,
        )

    # ── duration manipulation ──────────────────────────────────────────────

    def extend(self, seconds: int) -> Timer:
        """Add *seconds* to ``remaining``.

        Raises ``ValueError`` if the timer is in a terminal state or if
        *seconds* is negative.
        """
        if self.status in _TERMINAL_STATES:
            _raise(f"Cannot extend timer in {self.status.value} state")
        if seconds < 0:
            _raise("seconds must be non-negative")
        return Timer(
            id=self.id,
            name=self.name,
            duration=self.duration + seconds,
            remaining=self.remaining + seconds,
            status=self.status,
            created_at=self.created_at,
        )

    def reduce(self, seconds: int) -> Timer:
        """Subtract *seconds* from ``remaining``, clamped at 0.

        Raises ``ValueError`` if the timer is in a terminal state or if
        *seconds* is negative.
        """
        if self.status in _TERMINAL_STATES:
            _raise(f"Cannot reduce timer in {self.status.value} state")
        if seconds < 0:
            _raise("seconds must be non-negative")
        return Timer(
            id=self.id,
            name=self.name,
            duration=max(self.duration - seconds, 0),
            remaining=max(self.remaining - seconds, 0),
            status=self.status,
            created_at=self.created_at,
        )

    # ── rename ─────────────────────────────────────────────────────────────

    def rename(self, name: str) -> Timer:
        """Set a new *name*.

        Raises ``ValueError`` if the timer is in a terminal state.
        """
        if self.status in _TERMINAL_STATES:
            _raise(f"Cannot rename timer in {self.status.value} state")
        return Timer(
            id=self.id,
            name=name,
            duration=self.duration,
            remaining=self.remaining,
            status=self.status,
            created_at=self.created_at,
        )


# ── factory ───────────────────────────────────────────────────────────────────


def create_timer(name: str, duration_secs: int) -> Timer:
    """Create a new ``Timer`` in ``PENDING`` status.

    Parameters
    ----------
    name:
        Human-readable label for the timer.
    duration_secs:
        Total duration in whole seconds.  **Must be positive**.

    Raises
    ------
    ValueError
        If *duration_secs* is ≤ 0.
    """
    if duration_secs <= 0:
        raise ValueError("Duration must be positive")
    return Timer(
        id=str(uuid.uuid4()),
        name=name,
        duration=duration_secs,
        remaining=duration_secs,
        status=TimerStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
