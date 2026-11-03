"""Compare two models evaluated with the shared protocol (stage 6).

Usage:
    python scripts/compare_models.py

Defaults compare A = baseline_v1 with B = bertimbau_v1. The script first audits
that the two experiments are comparable and stops, listing every failed check,
if they are not. Only then it compares them:

    * headline metrics of each model, as recorded in its report;
    * paired bootstrap differences (B - A) of top-1, top-3 and macro F1 and
      McNemar's exact test, per test set, on both test sets pooled and on the
      out-of-fold predictions of the training set;
    * one row per test example with the predictions of both models.

Outputs (reports/comparison/):
    comparison.json, per_example.csv, paired_differences.png
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ncm_classifier.evaluation.comparison import mcnemar_exact, paired_accuracy, paired_macro_f1
from ncm_classifier.evaluation.protocol import (
    folds_fingerprint,
    frozen_checksum,
    load_frozen_test,
    sha256_bytes,
)
from ncm_classifier.evaluation.report import calibrate_out_of_fold
from ncm_classifier.models.calibration import apply_temperature
from ncm_classifier.rules.small_package import apply_small_package_rule

logger = logging.getLogger(__name__)

OUTPUT_DIR: Final = Path("reports/comparison")
TOP_K: Final = 3


@dataclass(frozen=True)
class Experiment:
    name: str
    report_path: Path
    predictions_dir: Path
    out_of_fold_path: Path

    def report(self) -> dict:
        return json.loads(self.report_path.read_text(encoding="utf-8"))

    def predictions(self, test: Path) -> pd.DataFrame:
        path = self.predictions_dir / f"{self.name}__{test.stem}.csv"
        return pd.read_csv(path, dtype=str, keep_default_na=False)

    def classes(self, test: Path) -> list[str]:
        path = self.predictions_dir / f"{self.name}__{test.stem}_confusion.csv"
        return pd.read_csv(path, index_col=0, dtype=str).columns.tolist()


BASELINE: Final = Experiment(
    "baseline_v1",
    Path("reports/baseline_v1.json"),
    Path("reports/predictions"),
    Path("reports/predictions/baseline_v1__out_of_fold_proba.npy"),
)
BERTIMBAU: Final = Experiment(
    "bertimbau_v1",
    Path("experiments/bertimbau/metrics/bertimbau_v1.json"),
    Path("experiments/bertimbau/predictions"),
    Path("experiments/bertimbau/reports/out_of_fold_proba.npy"),
)


def _last_commit(path: Path) -> str:
    return subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", "log", "-1", "--format=%H", "--", str(path)],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _hits(predictions: pd.DataFrame, column: str) -> np.ndarray:
    return (predictions[column] == "True").to_numpy()


def audit(
    a: Experiment, b: Experiment, train_path: Path, tests: list[Path], data_version: dict
) -> list[dict[str, object]]:
    """Every check that must hold for the comparison to be fair."""
    report_a, report_b = a.report(), b.report()
    train = pd.read_parquet(train_path)
    labels = train["position"].to_numpy(dtype=str)
    classes = np.unique(labels).tolist()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    train_sha = sha256_bytes(train_path)
    check(
        "same training file",
        report_a["train_sha256"] == report_b["train_sha256"] == train_sha,
        train_sha,
    )
    fingerprint = folds_fingerprint(train["example_id"].tolist(), labels)
    check(
        "same cross-validation folds",
        report_a["protocol"] == report_b["protocol"]
        and report_a["protocol"]["folds_sha256"] == fingerprint,
        fingerprint,
    )
    commit_a = _last_commit(a.report_path)
    check(
        "A report produced by the code B ran",
        commit_a == data_version["repo_commit"],
        f"A: {commit_a[:7]}, B: {data_version['repo_commit'][:7]}",
    )
    tests_a = {t["file"]: t for t in report_a["tests"]}
    tests_b = {t["file"]: t for t in report_b["tests"]}
    for test in tests:
        frozen = load_frozen_test(test)  # refuses changed or unreviewed files
        check(
            f"{test.name}: same frozen file",
            tests_a[test.name]["sha256"] == tests_b[test.name]["sha256"] == frozen_checksum(test),
        )
        for experiment, report_tests in ((a, tests_a), (b, tests_b)):
            predictions = experiment.predictions(test)
            check(
                f"{test.name}: {experiment.name} predicts every row, in order",
                predictions["id"].tolist() == frozen["id"].tolist(),
            )
            recorded = report_tests[test.name]["metrics_calibrated_with_rules"]["top1"]["value"]
            check(
                f"{test.name}: {experiment.name} predictions match its report",
                round(float(_hits(predictions, "hit_top1").mean()), 4) == recorded,
            )
            check(
                f"{test.name}: {experiment.name} classes are the training positions",
                experiment.classes(test) == classes,
            )
    for experiment, report in ((a, report_a), (b, report_b)):
        refit = calibrate_out_of_fold(
            train["text"].tolist(), labels, np.load(experiment.out_of_fold_path), classes
        )
        check(
            f"{experiment.name}: temperature and review threshold come from out-of-fold data",
            round(refit.temperature, 4) == report["selection"]["temperature"]
            and abs(refit.review.value - report["review_out_of_fold"]["value"]) < 1e-9,
            f"T={refit.temperature:.4f}, threshold={refit.review.value:.4f}",
        )
    return checks


def _paired(truth: np.ndarray, frame_a: pd.DataFrame, frame_b: pd.DataFrame) -> dict[str, object]:
    hits_a, hits_b = _hits(frame_a, "hit_top1"), _hits(frame_b, "hit_top1")
    return {
        "rows": len(truth),
        "top1": paired_accuracy(hits_a, hits_b, "top1").to_dict(),
        "top3": paired_accuracy(
            _hits(frame_a, "hit_top3"), _hits(frame_b, "hit_top3"), "top3"
        ).to_dict(),
        "macro_f1": paired_macro_f1(truth, frame_a["top1"], frame_b["top1"]).to_dict(),
        "mcnemar_top1": mcnemar_exact(hits_a, hits_b).to_dict(),
    }


def _headline(test_report: dict) -> dict[str, object]:
    metrics = test_report["metrics_calibrated_with_rules"]
    keys = ("top1", "top3", "macro_f1", "macro_precision", "macro_recall")
    return {
        **{key: metrics[key] for key in keys},
        "ece": metrics["ece"],
        "ece_raw": test_report["metrics_raw"]["ece"],
        "review_rate": test_report["review"]["review_rate"],
        "accepted_top1": test_report["review"]["accepted_top1"],
        "rule_31_05_rows": test_report["rule_31_05_rows"],
        "by_chapter": test_report["by_chapter"],
    }


def _out_of_fold_frame(texts: list[str], labels: np.ndarray, proba: np.ndarray) -> pd.DataFrame:
    """Final out-of-fold predictions: temperature and 31.05 rule, as on the tests."""
    classes = np.unique(labels)
    calibration = calibrate_out_of_fold(texts, labels, proba, classes)
    final, _ = apply_small_package_rule(
        texts, apply_temperature(proba, calibration.temperature), classes
    )
    ranked = classes[np.argsort(-final, axis=1, kind="stable")[:, :TOP_K]]
    return pd.DataFrame(
        {
            "top1": ranked[:, 0],
            "hit_top1": (ranked[:, 0] == labels).astype(str),
            "hit_top3": (ranked == labels[:, None]).any(axis=1).astype(str),
        }
    )


def _per_example(test: Path, frame_a: pd.DataFrame, frame_b: pd.DataFrame) -> pd.DataFrame:
    frozen = load_frozen_test(test)
    columns = ["top1", "top2", "top3", "p_top1", "rule_31_05", "needs_review", "hit_top1"]
    merged = frozen[["id", "text", "position"]].rename(columns={"position": "true"})
    merged = merged.merge(frame_a[["id", *columns]].add_prefix("a_"), left_on="id", right_on="a_id")
    merged = merged.merge(frame_b[["id", *columns]].add_prefix("b_"), left_on="id", right_on="b_id")
    hit_a, hit_b = merged["a_hit_top1"] == "True", merged["b_hit_top1"] == "True"
    merged["outcome"] = np.select(
        [hit_a & hit_b, hit_a & ~hit_b, ~hit_a & hit_b],
        ["both_right", "only_a", "only_b"],
        default="both_wrong",
    )
    merged.insert(0, "test", test.stem)
    return merged.drop(columns=["a_id", "b_id"])


def _plot(paired: dict[str, dict], names: tuple[str, str], path: Path) -> None:
    metrics = ("top1", "macro_f1")
    figure, axes = plt.subplots(1, len(metrics), figsize=(10, 3.2), sharey=True)
    labels = list(paired)
    for axis, metric in zip(axes, metrics, strict=True):
        for row, label in enumerate(labels):
            diff = paired[label][metric]["difference"]
            axis.errorbar(
                diff["value"],
                row,
                xerr=[[diff["value"] - diff["low"]], [diff["high"] - diff["value"]]],
                fmt="o",
                color="#2f5d8a",
                capsize=4,
            )
        axis.axvline(0.0, color="#888888", linewidth=1, linestyle="--")
        axis.set_title(f"{metric}: {names[1]} - {names[0]}")
        axis.set_yticks(range(len(labels)), labels)
        axis.grid(axis="x", alpha=0.3)
    axes[0].invert_yaxis()  # the y axis is shared: inverting it once puts the first label on top
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("data/processed/train_v1.parquet"))
    parser.add_argument(
        "--test",
        type=Path,
        nargs="+",
        default=[Path("data/labeled/test_v1.csv"), Path("data/labeled/test_v2.csv")],
    )
    parser.add_argument(
        "--data-version", type=Path, default=Path("experiments/bertimbau/data_version.json")
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    a, b = BASELINE, BERTIMBAU
    data_version = json.loads(args.data_version.read_text(encoding="utf-8"))
    checks = audit(a, b, args.train, args.test, data_version)
    for item in checks:
        logger.info("%s %s %s", "PASS" if item["passed"] else "FAIL", item["check"], item["detail"])
    failed = [item["check"] for item in checks if not item["passed"]]
    if failed:
        raise SystemExit(f"Not comparable, stopping: {failed}")

    report_a, report_b = a.report(), b.report()
    tests_a = {t["file"]: t for t in report_a["tests"]}
    tests_b = {t["file"]: t for t in report_b["tests"]}
    paired, headline, examples = {}, {}, []
    pooled_a, pooled_b, pooled_truth = [], [], []
    for test in args.test:
        frame_a, frame_b = a.predictions(test), b.predictions(test)
        truth = frame_a["true"].to_numpy()
        paired[test.stem] = _paired(truth, frame_a, frame_b)
        headline[test.stem] = {
            a.name: _headline(tests_a[test.name]),
            b.name: _headline(tests_b[test.name]),
        }
        examples.append(_per_example(test, frame_a, frame_b))
        pooled_a.append(frame_a)
        pooled_b.append(frame_b)
        pooled_truth.append(truth)
    paired["tests_pooled"] = _paired(
        np.concatenate(pooled_truth),
        pd.concat(pooled_a, ignore_index=True),
        pd.concat(pooled_b, ignore_index=True),
    )

    train = pd.read_parquet(args.train)
    texts, labels = train["text"].tolist(), train["position"].to_numpy(dtype=str)
    paired["out_of_fold"] = _paired(
        labels,
        _out_of_fold_frame(texts, labels, np.load(a.out_of_fold_path)),
        _out_of_fold_frame(texts, labels, np.load(b.out_of_fold_path)),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "model_a": a.name,
        "model_b": b.name,
        "difference": "model_b - model_a",
        "bootstrap": {"resamples": 1000, "seed": 0, "paired": True},
        "audit": checks,
        "selection": {a.name: report_a["selection"], b.name: report_b["selection"]},
        "out_of_fold_review": {
            a.name: report_a["review_out_of_fold"],
            b.name: report_b["review_out_of_fold"],
        },
        "headline": headline,
        "paired": paired,
    }
    (OUTPUT_DIR / "comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.concat(examples, ignore_index=True).to_csv(OUTPUT_DIR / "per_example.csv", index=False)
    _plot(paired, (a.name, b.name), OUTPUT_DIR / "paired_differences.png")
    for label, values in paired.items():
        logger.info(
            "%s: top1 %+.4f [%+.4f, %+.4f] | macro F1 %+.4f [%+.4f, %+.4f] | McNemar p=%.3f",
            label,
            values["top1"]["difference"]["value"],
            values["top1"]["difference"]["low"],
            values["top1"]["difference"]["high"],
            values["macro_f1"]["difference"]["value"],
            values["macro_f1"]["difference"]["low"],
            values["macro_f1"]["difference"]["high"],
            values["mcnemar_top1"]["p_value"],
        )
    logger.info("Saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
