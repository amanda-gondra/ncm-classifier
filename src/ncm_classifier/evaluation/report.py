"""Post-processing and evaluation shared by every model of the project.

Each model only produces raw probabilities. Everything after that is done
here, in the same order for every model:

    raw probabilities -> temperature -> 31.05 rule -> manual review threshold

* `calibrate_out_of_fold` fits the temperature and the review threshold on the
  out-of-fold predictions of the training set;
* `evaluate_split` applies them, unchanged, to a frozen test set.

So differences between two model reports come from the models, not from the
evaluation code.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.metrics import f1_score

from ncm_classifier.evaluation.breakdown import chapter_metrics, confusion_pairs, confusion_table
from ncm_classifier.evaluation.metrics import EvaluationResult, evaluate
from ncm_classifier.evaluation.protocol import SEED
from ncm_classifier.evaluation.review import (
    TARGET_ACCURACY,
    ReviewThreshold,
    fit_review_threshold,
    summarize_review,
)
from ncm_classifier.models.calibration import apply_temperature, fit_temperature
from ncm_classifier.rules.small_package import apply_small_package_rule

logger = logging.getLogger(__name__)

TOP_K = 3


@dataclass(frozen=True)
class OutOfFoldCalibration:
    temperature: float
    review: ReviewThreshold
    summary: dict[str, object]


@dataclass(frozen=True)
class SplitEvaluation:
    summary: dict[str, object]
    predictions: pd.DataFrame
    confusion: pd.DataFrame


def log_result(name: str, label: str, result: EvaluationResult) -> None:
    logger.info(
        "%s %s (%d rows): top1 %.3f [%.3f-%.3f] | top3 %.3f [%.3f-%.3f] | "
        "macro F1 %.3f [%.3f-%.3f] | ECE %.3f",
        name,
        label,
        result.rows,
        result.top1.value,
        result.top1.low,
        result.top1.high,
        result.top3.value,
        result.top3.low,
        result.top3.high,
        result.macro_f1.value,
        result.macro_f1.low,
        result.macro_f1.high,
        result.ece,
    )


def _top1_hits(
    proba: NDArray[np.float64], classes: NDArray[np.str_], truth: NDArray[np.str_]
) -> NDArray[np.bool_]:
    return classes[proba.argmax(axis=1)] == truth


def calibrate_out_of_fold(
    texts: Sequence[str],
    labels: Sequence[str],
    out_of_fold: NDArray[np.float64],
    classes: Sequence[str],
    target_accuracy: float = TARGET_ACCURACY,
    seed: int = SEED,
) -> OutOfFoldCalibration:
    """Fit the temperature and the review threshold on out-of-fold predictions."""
    names = np.asarray(classes, dtype=str)
    truth = np.asarray(labels, dtype=str)

    temperature = fit_temperature(out_of_fold, truth, names)
    calibrated = apply_temperature(out_of_fold, temperature)
    final, rule_applied = apply_small_package_rule(list(texts), calibrated, names)

    hits_calibrated = _top1_hits(calibrated, names, truth)
    hits_final = _top1_hits(final, names, truth)
    confidence = final.max(axis=1)
    review = fit_review_threshold(confidence, hits_final, target_accuracy)
    review_summary = summarize_review(confidence, hits_final, review.value, seed=seed)

    logger.info("Calibration temperature (out-of-fold, training only): %.3f", temperature)
    logger.info(
        "Out-of-fold top1: %.4f -> %.4f with the 31.05 rule (%d rows changed)",
        hits_calibrated.mean(),
        hits_final.mean(),
        int(rule_applied.sum()),
    )
    logger.info(
        "Review threshold %.4f (target %.0f%% reached: %s): %.1f%% of out-of-fold rows to review",
        review.value,
        100 * target_accuracy,
        review.target_reached,
        100 * review_summary.review_rate.value,
    )

    summary = {
        "temperature": round(temperature, 4),
        "rule_31_05": {
            "top1_without_rule": round(float(hits_calibrated.mean()), 4),
            "top1_with_rule": round(float(hits_final.mean()), 4),
            "rows_changed": int(rule_applied.sum()),
        },
        "review": {**asdict(review), **review_summary.to_dict()},
    }
    return OutOfFoldCalibration(temperature, review, summary)


def evaluate_split(
    name: str,
    ids: Sequence[str],
    texts: Sequence[str],
    truth: Sequence[str],
    raw_proba: NDArray[np.float64],
    classes: Sequence[str],
    calibration: OutOfFoldCalibration,
    seed: int = SEED,
) -> SplitEvaluation:
    """Evaluate raw probabilities on one frozen split with the fitted post-processing."""
    names = np.asarray(classes, dtype=str)
    true = np.asarray(truth, dtype=str)
    row_ids = np.asarray(ids, dtype=str)

    calibrated = apply_temperature(raw_proba, calibration.temperature)
    final, rule_applied = apply_small_package_rule(list(texts), calibrated, names)

    result_raw = evaluate(true, raw_proba, names, seed=seed)
    result_cal = evaluate(true, calibrated, names, seed=seed)
    result_final = evaluate(true, final, names, seed=seed)
    log_result(name, "raw", result_raw)
    log_result(name, "calibrated", result_cal)
    log_result(name, "calibrated + 31.05 rule", result_final)

    order = np.argsort(-final, axis=1, kind="stable")[:, :TOP_K]
    ranked = names[order]
    ranked_proba = np.take_along_axis(final, order, axis=1)
    confidence = ranked_proba[:, 0]
    hits1 = ranked[:, 0] == true
    needs_review = confidence < calibration.review.value
    review = summarize_review(confidence, hits1, calibration.review.value, seed=seed)

    labels = sorted(set(true))
    per_position = f1_score(true, ranked[:, 0], labels=labels, average=None, zero_division=0)

    predictions = pd.DataFrame({"id": row_ids, "true": true})
    for k in range(TOP_K):
        predictions[f"top{k + 1}"] = ranked[:, k]
    for k in range(TOP_K):
        predictions[f"p_top{k + 1}"] = ranked_proba[:, k].round(6)
    predictions["raw_top1"] = names[raw_proba.argmax(axis=1)]
    predictions["rule_31_05"] = rule_applied
    predictions["needs_review"] = needs_review
    predictions["hit_top1"] = hits1
    predictions["hit_top3"] = (ranked == true[:, None]).any(axis=1)

    errors = [
        {
            "id": row_ids[i],
            "text": texts[i],
            "true": true[i],
            "top3": list(ranked[i]),
            "confidence": round(float(confidence[i]), 3),
            "rule_31_05": bool(rule_applied[i]),
            "needs_review": bool(needs_review[i]),
        }
        for i in np.flatnonzero(~hits1)
    ]
    summary = {
        "metrics_raw": result_raw.to_dict(),
        "metrics_calibrated": result_cal.to_dict(),
        "metrics_calibrated_with_rules": result_final.to_dict(),
        "rule_31_05_rows": row_ids[rule_applied].tolist(),
        "review": review.to_dict(),
        "f1_by_position": {
            label: round(float(score), 4) for label, score in zip(labels, per_position, strict=True)
        },
        "by_chapter": chapter_metrics(true, ranked[:, 0]),
        "confusion_pairs": confusion_pairs(true, ranked[:, 0]),
        "errors": errors,
    }
    confusion = confusion_table(true, ranked[:, 0], names)
    return SplitEvaluation(summary, predictions, confusion)
