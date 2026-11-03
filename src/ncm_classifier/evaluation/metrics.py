"""Evaluation metrics for a classifier that returns one probability per class.

Every headline number comes with a 95% bootstrap confidence interval: with
~150 test rows, a difference of a few points between two models can be noise,
and the interval makes that visible instead of hiding it.

Metrics:
    top1, top3       share of rows whose true position is the first (or among
                     the first three) suggestions; top3 matches how the tool is
                     used, since a person picks from a short list.
    macro_f1         F1 averaged over positions, so rare positions weigh as much
                     as common ones.
    macro_precision  precision and recall of the first suggestion, averaged over
    macro_recall     positions in the same way.
    ece              expected calibration error of the top-1 confidence; low ECE
                     means "90% confident" is right about 90% of the time.

The macro averages are taken over the positions present in the true labels of
the evaluated rows. A position the model predicts but that has no row counts
as a false positive of the true positions, not as an extra position.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import precision_recall_fscore_support

DEFAULT_BOOTSTRAP: Final = 1000
DEFAULT_BINS: Final = 10


@dataclass(frozen=True)
class Interval:
    value: float
    low: float
    high: float


@dataclass(frozen=True)
class EvaluationResult:
    rows: int
    top1: Interval
    top3: Interval
    macro_f1: Interval
    ece: float
    macro_precision: Interval
    macro_recall: Interval

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def bootstrap_indices(
    n_rows: int, n_bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = 0
) -> NDArray[np.int_]:
    """Draw the row indices of every bootstrap resample (one resample per row)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_rows, size=(n_bootstrap, n_rows))


def percentile_interval(value: float, boot: NDArray[np.float64]) -> Interval:
    """95% percentile interval of the bootstrap values around the observed value."""
    low, high = np.percentile(boot, [2.5, 97.5])
    return Interval(round(value, 4), round(float(low), 4), round(float(high), 4))


def _ranked_labels(proba: NDArray[np.float64], classes: NDArray[np.str_]) -> NDArray[np.str_]:
    """Return the classes ordered from most to least probable, one row per sample."""
    return classes[np.argsort(-proba, axis=1, kind="stable")]


def top_k_hits(
    y_true: NDArray[np.str_], proba: NDArray[np.float64], classes: NDArray[np.str_], k: int
) -> NDArray[np.bool_]:
    if k < 1:
        raise ValueError("k must be at least 1")
    ranked = _ranked_labels(proba, classes)[:, :k]
    return (ranked == y_true[:, None]).any(axis=1)


def expected_calibration_error(
    hits: NDArray[np.bool_], confidence: NDArray[np.float64], bins: int = DEFAULT_BINS
) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    error = 0.0
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        in_bin = (confidence > low) & (confidence <= high)
        if in_bin.any():
            gap = abs(hits[in_bin].mean() - confidence[in_bin].mean())
            error += in_bin.mean() * gap
    return float(error)


def macro_scores(
    y_true: NDArray[np.str_], y_pred: NDArray[np.str_], labels: Sequence[str]
) -> tuple[float, float, float]:
    """Return macro precision, recall and F1 over the given labels."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=list(labels), average="macro", zero_division=0
    )
    return float(precision), float(recall), float(f1)


def evaluate(
    y_true: Sequence[str],
    proba: NDArray[np.float64],
    classes: Sequence[str],
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> EvaluationResult:
    """Compute the headline metrics and their bootstrap confidence intervals."""
    truth = np.asarray(y_true, dtype=str)
    labels = np.asarray(classes, dtype=str)
    if proba.shape != (len(truth), len(labels)):
        raise ValueError("proba must have one row per sample and one column per class")
    unknown = set(truth) - set(labels)
    if unknown:
        raise ValueError(f"true labels missing from the model classes: {sorted(unknown)}")

    predicted = _ranked_labels(proba, labels)[:, 0]
    hits1 = top_k_hits(truth, proba, labels, 1)
    hits3 = top_k_hits(truth, proba, labels, 3)
    precision, recall, f1 = macro_scores(truth, predicted, sorted(set(truth)))

    samples = bootstrap_indices(len(truth), n_bootstrap, seed)
    boot_top1 = hits1[samples].mean(axis=1)
    boot_top3 = hits3[samples].mean(axis=1)
    # Each resample is scored over the positions it actually contains. Scoring it over
    # every test position would count a position missing from the resample as F1 = 0
    # and drag the interval below the real value when positions have few rows.
    boot_macro = np.array(
        [macro_scores(truth[s], predicted[s], sorted(set(truth[s]))) for s in samples]
    )

    return EvaluationResult(
        rows=len(truth),
        top1=percentile_interval(float(hits1.mean()), boot_top1),
        top3=percentile_interval(float(hits3.mean()), boot_top3),
        macro_f1=percentile_interval(f1, boot_macro[:, 2]),
        ece=round(expected_calibration_error(hits1, proba.max(axis=1)), 4),
        macro_precision=percentile_interval(precision, boot_macro[:, 0]),
        macro_recall=percentile_interval(recall, boot_macro[:, 1]),
    )
