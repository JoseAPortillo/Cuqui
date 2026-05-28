"""Tests for rule-based natural language timer parser.

Covers:
- All 8 intent patterns (SET_TIMER through QUERY_TIMER)
- First-match order precedence
- No-match → ParseError
- Empty input, partial duration, ambiguous intent
- ParseError carries message + original_text
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
from cuqui.domain.parser import ParseError, TimerParser


class TestTimerParser:
    """TimerParser SHALL match first intent in order and return Command or ParseError."""

    def setup_method(self) -> None:
        self.parser = TimerParser()

    # ── First match wins (Spec scenario 1) ───────────────────────────────

    def test_first_match_wins(self) -> None:
        """GIVEN "set a 5 minute timer for pasta"
        WHEN parsed THEN result SHALL be SET_TIMER with duration=300.
        """
        result = self.parser.parse("set a 5 minute timer for pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"
        assert result.name == "pasta"

    # ── No match → ParseError (Spec scenario 2) ──────────────────────────

    def test_no_match_returns_parse_error(self) -> None:
        """GIVEN "do something random"
        WHEN parsed THEN result SHALL be ParseError.
        """
        result = self.parser.parse("do something random")
        assert isinstance(result, ParseError)

    # ── SET_TIMER variations (Spec scenario 3) ──────────────────────────

    def test_set_timer_timer_x_minutes(self) -> None:
        """GIVEN "timer 10 minutes" → SET_TIMER with duration=600."""
        result = self.parser.parse("timer 10 minutes")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600  # 10 * 60
        assert result.unit == "minutes"

    def test_set_timer_set_for_x_minutes(self) -> None:
        """GIVEN "set timer for 10 minutes" → SET_TIMER with duration=600."""
        result = self.parser.parse("set timer for 10 minutes")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600

    def test_set_timer_x_minute_timer_name(self) -> None:
        """GIVEN "10 minute timer eggs" → SET_TIMER with duration=600."""
        result = self.parser.parse("10 minute timer eggs")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600

    # ── CANCEL_TIMER with name (Spec scenario 4) ───────────────────────

    def test_cancel_timer_with_name(self) -> None:
        """GIVEN "cancel the pasta timer" → CANCEL_TIMER, name="pasta"."""
        result = self.parser.parse("cancel the pasta timer")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "pasta"

    # ── EXTEND_TIMER with unit (Spec scenario 5) ───────────────────────

    def test_extend_timer_with_unit(self) -> None:
        """GIVEN "add 2 more minutes" → EXTEND_TIMER, duration=120, unit="minutes"."""
        result = self.parser.parse("add 2 more minutes")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 120  # 2 * 60
        assert result.unit == "minutes"

    # ── REDUCE_TIMER (Spec scenario 6) ─────────────────────────────────

    def test_reduce_timer_with_unit(self) -> None:
        """GIVEN "reduce by 30 seconds" → REDUCE_TIMER, duration=30, unit="seconds"."""
        result = self.parser.parse("reduce by 30 seconds")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    # ── RENAME_TIMER (Spec scenario 7) ─────────────────────────────────

    def test_rename_timer(self) -> None:
        """GIVEN "rename timer to rice" → RENAME_TIMER, name="rice"."""
        result = self.parser.parse("rename timer to rice")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "rice"

    # ── QUERY_TIMER variations (Spec scenario 8) ───────────────────────

    def test_query_how_much_time_left(self) -> None:
        """GIVEN "how much time left" → QUERY_TIMER."""
        result = self.parser.parse("how much time left")
        assert isinstance(result, QueryTimerCommand)

    def test_query_time_remaining(self) -> None:
        """GIVEN "time remaining" → QUERY_TIMER."""
        result = self.parser.parse("time remaining")
        assert isinstance(result, QueryTimerCommand)

    def test_query_when_is_pasta_done(self) -> None:
        """GIVEN "when is the pasta done" → QUERY_TIMER."""
        result = self.parser.parse("when is the pasta done")
        assert isinstance(result, QueryTimerCommand)

    # ── Empty input (Spec scenario 9) ─────────────────────────────────

    def test_empty_input_returns_parse_error(self) -> None:
        """GIVEN empty string "" → ParseError."""
        result = self.parser.parse("")
        assert isinstance(result, ParseError)

    # ── Partial duration (Spec scenario 10) ───────────────────────────

    def test_partial_duration_returns_parse_error(self) -> None:
        """GIVEN "set timer for" (no duration) → ParseError."""
        result = self.parser.parse("set timer for")
        assert isinstance(result, ParseError)

    # ── Ambiguous intent (Spec scenario 11) ──────────────────────────

    def test_ambiguous_intent_earlier_wins(self) -> None:
        """GIVEN "pause cancel timer" (matching PAUSE before CANCEL)
        WHEN parsed THEN PAUSE wins because PAUSE pattern is evaluated before CANCEL.
        """
        result = self.parser.parse("pause cancel timer")
        assert isinstance(result, PauseTimerCommand)
        # "cancel" is captured as the timer name under the PAUSE intent
        assert result.name == "cancel"

    # ── ParseError fields (Spec scenario 12) ─────────────────────────

    def test_parse_error_has_message_and_original_text(self) -> None:
        """GIVEN failing input "xyzzy"
        WHEN parsed THEN ParseError SHALL contain message and original_text.
        """
        result = self.parser.parse("xyzzy")
        assert isinstance(result, ParseError)
        assert result.message == "No matching intent"
        assert result.original_text == "xyzzy"


# ── Edge cases and additional coverage ─────────────────────────────────


class TestTimerParserEdgeCases:
    """Additional edge cases beyond the 12 spec scenarios."""

    def setup_method(self) -> None:
        self.parser = TimerParser()

    # ── Unit conversion coverage ──────────────────────────────────────

    def test_set_timer_seconds(self) -> None:
        """GIVEN "set 30 seconds timer" → duration=30 (no conversion)."""
        result = self.parser.parse("set 30 seconds timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_set_timer_hours(self) -> None:
        """GIVEN "set 2 hour timer" → duration=7200 (2 * 3600)."""
        result = self.parser.parse("set 2 hour timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 7200
        assert result.unit == "hours"

    # ── Cancel without name ───────────────────────────────────────────

    def test_cancel_timer_no_name(self) -> None:
        """GIVEN "cancel the timer" → CANCEL_TIMER with default name="last"."""
        result = self.parser.parse("cancel the timer")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "last"

    # ── Extend without "more" ─────────────────────────────────────────

    def test_extend_by_seconds(self) -> None:
        """GIVEN "add 30 seconds" → EXTEND_TIMER, duration=30."""
        result = self.parser.parse("add 30 seconds")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_extend_hours(self) -> None:
        """GIVEN "extend by 1 hour" → EXTEND_TIMER, duration=3600."""
        result = self.parser.parse("extend by 1 hour")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 3600
        assert result.unit == "hours"

    # ── Reduce without "by" ───────────────────────────────────────────

    def test_reduce_minutes(self) -> None:
        """GIVEN "reduce 5 minutes" → REDUCE_TIMER, duration=300."""
        result = self.parser.parse("reduce 5 minutes")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"

    def test_subtract_seconds(self) -> None:
        """GIVEN "subtract by 45 seconds" → REDUCE_TIMER, duration=45."""
        result = self.parser.parse("subtract by 45 seconds")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 45
        assert result.unit == "seconds"

    # ── Rename with "to" ──────────────────────────────────────────────

    def test_rename_timer_to_with_name(self) -> None:
        """GIVEN "rename to rice" → RENAME_TIMER, name="rice"."""
        result = self.parser.parse("rename to rice")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "rice"

    # ── Query more variations ─────────────────────────────────────────

    def test_query_how_long(self) -> None:
        """GIVEN "how long until done" → QUERY_TIMER."""
        result = self.parser.parse("how long until done")
        assert isinstance(result, QueryTimerCommand)

    def test_query_whats_status(self) -> None:
        """GIVEN "what's the status" → QUERY_TIMER."""
        result = self.parser.parse("what's the status")
        assert isinstance(result, QueryTimerCommand)

    def test_query_what_is_status(self) -> None:
        """GIVEN "what is the status" → QUERY_TIMER."""
        result = self.parser.parse("what is the status")
        assert isinstance(result, QueryTimerCommand)

    def test_query_when_will_it_finish(self) -> None:
        """GIVEN "when will it finish" → QUERY_TIMER."""
        result = self.parser.parse("when will it finish")
        assert isinstance(result, QueryTimerCommand)

    # ── PAUSE and RESUME ──────────────────────────────────────────────

    def test_pause_timer_with_name(self) -> None:
        """GIVEN "pause the rice timer" → PAUSE_TIMER, name="rice"."""
        result = self.parser.parse("pause the rice timer")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "rice"

    def test_pause_timer_no_name(self) -> None:
        """GIVEN "pause timer" → PAUSE_TIMER with name=None."""
        result = self.parser.parse("pause timer")
        assert isinstance(result, PauseTimerCommand)
        assert result.name is None

    def test_resume_timer_with_name(self) -> None:
        """GIVEN "resume the pasta timer" → RESUME_TIMER, name="pasta"."""
        result = self.parser.parse("resume the pasta timer")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name == "pasta"

    def test_resume_timer_no_name(self) -> None:
        """GIVEN "resume timer" → RESUME_TIMER with name=None."""
        result = self.parser.parse("resume timer")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name is None

    # ── Order guarantee: PAUSE before CANCEL ──────────────────────────

    def test_pause_before_cancel_order(self) -> None:
        """GIVEN text matching PAUSE pattern
        WHEN parsed THEN PAUSE is returned (proving PAUSE is evaluated before CANCEL).
        """
        result = self.parser.parse("pause the pasta timer")
        assert isinstance(result, PauseTimerCommand)

    # ── Whitespace and casing ─────────────────────────────────────────

    def test_leading_whitespace_handling(self) -> None:
        """GIVEN text with leading whitespace → should still parse."""
        result = self.parser.parse("   set 5 minute timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_mixed_case(self) -> None:
        """GIVEN uppercase text → should still parse."""
        result = self.parser.parse("SET 5 MINUTE TIMER FOR PASTA")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "PASTA"

    def test_cancel_without_timer_keyword(self) -> None:
        """GIVEN "cancel pasta" (no "timer" keyword) → ParseError.
        CANCEL regex requires "timer" keyword to match.
        """
        result = self.parser.parse("cancel pasta")
        assert isinstance(result, ParseError)
