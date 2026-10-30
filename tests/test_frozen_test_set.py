"""Guards the frozen test set: any change to its bytes must be deliberate."""

import csv
import hashlib
from pathlib import Path

from ncm_classifier.data.scope import load_scope

ROOT = Path(__file__).resolve().parents[1]
TEST_SET = ROOT / "data" / "labeled" / "test_v1.csv"
CHECKSUM = ROOT / "data" / "labeled" / "test_v1.sha256"
EXPECTED_COLUMNS = [
    "id",
    "text",
    "position",
    "source_type",
    "source_url",
    "label_rule",
    "reviewed",
]


def _read_rows() -> list[dict[str, str]]:
    with TEST_SET.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_COLUMNS
        return list(reader)


def test_checksum_matches_frozen_version() -> None:
    content = TEST_SET.read_bytes().replace(b"\r\n", b"\n")
    expected = CHECKSUM.read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(content).hexdigest() == expected


def test_rows_are_unique_reviewed_and_in_scope() -> None:
    rows = _read_rows()
    scope = load_scope(ROOT / "configs" / "scope.json")

    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert all(row["reviewed"] == "true" for row in rows)
    assert {row["position"] for row in rows} == set(scope.positions)
    assert all(row["source_url"].startswith("https://") for row in rows)
