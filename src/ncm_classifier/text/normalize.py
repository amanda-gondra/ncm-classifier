"""Text normalization shared by training and inference.

The same function must run in both places. If they diverge, the model
receives different text in production than it saw in training and fails
silently, with no error to warn anyone.

Design rule: never delete information that decides the NCM code.
Numbers such as fertilizer formulas (NPK 20-05-20), weights and volumes
are kept and standardized, not removed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

# Abbreviations common in agribusiness invoices. Applied to whole tokens only,
# after accents are removed, so "sc" never changes inside a word like "escova".
ABBREVIATIONS: Final[dict[str, str]] = {
    "sc": "saco",
    "scs": "saco",
    "cx": "caixa",
    "pct": "pacote",
    "und": "unidade",
    "un": "unidade",
    "gl": "galao",
    "rl": "rolo",
}

# Every accepted spelling of a unit, mapped to one canonical form.
UNIT_SPELLINGS: Final[dict[str, tuple[str, ...]]] = {
    "kg": ("kg", "kgs", "quilo", "quilos", "kilo", "kilos"),
    "g": ("g", "gr", "grs", "grama", "gramas"),
    "ml": ("ml",),
    "l": ("l", "lt", "lts", "litro", "litros"),
    "m": ("m", "mt", "mts", "metro", "metros"),
    "t": ("t", "ton", "tonelada", "toneladas"),
}
_UNIT_LOOKUP: Final[dict[str, str]] = {
    spelling: canonical for canonical, spellings in UNIT_SPELLINGS.items() for spelling in spellings
}
# Longest spellings first, so the regex tries "ml" before "m" and "kgs" before "kg".
_UNIT_ALTERNATION: Final = "|".join(
    re.escape(spelling) for spelling in sorted(_UNIT_LOOKUP, key=len, reverse=True)
)
_NUMBER_WITH_UNIT: Final = re.compile(rf"(\d+(?:\.\d+)?)\s*({_UNIT_ALTERNATION})\b")
_DECIMAL_COMMA: Final = re.compile(r"(?<=\d),(?=\d)")
# "npk 20 05 20", "npk 20.05.20", "npk20-5-20"
_NPK_WITH_PREFIX: Final = re.compile(
    r"\bnpk\s*(\d{1,2})\s*[-./ ]\s*(\d{1,2})\s*[-./ ]\s*(\d{1,2})\b"
)
# "20-05-20" or "4.14.8" without the "npk" prefix (spaces are not accepted here,
# to avoid joining unrelated numbers).
_FORMULA_TRIPLE: Final = re.compile(r"\b(\d{1,2})[-.](\d{1,2})[-.](\d{1,2})\b")
_DISALLOWED_CHARS: Final = re.compile(r"[^a-z0-9 .\-]")
_LOOSE_PUNCTUATION: Final = re.compile(r"(?<!\d)[.\-]|[.\-](?!\d)")
_WHITESPACE: Final = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _format_formula(match: re.Match[str]) -> str:
    return "-".join(part.zfill(2) for part in match.groups())


def _canonical_unit(match: re.Match[str]) -> str:
    number, unit = match.groups()
    return f"{number} {_UNIT_LOOKUP[unit]}"


def normalize_text(text: str) -> str:
    """Return a standardized version of a product description.

    Steps, in order: Unicode compatibility form, lowercase, accents removed,
    fertilizer formulas, decimal commas, units, punctuation, abbreviations
    and whitespace. The function is idempotent: applying it twice gives the
    same result as applying it once.

    >>> normalize_text("ADUBO NPK 20 05 20 SC 50KG")
    'adubo npk 20-05-20 saco 50 kg'
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")

    result = unicodedata.normalize("NFKC", text).lower()
    result = _strip_accents(result)
    result = _NPK_WITH_PREFIX.sub(lambda m: "npk " + _format_formula(m), result)
    result = _FORMULA_TRIPLE.sub(_format_formula, result)
    result = _DECIMAL_COMMA.sub(".", result)
    result = _NUMBER_WITH_UNIT.sub(_canonical_unit, result)
    result = _DISALLOWED_CHARS.sub(" ", result)
    result = _LOOSE_PUNCTUATION.sub(" ", result)

    tokens = [ABBREVIATIONS.get(token, token) for token in result.split()]
    return _WHITESPACE.sub(" ", " ".join(tokens)).strip()
