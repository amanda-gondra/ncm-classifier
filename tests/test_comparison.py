import numpy as np
import pytest

from ncm_classifier.evaluation.comparison import mcnemar_exact, paired_accuracy, paired_macro_f1


def test_identical_models_have_a_zero_difference() -> None:
    hits = np.array([True, False, True, True])
    result = paired_accuracy(hits, hits, n_bootstrap=200)
    assert result.difference.value == 0.0
    assert result.difference.low == result.difference.high == 0.0
    assert result.share_tied == 1.0


def test_difference_is_b_minus_a() -> None:
    a = np.array([True, False, False, False])
    b = np.array([True, True, True, False])
    result = paired_accuracy(a, b, n_bootstrap=200)
    assert result.model_a == 0.25
    assert result.model_b == 0.75
    assert result.difference.value == 0.5
    assert result.difference.low >= 0.0
    assert result.share_b_better > 0.5


def test_paired_macro_f1_matches_the_evaluation_definition() -> None:
    truth = ["x", "x", "y", "y"]
    perfect = ["x", "x", "y", "y"]
    all_x = ["x", "x", "x", "x"]
    result = paired_macro_f1(truth, all_x, perfect, n_bootstrap=100)
    assert result.model_b == 1.0
    # F1 of x = 2 * 0.5 * 1 / 1.5 = 2/3, F1 of y = 0, mean = 1/3.
    assert result.model_a == pytest.approx(1 / 3, abs=1e-4)


def test_mcnemar_counts_and_p_value() -> None:
    a = np.array([True] * 5 + [False] * 5)
    b = np.array([True] * 5 + [True] * 4 + [False])
    result = mcnemar_exact(a, b)
    assert (result.both_right, result.only_a, result.only_b, result.both_wrong) == (5, 0, 4, 1)
    assert result.p_value == pytest.approx(0.125)  # 2 * 0.5**4


def test_mcnemar_without_disagreement_has_p_value_one() -> None:
    hits = np.array([True, False])
    assert mcnemar_exact(hits, hits).p_value == 1.0


def test_mismatched_lengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="same length"):
        paired_accuracy([True], [True, False])
