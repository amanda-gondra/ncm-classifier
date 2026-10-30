import pytest

from ncm_classifier.data.dedup import jaccard, near_duplicate_mask, shingles


def test_shingles_ignore_case_and_accents() -> None:
    assert shingles("Ração Bovina") == shingles("RACAO BOVINA")


def test_short_and_empty_texts() -> None:
    assert shingles("sal") == frozenset({"sal"})
    assert shingles("") == frozenset()


def test_jaccard_bounds() -> None:
    same = shingles("arame farpado 500 m")
    assert jaccard(same, same) == 1.0
    assert jaccard(frozenset(), frozenset()) == 0.0


def test_copy_with_small_edit_is_flagged() -> None:
    reference = ["Arame farpado Gerdau Touro em rolo de 500m disponível na Lapa, PR."]
    candidates = [
        "Arame farpado Gerdau Touro em rolo de 500m disponível na Lapa - PR",
        "Semente de Braquiária Marandu em saco de 20 kg",
    ]
    assert near_duplicate_mask(candidates, reference) == [True, False]


@pytest.mark.parametrize("threshold", [0.0, 1.5])
def test_invalid_threshold(threshold: float) -> None:
    with pytest.raises(ValueError):
        near_duplicate_mask(["a"], ["a"], threshold=threshold)
