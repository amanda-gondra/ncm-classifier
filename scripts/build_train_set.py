"""Build a training set from the selected sources, checked against the frozen test set.

Usage:
    python scripts/build_train_set.py --sources real synthetic official --name train_v1
    python scripts/build_train_set.py --sources real official --name train_v1_no_synthetic

Sources, listed in priority order (the first occurrence of a repeated text wins):
    real       data/labeled/train_real_v1.csv       real descriptions, human reviewed
    synthetic  data/labeled/train_synthetic_v1.csv  LLM-written, marked as synthetic
    official   official NCM descriptions for the positions in scope

Outputs data/processed/<name>.parquet and data/processed/<name>_report.json.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Final

import pandas as pd

from ncm_classifier.data.ncm_table import load_ncm_table
from ncm_classifier.data.official_examples import build_official_examples
from ncm_classifier.data.scope import load_scope
from ncm_classifier.data.training_set import assemble_training_set

logger = logging.getLogger(__name__)

LABELED_DIR: Final = Path("data/labeled")
MANUAL_SOURCES: Final = {
    "real": LABELED_DIR / "train_real_v1.csv",
    "synthetic": LABELED_DIR / "train_synthetic_v1.csv",
}
SOURCE_ORDER: Final = ("real", "synthetic", "official")


def _load_manual(path: Path) -> pd.DataFrame:
    """Read a labeled CSV and keep only rows a human has reviewed."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    reviewed = frame[frame["reviewed"] == "true"]
    skipped = len(frame) - len(reviewed)
    if skipped:
        logger.warning("%s: %d rows not reviewed yet were skipped", path.name, skipped)
    return reviewed.rename(columns={"id": "example_id", "source_url": "source_ref"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=SOURCE_ORDER, required=True)
    parser.add_argument("--name", required=True, help="output file name, without extension")
    parser.add_argument("--ncm-file", type=Path, default=Path("data/raw/ncm_siscomex.json"))
    parser.add_argument("--scope-file", type=Path, default=Path("configs/scope.json"))
    parser.add_argument("--test-file", type=Path, default=LABELED_DIR / "test_v1.csv")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--reference-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    scope = load_scope(args.scope_file)
    test_set = pd.read_csv(args.test_file, dtype=str, keep_default_na=False)

    frames = []
    for name in (source for source in SOURCE_ORDER if source in args.sources):
        if name == "official":
            table = load_ncm_table(args.ncm_file).active_on(args.reference_date)
            scope.validate_against(table)
            official = build_official_examples(table, scope.positions)
            official["example_id"] = "ncm-" + official["source_ref"]
            frames.append(official)
        else:
            frames.append(_load_manual(MANUAL_SOURCES[name]))

    train, report = assemble_training_set(frames, test_set, scope.positions)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_path = args.output_dir / f"{args.name}.parquet"
    report_path = args.output_dir / f"{args.name}_report.json"
    train.to_parquet(train_path, index=False)
    report_path.write_text(
        json.dumps(
            {"sources": list(args.sources), "reference_date": str(args.reference_date)}
            | asdict(report),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Rows by source: %s", report.rows_by_source)
    logger.info(
        "Dropped: %d near test, %d label conflicts, %d repeated",
        report.dropped_near_test,
        report.dropped_label_conflict,
        report.dropped_repeated,
    )
    logger.info("Saved %d rows to %s", report.output_rows, train_path)


if __name__ == "__main__":
    main()
