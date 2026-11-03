"""Train the TF-IDF + logistic regression baseline and evaluate it on frozen test sets.

Usage:
    python scripts/train_baseline.py --train data/processed/train_v1.parquet --name baseline_v1 \
        --test data/labeled/test_v1.csv data/labeled/test_v2.csv

Every choice is made on the training set only, on the folds of
`ncm_classifier.evaluation.protocol`:
    * the regularization strength C, by 5-fold cross-validation;
    * the calibration temperature and the manual review threshold, fitted on the
      out-of-fold probabilities of those same folds.
Test sets are read after the model is final. A test file with rows not yet
reviewed by a human is rejected.

Outputs:
    models/<name>.joblib                       {"pipeline", "temperature",
                                                "review_threshold"} (not in Git)
    reports/<name>.json                        metrics with confidence intervals,
                                               breakdowns and every test error
    reports/predictions/<name>__<test>.csv     one row per test example
    reports/predictions/<name>__<test>_confusion.csv
    reports/predictions/<name>__out_of_fold_proba.npy
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Final

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, cross_val_predict

from ncm_classifier.evaluation.protocol import (
    FOLDS,
    folds_fingerprint,
    load_frozen_test,
    make_folds,
    sha256_bytes,
    sha256_text,
)
from ncm_classifier.evaluation.report import calibrate_out_of_fold, evaluate_split
from ncm_classifier.models.baseline import build_baseline

logger = logging.getLogger(__name__)

C_GRID: Final = (1.0, 3.0, 10.0, 30.0)
PREDICTIONS_DIR: Final = Path("reports/predictions")


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
    folds = make_folds(args.seed)

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
    calibration = calibrate_out_of_fold(texts, labels, out_of_fold, classes, seed=args.seed)

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    # Raw out-of-fold probabilities, rows in training order and columns in class order,
    # so other models can be compared with this one on the same folds.
    np.save(PREDICTIONS_DIR / f"{args.name}__out_of_fold_proba.npy", out_of_fold)
    tests = []
    for path in args.test:
        test = load_frozen_test(path)
        evaluation = evaluate_split(
            path.name,
            test["id"].tolist(),
            test["text"].tolist(),
            test["position"].tolist(),
            model.predict_proba(test["text"].tolist()),
            classes,
            calibration,
            seed=args.seed,
        )
        stem = f"{args.name}__{path.stem}"
        evaluation.predictions.to_csv(PREDICTIONS_DIR / f"{stem}.csv", index=False)
        evaluation.confusion.to_csv(PREDICTIONS_DIR / f"{stem}_confusion.csv")
        tests.append({"file": path.name, "sha256": sha256_text(path), **evaluation.summary})

    report = {
        "model": "tfidf_word_char_logistic_regression",
        "train_file": args.train.name,
        "train_sha256": sha256_bytes(args.train),
        "train_rows": len(train),
        "train_rows_by_source": train["source_type"].value_counts().sort_index().to_dict(),
        "protocol": {
            "folds": FOLDS,
            "folds_sha256": folds_fingerprint(train["example_id"].tolist(), labels, args.seed),
        },
        "selection": {
            "C_grid": list(C_GRID),
            "best_C": best_c,
            "cv_macro_f1": search.best_score_,
            "temperature": calibration.summary["temperature"],
        },
        "rule_31_05_out_of_fold": calibration.summary["rule_31_05"],
        "review_out_of_fold": calibration.summary["review"],
        "tests": tests,
        "seed": args.seed,
    }

    Path("models").mkdir(exist_ok=True)
    joblib.dump(
        {
            "pipeline": model,
            "temperature": calibration.temperature,
            "review_threshold": calibration.review.value,
        },
        Path("models") / f"{args.name}.joblib",
    )
    report_path = Path("reports") / f"{args.name}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Report saved to %s", report_path)


if __name__ == "__main__":
    main()
