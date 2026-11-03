from ncm_classifier.evaluation.breakdown import chapter_metrics, confusion_pairs, confusion_table

TRUTH = ["3102", "3102", "3105", "7313", "7313"]
PRED = ["3102", "3105", "3105", "7217", "7313"]


def test_chapter_metrics_separate_position_and_chapter_errors() -> None:
    result = chapter_metrics(TRUTH, PRED)
    # Chapter 31: one wrong position, but always the right chapter.
    assert result["31"] == {"rows": 3, "position_accuracy": 0.6667, "chapter_accuracy": 1.0}
    # Chapter 73: the error left the chapter (7313 -> 7217).
    assert result["73"] == {"rows": 2, "position_accuracy": 0.5, "chapter_accuracy": 0.5}


def test_confusion_table_has_true_rows_and_predicted_columns() -> None:
    table = confusion_table(TRUTH, PRED, ["3102", "3105", "7217", "7313"])
    assert table.loc["3102", "3105"] == 1
    assert table.loc["7313", "7217"] == 1
    assert int(table.to_numpy().trace()) == 3


def test_confusion_pairs_list_only_errors_most_frequent_first() -> None:
    pairs = confusion_pairs(TRUTH + ["3102"], PRED + ["3105"])
    assert pairs[0] == {"true": "3102", "predicted": "3105", "count": 2}
    assert pairs[1] == {"true": "7313", "predicted": "7217", "count": 1}
    assert len(pairs) == 2
