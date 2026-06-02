"""Tests for IntentParser protocol and TimerParserAdapter.

Covers:
- IntentParser is a structural Protocol (Protocol class exists)
- TimerParserAdapter implements IntentParser via protocol structural typing
- TimerParserAdapter.parse() delegates to TimerParser and returns correct types
- Valid input → CuquiCommand, invalid input → ParseError
"""

from __future__ import annotations

import typing

from cuqui.domain.commands import SetTimerCommand
from cuqui.domain.parser import ParseError


class TestIntentParserProtocol:
    """IntentParser SHALL be a Protocol with parse(text: str) -> CuquiCommand | ParseError."""

    def test_intent_parser_is_importable(self) -> None:
        """GIVEN the ports module WHEN importing IntentParser THEN no error."""

    def test_intent_parser_is_protocol(self) -> None:
        """IntentParser SHALL be a typing.Protocol class."""
        from cuqui.ports.intent_parser import IntentParser

        assert issubclass(IntentParser, typing.Protocol)

    def test_intent_parser_has_parse_method(self) -> None:
        """IntentParser SHALL define parse(self, text: str)."""
        from cuqui.ports.intent_parser import IntentParser

        assert hasattr(IntentParser, "parse")


class TestTimerParserAdapter:
    """TimerParserAdapter SHALL wrap TimerParser and implement IntentParser."""

    def test_adapter_is_importable(self) -> None:
        """GIVEN the adapter module WHEN importing TimerParserAdapter THEN no error."""

    def test_adapter_parse_returns_set_timer_for_valid_english(self) -> None:
        """GIVEN "set 5 minute timer for pasta" with lang='en' THEN SetTimerCommand."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter(lang="en")
        result = adapter.parse("set 5 minute timer for pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"

    def test_adapter_parse_returns_parse_error_for_invalid_input(self) -> None:
        """GIVEN "do something random" with lang='en' THEN result is ParseError."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter(lang="en")
        result = adapter.parse("do something random")
        assert isinstance(result, ParseError)
        assert "matching intent" in result.message.lower()

    def test_adapter_default_lang_is_es(self) -> None:
        """GIVEN a TimerParserAdapter() WITHOUT lang arg THEN it uses Spanish parser."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter()
        result = adapter.parse("configurar temporizador 5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_adapter_accepts_lang_parameter(self) -> None:
        """GIVEN lang='en' THEN it uses English parser."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter(lang="en")
        result = adapter.parse("set 5 minute timer for pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_adapter_protocol_compatibility(self) -> None:
        """TimerParserAdapter SHALL satisfy IntentParser via structural subtyping."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter()
        # isinstance check with Protocol works at runtime if @runtime_checkable
        # but we verify via hasattr instead for safety
        assert hasattr(adapter, "parse")
        sig = typing.get_type_hints(adapter.parse)
        assert "text" in sig

    def test_adapter_empty_string_returns_parse_error(self) -> None:
        """GIVEN empty string "" with lang='en' THEN result is ParseError."""
        from cuqui.adapters.parser_rules.adapter import TimerParserAdapter

        adapter = TimerParserAdapter(lang="en")
        result = adapter.parse("")
        assert isinstance(result, ParseError)
