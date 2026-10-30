"""Assemble the training set from its sources without leaking into the test set.

Rules, applied in this order:

1. Every position must be inside the scope; anything else is an error.
2. A training source may not share a URL with the test set; that is an error,
   because it means the same page fed both sides.
3. Rows that are near-duplicates of any test text are dropped.
4. Texts that appear with two different positions are dropped: the label is
   ambiguous and would teach the model noise.
5. Repeated texts keep their first occurrence. Sources are passed in priority
   order, so a real description wins over a synthetic or official one.

The function returns the rows and a report with what was removed and why, so
every number in the README can be traced back to this step.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

import pandas as pd

from ncm_classifier.data.dedup import DEFAULT_THRESHOLD, near_duplicate_mask
from ncm_classifier.text import normalize_text

COLUMNS: Final = ["example_id", "text", "position", "source_type", "source_ref"]


class TrainingSetError(ValueError):
    """Raised when a source breaks a rule that cannot be fixed by dropping rows."""


@dataclass
class AssemblyReport:
    input_rows: int = 0
    dropped_near_test: int = 0
    dropped_label_conflict: int = 0
    dropped_repeated: int = 0
    output_rows: int = 0
    rows_by_source: dict[str, int] = field(default_factory=dict)
    rows_by_position: dict[str, int] = field(default_factory=dict)


def assemble_training_set(
    sources: Sequence[pd.DataFrame],
    test_set: pd.DataFrame,
    scope_positions: Sequence[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[pd.DataFrame, AssemblyReport]:
    """Combine sources (in priority order) into one leak-free training table."""
    for source in sources:
        missing = set(COLUMNS) - set(source.columns)
        if missing:
            raise TrainingSetError(f"source is missing columns: {sorted(missing)}")

    combined = pd.concat([source[COLUMNS] for source in sources], ignore_index=True)
    report = AssemblyReport(input_rows=len(combined))

    outside = sorted(set(combined["position"]) - set(scope_positions))
    if outside:
        raise TrainingSetError(f"positions outside the scope: {outside}")

    shared_urls = sorted(set(combined["source_ref"]) & set(test_set["source_url"]))
    if shared_urls:
        raise TrainingSetError(f"training sources shared with the test set: {shared_urls[:5]}")

    near_test = near_duplicate_mask(combined["text"].tolist(), test_set["text"].tolist(), threshold)
    report.dropped_near_test = sum(near_test)
    combined = combined[[not flag for flag in near_test]].reset_index(drop=True)

    normalized = combined["text"].map(normalize_text)
    labels_per_text = combined.groupby(normalized)["position"].nunique()
    conflicting = normalized.map(labels_per_text) > 1
    report.dropped_label_conflict = int(conflicting.sum())
    combined, normalized = combined[~conflicting], normalized[~conflicting]

    repeated = normalized.duplicated()
    report.dropped_repeated = int(repeated.sum())
    combined = combined[~repeated].reset_index(drop=True)

    if not combined["example_id"].is_unique:
        raise TrainingSetError("example ids must be unique across sources")

    report.output_rows = len(combined)
    report.rows_by_source = combined["source_type"].value_counts().sort_index().to_dict()
    report.rows_by_position = combined["position"].value_counts().sort_index().to_dict()
    return combined, report
