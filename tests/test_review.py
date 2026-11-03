import numpy as np
import pytest

from ncm_classifier.evaluation.review import fit_review_threshold, summarize_review


def test_threshold_accepts_as_many_rows_as_the_target_allows() -> None:
    confidence = [0.99, 0.95, 0.90, 0.80, 0.60, 0.40]
    hits = [True, True, True, True, False, False]
    # Accepting down to 0.80 keeps 4/4 right; going to 0.60 drops to 4/5 = 0.8.
    threshold = fit_review_threshold(confidence, hits, target=0.95)
    assert threshold.value == 0.80
    assert threshold.target_reached
    assert fit_review_threshold(confidence, hits, target=0.80).value == 0.60


def test_rows_with_equal_confidence_are_accepted_together() -> None:
    confidence = [0.9, 0.7, 0.7]
    hits = [True, True, False]
    # A cut between the two 0.7 rows is impossible; accepting both gives 2/3.
    assert fit_review_threshold(confidence, hits, target=0.95).value == 0.9


def test_unreachable_target_sends_everything_to_review() -> None:
    confidence = np.array([0.9, 0.5])
    threshold = fit_review_threshold(confidence, [False, True], target=0.95)
    assert not threshold.target_reached
    assert (confidence < threshold.value).all()


def test_summary_counts_review_rate_and_accepted_accuracy() -> None:
    confidence = [0.99, 0.95, 0.90, 0.80, 0.60, 0.40]
    hits = [True, True, True, False, False, False]
    summary = summarize_review(confidence, hits, threshold=0.90, n_bootstrap=200)
    assert summary.accepted_rows == 3
    assert summary.review_rate.value == 0.5
    assert summary.accepted_top1 is not None
    assert summary.accepted_top1.value == 1.0
    assert 0.0 <= summary.review_rate.low <= 0.5 <= summary.review_rate.high <= 1.0


def test_summary_without_accepted_rows_has_no_accuracy() -> None:
    summary = summarize_review([0.5, 0.4], [True, False], threshold=0.9, n_bootstrap=50)
    assert summary.accepted_rows == 0
    assert summary.accepted_top1 is None
    assert summary.review_rate.value == 1.0


@pytest.mark.parametrize("target", [0.0, 1.5])
def test_invalid_target_is_rejected(target: float) -> None:
    with pytest.raises(ValueError, match="target"):
        fit_review_threshold([0.9], [True], target=target)
