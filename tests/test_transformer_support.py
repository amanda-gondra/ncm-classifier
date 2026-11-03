import numpy as np
import pytest
from sklearn.utils.class_weight import compute_class_weight

from ncm_classifier.models.transformer_support import (
    balanced_class_weights,
    prepare_input,
    select_best,
)


def test_raw_mode_keeps_case_and_accents() -> None:
    assert prepare_input(["  Adubo  Fosfatado\tNPK\n"], "raw") == ["Adubo Fosfatado NPK"]


def test_normalized_mode_is_the_baseline_normalization() -> None:
    assert prepare_input(["ADUBO NPK 20 05 20 SC 50KG"], "normalized") == [
        "adubo npk 20-05-20 saco 50 kg"
    ]


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown input mode"):
        prepare_input(["x"], "lowercase")


def test_class_weights_match_the_baseline_formula() -> None:
    labels = ["a", "a", "a", "b"]
    expected = compute_class_weight("balanced", classes=np.array(["a", "b"]), y=np.array(labels))
    assert np.allclose(balanced_class_weights(labels, ["a", "b"]), expected)
    assert np.allclose(expected, [4 / (2 * 3), 4 / (2 * 1)])


def test_class_without_rows_is_rejected() -> None:
    with pytest.raises(ValueError, match="without training rows"):
        balanced_class_weights(["a"], ["a", "b"])


def test_select_best_uses_the_mean_and_keeps_the_first_tie() -> None:
    scores = {("raw", 1): [0.5, 0.7], ("raw", 2): [0.6, 0.8], ("normalized", 2): [0.8, 0.6]}
    assert select_best(scores) == ("raw", 2)
