"""Tests for Timer domain entity — state machine, duration ops, rename."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from cuqui.domain.timer import Timer, TimerStatus, create_timer


# ── TimerStatus Enum ──────────────────────────────────────────────────────────


class TestTimerStatus:
    """TimerStatus enum MUST have exactly five members with the correct values."""

    def test_enum_values(self) -> None:
        assert TimerStatus.PENDING == "pending"
        assert TimerStatus.RUNNING == "running"
        assert TimerStatus.PAUSED == "paused"
        assert TimerStatus.COMPLETED == "completed"
        assert TimerStatus.CANCELLED == "cancelled"

    def test_enum_membership(self) -> None:
        assert len(TimerStatus) == 5


# ── Timer Creation ────────────────────────────────────────────────────────────


class TestCreateTimer:
    """Timer SHALL be created via create_timer() factory with validation."""

    def test_create_valid_timer(self) -> None:
        """GIVEN duration 300s and name "Pasta"
        WHEN a Timer is created
        THEN status SHALL be "pending", remaining SHALL equal duration,
        and name SHALL be "Pasta"
        """
        timer = create_timer(name="Pasta", duration_secs=300)

        assert timer.name == "Pasta"
        assert timer.duration == 300
        assert timer.remaining == 300
        assert timer.status == TimerStatus.PENDING
        assert isinstance(timer.id, str) and len(timer.id) > 0
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            timer.id,
        )
        assert isinstance(timer.created_at, datetime)

    def test_create_timer_zero_duration_raises_error(self) -> None:
        """GIVEN duration 0s WHEN creating a Timer THEN MUST reject."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            create_timer(name="Test", duration_secs=0)

    def test_create_timer_negative_duration_raises_error(self) -> None:
        """GIVEN duration -60s WHEN creating a Timer THEN MUST reject."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            create_timer(name="Test", duration_secs=-60)


# ── State Transitions — start() ───────────────────────────────────────────────


class TestStart:
    """start() transitions pending→running; other states reject."""

    def test_start_pending(self) -> None:
        timer = create_timer("Pasta", 300)
        started = timer.start()
        assert started.status == TimerStatus.RUNNING
        assert started.remaining == 300  # unchanged
        # Prove immutability — original unchanged
        assert timer.status == TimerStatus.PENDING

    def test_start_running_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start()
        with pytest.raises(ValueError, match="Cannot start timer in running state"):
            timer.start()

    def test_start_paused_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().pause()
        with pytest.raises(ValueError, match="Cannot start timer in paused state"):
            timer.start()

    def test_start_completed_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().complete()
        with pytest.raises(ValueError, match="Cannot start timer in completed state"):
            timer.start()


# ── State Transitions — pause() ───────────────────────────────────────────────


class TestPause:
    """pause() transitions running→paused; other states reject."""

    def test_pause_running(self) -> None:
        timer = create_timer("Pasta", 300).start()
        paused = timer.pause()
        assert paused.status == TimerStatus.PAUSED
        assert paused.remaining == 300

    def test_pause_pending_raises_error(self) -> None:
        timer = create_timer("Pasta", 300)
        with pytest.raises(ValueError, match="Cannot pause timer in pending state"):
            timer.pause()

    def test_pause_paused_raises_error(self) -> None:
        """GIVEN a Timer in "paused" state WHEN calling pause again THEN domain error."""
        timer = create_timer("Pasta", 300).start().pause()
        with pytest.raises(ValueError, match="Cannot pause timer in paused state"):
            timer.pause()

    def test_pause_completed_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().complete()
        with pytest.raises(ValueError, match="Cannot pause timer in completed state"):
            timer.pause()


# ── State Transitions — resume() ──────────────────────────────────────────────


class TestResume:
    """resume() transitions paused→running; other states reject."""

    def test_resume_paused(self) -> None:
        timer = create_timer("Pasta", 300).start().pause()
        resumed = timer.resume()
        assert resumed.status == TimerStatus.RUNNING
        assert resumed.remaining == 300

    def test_resume_running_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start()
        with pytest.raises(ValueError, match="Cannot resume timer in running state"):
            timer.resume()

    def test_resume_pending_raises_error(self) -> None:
        timer = create_timer("Pasta", 300)
        with pytest.raises(ValueError, match="Cannot resume timer in pending state"):
            timer.resume()


# ── State Transitions — complete() ────────────────────────────────────────────


class TestComplete:
    """complete() transitions running→completed with remaining=0; other states reject."""

    def test_complete_running(self) -> None:
        timer = create_timer("Pasta", 300).start()
        completed = timer.complete()
        assert completed.status == TimerStatus.COMPLETED
        assert completed.remaining == 0

    def test_complete_pending_raises_error(self) -> None:
        timer = create_timer("Pasta", 300)
        with pytest.raises(ValueError, match="Cannot complete timer in pending state"):
            timer.complete()

    def test_complete_paused_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().pause()
        with pytest.raises(ValueError, match="Cannot complete timer in paused state"):
            timer.complete()

    def test_complete_completed_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().complete()
        with pytest.raises(ValueError, match="Cannot complete timer in completed state"):
            timer.complete()


# ── State Transitions — cancel() ──────────────────────────────────────────────


class TestCancel:
    """cancel() transitions active→cancelled; completed returns self (no-op); cancelled no-ops."""

    def test_cancel_pending(self) -> None:
        timer = create_timer("Pasta", 300)
        cancelled = timer.cancel()
        assert cancelled.status == TimerStatus.CANCELLED
        assert cancelled.remaining == 300  # preserved

    def test_cancel_running(self) -> None:
        """GIVEN a running Timer WHEN cancel is called THEN state is cancelled, remaining preserved."""
        timer = create_timer("Pasta", 300).start()
        cancelled = timer.cancel()
        assert cancelled.status == TimerStatus.CANCELLED
        assert cancelled.remaining == 300

    def test_cancel_paused(self) -> None:
        timer = create_timer("Pasta", 300).start().pause()
        cancelled = timer.cancel()
        assert cancelled.status == TimerStatus.CANCELLED
        assert cancelled.remaining == 300

    def test_cancel_completed_is_noop(self) -> None:
        """completed → cancel → no-op (returns self, unchanged)."""
        timer = create_timer("Pasta", 300).start().complete()
        result = timer.cancel()
        assert result is timer
        assert result.status == TimerStatus.COMPLETED

    def test_cancel_cancelled_is_noop(self) -> None:
        """cancelled → cancel → no-op (returns self, unchanged)."""
        timer = create_timer("Pasta", 300).cancel()
        result = timer.cancel()
        assert result is timer

    def test_start_on_cancelled_is_noop(self) -> None:
        """cancelled → any state transition → no-op."""
        timer = create_timer("Pasta", 300).cancel()
        result = timer.start()
        assert result is timer
        assert result.status == TimerStatus.CANCELLED

    def test_pause_on_cancelled_is_noop(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        result = timer.pause()
        assert result is timer

    def test_resume_on_cancelled_is_noop(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        result = timer.resume()
        assert result is timer

    def test_complete_on_cancelled_is_noop(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        result = timer.complete()
        assert result is timer


# ── Full Lifecycle ────────────────────────────────────────────────────────────


class TestFullLifecycle:
    """Verify the complete lifecycle path: pending→running→paused→resumed→completed."""

    def test_full_lifecycle(self) -> None:
        """GIVEN a Timer in "pending" state
        WHEN start → pause → resume → complete
        THEN final state SHALL be "completed" with remaining=0
        """
        timer = create_timer("Pasta", 300)
        t1 = timer.start()
        assert t1.status == TimerStatus.RUNNING
        t2 = t1.pause()
        assert t2.status == TimerStatus.PAUSED
        t3 = t2.resume()
        assert t3.status == TimerStatus.RUNNING
        t4 = t3.complete()
        assert t4.status == TimerStatus.COMPLETED
        assert t4.remaining == 0


# ── Duration Manipulation — extend() ──────────────────────────────────────────


class TestExtend:
    """extend(seconds) SHALL add to remaining; terminal states reject."""

    def test_extend_running_timer(self) -> None:
        """GIVEN a running Timer with 120s remaining WHEN extend(30) THEN remaining=150."""
        timer = create_timer("Pasta", 120).start()
        extended = timer.extend(30)
        assert extended.remaining == 150

    def test_extend_paused_timer(self) -> None:
        timer = create_timer("Pasta", 120).start().pause()
        extended = timer.extend(30)
        assert extended.remaining == 150

    def test_extend_pending_timer(self) -> None:
        timer = create_timer("Pasta", 120)
        extended = timer.extend(15)
        assert extended.remaining == 135

    def test_extend_completed_timer_raises_error(self) -> None:
        """GIVEN a Timer in "completed" state WHEN extend THEN domain error."""
        timer = create_timer("Pasta", 120).start().complete()
        with pytest.raises(ValueError, match="Cannot extend timer in completed state"):
            timer.extend(30)

    def test_extend_cancelled_timer_raises_error(self) -> None:
        timer = create_timer("Pasta", 120).cancel()
        with pytest.raises(ValueError, match="Cannot extend timer in cancelled state"):
            timer.extend(30)

    def test_extend_with_zero(self) -> None:
        timer = create_timer("Pasta", 120).start()
        extended = timer.extend(0)
        assert extended.remaining == 120  # unchanged

    def test_extend_with_negative_raises_error(self) -> None:
        timer = create_timer("Pasta", 120).start()
        with pytest.raises(ValueError, match="seconds must be non-negative"):
            timer.extend(-10)


# ── Duration Manipulation — reduce() ──────────────────────────────────────────


class TestReduce:
    """reduce(seconds) SHALL subtract, clamping at 0 minimum; terminal states reject."""

    def test_reduce_running_timer(self) -> None:
        timer = create_timer("Pasta", 120).start()
        reduced = timer.reduce(30)
        assert reduced.remaining == 90

    def test_reduce_below_zero_clamps(self) -> None:
        """GIVEN a running Timer with 10s remaining WHEN reduce(30) THEN remaining=0 (clamped)."""
        timer = create_timer("Pasta", 10).start()
        reduced = timer.reduce(30)
        assert reduced.remaining == 0

    def test_reduce_to_zero(self) -> None:
        """Reducing by exactly the remaining amount yields 0."""
        timer = create_timer("Pasta", 60).start()
        reduced = timer.reduce(60)
        assert reduced.remaining == 0

    def test_reduce_paused_timer(self) -> None:
        timer = create_timer("Pasta", 120).start().pause()
        reduced = timer.reduce(20)
        assert reduced.remaining == 100

    def test_reduce_completed_timer_raises_error(self) -> None:
        timer = create_timer("Pasta", 120).start().complete()
        with pytest.raises(ValueError, match="Cannot reduce timer in completed state"):
            timer.reduce(10)

    def test_reduce_cancelled_timer_raises_error(self) -> None:
        timer = create_timer("Pasta", 120).cancel()
        with pytest.raises(ValueError, match="Cannot reduce timer in cancelled state"):
            timer.reduce(10)

    def test_reduce_with_negative_raises_error(self) -> None:
        timer = create_timer("Pasta", 120).start()
        with pytest.raises(ValueError, match="seconds must be non-negative"):
            timer.reduce(-5)


# ── Rename ────────────────────────────────────────────────────────────────────


class TestRename:
    """rename() SHALL work in non-terminal states; terminal states reject."""

    def test_rename_running_timer(self) -> None:
        """GIVEN a running Timer named "Pasta" WHEN rename("Rice") THEN name="Rice"."""
        timer = create_timer("Pasta", 300).start()
        renamed = timer.rename("Rice")
        assert renamed.name == "Rice"
        assert renamed.status == TimerStatus.RUNNING  # status unchanged

    def test_rename_pending_timer(self) -> None:
        timer = create_timer("Pasta", 300)
        renamed = timer.rename("Rice")
        assert renamed.name == "Rice"

    def test_rename_paused_timer(self) -> None:
        timer = create_timer("Pasta", 300).start().pause()
        renamed = timer.rename("Rice")
        assert renamed.name == "Rice"

    def test_rename_cancelled_timer_raises_error(self) -> None:
        """GIVEN a cancelled Timer WHEN rename THEN domain error."""
        timer = create_timer("Pasta", 300).cancel()
        with pytest.raises(ValueError, match="Cannot rename timer in cancelled state"):
            timer.rename("Rice")

    def test_rename_completed_timer_raises_error(self) -> None:
        timer = create_timer("Pasta", 300).start().complete()
        with pytest.raises(ValueError, match="Cannot rename timer in completed state"):
            timer.rename("Rice")

    def test_rename_empty_string(self) -> None:
        timer = create_timer("Pasta", 300).start()
        renamed = timer.rename("")
        assert renamed.name == ""


# ── Immutability ──────────────────────────────────────────────────────────────


class TestImmutability:
    """Timer instances MUST be frozen — fields cannot be mutated after creation."""

    def test_timer_is_frozen_dataclass(self) -> None:
        timer = create_timer("Pasta", 300)
        with pytest.raises(AttributeError):
            timer.name = "Changed"  # type: ignore[misc]

    def test_create_timer_returns_new_instance(self) -> None:
        """Immutability: each transition returns a new Timer, leaving the original unchanged."""
        timer = create_timer("Pasta", 300)
        started = timer.start()
        assert started is not timer
        assert timer.status == TimerStatus.PENDING


# ── Terminal No-Op Rules ──────────────────────────────────────────────────────


class TestTerminalNoOps:
    """Terminal state rules: completed→cancel no-op; cancelled→everything no-op."""

    def test_cancelled_extend_raises(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        with pytest.raises(ValueError, match="Cannot extend timer in cancelled state"):
            timer.extend(10)

    def test_cancelled_reduce_raises(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        with pytest.raises(ValueError, match="Cannot reduce timer in cancelled state"):
            timer.reduce(10)

    def test_cancelled_rename_raises(self) -> None:
        timer = create_timer("Pasta", 300).cancel()
        with pytest.raises(ValueError, match="Cannot rename timer in cancelled state"):
            timer.rename("New")
