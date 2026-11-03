import numpy as np
import pytest

from ncm_classifier.evaluation.metrics import evaluate, expected_calibration_error, top_k_hits

CLASSES = np.array(["0102", "1005", "7313"])
PROBA = np.array(
    [
        [0.7, 0.2, 0.1],  # true 0102 -> top1 hit
        [0.5, 0.4, 0.1],  # true 1005 -> top1 miss, top2 hit
        [0.6, 0.3, 0.1],  # true 7313 -> only in top3
    ]
)
TRUTH = np.array(["0102", "1005", "7313"])


def test_top_k_hits() -> None:
    assert top_k_hits(TRUTH, PROBA, CLASSES, 1).tolist() == [True, False, False]
    assert top_k_hits(TRUTH, PROBA, CLASSES, 2).tolist() == [True, True, False]
    assert top_k_hits(TRUTH, PROBA, CLASSES, 3).all()


def test_evaluate_values_and_interval_bounds() -> None:
    result = evaluate(TRUTH, PROBA, CLASSES, n_bootstrap=200, seed=1)
    assert result.rows == 3
    assert result.top1.value == pytest.approx(1 / 3, abs=1e-4)
    assert result.top3.value == 1.0
    for interval in (result.top1, result.top3, result.macro_f1):
        assert 0.0 <= interval.low <= interval.value <= interval.high <= 1.0


def test_macro_precision_and_recall() -> None:
    # Every row is predicted as 0102: precision of 0102 is 1/3, recall is 1; the other
    # two positions are never predicted, so their precision and recall are 0.
    result = evaluate(TRUTH, PROBA, CLASSES, n_bootstrap=200, seed=1)
    assert result.macro_precision.value == pytest.approx(1 / 9, abs=1e-4)
    assert result.macro_recall.value == pytest.approx(1 / 3, abs=1e-4)
    for interval in (result.macro_precision, result.macro_recall):
        assert 0.0 <= interval.low <= interval.high <= 1.0


def test_perfect_model_with_one_row_per_class_has_f1_interval_at_one() -> None:
    # Regression: resamples miss some classes; those must not count as F1 = 0.
    classes = np.array([f"{i:04d}" for i in range(20)])
    truth = classes.copy()
    proba = np.eye(20)
    result = evaluate(truth, proba, classes, n_bootstrap=200, seed=0)
    assert result.macro_f1.value == 1.0
    assert result.macro_f1.low == 1.0


def test_perfectly_calibrated_bin_has_zero_error() -> None:
    hits = np.array([True, False])
    confidence = np.array([0.5, 0.5])
    assert expected_calibration_error(hits, confidence) == pytest.approx(0.0)


def test_unknown_true_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing from the model classes"):
        evaluate(np.array(["9999", "1005", "7313"]), PROBA, CLASSES, n_bootstrap=10)


def test_shape_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="one row per sample"):
        evaluate(TRUTH[:2], PROBA, CLASSES, n_bootstrap=10)
