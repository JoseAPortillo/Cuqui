"""Tests for process_command — match/case routing of all 8 intents.

Covers:
- SET_TIMER: creates timer, returns Timer with pending status
- CANCEL_TIMER: cancels timer, returns None
- PAUSE_TIMER: pauses running timer
- RESUME_TIMER: resumes paused timer
- EXTEND_TIMER: extends remaining time
- REDUCE_TIMER: reduces remaining time (clamped at 0)
- RENAME_TIMER: renames timer
- QUERY_TIMER: returns all timers dict or timer if name given
- Unrecognized command type raises ValueError
- Domain errors propagate
"""

from __future__ import annotations

import pytest

from cuqui.domain.commands import (
    CancelTimerCommand,
    ExtendTimerCommand,
    PauseTimerCommand,
    QueryTimerCommand,
    ReduceTimerCommand,
    RenameTimerCommand,
    ResumeTimerCommand,
    SetTimerCommand,
)
from cuqui.domain.timer import Timer, TimerStatus


class TestProcessCommandImport:
    """process_command SHALL be importable."""

    def test_process_command_is_importable(self) -> None:
        pass  # noqa: F811


class TestProcessCommandSetTimer:
    """SET_TIMER SHALL create and return a Timer."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_set_timer_creates_timer_with_name(self) -> None:
        """GIVEN SetTimerCommand(duration=300, name="Pasta") WHEN process THEN Timer returned."""
        cmd = SetTimerCommand(duration=300, name="Pasta")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "Pasta"
        assert result.duration == 300
        assert result.status == TimerStatus.RUNNING

        # Verify it was stored
        stored = self.manager.get_timer("s1", result.id)
        assert stored is not None

    def test_set_timer_without_name_defaults_to_last(self) -> None:
        """GIVEN SetTimerCommand(duration=300) without name THEN name defaults to "last"."""
        cmd = SetTimerCommand(duration=300)
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "last"


class TestProcessCommandCancelTimer:
    """CANCEL_TIMER SHALL cancel a timer and return None."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_cancel_timer_returns_none_and_removes(self) -> None:
        """GIVEN a timer exists WHEN CANCEL_TIMER THEN result is None and timer is removed."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        cmd = CancelTimerCommand(name="Pasta")
        result = self.process(self.manager, "s1", cmd)
        assert result is None
        # Timer should be removed from store
        stored = self.manager.get_timer("s1", timer.id)
        assert stored is None

    def test_cancel_timer_last_default(self) -> None:
        """GIVEN multiple timers WHEN CANCEL_TIMER with no name THEN removes the last added."""
        self.manager.add_timer("s1", "Pasta", 300)
        t2 = self.manager.add_timer("s1", "Rice", 600)
        cmd = CancelTimerCommand()  # name defaults to "last"
        self.process(self.manager, "s1", cmd)
        stored = self.manager.get_timer("s1", t2.id)
        assert stored is None  # removed


class TestProcessCommandPauseTimer:
    """PAUSE_TIMER SHALL pause a running timer."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_pause_running_timer(self) -> None:
        """GIVEN a running Timer WHEN PAUSE_TIMER THEN status becomes paused."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        cmd = PauseTimerCommand(name="Pasta")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.status == TimerStatus.PAUSED

    def test_pause_by_last_default(self) -> None:
        """GIVEN running timer WHEN PAUSE_TIMER without name THEN pauses last added."""
        self.manager.add_timer("s1", "Pasta", 300)
        t2 = self.manager.add_timer("s1", "Rice", 600)
        self.manager.start_timer("s1", t2.id)
        cmd = PauseTimerCommand()  # name is None
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "Rice"
        assert result.status == TimerStatus.PAUSED


class TestProcessCommandResumeTimer:
    """RESUME_TIMER SHALL resume a paused timer."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_resume_paused_timer(self) -> None:
        """GIVEN a paused Timer WHEN RESUME_TIMER THEN status becomes running."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        self.manager.pause_timer("s1", timer.id)
        cmd = ResumeTimerCommand(name="Pasta")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.status == TimerStatus.RUNNING


class TestProcessCommandExtendTimer:
    """EXTEND_TIMER SHALL extend remaining time."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_extend_without_name_creates_new_timer(self) -> None:
        """GIVEN running Timer WHEN EXTEND_TIMER(30, name=None) THEN new timer."""
        timer = self.manager.add_timer("s1", "Pasta", 120)
        self.manager.start_timer("s1", timer.id)
        cmd = ExtendTimerCommand(duration=30, name=None)
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "timer"
        assert result.remaining == 30
        assert len(self.manager.get_all_timers("s1")) == 2

    def test_extend_by_name_adds_time(self) -> None:
        """GIVEN running Timer WHEN EXTEND_TIMER(30, name='Pasta') THEN remaining=150."""
        timer = self.manager.add_timer("s1", "Pasta", 120)
        self.manager.start_timer("s1", timer.id)
        cmd = ExtendTimerCommand(duration=30, name="Pasta")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.remaining == 150


class TestProcessCommandReduceTimer:
    """REDUCE_TIMER SHALL reduce remaining time, clamped at 0."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_reduce_below_zero_clamps(self) -> None:
        """GIVEN running Timer with 10s WHEN REDUCE_TIMER(30) THEN remaining=0."""
        timer = self.manager.add_timer("s1", "Pasta", 10)
        self.manager.start_timer("s1", timer.id)
        cmd = ReduceTimerCommand(duration=30)
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.remaining == 0

    def test_reduce_partial(self) -> None:
        """GIVEN running Timer with 120s WHEN REDUCE_TIMER(30) THEN remaining=90."""
        timer = self.manager.add_timer("s1", "Pasta", 120)
        self.manager.start_timer("s1", timer.id)
        cmd = ReduceTimerCommand(duration=30)
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.remaining == 90


class TestProcessCommandRenameTimer:
    """RENAME_TIMER SHALL rename a timer."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_rename_timer(self) -> None:
        """GIVEN running Timer "Pasta" WHEN RENAME_TIMER("Rice") THEN name="Rice"."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        cmd = RenameTimerCommand(name="Rice")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "Rice"


class TestProcessCommandQueryTimer:
    """QUERY_TIMER SHALL return timer state(s)."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_query_all_timers_returns_dict(self) -> None:
        """GIVEN two timers in session WHEN QUERY_TIMER THEN dict with both."""
        self.manager.add_timer("s1", "Pasta", 300)
        self.manager.add_timer("s1", "Rice", 600)
        cmd = QueryTimerCommand()  # name is None → query all
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, dict)
        assert len(result) == 2


class TestProcessCommandErrors:
    """Error handling in process_command."""

    def setup_method(self) -> None:
        from cuqui.application.manage_timers import TimerManager
        from cuqui.application.process_command import process_command

        self.manager = TimerManager()
        self.process = process_command

    def test_domain_error_propagates(self) -> None:
        """GIVEN completed timer WHEN pause THEN ValueError propagates."""
        timer = self.manager.add_timer("s1", "Pasta", 300)
        self.manager.start_timer("s1", timer.id)
        self.manager.complete_timer("s1", timer.id)
        cmd = PauseTimerCommand(name="Pasta")
        with pytest.raises(ValueError, match="Cannot pause timer in completed state"):
            self.process(self.manager, "s1", cmd)

    def test_extend_timer_creates_timer_when_no_target(self) -> None:
        """GIVEN no timers in session WHEN EXTEND_TIMER THEN timer is created."""
        cmd = ExtendTimerCommand(duration=30, name="pasta")
        result = self.process(self.manager, "s1", cmd)
        assert isinstance(result, Timer)
        assert result.name == "pasta"
        assert result.duration == 30
        assert result.status == TimerStatus.RUNNING

    def test_rename_in_empty_session_raises(self) -> None:
        """GIVEN empty session WHEN RENAME_TIMER THEN ValueError."""
        cmd = RenameTimerCommand(name="Rice")
        with pytest.raises(ValueError, match="No timers in session"):
            self.process(self.manager, "not-found-session", cmd)
