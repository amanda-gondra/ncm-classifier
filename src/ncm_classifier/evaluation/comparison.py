"""Paired comparison of two models evaluated on the same rows.

Both models are scored on the same bootstrap resamples (the same row indices),
so the interval is for the difference itself. Rows that are easy or hard for
both models cancel out, which makes this more informative than checking
whether two separate intervals overlap.

McNemar's exact test looks only at the rows where exactly one model is right.
If the models were equally good, each of those rows would be equally likely to
favour either one (binomial with p = 0.5); the p-value says how surprising the
observed split is under that hypothesis.

Differences are always "model B minus model A".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import binomtest

from ncm_classifier.evaluation.metrics import (
    DEFAULT_BOOTSTRAP,
    Interval,
    bootstrap_indices,
    macro_scores,
    percentile_interval,
)


@dataclass(frozen=True)
class PairedDifference:
    metric: str
    model_a: float
    model_b: float
    difference: Interval
    share_b_better: float
    share_tied: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class McNemarResult:
    both_right: int
    only_a: int
    only_b: int
    both_wrong: int
    p_value: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _hits(hits_a: ArrayLike, hits_b: ArrayLike) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    a = np.asarray(hits_a, dtype=bool)
    b = np.asarray(hits_b, dtype=bool)
    if a.ndim != 1 or a.shape != b.shape or len(a) == 0:
        raise ValueError("hits must be non-empty 1-D arrays of the same length")
    return a, b


def _difference(
    metric: str, value_a: float, value_b: float, boot_a: NDArray, boot_b: NDArray
) -> PairedDifference:
    boot_diff = boot_b - boot_a
    return PairedDifference(
        metric=metric,
        model_a=round(value_a, 4),
        model_b=round(value_b, 4),
        difference=percentile_interval(value_b - value_a, boot_diff),
        share_b_better=round(float((boot_diff > 0).mean()), 4),
        share_tied=round(float((boot_diff == 0).mean()), 4),
    )


def paired_accuracy(
    hits_a: ArrayLike,
    hits_b: ArrayLike,
    metric: str = "top1",
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> PairedDifference:
    """Difference in accuracy (top-1 or top-3 hits) on paired resamples."""
    a, b = _hits(hits_a, hits_b)
    samples = bootstrap_indices(len(a), n_bootstrap, seed)
    return _difference(
        metric, float(a.mean()), float(b.mean()), a[samples].mean(axis=1), b[samples].mean(axis=1)
    )


def paired_macro_f1(
    y_true: Sequence[str],
    pred_a: Sequence[str],
    pred_b: Sequence[str],
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> PairedDifference:
    """Difference in macro F1, with the same definition used by `evaluate`."""
    truth = np.asarray(y_true, dtype=str)
    a = np.asarray(pred_a, dtype=str)
    b = np.asarray(pred_b, dtype=str)
    if not truth.shape == a.shape == b.shape or len(truth) == 0:
        raise ValueError("y_true, pred_a and pred_b must be non-empty and of the same length")

    def f1(pred: NDArray[np.str_], rows: NDArray[np.int_] | slice) -> float:
        return macro_scores(truth[rows], pred[rows], sorted(set(truth[rows])))[2]

    samples = bootstrap_indices(len(truth), n_bootstrap, seed)
    boot_a = np.array([f1(a, s) for s in samples])
    boot_b = np.array([f1(b, s) for s in samples])
    everything = slice(None)
    return _difference("macro_f1", f1(a, everything), f1(b, everything), boot_a, boot_b)


def mcnemar_exact(hits_a: ArrayLike, hits_b: ArrayLike) -> McNemarResult:
    a, b = _hits(hits_a, hits_b)
    only_a = int((a & ~b).sum())
    only_b = int((~a & b).sum())
    discordant = only_a + only_b
    p_value = 1.0 if discordant == 0 else float(binomtest(only_b, discordant, 0.5).pvalue)
    return McNemarResult(
        both_right=int((a & b).sum()),
        only_a=only_a,
        only_b=only_b,
        both_wrong=int((~a & ~b).sum()),
        p_value=round(p_value, 4),
    )
