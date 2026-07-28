"""Tests for LLMIntentParser.

Covers:
- LLM returning valid JSON → correct CuquiCommand
- LLM returning invalid JSON → fallback to regex parser
- LLM raising exception → fallback to regex parser
- No API key → pure regex fallback
- All 8 intents from LLM JSON
- Compound duration parsing via LLM (the key use case)
- Markdown code fence stripping
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

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
from cuqui.domain.parser import ParseError


def _mock_openai_response(content: str) -> MagicMock:
    """Return a MagicMock that mimics OpenAI chat completion response."""
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    return mock


def _build_parser(response_content: str | None = None, side_effect=None):
    """Create LLMIntentParser with a mocked OpenAI client.

    Uses patch to intercept OpenAI() construction so that
    _client.chat.completions.create returns the expected mock.
    """
    mock_client = MagicMock()
    if side_effect is not None:
        mock_client.chat.completions.create.side_effect = side_effect
    elif response_content is not None:
        mock_client.chat.completions.create.return_value = (
            _mock_openai_response(response_content)
        )

    with patch(
        "cuqui.adapters.parser_llm.adapter.OpenAI", return_value=mock_client
    ):
        from cuqui.adapters.parser_llm.adapter import LLMIntentParser

        parser = LLMIntentParser(api_key="test-key")
    return parser


class TestLLMIntentParserNoAPIKey:
    """Without an API key, LLMIntentParser falls back to regex."""

    def test_no_key_uses_fallback(self) -> None:
        with patch(
            "cuqui.adapters.parser_llm.adapter.OpenAI", return_value=None
        ):
            from cuqui.adapters.parser_llm.adapter import LLMIntentParser

            parser = LLMIntentParser(api_key="test-key")
            # OpenAI() returning None means _client is None
            parser._client = None

        result = parser.parse("configurar 5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"


class TestLLMIntentParserSetTimer:
    """set_timer intent via LLM JSON response."""

    def test_simple_duration(self) -> None:
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "set_timer",
                    "duration_seconds": 300,
                    "name": "pasta",
                }
            )
        )
        result = parser.parse("5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"

    def test_compound_duration(self) -> None:
        """The key use case: '1 hora y 20 minutos' → 4800 seconds."""
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "set_timer",
                    "duration_seconds": 4800,
                    "name": None,
                }
            )
        )
        result = parser.parse("1 hora y 20 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 4800
        assert result.name is None

    def test_duration_with_name(self) -> None:
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "set_timer",
                    "duration_seconds": 7200,
                    "name": "huevo",
                }
            )
        )
        result = parser.parse("2 horas para el huevo")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 7200
        assert result.name == "huevo"

    def test_no_duration_returns_parse_error(self) -> None:
        parser = _build_parser(
            json.dumps({"intent": "set_timer", "name": "test"})
        )
        result = parser.parse("algo raro")
        assert isinstance(result, ParseError)


class TestLLMIntentParserCancelTimer:
    def test_cancel_with_name(self) -> None:
        parser = _build_parser(
            json.dumps({"intent": "cancel_timer", "name": "pasta"})
        )
        result = parser.parse("cancelar el timer de pasta")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "pasta"

    def test_cancel_without_name(self) -> None:
        parser = _build_parser(json.dumps({"intent": "cancel_timer"}))
        result = parser.parse("cancelar")
        assert isinstance(result, CancelTimerCommand)
        assert result.name == "last"


class TestLLMIntentParserPauseResume:
    def test_pause(self) -> None:
        parser = _build_parser(
            json.dumps({"intent": "pause_timer", "name": "huevo"})
        )
        result = parser.parse("pausar el de huevo")
        assert isinstance(result, PauseTimerCommand)
        assert result.name == "huevo"

    def test_resume(self) -> None:
        parser = _build_parser(
            json.dumps({"intent": "resume_timer", "name": "huevo"})
        )
        result = parser.parse("reanudar el de huevo")
        assert isinstance(result, ResumeTimerCommand)
        assert result.name == "huevo"


class TestLLMIntentParserExtendReduce:
    def test_extend(self) -> None:
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "extend_timer",
                    "duration_seconds": 600,
                    "name": "pasta",
                }
            )
        )
        result = parser.parse("agregarle 10 minutos a la pasta")
        assert isinstance(result, ExtendTimerCommand)
        assert result.duration == 600
        assert result.name == "pasta"

    def test_reduce(self) -> None:
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "reduce_timer",
                    "duration_seconds": 120,
                    "name": "pasta",
                }
            )
        )
        result = parser.parse("quitarle 2 minutos a la pasta")
        assert isinstance(result, ReduceTimerCommand)
        assert result.duration == 120
        assert result.name == "pasta"


class TestLLMIntentParserRenameQuery:
    def test_rename(self) -> None:
        parser = _build_parser(
            json.dumps(
                {
                    "intent": "rename_timer",
                    "name": "huevo duro",
                    "target_name": "huevo",
                }
            )
        )
        result = parser.parse("renombrar el de huevo a huevo duro")
        assert isinstance(result, RenameTimerCommand)
        assert result.name == "huevo duro"
        assert result.target_name == "huevo"

    def test_query(self) -> None:
        parser = _build_parser(json.dumps({"intent": "query_timer"}))
        result = parser.parse("cuánto falta")
        assert isinstance(result, QueryTimerCommand)


class TestLLMIntentParserFallback:
    """When LLM fails, fall back to regex parser."""

    def test_invalid_json_falls_back(self) -> None:
        parser = _build_parser("not valid json {{{")
        result = parser.parse("configurar 5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_api_exception_falls_back(self) -> None:
        parser = _build_parser(side_effect=RuntimeError("API down"))
        result = parser.parse("configurar 5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300

    def test_unknown_intent_returns_parse_error(self) -> None:
        parser = _build_parser(
            json.dumps({"intent": "nonexistent_intent"})
        )
        result = parser.parse("algo")
        assert isinstance(result, ParseError)


class TestLLMIntentParserMarkdownFences:
    """LLMs sometimes wrap JSON in markdown code fences."""

    def test_strips_json_fence(self) -> None:
        fenced = (
            '```json\n'
            '{"intent": "set_timer", "duration_seconds": 300, "name": "pasta"}\n'
            "```"
        )
        parser = _build_parser(fenced)
        result = parser.parse("5 minutos para pasta")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 300
        assert result.name == "pasta"

    def test_strips_plain_fence(self) -> None:
        fenced = (
            "```\n"
            '{"intent": "set_timer", "duration_seconds": 120}\n'
            "```"
        )
        parser = _build_parser(fenced)
        result = parser.parse("2 minutos")
        assert isinstance(result, SetTimerCommand)
        assert result.duration == 120
