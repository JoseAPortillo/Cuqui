"""Rule-based natural language parser for Cuqui cooking timer commands.

Provides:
    ParseError:   Frozen dataclass carrying error message + original text.
    TimerParser:  Class with ordered regex-list per language, ``.parse(text)``
                  returning ``CuquiCommand | ParseError``.

Zero framework dependencies — only Python stdlib (``re``, ``dataclasses``).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from cuqui.domain.commands import (
    CancelTimerCommand,
    CuquiCommand,
    ExtendTimerCommand,
    PauseTimerCommand,
    QueryTimerCommand,
    ReduceTimerCommand,
    RenameTimerCommand,
    ResumeTimerCommand,
    SetTimerCommand,
)

__all__ = [
    "ParseError",
    "TimerParser",
]

# ── Parse Error ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ParseError:
    """A failed parse result — not an exception, just a value object.

    Attributes:
        message:       Human-readable explanation of why parsing failed.
        original_text: The input text that could not be parsed.
    """

    message: str
    original_text: str


# ── Unit conversion helpers ────────────────────────────────────────────────────

_UNIT_MULTIPLIER: dict[str, int] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "segundo": 1,
    "minuto": 60,
    "hora": 3600,
    "día": 86400,
    "dia": 86400,
}

_UNIT_ENGLISH: dict[str, str] = {
    "segundo": "second",
    "minuto": "minute",
    "hora": "hour",
    "día": "day",
    "dia": "day",
}

_UNIT_PLURAL: dict[str, str] = {
    "second": "seconds",
    "minute": "minutes",
    "hour": "hours",
    "day": "days",
}


def _normalize_unit(unit_singular: str) -> str:
    """Map a time-unit label (any supported language) to its English singular form.

    Returns the input unchanged if no mapping exists (safe fallback).
    """
    return _UNIT_ENGLISH.get(unit_singular, unit_singular)


def _to_seconds(number: int, unit_singular: str) -> int:
    """Convert *number* of *unit_singular* to total seconds."""
    return number * _UNIT_MULTIPLIER.get(_normalize_unit(unit_singular), 1)


def _pluralize(unit_singular: str) -> str:
    """Return the plural form of a time-unit label (always English)."""
    english = _normalize_unit(unit_singular)
    return _UNIT_PLURAL.get(english, english + "s")


def _parse_number(text: str) -> int:
    """Convert a Spanish number word or digit string to an integer."""
    word_map = {"un": 1, "una": 1, "uno": 1}
    key = text.strip().lower()
    if key in word_map:
        return word_map[key]
    return int(text)


# ── Timer Parser ───────────────────────────────────────────────────────────────


class TimerParser:
    """Parse natural-language utterances into typed ``CuquiCommand`` objects.

    Pattern matching is **ordered** — the first intent whose regex matches
    wins.  If no pattern matches, a ``ParseError`` is returned (never raised).

    Parameters
    ----------
    lang:
        Language code (``"en"`` or ``"es"``).  Defaults to ``"es"``.

    Intent evaluation order (same for all languages)
    -------------------------------------------------
    #. ``SET_TIMER``
    #. ``PAUSE_TIMER``      — evaluated BEFORE CANCEL so that utterances
    #. ``CANCEL_TIMER``       containing the word *cancel* (e.g. *"pause
    #. ``RESUME_TIMER``       cancel timer"*) do not accidentally trigger
    #. ``EXTEND_TIMER``       CANCEL — PAUSE is checked first.
    #. ``REDUCE_TIMER``
    #. ``RENAME_TIMER``
    #. ``QUERY_TIMER``
    """

    # ── English patterns ──────────────────────────────────────────────────

    _SET_TIMER_EN = re.compile(
        r"(?:set\s+)?(?:a\s+)?"
        r"(?:timer\s+)?(?:for\s+)?"
        r"(\d+)\s*(minute|second|hour)?s?\s*"
        r"(?:timer\s+)?"
        r"(?:(?:for|called)\s+)?(.+)?",
        re.IGNORECASE,
    )

    _PAUSE_TIMER_EN = re.compile(
        r"pause\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _CANCEL_TIMER_EN = re.compile(
        r"cancel\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _RESUME_TIMER_EN = re.compile(
        r"resume\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _EXTEND_TIMER_EN = re.compile(
        r"(?:add|extend)(?:\s+by)?\s+"
        r"(\d+)\s*(?:more\s+)?"
        r"(minute|second|hour)?s?\s*"
        r"(?:to\s+)?(.+)?",
        re.IGNORECASE,
    )

    _REDUCE_TIMER_EN = re.compile(
        r"(?:reduce|subtract)(?:\s+by)?\s+"
        r"(\d+)\s*(?:more\s+)?"
        r"(minute|second|hour)?s?\s*"
        r"(?:from\s+)?(.+)?",
        re.IGNORECASE,
    )

    _RENAME_TIMER_EN = re.compile(
        r"rename\s+(?:timer\s+)?(?:to\s+)?(.+)",
        re.IGNORECASE,
    )

    _QUERY_TIMER_EN = re.compile(
        r"(?:"
        r"how\s+(?:much|long)|"
        r"time\s+(?:left|remaining)|"
        r"when\s+(?:is|will)|"
        r"what(?:'?s|\s+is)\s+(?:the\s+)?(?:status|time)"
        r")",
        re.IGNORECASE,
    )

    # ── Spanish patterns ──────────────────────────────────────────────────

    _SET_TIMER_ES = re.compile(
        r"(?:(?:configur(?:ar|á|a)|pon(?:e|é|er)?|crear|set(?:eá|ear))"
        r"\s+(?:un\s+(?=temporizador))?)?"
        r"(?:temporizador\s+)?(?:de\s+|para\s+)?"
        r"(\d+|un(?:a|o)?)\s*(minuto|segundo|hora|d(?:í|i)a)?s?\s*"
        r"(?:temporizador\s+)?"
        r"(?:(?:para|llamado|a)\s+)?(.+)?",
        re.IGNORECASE,
    )

    # PAUSE 1: pausar [el] temporizador [de] [name]
    _PAUSE_TIMER_ES = re.compile(
        r"paus(?:a|á|ar)\s+(?:el\s+)?temporizador(?:\s+(?:de\s+)?(.+))?",
        re.IGNORECASE,
    )
    # PAUSE 2: pausar [el] [name] temporizador (ambiguous intent, name before keyword)
    _PAUSE_TIMER_ES_NAME_FIRST = re.compile(
        r"paus(?:a|á|ar)\s+(?:el\s+)?(.+?)\s+temporizador",
        re.IGNORECASE,
    )
    # PAUSE 3: pausar [el|la] [name]  (short form, no "temporizador")
    _PAUSE_TIMER_ES_ONLY_NAME = re.compile(
        r"paus(?:a|á|ar)\s+(.+)",
        re.IGNORECASE,
    )

    # CANCEL 1: cancelar [el] temporizador [de] [name]
    _CANCEL_TIMER_ES = re.compile(
        r"cancel(?:a|á|ar)\s+(?:el\s+)?temporizador(?:\s+(?:de\s+)?(.+))?",
        re.IGNORECASE,
    )
    # CANCEL 2: cancelar [el] [name] temporizador
    _CANCEL_TIMER_ES_NAME_FIRST = re.compile(
        r"cancel(?:a|á|ar)\s+(?:el\s+)?(.+?)\s+temporizador",
        re.IGNORECASE,
    )
    # CANCEL 3: cancelar [el|la] [name]  (short form, no "temporizador")
    _CANCEL_TIMER_ES_ONLY_NAME = re.compile(
        r"cancel(?:a|á|ar)\s+(.+)",
        re.IGNORECASE,
    )

    # RESUME 1: reanudar [el] temporizador [de] [name]
    _RESUME_TIMER_ES = re.compile(
        r"reanud(?:a|á|ar)\s+(?:el\s+)?temporizador(?:\s+(?:de\s+)?(.+))?",
        re.IGNORECASE,
    )
    # RESUME 2: reanudar [el] [name] temporizador
    _RESUME_TIMER_ES_NAME_FIRST = re.compile(
        r"reanud(?:a|á|ar)\s+(?:el\s+)?(.+?)\s+temporizador",
        re.IGNORECASE,
    )
    # RESUME 3: reanudar [el|la] [name]  (short form, no "temporizador")
    _RESUME_TIMER_ES_ONLY_NAME = re.compile(
        r"reanud(?:a|á|ar)\s+(.+)",
        re.IGNORECASE,
    )

    _EXTEND_TIMER_ES = re.compile(
        r"(?:agreg(?:ar|á|a)|añad(?:ir|í|e)|anad(?:ir|í|e)|extiende|extender)"
        r"(?:le\s+)?\s*"
        r"(\d+|un(?:a|o)?)\s*(?:más\s+)?"
        r"(minuto|segundo|hora|d(?:í|i)a)s?\s*"
        r"(?:(?:a|para|al)\s+)?(.+)?",
        re.IGNORECASE,
    )

    _REDUCE_TIMER_ES = re.compile(
        r"(?:reduc(?:ir|í|e)|rest(?:ar|á|a)|quit(?:ar|á|a))(?:le\s+)?\s*"
        r"(\d+|un(?:a|o)?)\s*(?:más\s+)?"
        r"(minuto|segundo|hora|d(?:í|i)a)s?\s*"
        r"(?:(?:a|para|al)\s+)?(.+)?",
        re.IGNORECASE,
    )

    _RENAME_TIMER_ES = re.compile(
        r"renombr(?:a|á|ar)\s+(?:temporizador\s+)?(?:a\s+)?(.+)",
        re.IGNORECASE,
    )

    _QUERY_TIMER_ES = re.compile(
        r"(?:"
        r"cuánto\s+(?:tiempo\s+)?(?:falta|queda)|"
        r"tiempo\s+(?:restante|que\s+queda)|"
        r"cuándo\s+(?:termina|finaliza)|"
        r"qué\s+(?:tiempo\s+)?(?:queda|resta)"
        r")",
        re.IGNORECASE,
    )

    LANGS: ClassVar[dict[str, list[tuple[re.Pattern, Callable[..., CuquiCommand]]]]] = {}

    def __init__(self, lang: str = "es") -> None:
        if lang not in self.LANGS:
            raise ValueError(f"Unsupported language: {lang!r}")
        self._patterns = self.LANGS[lang]

    # ── Public API ───────────────────────────────────────────────────────

    def parse(self, text: str) -> CuquiCommand | ParseError:
        """Try to match *text* against each intent pattern (in order).

        Returns the first matching ``CuquiCommand``, or a ``ParseError``
        if no pattern matches or required parameters are missing.
        """
        stripped = text.strip().rstrip(".,!?;:")
        if not stripped:
            return ParseError(
                message="No matching intent",
                original_text=text,
            )

        for regex, builder in self._patterns:
            match = regex.match(stripped)
            if match:
                try:
                    command = builder(match)
                except ValueError:
                    return ParseError(
                        message="Missing required parameters",
                        original_text=text,
                    )
                if command is not None:
                    return command
                return ParseError(
                    message="Missing required parameters",
                    original_text=text,
                )

        return ParseError(
            message="No matching intent",
            original_text=text,
        )

    # ── Intent extractors (shared across languages) ──────────────────────

    @staticmethod
    def _build_set_timer(match: re.Match) -> CuquiCommand:
        number = _parse_number(match.group(1))
        unit_singular = (match.group(2) or "minute").lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        name = match.group(3).strip() if match.group(3) else None
        return SetTimerCommand(duration=duration, unit=unit, name=name)

    @staticmethod
    def _build_pause_timer(match: re.Match) -> CuquiCommand:
        name = match.group(1)  # may be None
        return PauseTimerCommand(name=name)

    @staticmethod
    def _build_cancel_timer(match: re.Match) -> CuquiCommand:
        name = match.group(1)  # may be None
        if name is not None:
            return CancelTimerCommand(name=name)
        return CancelTimerCommand()

    @staticmethod
    def _build_resume_timer(match: re.Match) -> CuquiCommand:
        name = match.group(1)  # may be None
        return ResumeTimerCommand(name=name)

    @staticmethod
    def _build_extend_timer(match: re.Match) -> CuquiCommand:
        number = _parse_number(match.group(1))
        unit_singular = (match.group(2) or "minute").lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        name = match.group(3).strip() if match.group(3) else None
        return ExtendTimerCommand(duration=duration, unit=unit, name=name)

    @staticmethod
    def _build_reduce_timer(match: re.Match) -> CuquiCommand:
        number = _parse_number(match.group(1))
        unit_singular = (match.group(2) or "minute").lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        name = match.group(3).strip() if match.group(3) else None
        return ReduceTimerCommand(duration=duration, unit=unit, name=name)

    @staticmethod
    def _build_rename_timer(match: re.Match) -> CuquiCommand:
        raw = match.group(1).strip()
        # Handle separator: "old_name a new_name" (ES) or "old_name to new_name" (EN).
        target_name = None
        new_name = raw
        for sep in (" a ", " to "):
            if sep in raw:
                parts = raw.rsplit(sep, 1)
                target_name = parts[0].strip() or None
                new_name = parts[1].strip()
                break
        return RenameTimerCommand(name=new_name, target_name=target_name)

    @staticmethod
    def _build_query_timer(match: re.Match) -> CuquiCommand:
        return QueryTimerCommand()


# ── Language pattern registry ──────────────────────────────────────────────────

TimerParser.LANGS: dict[str, list[tuple[re.Pattern, Callable[..., CuquiCommand]]]] = {
    "en": [
        (TimerParser._SET_TIMER_EN, TimerParser._build_set_timer),
        (TimerParser._PAUSE_TIMER_EN, TimerParser._build_pause_timer),
        (TimerParser._CANCEL_TIMER_EN, TimerParser._build_cancel_timer),
        (TimerParser._RESUME_TIMER_EN, TimerParser._build_resume_timer),
        (TimerParser._EXTEND_TIMER_EN, TimerParser._build_extend_timer),
        (TimerParser._REDUCE_TIMER_EN, TimerParser._build_reduce_timer),
        (TimerParser._RENAME_TIMER_EN, TimerParser._build_rename_timer),
        (TimerParser._QUERY_TIMER_EN, TimerParser._build_query_timer),
    ],
    "es": [
        (TimerParser._SET_TIMER_ES, TimerParser._build_set_timer),
        (TimerParser._PAUSE_TIMER_ES, TimerParser._build_pause_timer),
        (TimerParser._PAUSE_TIMER_ES_NAME_FIRST, TimerParser._build_pause_timer),
        (TimerParser._PAUSE_TIMER_ES_ONLY_NAME, TimerParser._build_pause_timer),
        (TimerParser._CANCEL_TIMER_ES, TimerParser._build_cancel_timer),
        (TimerParser._CANCEL_TIMER_ES_NAME_FIRST, TimerParser._build_cancel_timer),
        (TimerParser._CANCEL_TIMER_ES_ONLY_NAME, TimerParser._build_cancel_timer),
        (TimerParser._RESUME_TIMER_ES, TimerParser._build_resume_timer),
        (TimerParser._RESUME_TIMER_ES_NAME_FIRST, TimerParser._build_resume_timer),
        (TimerParser._RESUME_TIMER_ES_ONLY_NAME, TimerParser._build_resume_timer),
        (TimerParser._EXTEND_TIMER_ES, TimerParser._build_extend_timer),
        (TimerParser._REDUCE_TIMER_ES, TimerParser._build_reduce_timer),
        (TimerParser._RENAME_TIMER_ES, TimerParser._build_rename_timer),
        (TimerParser._QUERY_TIMER_ES, TimerParser._build_query_timer),
    ],
}
