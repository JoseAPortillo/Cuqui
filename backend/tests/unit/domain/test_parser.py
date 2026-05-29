"""Tests for rule-based natural language timer parser (EN + ES).

Covers:
- All 8 intent patterns for English and Spanish
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


# ── Language-agnostic tests ────────────────────────────────────────────────────


class TestTimerParserShared:
    """Tests that apply regardless of parser language."""

    def setup_method(self) -> None:
        self.parser = TimerParser(lang="en")

    def test_no_match_returns_parse_error(self) -> None:
        """GIVEN "do something random" THEN ParseError."""
        result = self.parser.parse("do something random")
        assert isinstance(result, ParseError)

    def test_empty_input_returns_parse_error(self) -> None:
        """GIVEN empty string "" THEN ParseError."""
        result = self.parser.parse("")
        assert isinstance(result, ParseError)

    def test_parse_error_has_message_and_original_text(self) -> None:
        """GIVEN failing input THEN ParseError SHALL carry message and original_text."""
        result = self.parser.parse("xyzzy")
        assert isinstance(result, ParseError)
        assert result.message == "No matching intent"
        assert result.original_text == "xyzzy"


# ── English tests ──────────────────────────────────────────────────────────────


class TestTimerParserEnglish:
    """TimerParser(lang='en') SHALL match English utterances."""

    def setup_method(self) -> None:
        self.parser = TimerParser(lang="en")

    def test_first_match_wins(self) -> None:
        """GIVEN "set a 5 minute timer for pasta" → SET_TIMER duration=300."""
        result = self.parser.parse("set a 5 minute timer for pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"
        assert result.name == "pasta"

    def test_set_timer_timer_x_minutes(self) -> None:
        """GIVEN "timer 10 minutes" → SET_TIMER duration=600."""
        result = self.parser.parse("timer 10 minutes")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600
        assert result.unit == "minutes"

    def test_set_timer_set_for_x_minutes(self) -> None:
        """GIVEN "set timer for 10 minutes" → SET_TIMER duration=600."""
        result = self.parser.parse("set timer for 10 minutes")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600

    def test_set_timer_x_minute_timer_name(self) -> None:
        """GIVEN "10 minute timer eggs" → SET_TIMER duration=600."""
        result = self.parser.parse("10 minute timer eggs")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600

    def test_cancel_timer_with_name(self) -> None:
        """GIVEN "cancel the pasta timer" → CANCEL_TIMER name='pasta'."""
        result = self.parser.parse("cancel the pasta timer")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "pasta"

    def test_extend_timer_with_unit(self) -> None:
        """GIVEN "add 2 more minutes" → EXTEND_TIMER duration=120."""
        result = self.parser.parse("add 2 more minutes")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 120
        assert result.unit == "minutes"

    def test_reduce_timer_with_unit(self) -> None:
        """GIVEN "reduce by 30 seconds" → REDUCE_TIMER duration=30."""
        result = self.parser.parse("reduce by 30 seconds")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_rename_timer(self) -> None:
        """GIVEN "rename timer to rice" → RENAME_TIMER name='rice'."""
        result = self.parser.parse("rename timer to rice")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "rice"

    def test_query_how_much_time_left(self) -> None:
        """GIVEN "how much time left" → QUERY_TIMER."""
        result = self.parser.parse("how much time left")
        assert isinstance(result, QueryTimerCommand)

    def test_partial_duration_returns_parse_error(self) -> None:
        """GIVEN "set timer for" (no duration) → ParseError."""
        result = self.parser.parse("set timer for")
        assert isinstance(result, ParseError)

    def test_ambiguous_intent_earlier_wins(self) -> None:
        """GIVEN "pause cancel timer" → PAUSE wins (evaluated before CANCEL)."""
        result = self.parser.parse("pause cancel timer")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "cancel"


class TestTimerParserEnglishEdgeCases:
    """Additional English edge cases."""

    def setup_method(self) -> None:
        self.parser = TimerParser(lang="en")

    def test_set_timer_seconds(self) -> None:
        result = self.parser.parse("set 30 seconds timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_set_timer_hours(self) -> None:
        result = self.parser.parse("set 2 hour timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 7200
        assert result.unit == "hours"

    def test_cancel_timer_no_name(self) -> None:
        result = self.parser.parse("cancel the timer")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "last"

    def test_extend_by_seconds(self) -> None:
        result = self.parser.parse("add 30 seconds")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 30

    def test_extend_hours(self) -> None:
        result = self.parser.parse("extend by 1 hour")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 3600
        assert result.unit == "hours"

    def test_reduce_minutes(self) -> None:
        result = self.parser.parse("reduce 5 minutes")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 300

    def test_subtract_seconds(self) -> None:
        result = self.parser.parse("subtract by 45 seconds")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 45

    def test_rename_timer_to_with_name(self) -> None:
        result = self.parser.parse("rename to rice")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "rice"

    def test_query_how_long(self) -> None:
        result = self.parser.parse("how long until done")
        assert isinstance(result, QueryTimerCommand)

    def test_query_whats_status(self) -> None:
        result = self.parser.parse("what's the status")
        assert isinstance(result, QueryTimerCommand)

    def test_query_what_is_status(self) -> None:
        result = self.parser.parse("what is the status")
        assert isinstance(result, QueryTimerCommand)

    def test_query_when_will_it_finish(self) -> None:
        result = self.parser.parse("when will it finish")
        assert isinstance(result, QueryTimerCommand)

    def test_pause_timer_with_name(self) -> None:
        result = self.parser.parse("pause the rice timer")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "rice"

    def test_pause_timer_no_name(self) -> None:
        result = self.parser.parse("pause timer")
        assert isinstance(result, PauseTimerCommand)
        assert result.name is None

    def test_resume_timer_with_name(self) -> None:
        result = self.parser.parse("resume the pasta timer")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name == "pasta"

    def test_resume_timer_no_name(self) -> None:
        result = self.parser.parse("resume timer")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name is None

    def test_pause_before_cancel_order(self) -> None:
        result = self.parser.parse("pause the pasta timer")
        assert isinstance(result, PauseTimerCommand)

    def test_leading_whitespace_handling(self) -> None:
        result = self.parser.parse("   set 5 minute timer")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_mixed_case(self) -> None:
        result = self.parser.parse("SET 5 MINUTE TIMER FOR PASTA")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "PASTA"

    def test_cancel_without_timer_keyword(self) -> None:
        """GIVEN "cancel pasta" (no "timer") → ParseError."""
        result = self.parser.parse("cancel pasta")
        assert isinstance(result, ParseError)

    def test_query_time_remaining(self) -> None:
        result = self.parser.parse("time remaining")
        assert isinstance(result, QueryTimerCommand)

    def test_query_when_is_pasta_done(self) -> None:
        result = self.parser.parse("when is the pasta done")
        assert isinstance(result, QueryTimerCommand)


# ── Spanish tests ──────────────────────────────────────────────────────────────


class TestTimerParserSpanish:
    """TimerParser(lang='es') SHALL match Spanish utterances."""

    def setup_method(self) -> None:
        self.parser = TimerParser(lang="es")

    def test_set_timer_configurar(self) -> None:
        """GIVEN "configurar temporizador de 10 minutos para pasta"
        WHEN parsed THEN result SHALL be SET_TIMER with duration=600.
        """
        result = self.parser.parse("configurar temporizador de 10 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600
        assert result.unit == "minutes"
        assert result.name == "pasta"

    def test_set_timer_poner(self) -> None:
        """GIVEN "poner temporizador 5 minutos" → SET_TIMER duration=300."""
        result = self.parser.parse("poner temporizador 5 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"

    def test_set_timer_crear(self) -> None:
        """GIVEN "crear un temporizador de 2 minutos" → SET_TIMER duration=120."""
        result = self.parser.parse("crear un temporizador de 2 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 120
        assert result.unit == "minutes"

    def test_set_timer_temporizador_x_minutos(self) -> None:
        """GIVEN "temporizador 10 minutos" → SET_TIMER duration=600."""
        result = self.parser.parse("temporizador 10 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600
        assert result.unit == "minutes"

    def test_set_timer_shorthand(self) -> None:
        """GIVEN "5 minutos" → SET_TIMER duration=300 (shorthand, no verb)."""
        result = self.parser.parse("5 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"

    def test_set_timer_segundos(self) -> None:
        """GIVEN "configurar temporizador 30 segundos" → SET_TIMER duration=30."""
        result = self.parser.parse("configurar temporizador 30 segundos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_set_timer_horas(self) -> None:
        """GIVEN "poner temporizador 2 horas" → SET_TIMER duration=7200."""
        result = self.parser.parse("poner temporizador 2 horas")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 7200
        assert result.unit == "hours"

    def test_cancel_timer_with_name(self) -> None:
        """GIVEN "cancelar el temporizador pasta" → CANCEL_TIMER name='pasta'."""
        result = self.parser.parse("cancelar el temporizador pasta")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "pasta"

    def test_cancel_timer_no_name(self) -> None:
        """GIVEN "cancela el temporizador" → CANCEL_TIMER name='last'."""
        result = self.parser.parse("cancela el temporizador")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "last"

    def test_pause_timer(self) -> None:
        """GIVEN "pausar el temporizador" → PAUSE_TIMER name=None."""
        result = self.parser.parse("pausar el temporizador")
        assert isinstance(result, PauseTimerCommand)
        assert result.name is None

    def test_pause_timer_voseo(self) -> None:
        """GIVEN "pausá el temporizador" (voseo) → PAUSE_TIMER."""
        result = self.parser.parse("pausá el temporizador")
        assert isinstance(result, PauseTimerCommand)

    def test_pause_timer_with_name(self) -> None:
        """GIVEN "pausa el temporizador pasta" → PAUSE_TIMER name='pasta'."""
        result = self.parser.parse("pausa el temporizador pasta")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "pasta"

    def test_resume_timer(self) -> None:
        """GIVEN "reanudar el temporizador" → RESUME_TIMER name=None."""
        result = self.parser.parse("reanudar el temporizador")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name is None

    def test_resume_timer_with_name(self) -> None:
        """GIVEN "reanuda el temporizador pasta" → RESUME_TIMER name='pasta'."""
        result = self.parser.parse("reanuda el temporizador pasta")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name == "pasta"

    def test_extend_agregar(self) -> None:
        """GIVEN "agregar 2 minutos" → EXTEND_TIMER duration=120, unit='minutes'."""
        result = self.parser.parse("agregar 2 minutos")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 120
        assert result.unit == "minutes"

    def test_extend_anadir(self) -> None:
        """GIVEN "añadir 30 segundos" → EXTEND_TIMER duration=30."""
        result = self.parser.parse("añadir 30 segundos")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_extend_extenderle(self) -> None:
        """GIVEN "extenderle 5 minutos" → EXTEND_TIMER duration=300."""
        result = self.parser.parse("extenderle 5 minutos")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 300

    def test_reduce_reducir(self) -> None:
        """GIVEN "reducir 5 minutos" → REDUCE_TIMER duration=300."""
        result = self.parser.parse("reducir 5 minutos")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 300
        assert result.unit == "minutes"

    def test_reduce_restar(self) -> None:
        """GIVEN "restar 30 segundos" → REDUCE_TIMER duration=30."""
        result = self.parser.parse("restar 30 segundos")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 30
        assert result.unit == "seconds"

    def test_reduce_quitarle(self) -> None:
        """GIVEN "quitarle 2 minutos" → REDUCE_TIMER duration=120."""
        result = self.parser.parse("quitarle 2 minutos")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 120

    def test_rename_temporizador_a(self) -> None:
        """GIVEN "renombrar temporizador a arroz" → RENAME_TIMER name='arroz'."""
        result = self.parser.parse("renombrar temporizador a arroz")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "arroz"

    def test_rename_direct(self) -> None:
        """GIVEN "renombrar a arroz" → RENAME_TIMER name='arroz'."""
        result = self.parser.parse("renombrar a arroz")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "arroz"

    def test_query_cuanto_tiempo_falta(self) -> None:
        """GIVEN "cuánto tiempo falta" → QUERY_TIMER."""
        result = self.parser.parse("cuánto tiempo falta")
        assert isinstance(result, QueryTimerCommand)

    def test_query_cuanto_queda(self) -> None:
        """GIVEN "cuánto queda" → QUERY_TIMER."""
        result = self.parser.parse("cuánto queda")
        assert isinstance(result, QueryTimerCommand)

    def test_query_tiempo_restante(self) -> None:
        """GIVEN "tiempo restante" → QUERY_TIMER."""
        result = self.parser.parse("tiempo restante")
        assert isinstance(result, QueryTimerCommand)

    def test_query_tiempo_que_queda(self) -> None:
        """GIVEN "tiempo que queda" → QUERY_TIMER."""
        result = self.parser.parse("tiempo que queda")
        assert isinstance(result, QueryTimerCommand)

    def test_query_cuando_termina(self) -> None:
        """GIVEN "cuándo termina" → QUERY_TIMER."""
        result = self.parser.parse("cuándo termina")
        assert isinstance(result, QueryTimerCommand)

    def test_query_cuando_finaliza(self) -> None:
        """GIVEN "cuándo finaliza" → QUERY_TIMER."""
        result = self.parser.parse("cuándo finaliza")
        assert isinstance(result, QueryTimerCommand)

    def test_query_que_tiempo_queda(self) -> None:
        """GIVEN "qué tiempo queda" → QUERY_TIMER."""
        result = self.parser.parse("qué tiempo queda")
        assert isinstance(result, QueryTimerCommand)

    def test_query_que_resta(self) -> None:
        """GIVEN "qué resta" → QUERY_TIMER."""
        result = self.parser.parse("qué resta")
        assert isinstance(result, QueryTimerCommand)

    def test_partial_duration_returns_parse_error(self) -> None:
        """GIVEN "configurar temporizador para" (no duration) → ParseError."""
        result = self.parser.parse("configurar temporizador para")
        assert isinstance(result, ParseError)

    def test_ambiguous_intent_pause_wins(self) -> None:
        """GIVEN "pausar cancelar temporizador" → PAUSE wins (evaluated before CANCEL)."""
        result = self.parser.parse("pausar cancelar temporizador")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "cancelar"


class TestTimerParserSpanishEdgeCases:
    """Additional Spanish edge cases."""

    def setup_method(self) -> None:
        self.parser = TimerParser(lang="es")

    def test_leading_whitespace(self) -> None:
        """GIVEN text with leading whitespace → should still parse."""
        result = self.parser.parse("   configurar temporizador 5 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_mixed_case(self) -> None:
        """GIVEN uppercase text → should still parse."""
        result = self.parser.parse("CONFIGURAR TEMPORIZADOR 5 MINUTOS PARA PASTA")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "PASTA"

    def test_cancel_without_temporizador_keyword(self) -> None:
        """GIVEN "cancelar pasta" (no "temporizador") → ParseError."""
        result = self.parser.parse("cancelar pasta")
        assert isinstance(result, ParseError)

    def test_pause_timer_no_name(self) -> None:
        """GIVEN "pausar temporizador" → PAUSE_TIMER name=None."""
        result = self.parser.parse("pausar temporizador")
        assert isinstance(result, PauseTimerCommand)
        assert result.name is None

    def test_resume_timer_no_name(self) -> None:
        """GIVEN "reanudar temporizador" → RESUME_TIMER name=None."""
        result = self.parser.parse("reanudar temporizador")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name is None

    def test_set_timer_con_nombre(self) -> None:
        """GIVEN "crear temporizador 5 minutos para pasta" with named timer."""
        result = self.parser.parse("crear temporizador 5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"

    def test_set_timer_llamado(self) -> None:
        """GIVEN "configurar temporizador 10 minutos llamado arroz"."""
        result = self.parser.parse("configurar temporizador 10 minutos llamado arroz")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 600
        assert result.name == "arroz"

    def test_temporizador_no_match(self) -> None:
        """GIVEN random Spanish text → ParseError."""
        result = self.parser.parse("hacer algo aleatorio")
        assert isinstance(result, ParseError)
