"""LLM-based intent parser adapter using OpenAI chat completions.

Falls back to the regex-based ``TimerParserAdapter`` when the LLM is
unavailable or returns an unparseable response.

Usage::

    parser = LLMIntentParser()                         # needs OPENAI_API_KEY
    parser = LLMIntentParser(api_key="sk-...")         # explicit key
    parser = LLMIntentParser(api_key=None)             # regex-only fallback
"""

from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from cuqui.adapters.parser_rules.adapter import TimerParserAdapter
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
from cuqui.domain.parser import ParseError

logger = logging.getLogger(__name__)

__all__ = ["LLMIntentParser"]

_SYSTEM_PROMPT = """\
You are a timer command parser for a cooking app called Cuqui.
Given a user's natural language text (transcribed from voice), extract the
intended command and return ONLY a JSON object — no explanation, no markdown.

## Commands

1. **set_timer** — Create a new timer
   - `duration_seconds` (int, REQUIRED, > 0)
   - `name` (string, optional)

2. **cancel_timer** — Cancel / stop a timer
   - `name` (string, optional, defaults to "last")

3. **pause_timer** — Pause a running timer
   - `name` (string, optional)

4. **resume_timer** — Resume a paused timer
   - `name` (string, optional)

5. **extend_timer** — Add time to a running timer
   - `duration_seconds` (int, REQUIRED, > 0)
   - `name` (string, optional)

6. **reduce_timer** — Subtract time from a running timer
   - `duration_seconds` (int, REQUIRED, > 0)
   - `name` (string, optional)

7. **rename_timer** — Rename a timer
   - `name` (string, REQUIRED — the NEW name)
   - `target_name` (string, optional — the timer to rename)

8. **query_timer** — Ask how much time is left
   - `name` (string, optional)

## Duration rules (CRITICAL)

ALWAYS compute the TOTAL duration in seconds.

Examples:
- "2 minutos" → 120
- "1 hora y 20 minutos" → 4800
- "dos horas y media" → 9000
- "medio minuto" → 30
- "un cuarto de hora" → 900
- "3 horas 15 minutos y 30 segundos" → 11730
- "30 seg" → 30
- "2 horas para pasta" → 7200 (name: "pasta")

Spanish number words:
cero=0, un/una/uno=1, dos=2, tres=3, cuatro=4, cinco=5, seis=6, siete=7,
ocho=8, nueve=9, diez=10, once=11, doce=12, trece=13, catorce=14, quince=15,
veinte=20, treinta=30, cuarenta=40, cincuenta=50, sesenta=60, setenta=70,
ochenta=80, noventa=90, cien=100, doscientos=200, trescientos=300,
cuatrocientos=400, quinientos=500
"media" = 30 (minutes), "mitad" depends on context

## Intent keywords (Spanish)

- set_timer: poner, poné, crear, configurar, temporizador, alarma, timer
- cancel_timer: cancelar, cancela, quitar, eliminar, borrar
- pause_timer: pausar, pausa, parar, detener
- resume_timer: reanudar, continuar, seguir, proseguir
- extend_timer: agregar, añadir, sumar, más tiempo, extender
- reduce_timer: quitar tiempo, reducir, restar, menos tiempo
- rename_timer: renombrar, cambiar nombre, llamar
- query_timer: cuánto falta, qué tiempo queda, cuándo termina, falta mucho

## Output examples

"poner 5 minutos para pasta"
→ {"intent": "set_timer", "duration_seconds": 300, "name": "pasta"}

"1 hora y 20 minutos"
→ {"intent": "set_timer", "duration_seconds": 4800}

"cancelar el timer de huevo"
→ {"intent": "cancel_timer", "name": "huevo"}

"agregarle 10 minutos a la pasta"
→ {"intent": "extend_timer", "duration_seconds": 600, "name": "pasta"}

"cuánto falta"
→ {"intent": "query_timer"}

"renombrar el de huevo a huevo duro"
→ {"intent": "rename_timer", "name": "huevo duro", "target_name": "huevo"}

## Rules

- If intent is ambiguous, default to set_timer.
- Return ONLY the JSON object. No extra text.
"""


class LLMIntentParser:
    """LLM-based parser with regex fallback.

    Parameters
    ----------
    api_key:
        OpenAI API key. Falls back to ``OPENAI_API_KEY`` env var.
    model:
        Model to use (default ``gpt-4o-mini``).
    fallback:
        Fallback parser (default ``TimerParserAdapter(lang="es")``).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        fallback: TimerParserAdapter | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = OpenAI(api_key=resolved_key) if resolved_key else None
        self._model = model
        self._fallback = fallback or TimerParserAdapter(lang="es")

    def parse(self, text: str) -> CuquiCommand | ParseError:
        """Parse *text* using the LLM, falling back to regex on failure."""
        if not self._client:
            return self._fallback.parse(text)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=200,
            )
            content = response.choices[0].message.content
            if content is None:
                return self._fallback.parse(text)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return self._parse_json(content, text)
        except Exception:
            logger.exception("LLM parse failed, falling back to regex")
            return self._fallback.parse(text)

    def _parse_json(
        self, content: str, original_text: str
    ) -> CuquiCommand | ParseError:
        """Convert LLM JSON output into a ``CuquiCommand``."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON: %s", content)
            return self._fallback.parse(original_text)

        intent = data.get("intent", "")
        name = data.get("name")
        target_name = data.get("target_name")
        duration = data.get("duration_seconds")

        try:
            match intent:
                case "set_timer":
                    if not duration or duration <= 0:
                        return ParseError("Invalid duration", original_text)
                    return SetTimerCommand(duration=int(duration), name=name)
                case "cancel_timer":
                    return CancelTimerCommand(name=name or "last")
                case "pause_timer":
                    return PauseTimerCommand(name=name)
                case "resume_timer":
                    return ResumeTimerCommand(name=name)
                case "extend_timer":
                    if not duration or duration <= 0:
                        return ParseError("Invalid duration", original_text)
                    return ExtendTimerCommand(
                        duration=int(duration), name=name
                    )
                case "reduce_timer":
                    if not duration or duration <= 0:
                        return ParseError("Invalid duration", original_text)
                    return ReduceTimerCommand(
                        duration=int(duration), name=name
                    )
                case "rename_timer":
                    if not name:
                        return ParseError(
                            "Missing name for rename", original_text
                        )
                    return RenameTimerCommand(
                        name=name, target_name=target_name
                    )
                case "query_timer":
                    return QueryTimerCommand(name=name)
                case _:
                    return ParseError(
                        f"Unknown intent: {intent}", original_text
                    )
        except Exception:
            logger.exception("Failed to build command from LLM output")
            return self._fallback.parse(original_text)
