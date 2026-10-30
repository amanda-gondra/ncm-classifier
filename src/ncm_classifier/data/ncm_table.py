"""Load the official NCM table published by Classif (Portal Unico Siscomex).

The raw file is never modified. This module reads it, validates every entry
and returns a clean table with one row per code, so the rest of the project
never parses the government format again.

Raw format (verified on the file published on 2026-10-30):
    {"Data_Ultima_Atualizacao_NCM": "...", "Ato": "...",
     "Nomenclaturas": [{"Codigo": "0101.21.00", "Descricao": "-- ...",
                        "Data_Inicio": "dd/mm/yyyy", "Data_Fim": "dd/mm/yyyy", ...}]}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Final

import pandas as pd

# Number of digits in a code mapped to its level in the nomenclature.
LEVEL_BY_DIGITS: Final[dict[int, str]] = {
    2: "chapter",
    4: "position",
    5: "first_subposition",
    6: "second_subposition",
    7: "item",
    8: "subitem",
}
_DATE_FORMAT: Final = "%d/%m/%Y"
_LEADING_DASHES: Final = re.compile(r"^[\s\-–]+")
# Some official descriptions carry HTML formatting, e.g. "<i>pellets</i>".
_HTML_TAGS: Final = re.compile(r"<[^>]+>")


class NcmTableError(ValueError):
    """Raised when the raw NCM file does not have the expected structure."""


@dataclass(frozen=True)
class NcmTableMetadata:
    """Version information published with the table."""

    last_update: str
    legal_act: str


@dataclass(frozen=True)
class NcmTable:
    metadata: NcmTableMetadata
    entries: pd.DataFrame

    def positions(self) -> pd.DataFrame:
        """Return one row per 4-digit position that has at least one 8-digit code.

        This is the classification level of the MVP. Some positions have no
        4-digit row in the official table (e.g. 73.13 only appears as 7313.00.00),
        so the description comes from the most general entry inside the position:
        the one with the shortest code.
        """
        within_positions = self.entries[self.entries["position"].notna()]
        most_general = (
            within_positions.assign(code_length=within_positions["code"].str.len())
            .sort_values(["position", "code_length"])
            .groupby("position")["description"]
            .first()
        )
        subitems = within_positions[within_positions["level"] == "subitem"]
        grouped = subitems.groupby("position").agg(
            chapter=("chapter", "first"),
            subitem_count=("code", "size"),
        )
        grouped["description"] = most_general.reindex(grouped.index)
        return grouped.reset_index().rename(columns={"position": "code"})[
            ["code", "chapter", "description", "subitem_count"]
        ]

    def active_on(self, reference: date) -> NcmTable:
        """Return a copy keeping only codes valid on the reference date."""
        mask = (self.entries["valid_from"] <= reference) & (self.entries["valid_to"] >= reference)
        return NcmTable(self.metadata, self.entries[mask].reset_index(drop=True))


def _parse_date(value: str, *, code: str) -> date:
    try:
        return datetime.strptime(value, _DATE_FORMAT).date()
    except (TypeError, ValueError) as exc:
        raise NcmTableError(f"invalid date {value!r} for code {code!r}") from exc


def _parse_entry(raw: dict[str, str]) -> dict[str, object]:
    try:
        formatted_code = raw["Codigo"].strip()
        raw_description = raw["Descricao"]
        start, end = raw["Data_Inicio"], raw["Data_Fim"]
    except KeyError as exc:
        raise NcmTableError(f"entry is missing field {exc.args[0]!r}: {raw!r}") from exc

    code = formatted_code.replace(".", "")
    if not code.isdigit() or len(code) not in LEVEL_BY_DIGITS:
        raise NcmTableError(f"unexpected code format: {formatted_code!r}")

    return {
        "code": code,
        "code_formatted": formatted_code,
        "level": LEVEL_BY_DIGITS[len(code)],
        "chapter": code[:2],
        "position": code[:4] if len(code) >= 4 else None,
        "description": _LEADING_DASHES.sub("", _HTML_TAGS.sub("", raw_description)).strip(),
        "raw_description": raw_description,
        "valid_from": _parse_date(start, code=formatted_code),
        "valid_to": _parse_date(end, code=formatted_code),
    }


def parse_ncm_payload(payload: dict[str, object]) -> NcmTable:
    """Validate and convert the decoded JSON payload into an NcmTable."""
    try:
        metadata = NcmTableMetadata(
            last_update=str(payload["Data_Ultima_Atualizacao_NCM"]),
            legal_act=str(payload["Ato"]),
        )
        raw_entries = payload["Nomenclaturas"]
    except KeyError as exc:
        raise NcmTableError(f"payload is missing field {exc.args[0]!r}") from exc

    if not isinstance(raw_entries, list) or not raw_entries:
        raise NcmTableError("'Nomenclaturas' must be a non-empty list")

    entries = pd.DataFrame([_parse_entry(raw) for raw in raw_entries])

    duplicated = entries[entries.duplicated("code", keep=False)]["code_formatted"].unique()
    if len(duplicated) > 0:
        raise NcmTableError(f"duplicated codes: {sorted(duplicated)[:10]}")

    return NcmTable(metadata=metadata, entries=entries)


def load_ncm_table(path: Path) -> NcmTable:
    """Read the raw JSON file downloaded from Classif."""
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise NcmTableError("the NCM file must contain a JSON object at the top level")
    return parse_ncm_payload(payload)
