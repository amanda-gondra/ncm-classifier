"""Train the TF-IDF + logistic regression baseline and evaluate it on frozen test sets.

Usage:
    python scripts/train_baseline.py --train data/processed/train_v1.parquet --name baseline_v1 \
        --test data/labeled/test_v1.csv data/labeled/test_v2.csv

Every choice is made on the training set only:
    * the regularization strength C, by 5-fold cross-validation;
    * the calibration temperature, fitted on the out-of-fold probabilities of
      those same folds.
Test sets are read after the model is final. A test file with rows not yet
reviewed by a human is rejected.

Outputs:
    models/<name>.joblib      {"pipeline", "temperature"} (not versioned in Git)
    reports/<name>.json       metrics with confidence intervals (raw and
                              calibrated), per-position F1 and every test error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict

from ncm_classifier.evaluation.metrics import EvaluationResult, evaluate
from ncm_classifier.models.baseline import build_baseline
from ncm_classifier.models.calibration import apply_temperature, fit_temperature
from ncm_classifier.rules.small_package import apply_small_package_rule

logger = logging.getLogger(__name__)

C_GRID: Final = (1.0, 3.0, 10.0, 30.0)
FOLDS: Final = 5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _load_test(path: Path) -> pd.DataFrame:
    test = pd.read_csv(path, dtype=str, keep_default_na=False)
    pending = int((test["reviewed"] != "true").sum())
    if pending:
        raise SystemExit(f"{path.name}: {pending} rows not reviewed yet; refusing to evaluate")
    return test


def _log(name: str, label: str, result: EvaluationResult) -> None:
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


def _evaluate_file(
    model: BaseEstimator, temperature: float, path: Path, seed: int
) -> dict[str, object]:
    test = _load_test(path)
    raw = model.predict_proba(test["text"].tolist())
    calibrated = apply_temperature(raw, temperature)
    classes = model.classes_
    truth = test["position"].to_numpy()

    final, rule_applied = apply_small_package_rule(test["text"].tolist(), calibrated, classes)

    result_raw = evaluate(truth, raw, classes, seed=seed)
    result_cal = evaluate(truth, calibrated, classes, seed=seed)
    result_final = evaluate(truth, final, classes, seed=seed)
    _log(path.name, "raw", result_raw)
    _log(path.name, "calibrated", result_cal)
    _log(path.name, "calibrated + 31.05 rule", result_final)

    ranked = classes[np.argsort(-final, axis=1, kind="stable")[:, :3]]
    labels = sorted(set(truth))
    per_position = f1_score(truth, ranked[:, 0], labels=labels, average=None)
    errors = [
        {
            "id": row_id,
            "text": text,
            "true": true,
            "top3": list(top3),
            "confidence": round(float(final[i].max()), 3),
            "rule_31_05": bool(rule_applied[i]),
        }
        for i, (row_id, text, true, top3) in enumerate(
            zip(test["id"], test["text"], truth, ranked, strict=True)
        )
        if top3[0] != true
    ]
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "metrics_raw": result_raw.to_dict(),
        "metrics_calibrated": result_cal.to_dict(),
        "metrics_calibrated_with_rules": result_final.to_dict(),
        "rule_31_05_rows": [
            row_id for row_id, hit in zip(test["id"], rule_applied, strict=True) if hit
        ],
        "f1_by_position": {
            label: round(float(score), 4) for label, score in zip(labels, per_position, strict=True)
        },
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--test", type=Path, nargs="+", default=[Path("data/labeled/test_v1.csv")])
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    train = pd.read_parquet(args.train)
    texts, labels = train["text"].tolist(), train["position"].to_numpy()
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=args.seed)

    search = GridSearchCV(
        build_baseline(seed=args.seed),
        param_grid={"classifier__C": list(C_GRID)},
        scoring="f1_macro",
        cv=folds,
        n_jobs=-1,
    )
    search.fit(texts, labels)
    model = search.best_estimator_
    best_c = search.best_params_["classifier__C"]
    logger.info("Best C=%s, CV macro F1=%.4f", best_c, search.best_score_)

    out_of_fold = cross_val_predict(
        build_baseline(c=best_c, seed=args.seed),
        texts,
        labels,
        cv=folds,
        method="predict_proba",
        n_jobs=-1,
    )
    classes = np.unique(labels)
    temperature = fit_temperature(out_of_fold, labels, classes)
    logger.info("Calibration temperature (out-of-fold, training only): %.3f", temperature)

    # The 31.05 rule comes from the heading text, not from data; its effect is measured
    # on the training folds too, so it is not judged on the test sets alone.
    oof_calibrated = apply_temperature(out_of_fold, temperature)
    oof_final, oof_applied = apply_small_package_rule(texts, oof_calibrated, classes)
    oof_top1 = float((classes[oof_calibrated.argmax(axis=1)] == labels).mean())
    oof_top1_rule = float((classes[oof_final.argmax(axis=1)] == labels).mean())
    logger.info(
        "Out-of-fold top1: %.4f -> %.4f with the 31.05 rule (%d rows changed)",
        oof_top1,
        oof_top1_rule,
        int(oof_applied.sum()),
    )

    report = {
        "model": "tfidf_word_char_logistic_regression",
        "train_file": args.train.name,
        "train_rows": len(train),
        "train_rows_by_source": train["source_type"].value_counts().sort_index().to_dict(),
        "selection": {
            "C_grid": list(C_GRID),
            "best_C": best_c,
            "cv_macro_f1": search.best_score_,
            "temperature": round(temperature, 4),
        },
        "rule_31_05_out_of_fold": {
            "top1_without_rule": round(oof_top1, 4),
            "top1_with_rule": round(oof_top1_rule, 4),
            "rows_changed": int(oof_applied.sum()),
        },
        "tests": [_evaluate_file(model, temperature, path, args.seed) for path in args.test],
        "seed": args.seed,
    }

    Path("models").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    joblib.dump(
        {"pipeline": model, "temperature": temperature}, Path("models") / f"{args.name}.joblib"
    )
    report_path = Path("reports") / f"{args.name}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Report saved to %s", report_path)


if __name__ == "__main__":
    main()
