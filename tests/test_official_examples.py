from ncm_classifier.data.ncm_table import parse_ncm_payload
from ncm_classifier.data.official_examples import build_official_examples


def _entry(code: str, description: str) -> dict[str, str]:
    return {
        "Codigo": code,
        "Descricao": description,
        "Data_Inicio": "01/01/2022",
        "Data_Fim": "31/12/9999",
    }


PAYLOAD = {
    "Data_Ultima_Atualizacao_NCM": "Vigente em 30/10/2026",
    "Ato": "Teste",
    "Nomenclaturas": [
        _entry("31", "Adubos"),
        _entry("31.05", "Adubos minerais com dois ou três elementos."),
        _entry("3105.20.00", "- Com os três elementos N, P e K"),
        _entry("3105.90", "- Outros:"),
        _entry("3105.90.11", "-- Outros"),
        _entry("72.17", "Fios de ferro ou aço não ligado."),
        _entry("7217.10.90", "- Galvanizados"),
        _entry("7313.00.00", "Arame farpado de ferro ou aço"),
    ],
}


def _examples(positions: list[str]) -> dict[str, str]:
    examples = build_official_examples(parse_ncm_payload(PAYLOAD), positions)
    assert examples["text"].is_unique
    assert set(examples["source_type"]) == {"ncm_official"}
    return dict(zip(examples["source_ref"], examples["text"], strict=True))


def test_position_text_appears_once_without_trailing_punctuation() -> None:
    by_ref = _examples(["3105"])
    assert by_ref["3105"] == "Adubos minerais com dois ou três elementos"


def test_subitems_keep_only_specific_levels() -> None:
    by_ref = _examples(["3105"])
    assert by_ref["31052000"] == "Com os três elementos N, P e K"
    # 3105.90.11 has only generic levels below the position, so it adds nothing.
    assert "31059011" not in by_ref


def test_single_code_position_is_not_duplicated() -> None:
    by_ref = _examples(["7313"])
    # The position text and the 8-digit text are the same, so one example remains.
    assert list(by_ref.values()) == ["Arame farpado de ferro ou aço"]


def test_out_of_scope_positions_are_ignored() -> None:
    by_ref = _examples(["3105"])
    assert not any(ref.startswith("7217") for ref in by_ref)
