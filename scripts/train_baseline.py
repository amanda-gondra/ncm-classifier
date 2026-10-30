"""Train the TF-IDF + logistic regression baseline and evaluate it on the frozen test set.

Usage:
    python scripts/train_baseline.py --train data/processed/train_v1.parquet --name baseline_v1

The regularization strength C is chosen by 5-fold cross-validation on the
training set only. The test set is read once, after the model is final, so no
decision is tuned on it.

Outputs:
    models/<name>.joblib      fitted pipeline (not versioned in Git)
    reports/<name>.json       metrics with confidence intervals, per-position F1
                              and every test error, for the README and the article
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
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from ncm_classifier.evaluation.metrics import evaluate
from ncm_classifier.models.baseline import build_baseline

logger = logging.getLogger(__name__)

C_GRID: Final = (1.0, 3.0, 10.0, 30.0)
FOLDS: Final = 5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--test", type=Path, default=Path("data/labeled/test_v1.csv"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    train = pd.read_parquet(args.train)
    search = GridSearchCV(
        build_baseline(seed=args.seed),
        param_grid={"classifier__C": list(C_GRID)},
        scoring="f1_macro",
        cv=StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=args.seed),
        n_jobs=-1,
    )
    search.fit(train["text"].tolist(), train["position"].to_numpy())
    model = search.best_estimator_
    best_c = search.best_params_["classifier__C"]
    logger.info("Best C=%s, CV macro F1=%.4f", best_c, search.best_score_)

    test = pd.read_csv(args.test, dtype=str, keep_default_na=False)
    proba = model.predict_proba(test["text"].tolist())
    classes = model.classes_
    result = evaluate(test["position"].tolist(), proba, classes, seed=args.seed)

    ranked = classes[np.argsort(-proba, axis=1, kind="stable")[:, :3]]
    predicted = ranked[:, 0]
    truth = test["position"].to_numpy()
    per_position = f1_score(truth, predicted, labels=sorted(set(truth)), average=None)
    errors = [
        {
            "id": row_id,
            "text": text,
            "true": true,
            "top3": list(top3),
            "confidence": round(float(proba[i].max()), 3),
        }
        for i, (row_id, text, true, top3) in enumerate(
            zip(test["id"], test["text"], truth, ranked, strict=True)
        )
        if top3[0] != true
    ]

    report = {
        "model": "tfidf_word_char_logistic_regression",
        "train_file": args.train.name,
        "train_rows": len(train),
        "train_rows_by_source": train["source_type"].value_counts().sort_index().to_dict(),
        "test_file": args.test.name,
        "test_sha256": _sha256(args.test),
        "selection": {"C_grid": list(C_GRID), "best_C": best_c, "cv_macro_f1": search.best_score_},
        "metrics": result.to_dict(),
        "f1_by_position": {
            label: round(float(score), 4)
            for label, score in zip(sorted(set(truth)), per_position, strict=True)
        },
        "errors": errors,
        "seed": args.seed,
    }

    Path("models").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    joblib.dump(model, Path("models") / f"{args.name}.joblib")
    report_path = Path("reports") / f"{args.name}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics = result
    logger.info(
        "Test (%d rows): top1 %.3f [%.3f-%.3f] | top3 %.3f [%.3f-%.3f] | "
        "macro F1 %.3f [%.3f-%.3f] | ECE %.3f",
        metrics.rows,
        metrics.top1.value,
        metrics.top1.low,
        metrics.top1.high,
        metrics.top3.value,
        metrics.top3.low,
        metrics.top3.high,
        metrics.macro_f1.value,
        metrics.macro_f1.low,
        metrics.macro_f1.high,
        metrics.ece,
    )
    logger.info("Report saved to %s", report_path)


if __name__ == "__main__":
    main()
