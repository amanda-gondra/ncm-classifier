"""Guards the frozen test sets: any change to their bytes must be deliberate."""

import csv
import hashlib
from pathlib import Path

import pytest

from ncm_classifier.data.scope import load_scope

ROOT = Path(__file__).resolve().parents[1]
LABELED = ROOT / "data" / "labeled"
EXPECTED_COLUMNS = [
    "id",
    "text",
    "position",
    "source_type",
    "source_url",
    "label_rule",
    "reviewed",
]
# test_v1 covers every scope position; test_v2 was collected later from new sources
# and covers only part of the scope.
VERSIONS = {"test_v1": True, "test_v2": False}


def _read_rows(name: str) -> list[dict[str, str]]:
    with (LABELED / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_COLUMNS
        return list(reader)


@pytest.mark.parametrize("name", sorted(VERSIONS))
def test_checksum_matches_frozen_version(name: str) -> None:
    content = (LABELED / f"{name}.csv").read_bytes().replace(b"\r\n", b"\n")
    expected = (LABELED / f"{name}.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(content).hexdigest() == expected


@pytest.mark.parametrize("name", sorted(VERSIONS))
def test_rows_are_unique_reviewed_and_in_scope(name: str) -> None:
    rows = _read_rows(name)
    scope = set(load_scope(ROOT / "configs" / "scope.json").positions)
    positions = {row["position"] for row in rows}

    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert all(row["reviewed"] == "true" for row in rows)
    assert positions <= scope
    if VERSIONS[name]:
        assert positions == scope
    assert all(row["source_url"].startswith("https://") for row in rows)


def test_test_sets_share_no_sources() -> None:
    first, second = (_read_rows(name) for name in sorted(VERSIONS))
    assert not {row["source_url"] for row in first} & {row["source_url"] for row in second}
