from pathlib import Path

import numpy as np

from ncm_classifier.evaluation.protocol import (
    FOLDS,
    fold_ids,
    folds_fingerprint,
    make_folds,
    sha256_bytes,
    sha256_text,
)

LABELS = [f"{i % 4:04d}" for i in range(40)]
IDS = [f"r{i:03d}" for i in range(40)]


def test_every_row_is_validated_exactly_once() -> None:
    ids = fold_ids(LABELS)
    assert ids.min() == 0
    assert ids.max() == FOLDS - 1
    assert np.bincount(ids).tolist() == [8] * FOLDS


def test_fold_ids_match_the_splits_used_for_training() -> None:
    ids = fold_ids(LABELS)
    splits = make_folds().split(np.zeros(len(LABELS)), LABELS)
    for fold, (_, validation) in enumerate(splits):
        assert (ids[validation] == fold).all()


def test_fingerprint_is_stable_and_detects_changes() -> None:
    reference = folds_fingerprint(IDS, LABELS)
    assert folds_fingerprint(IDS, LABELS) == reference
    assert folds_fingerprint(IDS, LABELS, seed=1) != reference
    assert folds_fingerprint(IDS[::-1], LABELS) != reference


def test_text_hash_ignores_line_endings(tmp_path: Path) -> None:
    unix, windows = tmp_path / "unix.csv", tmp_path / "windows.csv"
    unix.write_bytes(b"id,text\n1,ureia\n")
    windows.write_bytes(b"id,text\r\n1,ureia\r\n")
    assert sha256_text(unix) == sha256_text(windows)
    assert sha256_bytes(unix) != sha256_bytes(windows)
