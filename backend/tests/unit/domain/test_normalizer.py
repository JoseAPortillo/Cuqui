"""Tests for Spanish text normalizer.

Covers:
- Number word → digit conversion
- Compound duration normalization
- Fraction expressions
- Non-timer text passes through unchanged
- Integration with TimerParser
"""

from __future__ import annotations

from cuqui.domain.normalizer import (
    _normalize_compound_durations,
    _normalize_fractions,
    _normalize_number_words,
    _parse_duration_parts,
    _text_to_number,
    normalize_es,
)


class TestTextToNumber:
    """Convert Spanish number words to integers."""

    def test_single_ones(self) -> None:
        assert _text_to_number("uno") == 1
        assert _text_to_number("tres") == 3
        assert _text_to_number("cinco") == 5

    def test_single_teens(self) -> None:
        assert _text_to_number("diez") == 10
        assert _text_to_number("once") == 11
        assert _text_to_number("quince") == 15

    def test_single_tens(self) -> None:
        assert _text_to_number("veinte") == 20
        assert _text_to_number("treinta") == 30
        assert _text_to_number("noventa") == 90

    def test_compound_tens(self) -> None:
        assert _text_to_number("treinta y cinco") == 35
        assert _text_to_number("cuarenta y dos") == 42
        assert _text_to_number("veintiuno") == 21

    def test_hundreds(self) -> None:
        assert _text_to_number("cien") == 100
        assert _text_to_number("doscientos") == 200
        assert _text_to_number("quinientos") == 500

    def test_compound_hundreds(self) -> None:
        assert _text_to_number("doscientos treinta y cinco") == 235
        assert _text_to_number("ciento veinte") == 120

    def test_un_returns_one(self) -> None:
        assert _text_to_number("un") == 1
        assert _text_to_number("una") == 1

    def test_empty_returns_none(self) -> None:
        assert _text_to_number("") is None
        assert _text_to_number("  ") is None

    def test_non_number_returns_none(self) -> None:
        assert _text_to_number("pasta") is None


class TestNormalizeNumberWords:
    """Replace number words with digits in text."""

    def test_simple_replacement(self) -> None:
        result = _normalize_number_words("dos minutos")
        assert result == "2 minutos"

    def test_compound_number(self) -> None:
        result = _normalize_number_words("treinta y cinco segundos")
        assert result == "35 segundos"

    def test_no_numbers_unchanged(self) -> None:
        result = _normalize_number_words("para pasta")
        assert result == "para pasta"

    def test_mixed_text(self) -> None:
        result = _normalize_number_words("poner tres horas para huevo")
        assert result == "poner 3 horas para huevo"


class TestNormalizeFractions:
    """Replace fraction expressions with explicit values."""

    def test_media_hora(self) -> None:
        result = _normalize_fractions("media hora")
        assert result == "30 minutos"

    def test_un_cuarto(self) -> None:
        result = _normalize_fractions("un cuarto de hora")
        assert result == "15 minutos"

    def test_tres_cuartos(self) -> None:
        result = _normalize_fractions("tres cuartos de hora")
        assert result == "45 minutos"

    def test_media_alone(self) -> None:
        result = _normalize_fractions("media")
        assert result == "30 minutos"

    def test_no_fraction_unchanged(self) -> None:
        result = _normalize_fractions("30 minutos")
        assert result == "30 minutos"


class TestParseDurationParts:
    """Parse duration expressions to total seconds."""

    def test_simple_minutes(self) -> None:
        assert _parse_duration_parts("30 minutos") == 1800

    def test_simple_hours(self) -> None:
        assert _parse_duration_parts("2 horas") == 7200

    def test_simple_seconds(self) -> None:
        assert _parse_duration_parts("45 segundos") == 45

    def test_compound_hours_minutes(self) -> None:
        assert _parse_duration_parts("1 hora y 20 minutos") == 4800

    def test_compound_multiple(self) -> None:
        assert _parse_duration_parts("2 horas 30 minutos 10 segundos") == 9010

    def test_compound_with_and(self) -> None:
        assert _parse_duration_parts("1 hora y 30 minutos") == 5400


class TestNormalizeCompoundDurations:
    """Normalize compound duration expressions."""

    def test_compound_with_name(self) -> None:
        result = _normalize_compound_durations("1 hora y 20 minutos para pasta")
        assert result == "80 minutos para pasta"

    def test_compound_without_name(self) -> None:
        result = _normalize_compound_durations("1 hora y 20 minutos")
        assert result == "80 minutos"

    def test_simple_unchanged(self) -> None:
        result = _normalize_compound_durations("30 minutos para pasta")
        assert result == "30 minutos para pasta"

    def test_no_duration_unchanged(self) -> None:
        result = _normalize_compound_durations("para pasta")
        assert result == "para pasta"

    def test_compound_llamado(self) -> None:
        result = _normalize_compound_durations("2 horas y 30 minutos llamado huevo")
        assert result == "150 minutos llamado huevo"


class TestNormalizeEs:
    """Full normalization pipeline."""

    def test_number_words_and_compound(self) -> None:
        result = normalize_es("dos horas y 30 minutos para pasta")
        assert result == "150 minutos para pasta"

    def test_fraction_and_name(self) -> None:
        result = normalize_es("un cuarto de hora para el huevo")
        assert result == "15 minutos para el huevo"

    def test_simple_passthrough(self) -> None:
        result = normalize_es("5 minutos para pasta")
        assert result == "5 minutos para pasta"

    def test_non_timer_passthrough(self) -> None:
        result = normalize_es("cancelar el timer de pasta")
        assert result == "cancelar el timer de pasta"

    def test_media_hora_compound(self) -> None:
        result = normalize_es("media hora y 10 minutos")
        assert result == "40 minutos"

    def test_complete_example(self) -> None:
        result = normalize_es("poner una hora y quince minutos para los fideos")
        assert result == "75 minutos para los fideos"


class TestIntegrationWithParser:
    """Normalizer works end-to-end through TimerParser."""

    def test_compound_duration_parses_correctly(self) -> None:
        from cuqui.domain.parser import TimerParser
        from cuqui.domain.commands import SetTimerCommand

        parser = TimerParser(lang="es")
        result = parser.parse("1 hora y 20 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 4800
        assert result.name == "pasta"

    def test_number_words_parses_correctly(self) -> None:
        from cuqui.domain.parser import TimerParser
        from cuqui.domain.commands import SetTimerCommand

        parser = TimerParser(lang="es")
        result = parser.parse("dos horas para el huevo")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 7200
        assert result.name == "el huevo"

    def test_fraction_parses_correctly(self) -> None:
        from cuqui.domain.parser import TimerParser
        from cuqui.domain.commands import SetTimerCommand

        parser = TimerParser(lang="es")
        result = parser.parse("un cuarto de hora para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 900
        assert result.name == "pasta"

    def test_existing_simple_timer_still_works(self) -> None:
        from cuqui.domain.parser import TimerParser
        from cuqui.domain.commands import SetTimerCommand

        parser = TimerParser(lang="es")
        result = parser.parse("5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"

    def test_english_not_affected(self) -> None:
        from cuqui.domain.parser import TimerParser
        from cuqui.domain.commands import SetTimerCommand

        parser = TimerParser(lang="en")
        result = parser.parse("set 5 minute timer for pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"
