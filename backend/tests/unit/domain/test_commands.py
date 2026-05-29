"""Tests for Intent enum and CuquiCommand frozen dataclasses.

Covers:
- Intent enum membership and values (8 members, SYNC_FINISH_TIME deferred)
- Per-intent command validation (all 8 commands)
- CuquiCommand type alias
- Clean imports (no FastAPI, async framework packages, or Pydantic)
"""

from __future__ import annotations

import re
import typing

import pytest

from cuqui.domain.commands import (
    CancelTimerCommand,
    CuquiCommand,
    ExtendTimerCommand,
    Intent,
    PauseTimerCommand,
    QueryTimerCommand,
    ReduceTimerCommand,
    RenameTimerCommand,
    ResumeTimerCommand,
    SetTimerCommand,
)

# ── Intent Enum ────────────────────────────────────────────────────────────────


class TestIntentMembership:
    """Intent enum SHALL have exactly 8 members, including SET_TIMER."""

    def test_set_timer_is_member(self) -> None:
        """GIVEN an Intent enum WHEN checking for SET_TIMER THEN it SHALL be a member."""
        assert Intent.SET_TIMER in Intent

    def test_cancel_timer_is_member(self) -> None:
        assert Intent.CANCEL_TIMER in Intent

    def test_pause_timer_is_member(self) -> None:
        assert Intent.PAUSE_TIMER in Intent

    def test_resume_timer_is_member(self) -> None:
        assert Intent.RESUME_TIMER in Intent

    def test_extend_timer_is_member(self) -> None:
        assert Intent.EXTEND_TIMER in Intent

    def test_reduce_timer_is_member(self) -> None:
        assert Intent.REDUCE_TIMER in Intent

    def test_rename_timer_is_member(self) -> None:
        assert Intent.RENAME_TIMER in Intent

    def test_query_timer_is_member(self) -> None:
        assert Intent.QUERY_TIMER in Intent

    def test_reject_sync_finish_time(self) -> None:
        """GIVEN an Intent enum WHEN checking for SYNC_FINISH_TIME
        THEN it SHALL NOT be a member."""
        with pytest.raises(AttributeError):
            Intent.SYNC_FINISH_TIME  # type: ignore[attr-defined]

    def test_exactly_eight_members(self) -> None:
        """The enum SHALL have exactly 8 members (SYNC_FINISH_TIME deferred)."""
        assert len(Intent) == 8


class TestIntentValues:
    """Intent enum SHALL use sequential IntEnum values."""

    def test_set_timer_value(self) -> None:
        assert Intent.SET_TIMER == 1

    def test_cancel_timer_value(self) -> None:
        assert Intent.CANCEL_TIMER == 2

    def test_pause_timer_value(self) -> None:
        assert Intent.PAUSE_TIMER == 3

    def test_resume_timer_value(self) -> None:
        assert Intent.RESUME_TIMER == 4

    def test_extend_timer_value(self) -> None:
        assert Intent.EXTEND_TIMER == 5

    def test_reduce_timer_value(self) -> None:
        assert Intent.REDUCE_TIMER == 6

    def test_rename_timer_value(self) -> None:
        assert Intent.RENAME_TIMER == 7

    def test_query_timer_value(self) -> None:
        assert Intent.QUERY_TIMER == 8


# ── SET_TIMER Command ──────────────────────────────────────────────────────────


class TestSetTimerCommand:
    """SetTimerCommand SHALL validate duration (positive int), optional unit and name."""

    def test_valid_full(self) -> None:
        """GIVEN duration 300, unit "seconds", name "Pasta"
        WHEN building a Command THEN it SHALL validate all fields.
        """
        cmd = SetTimerCommand(duration=300, unit="seconds", name="Pasta")
        assert cmd.duration == 300
        assert cmd.unit == "seconds"
        assert cmd.name == "Pasta"

    def test_valid_minimal(self) -> None:
        """GIVEN only duration
        WHEN building a Command THEN validation SHALL pass with defaults.
        """
        cmd = SetTimerCommand(duration=60)
        assert cmd.duration == 60
        assert cmd.unit is None
        assert cmd.name is None

    def test_invalid_duration_negative(self) -> None:
        """GIVEN duration -30 THEN validation SHALL raise ValueError."""
        with pytest.raises(ValueError, match="duration must be positive"):
            SetTimerCommand(duration=-30)

    def test_invalid_duration_zero(self) -> None:
        """GIVEN duration 0 THEN validation SHALL raise ValueError."""
        with pytest.raises(ValueError, match="duration must be positive"):
            SetTimerCommand(duration=0)

    def test_missing_duration_raises_error(self) -> None:
        """GIVEN no duration THEN construction SHALL fail with TypeError."""
        with pytest.raises(TypeError):
            SetTimerCommand()  # type: ignore[call-arg]

    def test_invalid_unit_raises_error(self) -> None:
        """GIVEN unit "epochs" (not seconds/minutes/hours) THEN validation SHALL fail."""
        with pytest.raises(ValueError, match="invalid unit"):
            SetTimerCommand(duration=300, unit="epochs")

    def test_name_too_long(self) -> None:
        """GIVEN name longer than 50 chars THEN validation SHALL fail."""
        with pytest.raises(ValueError, match="name too long"):
            SetTimerCommand(duration=300, name="a" * 51)


# ── CANCEL_TIMER Command ───────────────────────────────────────────────────────


class TestCancelTimerCommand:
    """CancelTimerCommand SHALL accept optional name, defaulting to "last"."""

    def test_default_name_is_last(self) -> None:
        """GIVEN no name THEN name SHALL default to "last"."""
        cmd = CancelTimerCommand()
        assert cmd.name == "last"

    def test_explicit_name(self) -> None:
        """GIVEN name "Pasta" THEN name SHALL be "Pasta"."""
        cmd = CancelTimerCommand(name="Pasta")
        assert cmd.name == "Pasta"

    def test_name_too_long(self) -> None:
        """GIVEN name longer than 50 chars THEN validation SHALL fail."""
        with pytest.raises(ValueError, match="name too long"):
            CancelTimerCommand(name="a" * 51)


# ── PAUSE_TIMER Command ────────────────────────────────────────────────────────


class TestPauseTimerCommand:
    """PauseTimerCommand SHALL accept optional name."""

    def test_without_name(self) -> None:
        """GIVEN no name THEN validation SHALL pass."""
        cmd = PauseTimerCommand()
        assert cmd.name is None

    def test_with_name(self) -> None:
        """GIVEN name "Pasta" THEN name SHALL be "Pasta"."""
        cmd = PauseTimerCommand(name="Pasta")
        assert cmd.name == "Pasta"

    def test_name_too_long(self) -> None:
        """GIVEN name longer than 50 chars THEN validation SHALL fail."""
        with pytest.raises(ValueError, match="name too long"):
            PauseTimerCommand(name="a" * 51)


# ── RESUME_TIMER Command ──────────────────────────────────────────────────────


class TestResumeTimerCommand:
    """ResumeTimerCommand SHALL accept optional name."""

    def test_without_name(self) -> None:
        cmd = ResumeTimerCommand()
        assert cmd.name is None

    def test_with_name(self) -> None:
        cmd = ResumeTimerCommand(name="Pasta")
        assert cmd.name == "Pasta"

    def test_name_too_long(self) -> None:
        with pytest.raises(ValueError, match="name too long"):
            ResumeTimerCommand(name="a" * 51)


# ── EXTEND_TIMER Command ──────────────────────────────────────────────────────


class TestExtendTimerCommand:
    """ExtendTimerCommand SHALL validate duration (positive int), optional unit."""

    def test_valid_with_unit(self) -> None:
        cmd = ExtendTimerCommand(duration=60, unit="minutes")
        assert cmd.duration == 60
        assert cmd.unit == "minutes"

    def test_valid_without_unit(self) -> None:
        cmd = ExtendTimerCommand(duration=30)
        assert cmd.duration == 30
        assert cmd.unit is None

    def test_invalid_duration_negative(self) -> None:
        with pytest.raises(ValueError, match="duration must be positive"):
            ExtendTimerCommand(duration=-10)


# ── REDUCE_TIMER Command ──────────────────────────────────────────────────────


class TestReduceTimerCommand:
    """ReduceTimerCommand SHALL validate duration (positive int), optional unit."""

    def test_valid_with_unit(self) -> None:
        cmd = ReduceTimerCommand(duration=30, unit="hours")
        assert cmd.duration == 30
        assert cmd.unit == "hours"

    def test_valid_without_unit(self) -> None:
        cmd = ReduceTimerCommand(duration=15)
        assert cmd.duration == 15
        assert cmd.unit is None

    def test_invalid_duration_negative(self) -> None:
        with pytest.raises(ValueError, match="duration must be positive"):
            ReduceTimerCommand(duration=-5)


# ── RENAME_TIMER Command ──────────────────────────────────────────────────────


class TestRenameTimerCommand:
    """RenameTimerCommand SHALL require name (non-optional)."""

    def test_valid_name(self) -> None:
        """GIVEN name "Rice" THEN name SHALL be "Rice"."""
        cmd = RenameTimerCommand(name="Rice")
        assert cmd.name == "Rice"

    def test_missing_name_raises_error(self) -> None:
        """GIVEN no name THEN construction SHALL fail with TypeError."""
        with pytest.raises(TypeError):
            RenameTimerCommand()  # type: ignore[call-arg]

    def test_name_too_long(self) -> None:
        """GIVEN name longer than 50 chars THEN validation SHALL fail."""
        with pytest.raises(ValueError, match="name too long"):
            RenameTimerCommand(name="a" * 51)


# ── QUERY_TIMER Command ───────────────────────────────────────────────────────


class TestQueryTimerCommand:
    """QueryTimerCommand SHALL accept optional name."""

    def test_without_name(self) -> None:
        cmd = QueryTimerCommand()
        assert cmd.name is None

    def test_with_name(self) -> None:
        cmd = QueryTimerCommand(name="Pasta")
        assert cmd.name == "Pasta"

    def test_name_too_long(self) -> None:
        with pytest.raises(ValueError, match="name too long"):
            QueryTimerCommand(name="a" * 51)


# ── CuquiCommand Type Alias ────────────────────────────────────────────────────


class TestCuquiCommandTypeAlias:
    """CuquiCommand SHALL be a Union type alias covering all 8 command types."""

    def test_type_alias_is_union(self) -> None:
        """CuquiCommand SHALL be a Union type."""
        assert typing.get_origin(CuquiCommand) is typing.Union

    def test_union_contains_all_commands(self) -> None:
        """The Union SHALL include all 8 command types."""
        args = typing.get_args(CuquiCommand)
        assert SetTimerCommand in args
        assert CancelTimerCommand in args
        assert PauseTimerCommand in args
        assert ResumeTimerCommand in args
        assert ExtendTimerCommand in args
        assert ReduceTimerCommand in args
        assert RenameTimerCommand in args
        assert QueryTimerCommand in args

    def test_union_exactly_eight_types(self) -> None:
        """There SHALL be exactly 8 types in CuquiCommand."""
        assert len(typing.get_args(CuquiCommand)) == 8

    def test_isinstance_narrowing_set_timer(self) -> None:
        """GIVEN a SetTimerCommand WHEN isinstance THEN it SHALL match SetTimerCommand."""
        cmd = SetTimerCommand(duration=300, name="Pasta")
        assert isinstance(cmd, SetTimerCommand)
        assert not isinstance(cmd, CancelTimerCommand)

    def test_isinstance_narrowing_cancel(self) -> None:
        cmd = CancelTimerCommand()
        assert isinstance(cmd, CancelTimerCommand)
        assert not isinstance(cmd, SetTimerCommand)


# ── Clean Imports ──────────────────────────────────────────────────────────────


class TestCleanImports:
    """Commands module SHALL NOT import FastAPI, async frameworks, or Pydantic."""

    FORBIDDEN_TOP_LEVEL = frozenset({"fastapi", "uvicorn", "starlette", "pydantic"})

    def test_no_forbidden_imports(self) -> None:
        """WHEN inspecting imports THEN no forbidden packages SHALL be present."""
        import cuqui.domain.commands as mod

        source = mod.__spec__.loader.get_source(mod.__name__)  # type: ignore[union-attr]
        imports = re.findall(r"^\s*import\s+(\S+)", source, re.MULTILINE)
        imports += re.findall(r"^\s*from\s+(\S+)", source, re.MULTILINE)
        for mod_name in imports:
            top = mod_name.split(".")[0]
            assert top not in self.FORBIDDEN_TOP_LEVEL, (
                f"Forbidden import found: {mod_name}"
            )
