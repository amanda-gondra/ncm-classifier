"""Convert the raw Classif JSON into a clean Parquet table plus a metadata file.

Usage:
    python scripts/build_ncm_table.py data/raw/ncm_siscomex.json
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from ncm_classifier.data.ncm_table import load_ncm_table

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("data/interim")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_file", type=Path, help="JSON downloaded from Classif")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    table = load_ncm_table(args.raw_file)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    table_path = args.output_dir / "ncm_table.parquet"
    metadata_path = args.output_dir / "ncm_table_metadata.json"
    table.entries.to_parquet(table_path, index=False)
    metadata_path.write_text(
        json.dumps(
            {**asdict(table.metadata), "source_file": args.raw_file.name},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    counts = table.entries["level"].value_counts().to_dict()
    logger.info("Table: %s (%s)", table.metadata.last_update, table.metadata.legal_act)
    logger.info("Entries by level: %s", counts)
    logger.info("Saved %s and %s", table_path, metadata_path)


if __name__ == "__main__":
    main()
