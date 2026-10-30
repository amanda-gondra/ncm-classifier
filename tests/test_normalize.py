import pytest

from ncm_classifier.text import normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ADUBO NPK 20 05 20 SC 50KG", "adubo npk 20-05-20 saco 50 kg"),
        ("Adubo NPK 4-14-8 saco 50 kg", "adubo npk 04-14-08 saco 50 kg"),
        ("adubo 20.05.20", "adubo 20-05-20"),
        ("Ração para Bovinos 40kg", "racao para bovinos 40 kg"),
        ("Defensivo agrícola glifosato 1L", "defensivo agricola glifosato 1 l"),
        ("Arame farpado rolo 250m", "arame farpado rolo 250 m"),
        ("Óleo 1,5 litros", "oleo 1.5 l"),
        ("Suplemento 25 KGS", "suplemento 25 kg"),
        ("Vermífugo 500 ML", "vermifugo 500 ml"),
        ("Lona 2 metros", "lona 2 m"),
        ("Semente de milho (híbrido)!!", "semente de milho hibrido"),
        ("Herbicida 10 GL", "herbicida 10 galao"),
    ],
)
def test_normalizes_real_invoice_styles(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_keeps_letters_that_look_like_units_inside_words() -> None:
    assert normalize_text("milho moido") == "milho moido"
    assert normalize_text("1 lata") == "1 lata"


def test_abbreviation_only_replaces_whole_tokens() -> None:
    assert normalize_text("escova sc") == "escova saco"


@pytest.mark.parametrize("raw", ["", "   ", "!!!"])
def test_empty_or_symbol_only_input_returns_empty_string(raw: str) -> None:
    assert normalize_text(raw) == ""


@pytest.mark.parametrize(
    "raw",
    [
        "ADUBO NPK 20 05 20 SC 50KG",
        "Óleo 1,5 litros",
        "Arame farpado rolo 250m",
        "Semente de milho (híbrido)!!",
    ],
)
def test_is_idempotent(raw: str) -> None:
    once = normalize_text(raw)
    assert normalize_text(once) == once


def test_rejects_non_string_input() -> None:
    with pytest.raises(TypeError):
        normalize_text(None)  # type: ignore[arg-type]
