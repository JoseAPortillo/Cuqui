"""Spanish text normalizer for timer commands.

Pre-processes Spanish text to normalize compound durations and number words
before the regex parser sees it.  Pure stdlib — no external dependencies.

Examples::

    normalize_es("1 hora y 20 minutos para pasta")
    # → "80 minutos para pasta"

    normalize_es("dos horas y media")
    # → "150 minutos"

    normalize_es("un cuarto de hora para el huevo")
    # → "15 minutos para el huevo"

    normalize_es("cancelar el timer de pasta")
    # → "cancelar el timer de pasta"  (unchanged)
"""

from __future__ import annotations

import re

__all__ = ["normalize_es"]

# ── Spanish number words → digits ─────────────────────────────────────────────

_ES_ONES: dict[str, int] = {
    "cero": 0, "un": 1, "una": 1, "uno": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}

_ES_TEENS: dict[str, int] = {
    "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciséis": 16, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
}

_ES_TENS: dict[str, int] = {
    "veinte": 20, "veintiuno": 21, "veintidós": 22, "veintidos": 22,
    "veintitrés": 23, "veintitres": 23, "veinticuatro": 24,
    "veinticinco": 25, "veintiséis": 26, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}

_ES_HUNDREDS: dict[str, int] = {
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}

_ES_ALL_NUMBERS: dict[str, int] = {}
_ES_ALL_NUMBERS.update(_ES_ONES)
_ES_ALL_NUMBERS.update(_ES_TEENS)
_ES_ALL_NUMBERS.update(_ES_TENS)
_ES_ALL_NUMBERS.update(_ES_HUNDREDS)
_ES_ALL_NUMBERS["mil"] = 1000

# ── Number word regex (with word boundaries) ──────────────────────────────────

# All individual number words, sorted longest-first for greedy matching
_ALL_WORD_LIST = sorted(_ES_ALL_NUMBERS.keys(), key=len, reverse=True)
_ALL_WORDS_RE = "|".join(re.escape(w) for w in _ALL_WORD_LIST)

# Matches compound Spanish number expressions:
# - Simple: "tres", "veinte"
# - Compound with y: "treinta y cinco"
# - Hundreds + rest: "doscientos treinta y cinco"
_NUM_WORD_RE = re.compile(
    rf"\b(?:(?:ciento|doscientos?|trescientos?|cuatrocientos?|quinientos?"
    rf"|seiscientos?|setecientos?|ochocientos?|novecientas?|novecientos?)"
    rf"\s+)?"
    rf"(?:"
    rf"(?:diez|once|doce|trece|catorce|quince"
    rf"|dieciséis|dieciseis|diecisiete|dieciocho|diecinueve"
    rf"|veintiuno|veintidós|veintidos|veintitrés|veintitres"
    rf"|veinticuatro|veinticinco|veintiséis|veintiseis"
    rf"|veintisiete|veintiocho|veintinueve"
    rf"|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)"
    rf"(?:\s+y\s+(?:un[ao]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve))?"
    rf"|"
    rf"(?:un[ao]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|mil)"
    rf")\b",
    re.IGNORECASE,
)

# ── Unit multiplier map ───────────────────────────────────────────────────────

_UNIT_SECONDS: dict[str, int] = {
    "segundo": 1, "segundos": 1,
    "minuto": 60, "minutos": 60,
    "hora": 3600, "horas": 3600,
    "día": 86400, "dia": 86400, "días": 86400, "dias": 86400,
}

# Singular forms for output
_UNIT_SINGULAR: dict[str, str] = {
    "segundo": "segundo", "segundos": "segundo",
    "minuto": "minuto", "minutos": "minuto",
    "hora": "hora", "horas": "hora",
    "día": "día", "dia": "día", "días": "día", "dias": "día",
}


def _text_to_number(text: str) -> int | None:
    """Convert a Spanish number expression to an integer.

    Handles compound expressions like "doscientos treinta y cinco" (235)
    and simple words like "tres" (3).

    Returns ``None`` if no number words are found.
    """
    text = text.strip().lower()
    if not text:
        return None

    # Try direct single-word lookup first
    direct = _ES_ALL_NUMBERS.get(text)
    if direct is not None:
        return direct

    # Handle "X y Z" pattern (e.g., "treinta y cinco")
    if " y " in text:
        parts = text.split(" y ", 1)
        left = _ES_ALL_NUMBERS.get(parts[0].strip())
        right = _ES_ALL_NUMBERS.get(parts[1].strip())
        if left is not None and right is not None:
            return left + right

    # Handle "Xcientos Y" pattern (e.g., "doscientos treinta")
    words = text.split()
    if len(words) >= 2:
        hundreds = _ES_ALL_NUMBERS.get(words[0].strip())
        rest = _text_to_number(" ".join(words[1:]))
        if hundreds is not None and rest is not None:
            return hundreds + rest

    return None


def _normalize_number_words(text: str) -> str:
    """Replace Spanish number words with their digit equivalents.

    Skips "un/una/uno" since the regex parser already handles them
    as the digit 1 — replacing them here would break article usage
    like "crear un temporizador de 2 minutos".
    """
    _SKIP = {"un", "una", "uno"}

    def _replace_match(m: re.Match) -> str:
        word = m.group(0).strip().lower()
        if word in _SKIP:
            return m.group(0)
        num = _text_to_number(m.group(0))
        return str(num) if num is not None else m.group(0)

    return _NUM_WORD_RE.sub(_replace_match, text)


# ── Fraction / special expressions ────────────────────────────────────────────

# Values in SECONDS for time-based fractions, or MINUTES for standalone
_FRACTIONS: list[tuple[str, int]] = [
    ("un cuarto de hora", 900),
    ("tres cuartos de hora", 2700),
    ("media hora", 1800),
    ("un tercio de hora", 1200),
    ("dos tercios de hora", 2400),
    ("un cuarto", 900),       # default to "de hora" context
    ("tres cuartos", 2700),
    ("un tercio", 1200),
    ("dos tercios", 2400),
    ("media", 1800),          # "media" alone = media hora = 30 min
    ("mitad", 1800),
]


def _normalize_fractions(text: str) -> str:
    """Replace fraction expressions with explicit duration values."""
    result = text
    for phrase, seconds in _FRACTIONS:
        if phrase not in result.lower():
            continue
        if seconds >= 3600:
            value = seconds // 3600
            unit = "hora" if value == 1 else "horas"
        else:
            value = seconds // 60
            unit = "minuto" if value == 1 else "minutos"
        replacement = f"{value} {unit}"
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        result = pattern.sub(replacement, result, count=1)
    return result


# ── Compound duration normalization ───────────────────────────────────────────

_DURATION_PAIR_RE = re.compile(
    r"(\d+|un(?:a|o)?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve"
    r"|diez|once|doce|trece|catorce|quince"
    r"|dieciséis|dieciseis|diecisiete|dieciocho|diecinueve"
    r"|veinte|veintiuno|veintidós|veintidos|veintitrés|veintitres"
    r"|veinticuatro|veinticinco|veintiséis|veintiseis"
    r"|veintisiete|veintiocho|veintinueve"
    r"|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa"
    r"|cien|ciento|doscientos?|trescientos?|cuatrocientos?|quinientos?"
    r"|seiscientos?|setecientos?|ochocientos?|novecientos?)"
    r"\s*(horas?|minutos?|segundos?|días?|dias?)",
    re.IGNORECASE,
)


def _parse_duration_parts(duration_text: str) -> int:
    """Parse a duration expression and return total seconds.

    Handles both digit strings and Spanish number words.
    """
    total = 0
    for pair in _DURATION_PAIR_RE.finditer(duration_text):
        num_text = pair.group(1)
        # Try digit first, then number words
        try:
            number = int(num_text)
        except ValueError:
            number = _text_to_number(num_text) or 0
        unit_raw = pair.group(2).lower().rstrip("s")
        multiplier = _UNIT_SECONDS.get(unit_raw, 1)
        total += number * multiplier
    return total


def _format_compact(total_seconds: int) -> str:
    """Format total seconds as the most compact single-unit expression.

    Always returns a single number+unit pair (the regex parser needs this).
    Uses the largest unit that divides evenly, falling back to minutes.
    """
    if total_seconds <= 0:
        return "0 minutos"

    # Try hours if it divides evenly
    if total_seconds % 3600 == 0:
        h = total_seconds // 3600
        return f"{h} {'hora' if h == 1 else 'horas'}"

    # Try minutes if it divides evenly
    if total_seconds % 60 == 0:
        m = total_seconds // 60
        return f"{m} {'minuto' if m == 1 else 'minutos'}"

    # Otherwise use minutes (truncated)
    m = total_seconds // 60
    if m > 0:
        return f"{m} minutos"

    return f"{total_seconds} segundos"


def _normalize_compound_durations(text: str) -> str:
    """Find and normalize compound duration expressions.

    "1 hora y 20 minutos para pasta" → "80 minutos para pasta"
    """
    # Split text into duration part and name part
    # The name part starts after a keyword like "para", "llamado", "a"
    name_match = re.search(r"\b(para|llamado|a)\s+", text, re.IGNORECASE)

    if name_match:
        duration_part = text[: name_match.start()]
        rest = text[name_match.start():]  # includes leading space
    else:
        duration_part = text
        rest = ""

    # Check if duration_part contains multiple number+unit pairs (compound)
    pairs = list(_DURATION_PAIR_RE.finditer(duration_part))
    if len(pairs) < 2:
        return text  # Simple or no duration, return unchanged

    total = _parse_duration_parts(duration_part)
    if total <= 0:
        return text

    normalized_duration = _format_compact(total)
    return f"{normalized_duration} {rest.lstrip()}" if rest else normalized_duration


# ── Main normalizer ───────────────────────────────────────────────────────────


def normalize_es(text: str) -> str:
    """Normalize Spanish timer text for the regex parser.

    Applies transformations in order:

    1. Fraction expressions → explicit values ("media hora" → "30 minutos")
    2. Number words → digits ("dos horas" → "2 horas")
    3. Compound durations → single expression ("1 hora y 20 minutos" → "80 minutos")

    Non-timer text passes through unchanged.
    """
    result = text
    result = _normalize_fractions(result)
    result = _normalize_number_words(result)
    result = _normalize_compound_durations(result)
    return result
