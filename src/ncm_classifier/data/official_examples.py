"""Training examples built from the official NCM descriptions.

Two kinds of example come out of the table for each position in scope:

* the position text itself (e.g. "Arame farpado de ferro ou aço; ..."), once;
* one example per 8-digit subitem, made of the specific levels below the
  position (subposition, item, subitem). Generic levels such as "Outros" are
  skipped, and the long position text is not repeated in every example, so the
  model learns the product words and not the legal boilerplate around them.

Example for 3105.20.00: "Que contenham os três elementos fertilizantes: azoto
(nitrogênio), fósforo e potássio".
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

import pandas as pd

from ncm_classifier.data.ncm_table import NcmTable
from ncm_classifier.text import normalize_text

SOURCE_TYPE: Final = "ncm_official"
_GENERIC_DESCRIPTIONS: Final = frozenset({"outros", "outras", "outro", "outra"})
_SPECIFIC_PREFIX_LENGTHS: Final = (5, 6, 7, 8)
_TRAILING_PUNCTUATION: Final = " .:;"
COLUMNS: Final = ["text", "position", "source_type", "source_ref"]


def _clean(description: str) -> str:
    return description.strip().rstrip(_TRAILING_PUNCTUATION).strip()


def _is_generic(description: str) -> bool:
    return normalize_text(description) in _GENERIC_DESCRIPTIONS


def _row(text: str, position: str, source_ref: str) -> dict[str, str]:
    return {
        "text": text,
        "position": position,
        "source_type": SOURCE_TYPE,
        "source_ref": source_ref,
    }


def build_official_examples(table: NcmTable, positions: Iterable[str]) -> pd.DataFrame:
    """Return the official examples for the given positions, without repeated texts."""
    wanted = set(positions)
    entries = table.entries[table.entries["position"].isin(wanted)]
    description_by_code = dict(zip(entries["code"], entries["description"], strict=True))
    position_text = table.positions().set_index("code")["description"]

    rows = [
        _row(_clean(position_text[position]), position, position)
        for position in sorted(wanted & set(position_text.index))
    ]

    subitems = entries[entries["level"] == "subitem"]
    for code, position in zip(subitems["code"], subitems["position"], strict=True):
        parts: list[str] = []
        for length in _SPECIFIC_PREFIX_LENGTHS:
            description = description_by_code.get(code[:length])
            if description is None:
                continue
            cleaned = _clean(description)
            if cleaned and not _is_generic(cleaned) and cleaned not in parts:
                parts.append(cleaned)
        if parts:
            rows.append(_row("; ".join(parts), position, code))

    examples = pd.DataFrame(rows, columns=COLUMNS)
    normalized = examples["text"].map(normalize_text)
    return examples[~normalized.duplicated()].reset_index(drop=True)
