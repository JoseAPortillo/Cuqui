"""Rule-based natural language parser for Cuqui cooking timer commands.

Provides:
    ParseError:   Frozen dataclass carrying error message + original text.
    TimerParser:  Class with ordered regex-list, ``.parse(text)``
                  returning ``CuquiCommand | ParseError``.

Zero framework dependencies — only Python stdlib (``re``, ``dataclasses``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
}

_UNIT_PLURAL: dict[str, str] = {
    "second": "seconds",
    "minute": "minutes",
    "hour": "hours",
}


def _to_seconds(number: int, unit_singular: str) -> int:
    """Convert *number* of *unit_singular* to total seconds."""
    return number * _UNIT_MULTIPLIER.get(unit_singular, 1)


def _pluralize(unit_singular: str) -> str:
    """Return the plural form of a time-unit label."""
    return _UNIT_PLURAL.get(unit_singular, unit_singular + "s")


# ── Timer Parser ───────────────────────────────────────────────────────────────


class TimerParser:
    """Parse natural-language utterances into typed ``CuquiCommand`` objects.

    Pattern matching is **ordered** — the first intent whose regex matches
    wins.  If no pattern matches, a ``ParseError`` is returned (never raised).

    Intent evaluation order
    -----------------------
    #. ``SET_TIMER``
    #. ``PAUSE_TIMER``      — evaluated BEFORE CANCEL so that utterances
    #. ``CANCEL_TIMER``       containing the word *cancel* (e.g. *"pause
    #. ``RESUME_TIMER``       cancel timer"*) do not accidentally trigger
    #. ``EXTEND_TIMER``       CANCEL — PAUSE is checked first.
    #. ``REDUCE_TIMER``
    #. ``RENAME_TIMER``
    #. ``QUERY_TIMER``
    """

    # ── Compiled regex patterns (module level, compiled once) ────────────

    _SET_TIMER_RE = re.compile(
        r"(?:set\s+)?(?:a\s+)?"
        r"(?:timer\s+)?(?:for\s+)?"
        r"(\d+)\s*(minute|second|hour)s?\s*"
        r"(?:timer\s+)?"
        r"(?:(?:for|called)\s+(\w+))?",
        re.IGNORECASE,
    )

    _PAUSE_TIMER_RE = re.compile(
        r"pause\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _CANCEL_TIMER_RE = re.compile(
        r"cancel\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _RESUME_TIMER_RE = re.compile(
        r"resume\s+(?:the\s+)?(?:(.+?)\s+)?timer",
        re.IGNORECASE,
    )

    _EXTEND_TIMER_RE = re.compile(
        r"(?:add|extend)(?:\s+by)?\s+"
        r"(\d+)\s*(?:more\s+)?"
        r"(minute|second|hour)s?",
        re.IGNORECASE,
    )

    _REDUCE_TIMER_RE = re.compile(
        r"(?:reduce|subtract)(?:\s+by)?\s+"
        r"(\d+)\s*(?:more\s+)?"
        r"(minute|second|hour)s?",
        re.IGNORECASE,
    )

    _RENAME_TIMER_RE = re.compile(
        r"rename\s+(?:timer\s+)?(?:to\s+)?(.+)",
        re.IGNORECASE,
    )

    _QUERY_TIMER_RE = re.compile(
        r"(?:"
        r"how\s+(?:much|long)|"
        r"time\s+(?:left|remaining)|"
        r"when\s+(?:is|will)|"
        r"what(?:'?s|\s+is)\s+(?:the\s+)?(?:status|time)"
        r")",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        # Ordered list of (compiled_regex, extractor_function).
        self._patterns: list[tuple[re.Pattern, ...]] = [
            (self._SET_TIMER_RE, self._build_set_timer),
            (self._PAUSE_TIMER_RE, self._build_pause_timer),
            (self._CANCEL_TIMER_RE, self._build_cancel_timer),
            (self._RESUME_TIMER_RE, self._build_resume_timer),
            (self._EXTEND_TIMER_RE, self._build_extend_timer),
            (self._REDUCE_TIMER_RE, self._build_reduce_timer),
            (self._RENAME_TIMER_RE, self._build_rename_timer),
            (self._QUERY_TIMER_RE, self._build_query_timer),
        ]

    # ── Public API ───────────────────────────────────────────────────────

    def parse(self, text: str) -> CuquiCommand | ParseError:
        """Try to match *text* against each intent pattern (in order).

        Returns the first matching ``CuquiCommand``, or a ``ParseError``
        if no pattern matches or required parameters are missing.
        """
        stripped = text.strip()
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
                # Extractor returned None → matched but validation failed.
                return ParseError(
                    message="Missing required parameters",
                    original_text=text,
                )

        return ParseError(
            message="No matching intent",
            original_text=text,
        )

    # ── Intent extractors (one per pattern) ───────────────────────────────

    @staticmethod
    def _build_set_timer(match: re.Match) -> CuquiCommand:
        number = int(match.group(1))
        unit_singular = match.group(2).lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        name = match.group(3)  # may be None
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
        return CancelTimerCommand()  # default name = "last"

    @staticmethod
    def _build_resume_timer(match: re.Match) -> CuquiCommand:
        name = match.group(1)  # may be None
        return ResumeTimerCommand(name=name)

    @staticmethod
    def _build_extend_timer(match: re.Match) -> CuquiCommand:
        number = int(match.group(1))
        unit_singular = match.group(2).lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        return ExtendTimerCommand(duration=duration, unit=unit)

    @staticmethod
    def _build_reduce_timer(match: re.Match) -> CuquiCommand:
        number = int(match.group(1))
        unit_singular = match.group(2).lower()
        duration = _to_seconds(number, unit_singular)
        unit = _pluralize(unit_singular)
        return ReduceTimerCommand(duration=duration, unit=unit)

    @staticmethod
    def _build_rename_timer(match: re.Match) -> CuquiCommand:
        name = match.group(1).strip()
        return RenameTimerCommand(name=name)

    @staticmethod
    def _build_query_timer(match: re.Match) -> CuquiCommand:
        return QueryTimerCommand()
