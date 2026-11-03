"""Where the errors are: by NCM chapter and by pair of confused positions.

A chapter is the first two digits of the position (31 for fertilizers, 73 for
iron and steel articles...). Two accuracies are reported per chapter:

    position_accuracy  the first suggestion is the right position;
    chapter_accuracy   the first suggestion is at least in the right chapter.

A large gap between them means the model finds the family of the product but
confuses neighbouring positions, which is a different problem from not
recognizing the product at all.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix


def chapter_of(position: str) -> str:
    return position[:2]


def chapter_metrics(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, dict[str, float]]:
    truth = np.asarray(y_true, dtype=str)
    predicted = np.asarray(y_pred, dtype=str)
    if truth.shape != predicted.shape:
        raise ValueError("y_true and y_pred must have the same length")

    true_chapter = np.array([chapter_of(p) for p in truth])
    predicted_chapter = np.array([chapter_of(p) for p in predicted])
    result: dict[str, dict[str, float]] = {}
    for chapter in sorted(set(true_chapter)):
        rows = true_chapter == chapter
        result[chapter] = {
            "rows": int(rows.sum()),
            "position_accuracy": round(float((predicted[rows] == truth[rows]).mean()), 4),
            "chapter_accuracy": round(float((predicted_chapter[rows] == chapter).mean()), 4),
        }
    return result


def confusion_table(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]
) -> pd.DataFrame:
    """Confusion matrix with true positions as rows and predicted ones as columns."""
    names = [str(label) for label in labels]
    matrix = confusion_matrix(list(y_true), list(y_pred), labels=names)
    table = pd.DataFrame(matrix, index=names, columns=names)
    table.index.name = "true"
    table.columns.name = "predicted"
    return table


def confusion_pairs(y_true: Sequence[str], y_pred: Sequence[str]) -> list[dict[str, object]]:
    """Every (true, predicted) pair that differs, most frequent first."""
    pairs = Counter(
        (str(true), str(pred)) for true, pred in zip(y_true, y_pred, strict=True) if true != pred
    )
    ordered = sorted(pairs.items(), key=lambda item: (-item[1], item[0]))
    return [{"true": true, "predicted": pred, "count": count} for (true, pred), count in ordered]
