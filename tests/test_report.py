import numpy as np
import pytest

from ncm_classifier.evaluation.report import calibrate_out_of_fold, evaluate_split

CLASSES = np.array(["3102", "3105", "7313"])
TEXTS = [
    "Ureia agricola saco 50 kg",
    "Ureia fertilizante 1 kg",
    "Grampo para cerca",
    "Ureia granulada big bag",
    "Grampo galvanizado 1 kg",
    "Ureia saco 25 kg",
]
LABELS = np.array(["3102", "3105", "7313", "3102", "7313", "3102"])
PROBA = np.array(
    [
        [0.80, 0.10, 0.10],
        [0.70, 0.20, 0.10],  # small package: the rule moves it to 3105
        [0.10, 0.10, 0.80],
        [0.60, 0.20, 0.20],
        [0.30, 0.10, 0.60],  # 1 kg, but top-1 is not Chapter 31: no rule
        [0.40, 0.30, 0.30],
    ]
)


@pytest.fixture(scope="module")
def calibration():
    return calibrate_out_of_fold(TEXTS, LABELS, PROBA, CLASSES)


def test_out_of_fold_calibration_reports_rule_and_review(calibration) -> None:
    summary = calibration.summary
    assert calibration.temperature > 0
    assert summary["rule_31_05"]["rows_changed"] == 1
    assert summary["rule_31_05"]["top1_with_rule"] == 1.0
    assert summary["review"]["target_reached"]
    assert summary["review"]["value"] == calibration.review.value
    assert "threshold" not in summary["review"]


def test_evaluate_split_keeps_one_prediction_per_row(calibration) -> None:
    ids = [f"t{i}" for i in range(len(TEXTS))]
    evaluation = evaluate_split("toy", ids, TEXTS, LABELS, PROBA, CLASSES, calibration)

    predictions = evaluation.predictions
    assert predictions["id"].tolist() == ids
    assert predictions["hit_top1"].all()
    assert predictions.loc[1, "rule_31_05"]
    assert predictions.loc[1, "raw_top1"] == "3102"
    assert predictions.loc[1, "top1"] == "3105"
    assert (predictions["p_top1"] >= predictions["p_top2"]).all()

    summary = evaluation.summary
    assert summary["rule_31_05_rows"] == ["t1"]
    assert summary["errors"] == []
    assert summary["metrics_calibrated_with_rules"]["top1"]["value"] == 1.0
    assert summary["by_chapter"]["31"]["position_accuracy"] == 1.0
    assert summary["review"]["rows"] == len(TEXTS)
    assert int(evaluation.confusion.to_numpy().trace()) == len(TEXTS)
