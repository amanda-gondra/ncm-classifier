"""Manual review routing: low-confidence suggestions go to a person.

A suggestion is accepted automatically when its confidence is at least a
threshold, and sent to manual review otherwise. The confidence is the final one
shown to the user: calibrated, after the 31.05 rule.

The threshold is fitted on the out-of-fold predictions of the training set
(never on a test set) as the lowest confidence for which the accepted
suggestions are still right at least TARGET_ACCURACY of the time. Lower
thresholds accept more rows; this one accepts as many as the target allows.

If no threshold reaches the target, every row goes to review: the threshold is
set just above the highest confidence and `target_reached` is false.

Test sets only measure the threshold: the share of rows sent to review and the
top-1 accuracy of the accepted ones, both with bootstrap intervals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
from numpy.typing import ArrayLike

from ncm_classifier.evaluation.metrics import (
    DEFAULT_BOOTSTRAP,
    Interval,
    bootstrap_indices,
    percentile_interval,
)

TARGET_ACCURACY: Final = 0.95


@dataclass(frozen=True)
class ReviewThreshold:
    value: float
    target_accuracy: float
    target_reached: bool


@dataclass(frozen=True)
class ReviewSummary:
    threshold: float
    rows: int
    accepted_rows: int
    review_rate: Interval
    accepted_top1: Interval | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _as_arrays(confidence: ArrayLike, hits: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    conf = np.asarray(confidence, dtype=float)
    hit = np.asarray(hits, dtype=bool)
    if conf.ndim != 1 or conf.shape != hit.shape:
        raise ValueError("confidence and hits must be 1-D arrays of the same length")
    if len(conf) == 0:
        raise ValueError("at least one row is needed")
    return conf, hit


def fit_review_threshold(
    confidence: ArrayLike, hits: ArrayLike, target: float = TARGET_ACCURACY
) -> ReviewThreshold:
    """Lowest confidence whose accepted rows reach the target top-1 accuracy."""
    if not 0.0 < target <= 1.0:
        raise ValueError("target must be in (0, 1]")
    conf, hit = _as_arrays(confidence, hits)

    order = np.argsort(-conf, kind="stable")
    sorted_conf = conf[order]
    accuracy = np.cumsum(hit[order]) / np.arange(1, len(conf) + 1)
    # A threshold accepts every row with the same confidence, so a cut is only valid
    # after the last row of a group of equal confidences.
    group_end = np.append(sorted_conf[1:] != sorted_conf[:-1], True)
    valid = np.flatnonzero(group_end & (accuracy >= target))

    if valid.size == 0:
        above_all = float(np.nextafter(sorted_conf[0], np.inf))
        return ReviewThreshold(above_all, target, target_reached=False)
    return ReviewThreshold(float(sorted_conf[valid[-1]]), target, target_reached=True)


def summarize_review(
    confidence: ArrayLike,
    hits: ArrayLike,
    threshold: float,
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> ReviewSummary:
    conf, hit = _as_arrays(confidence, hits)
    accepted = conf >= threshold

    samples = bootstrap_indices(len(conf), n_bootstrap, seed)
    boot_review = (~accepted)[samples].mean(axis=1)
    accepted_count = accepted[samples].sum(axis=1)
    accepted_hits = (accepted & hit)[samples].sum(axis=1)
    # A resample with no accepted row has no accuracy; it is left out of that interval.
    with_rows = accepted_count > 0
    boot_accuracy = accepted_hits[with_rows] / accepted_count[with_rows]

    accepted_top1 = None
    if accepted.any():
        accepted_top1 = percentile_interval(float(hit[accepted].mean()), boot_accuracy)
    return ReviewSummary(
        threshold=threshold,
        rows=len(conf),
        accepted_rows=int(accepted.sum()),
        review_rate=percentile_interval(float((~accepted).mean()), boot_review),
        accepted_top1=accepted_top1,
    )
