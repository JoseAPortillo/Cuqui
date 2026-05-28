"""Tests for Intent enum and CuquiCommand discriminated union.

Covers:
- Intent enum membership and values (8 members, SYNC_FINISH_TIME deferred)
- Per-intent payload validation (all 8 intents)
- CuquiCommand discriminated union with extras rejection
- Clean imports (no FastAPI or async framework packages)
"""

from __future__ import annotations

import re

import pytest
from pydantic import TypeAdapter, ValidationError

from cuqui.domain.commands import (
    CancelTimerPayload,
    CuquiCommand,
    ExtendTimerPayload,
    Intent,
    PauseTimerPayload,
    QueryTimerPayload,
    ReduceTimerPayload,
    RenameTimerPayload,
    ResumeTimerPayload,
    SetTimerPayload,
)

# TypeAdapter for the discriminated union (Annotated type alias cannot be
# instantiated directly — TypeAdapter is the canonical Pydantic v2 approach).
_cuqui_adapter = TypeAdapter(CuquiCommand)


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


# ── SET_TIMER Payload ──────────────────────────────────────────────────────────


class TestSetTimerPayload:
    """SetTimerPayload SHALL validate duration (positive int), optional unit and name."""

    def test_valid_full(self) -> None:
        """GIVEN intent SET_TIMER, duration 300, unit "seconds", name "Pasta"
        WHEN building a Command THEN model SHALL validate all fields.
        """
        cmd = SetTimerPayload(
            intent=Intent.SET_TIMER,
            duration=300,
            unit="seconds",
            name="Pasta",
        )
        assert cmd.intent == Intent.SET_TIMER
        assert cmd.duration == 300
        assert cmd.unit == "seconds"
        assert cmd.name == "Pasta"

    def test_valid_minimal(self) -> None:
        """GIVEN intent SET_TIMER, only duration
        WHEN building a Command THEN validation SHALL pass with defaults.
        """
        cmd = SetTimerPayload(intent=Intent.SET_TIMER, duration=60)
        assert cmd.duration == 60
        assert cmd.unit is None
        assert cmd.name is None

    def test_invalid_duration_negative(self) -> None:
        """GIVEN intent SET_TIMER and duration -30 THEN validation SHALL fail."""
        with pytest.raises(ValidationError):
            SetTimerPayload(intent=Intent.SET_TIMER, duration=-30)

    def test_invalid_duration_zero(self) -> None:
        """GIVEN intent SET_TIMER and duration 0 THEN validation SHALL fail."""
        with pytest.raises(ValidationError):
            SetTimerPayload(intent=Intent.SET_TIMER, duration=0)

    def test_missing_duration_raises_error(self) -> None:
        """GIVEN intent SET_TIMER with no duration THEN validation SHALL fail."""
        with pytest.raises(ValidationError):
            SetTimerPayload(intent=Intent.SET_TIMER)  # type: ignore[call-arg]

    def test_invalid_unit_raises_error(self) -> None:
        """GIVEN unit "epochs" (not seconds/minutes/hours) THEN validation SHALL fail."""
        with pytest.raises(ValidationError):
            SetTimerPayload(intent=Intent.SET_TIMER, duration=300, unit="epochs")


# ── CANCEL_TIMER Payload ───────────────────────────────────────────────────────


class TestCancelTimerPayload:
    """CancelTimerPayload SHALL accept optional name, defaulting to "last"."""

    def test_default_name_is_last(self) -> None:
        """GIVEN CANCEL_TIMER with no name THEN name SHALL default to "last"."""
        cmd = CancelTimerPayload(intent=Intent.CANCEL_TIMER)
        assert cmd.name == "last"

    def test_explicit_name(self) -> None:
        """GIVEN CANCEL_TIMER with name "Pasta" THEN name SHALL be "Pasta"."""
        cmd = CancelTimerPayload(intent=Intent.CANCEL_TIMER, name="Pasta")
        assert cmd.name == "Pasta"


# ── PAUSE_TIMER Payload ────────────────────────────────────────────────────────


class TestPauseTimerPayload:
    """PauseTimerPayload SHALL accept optional name."""

    def test_without_name(self) -> None:
        """GIVEN PAUSE_TIMER with no name THEN validation SHALL pass."""
        cmd = PauseTimerPayload(intent=Intent.PAUSE_TIMER)
        assert cmd.name is None

    def test_with_name(self) -> None:
        """GIVEN PAUSE_TIMER with name "Pasta" THEN name SHALL be "Pasta"."""
        cmd = PauseTimerPayload(intent=Intent.PAUSE_TIMER, name="Pasta")
        assert cmd.name == "Pasta"


# ── RESUME_TIMER Payload ──────────────────────────────────────────────────────


class TestResumeTimerPayload:
    """ResumeTimerPayload SHALL accept optional name."""

    def test_without_name(self) -> None:
        cmd = ResumeTimerPayload(intent=Intent.RESUME_TIMER)
        assert cmd.name is None

    def test_with_name(self) -> None:
        cmd = ResumeTimerPayload(intent=Intent.RESUME_TIMER, name="Pasta")
        assert cmd.name == "Pasta"


# ── EXTEND_TIMER Payload ──────────────────────────────────────────────────────


class TestExtendTimerPayload:
    """ExtendTimerPayload SHALL validate duration (positive int), optional unit."""

    def test_valid_with_unit(self) -> None:
        cmd = ExtendTimerPayload(
            intent=Intent.EXTEND_TIMER,
            duration=60,
            unit="minutes",
        )
        assert cmd.duration == 60
        assert cmd.unit == "minutes"

    def test_valid_without_unit(self) -> None:
        cmd = ExtendTimerPayload(intent=Intent.EXTEND_TIMER, duration=30)
        assert cmd.duration == 30
        assert cmd.unit is None

    def test_invalid_duration_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExtendTimerPayload(intent=Intent.EXTEND_TIMER, duration=-10)


# ── REDUCE_TIMER Payload ──────────────────────────────────────────────────────


class TestReduceTimerPayload:
    """ReduceTimerPayload SHALL validate duration (positive int), optional unit."""

    def test_valid_with_unit(self) -> None:
        cmd = ReduceTimerPayload(
            intent=Intent.REDUCE_TIMER,
            duration=30,
            unit="hours",
        )
        assert cmd.duration == 30
        assert cmd.unit == "hours"

    def test_valid_without_unit(self) -> None:
        cmd = ReduceTimerPayload(intent=Intent.REDUCE_TIMER, duration=15)
        assert cmd.duration == 15
        assert cmd.unit is None

    def test_invalid_duration_negative(self) -> None:
        with pytest.raises(ValidationError):
            ReduceTimerPayload(intent=Intent.REDUCE_TIMER, duration=-5)


# ── RENAME_TIMER Payload ──────────────────────────────────────────────────────


class TestRenameTimerPayload:
    """RenameTimerPayload SHALL require name (non-optional)."""

    def test_valid_name(self) -> None:
        """GIVEN RENAME_TIMER with name "Rice" THEN name SHALL be "Rice"."""
        cmd = RenameTimerPayload(intent=Intent.RENAME_TIMER, name="Rice")
        assert cmd.name == "Rice"

    def test_missing_name_raises_error(self) -> None:
        """GIVEN RENAME_TIMER with no name THEN validation SHALL fail."""
        with pytest.raises(ValidationError):
            RenameTimerPayload(intent=Intent.RENAME_TIMER)  # type: ignore[call-arg]


# ── QUERY_TIMER Payload ───────────────────────────────────────────────────────


class TestQueryTimerPayload:
    """QueryTimerPayload SHALL accept optional name."""

    def test_without_name(self) -> None:
        cmd = QueryTimerPayload(intent=Intent.QUERY_TIMER)
        assert cmd.name is None

    def test_with_name(self) -> None:
        cmd = QueryTimerPayload(intent=Intent.QUERY_TIMER, name="Pasta")
        assert cmd.name == "Pasta"


# ── CuquiCommand Discriminated Union ──────────────────────────────────────────


class TestCuquiCommand:
    """CuquiCommand SHALL discriminate by intent field via TypeAdapter."""

    def test_set_timer_via_discriminated_union(self) -> None:
        """GIVEN intent SET_TIMER WHEN using CuquiCommand THEN returns SetTimerPayload."""
        cmd = _cuqui_adapter.validate_python(
            {"intent": Intent.SET_TIMER, "duration": 300, "name": "Pasta"}
        )
        assert isinstance(cmd, SetTimerPayload)
        assert cmd.duration == 300

    def test_cancel_timer_via_union(self) -> None:
        cmd = _cuqui_adapter.validate_python({"intent": Intent.CANCEL_TIMER})
        assert isinstance(cmd, CancelTimerPayload)
        assert cmd.name == "last"

    def test_rename_timer_via_union(self) -> None:
        cmd = _cuqui_adapter.validate_python(
            {"intent": Intent.RENAME_TIMER, "name": "Rice"}
        )
        assert isinstance(cmd, RenameTimerPayload)
        assert cmd.name == "Rice"

    def test_extras_rejected(self) -> None:
        """GIVEN an unknown field WHEN building CuquiCommand THEN validation fails."""
        with pytest.raises(ValidationError):
            _cuqui_adapter.validate_python(
                {"intent": Intent.SET_TIMER, "duration": 300, "unknown": "x"}
            )

    def test_intent_int_value_also_accepted(self) -> None:
        """CuquiCommand SHALL accept raw int values for intent (Pydantic native)."""
        cmd = _cuqui_adapter.validate_python({"intent": 1, "duration": 300})
        assert isinstance(cmd, SetTimerPayload)
        assert cmd.intent == Intent.SET_TIMER


# ── Clean Imports ──────────────────────────────────────────────────────────────


class TestCleanImports:
    """Commands module SHALL NOT import FastAPI or async framework packages."""

    FRAMEWORK_TOP_LEVEL = frozenset({"fastapi", "uvicorn", "starlette"})

    def test_no_framework_imports(self) -> None:
        """WHEN inspecting imports THEN no FastAPI/async packages SHALL be present."""
        import cuqui.domain.commands as mod

        source = mod.__spec__.loader.get_source(mod.__name__)  # type: ignore[union-attr]
        imports = re.findall(r"^\s*import\s+(\S+)", source, re.MULTILINE)
        imports += re.findall(r"^\s*from\s+(\S+)", source, re.MULTILINE)
        for mod_name in imports:
            top = mod_name.split(".")[0]
            assert top not in self.FRAMEWORK_TOP_LEVEL, (
                f"Framework import found: {mod_name}"
            )
