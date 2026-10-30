import json
from datetime import date
from pathlib import Path

import pytest

from ncm_classifier.data.ncm_table import NcmTableError, load_ncm_table, parse_ncm_payload


def _entry(code: str, description: str, start: str = "01/04/2022", end: str = "31/12/9999"):
    return {"Codigo": code, "Descricao": description, "Data_Inicio": start, "Data_Fim": end}


def _payload(*entries: dict[str, str]) -> dict[str, object]:
    return {
        "Data_Ultima_Atualizacao_NCM": "Vigente em 30/10/2026",
        "Ato": "Resolução Gecex nº 926/2026",
        "Nomenclaturas": list(entries),
    }


SAMPLE = _payload(
    _entry("31", "Adubos (fertilizantes)."),
    _entry("31.05", "Adubos que contenham dois ou três dos elementos fertilizantes."),
    _entry("3105.20.00", "- Adubos que contenham nitrogênio, fósforo e potássio"),
    _entry("3105.90", "- Outros:", end="31/03/2022"),
)


def test_parses_levels_codes_and_clean_descriptions() -> None:
    table = parse_ncm_payload(SAMPLE)
    entries = table.entries.set_index("code")

    assert list(entries["level"]) == ["chapter", "position", "subitem", "second_subposition"]
    assert entries.loc["31052000", "position"] == "3105"
    assert entries.loc["31052000", "chapter"] == "31"
    assert entries.loc["31052000", "description"].startswith("Adubos que contenham")
    assert table.metadata.legal_act == "Resolução Gecex nº 926/2026"


def test_codes_keep_leading_zeros_as_text() -> None:
    table = parse_ncm_payload(_payload(_entry("0101.21.00", "-- Reprodutores de raça pura")))
    assert table.entries.loc[0, "code"] == "01012100"


def test_positions_returns_only_four_digit_codes() -> None:
    positions = parse_ncm_payload(SAMPLE).positions()
    assert list(positions["code"]) == ["3105"]


def test_active_on_drops_expired_codes() -> None:
    active = parse_ncm_payload(SAMPLE).active_on(date(2026, 10, 30))
    assert "310590" not in set(active.entries["code"])
    assert "31052000" in set(active.entries["code"])


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"Ato": "x", "Nomenclaturas": []},
        _payload(),
        _payload(_entry("31.0A", "bad code")),
        _payload(_entry("3105.20.00", "x", start="2022-04-01")),
        _payload(_entry("31", "a"), _entry("31", "b")),
    ],
)
def test_rejects_malformed_payloads(bad_payload: dict[str, object]) -> None:
    with pytest.raises(NcmTableError):
        parse_ncm_payload(bad_payload)


def test_load_reads_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "ncm.json"
    path.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    table = load_ncm_table(path)
    assert "nitrogênio" in table.entries.loc[2, "description"]
