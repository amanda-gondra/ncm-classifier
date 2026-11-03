"""Write the official descriptions of the scope positions to a package data file.

Usage:
    python scripts/build_positions.py

Reads the clean NCM table (data/interim/, built by build_ncm_table.py) and the
scope (configs/scope.json), and writes src/ncm_classifier/data/positions.json.
The API shows these descriptions next to each suggestion; the file is versioned
with the code, so the API never needs the 3 MB government table at run time.

Descriptions come from NcmTable.positions(), the same source as the official
training examples: positions without a 4-digit row in the table (73.13 only
appears as 7313.00.00) take the text of their most general entry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

import pandas as pd

from ncm_classifier.data.ncm_table import NcmTable, NcmTableMetadata
from ncm_classifier.data.scope import load_scope

logger = logging.getLogger(__name__)

TABLE: Final = Path("data/interim/ncm_table.parquet")
METADATA: Final = Path("data/interim/ncm_table_metadata.json")
OUTPUT: Final = Path("src/ncm_classifier/data/positions.json")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    table = NcmTable(
        NcmTableMetadata(metadata["last_update"], metadata["legal_act"]),
        pd.read_parquet(TABLE),
    )
    scope = load_scope(Path("configs/scope.json")).positions
    positions = table.positions().set_index("code").reindex(scope)
    missing = positions[positions["description"].isna()].index.tolist()
    if missing:
        raise SystemExit(f"positions without an official description: {missing}")

    content = {
        "ncm_table": table.metadata.last_update,
        "legal_act": table.metadata.legal_act,
        "level": "position",
        "positions": {
            code: {"formatted": f"{code[:2]}.{code[2:]}", "description": row.description}
            for code, row in positions.iterrows()
        },
    }
    OUTPUT.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %d positions to %s", len(content["positions"]), OUTPUT)


if __name__ == "__main__":
    main()
