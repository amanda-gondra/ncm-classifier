import numpy as np
import pytest

from ncm_classifier.rules.small_package import (
    apply_small_package_rule,
    is_small_package,
    package_weights_kg,
)

CLASSES = ["2309", "3102", "3103", "3105"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Superfosfato Simples 1kg Fósforo", [1.0]),
        ("Sulfato de amônio 500 g jardinagem", [0.5]),
        ("Adubo 05-20-20. Saca de 50 Kg.", [50.0]),
        ("sacos de 25 kg e Big Bag 1000 kg", [25.0, 1000.0]),
        ("Fosfato Natural 0,5KG", [0.5]),
        ("NPK 20-05-20 granulado", []),
        ("adubo líquido 1 litro", []),
    ],
)
def test_weights_in_kilograms(text: str, expected: list[float]) -> None:
    assert package_weights_kg(text) == pytest.approx(expected)


def test_small_package_needs_every_weight_at_or_below_limit() -> None:
    assert is_small_package("ureia 5 kg")
    assert is_small_package("ureia 10 kg")
    assert not is_small_package("ureia 10,5 kg")
    assert not is_small_package("pacote 1 kg ou saco 25 kg")
    assert not is_small_package("ureia agrícola granulada")


def test_rule_moves_chapter_31_mass_to_3105() -> None:
    texts = ["Superfosfato simples 1kg", "Superfosfato simples saco 50 kg", "Sal mineral 5 kg"]
    proba = np.array(
        [
            [0.1, 0.2, 0.6, 0.1],  # small package, top is 31.03 -> becomes 31.05
            [0.1, 0.2, 0.6, 0.1],  # 50 kg -> unchanged
            [0.7, 0.1, 0.1, 0.1],  # top is 23.09, not Chapter 31 -> unchanged
        ]
    )
    adjusted, applied = apply_small_package_rule(texts, proba, CLASSES)

    assert applied.tolist() == [True, False, False]
    assert adjusted[0].tolist() == pytest.approx([0.1, 0.0, 0.0, 0.9])
    assert np.allclose(adjusted.sum(axis=1), 1.0)
    assert np.array_equal(adjusted[1:], proba[1:])


def test_rule_requires_target_class() -> None:
    with pytest.raises(ValueError, match="must be one of the classes"):
        apply_small_package_rule(["x 1 kg"], np.array([[1.0]]), ["3102"])
