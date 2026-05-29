"""Tests for TimerManager — session-scoped CRUD and state delegation.

Covers:
- add_timer creates timer in session
- get_timer returns timer by id
- get_timer returns None for non-existent timer
- get_all_timers returns all timers in session
- remove_timer removes and returns the timer
- State transitions: start, pause, resume, cancel, complete
- Duration ops: extend, reduce (with clamp)
- Rename delegation
- Domain errors propagate from Timer methods
- Non-existent session returns empty state
"""

from __future__ import annotations

import pytest

from cuqui.domain.timer import Timer, TimerStatus


class TestTimerManagerImport:
    """TimerManager SHALL be importable."""

    def test_timer_manager_is_importable(self) -> None:
        """GIVEN the module WHEN importing TimerManager THEN no error."""


class TestTimerManagerAddGet:
    """TimerManager.add_timer and get_timer operations."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager

        self.manager = TimerManager()

    def test_add_timer_creates_and_returns(self) -> None:
        """GIVEN add_timer("s1", "Pasta", 300) WHEN get_timer THEN Timer with correct fields."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        assert isinstance(timer, Timer)
        assert timer.name == "Pasta"
        assert timer.duration == 300
        assert timer.status == TimerStatus.PENDING

        retrieved = self.manager.get_timer("s1", timer.id)
        assert retrieved is not None
        assert retrieved.name == "Pasta"

    def test_get_timer_nonexistent_returns_none(self) -> None:
        """GIVEN session with no timers WHEN get_timer("nonexistent") THEN None."""
        self.manager.add_timer("s1", "Pasta", 300)
        result = self.manager.get_timer("s1", "nonexistent-id")
        assert result is None

    def test_get_timer_unknown_session_returns_none(self) -> None:
        """GIVEN session does not exist WHEN get_timer THEN None."""
        result = self.manager.get_timer("unknown", "some-id")
        assert result is None

    def test_get_all_timers_empty_session(self) -> None:
        """GIVEN no timers in session WHEN get_all_timers THEN empty dict."""
        result = self.manager.get_all_timers("s1")
        assert result == {}

    def test_get_all_timers_returns_all(self) -> None:
        """GIVEN two timers in session WHEN get_all_timers THEN dict with both."""
        t1 = self.manager.add_timer("s1", "Pasta", 300)
        t2 = self.manager.add_timer("s1", "Rice", 600)
        result = self.manager.get_all_timers("s1")
        assert len(result) == 2
        assert t1.id in result
        assert t2.id in result

    def test_remove_timer_removes_and_returns(self) -> None:
        """GIVEN a timer in session WHEN remove_timer THEN removed and returned."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        removed = self.manager.remove_timer("s1", timer.id)
        assert removed is not None
        assert removed.id == timer.id
        # Verify it's gone
        assert self.manager.get_timer("s1", timer.id) is None

    def test_remove_timer_nonexistent_returns_none(self) -> None:
        """GIVEN non-existent timer WHEN remove_timer THEN None."""
        result = self.manager.remove_timer("s1", "nonexistent")
        assert result is None


class TestTimerManagerStateTransitions:
    """TimerManager SHALL delegate transitions to domain Timer methods."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager

        self.manager = TimerManager()

    def test_start_delegates_to_timer_start(self) -> None:
        """GIVEN a pending Timer WHEN start_timer THEN status becomes running."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        updated = self.manager.start_timer("s1", timer.id)
        assert updated.status == TimerStatus.RUNNING
        # Verify store was updated
        stored = self.manager.get_timer("s1", timer.id)
        assert stored is not None
        assert stored.status == TimerStatus.RUNNING

    def test_pause_delegates_to_timer_pause(self) -> None:
        """GIVEN a running Timer WHEN pause_timer THEN status becomes paused."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        paused = self.manager.pause_timer("s1", timer.id)
        assert paused.status == TimerStatus.PAUSED

    def test_resume_delegates_to_timer_resume(self) -> None:
        """GIVEN a paused Timer WHEN resume_timer THEN status becomes running."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        self.manager.pause_timer("s1", timer.id)
        resumed = self.manager.resume_timer("s1", timer.id)
        assert resumed.status == TimerStatus.RUNNING

    def test_cancel_delegates_to_timer_cancel(self) -> None:
        """GIVEN a pending Timer WHEN cancel_timer THEN status becomes cancelled."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        cancelled = self.manager.cancel_timer("s1", timer.id)
        assert cancelled.status == TimerStatus.CANCELLED

    def test_complete_delegates_to_timer_complete(self) -> None:
        """GIVEN a running Timer WHEN complete_timer THEN status becomes completed, remaining=0."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        completed = self.manager.complete_timer("s1", timer.id)
        assert completed.status == TimerStatus.COMPLETED
        assert completed.remaining == 0

    def test_extend_delegates_to_timer_extend(self) -> None:
        """GIVEN a running Timer with 120s WHEN extend_timer(30) THEN remaining=150."""
        timer = self.manager.add_timer("s1", "Pasta", 120)
        self.manager.start_timer("s1", timer.id)
        extended = self.manager.extend_timer("s1", timer.id, 30)
        assert extended.remaining == 150

    def test_reduce_delegates_to_timer_reduce(self) -> None:
        """GIVEN a running Timer with 10s WHEN reduce_timer(30) THEN remaining=0 (clamped)."""
        timer = self.manager.add_timer("s1", "Pasta", 10)
        self.manager.start_timer("s1", timer.id)
        reduced = self.manager.reduce_timer("s1", timer.id, 30)
        assert reduced.remaining == 0

    def test_rename_delegates_to_timer_rename(self) -> None:
        """GIVEN a running Timer named "Pasta" WHEN rename_timer("Rice") THEN name="Rice"."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        renamed = self.manager.rename_timer("s1", timer.id, "Rice")
        assert renamed.name == "Rice"

    def test_domain_error_propagates_on_invalid_transition(self) -> None:
        """GIVEN a completed Timer WHEN start_timer THEN ValueError propagates."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        self.manager.complete_timer("s1", timer.id)
        with pytest.raises(ValueError, match="Cannot start timer in completed state"):
            self.manager.start_timer("s1", timer.id)
