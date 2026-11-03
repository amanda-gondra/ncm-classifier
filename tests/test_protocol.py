from pathlib import Path

import numpy as np
import pytest

from ncm_classifier.evaluation.protocol import (
    FOLDS,
    fold_ids,
    folds_fingerprint,
    load_frozen_test,
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


def _frozen_file(directory: Path, content: bytes) -> Path:
    path = directory / "test_x.csv"
    path.write_bytes(content)
    path.with_suffix(".sha256").write_text(f"{sha256_text(path)}  test_x.csv\n", encoding="utf-8")
    return path


def test_frozen_test_is_loaded_when_unchanged_and_reviewed(tmp_path: Path) -> None:
    path = _frozen_file(tmp_path, b"id,text,position,reviewed\nt1,ureia,3102,true\n")
    assert load_frozen_test(path)["id"].tolist() == ["t1"]


def test_changed_frozen_test_is_refused(tmp_path: Path) -> None:
    path = _frozen_file(tmp_path, b"id,text,position,reviewed\nt1,ureia,3102,true\n")
    path.write_bytes(b"id,text,position,reviewed\nt1,ureia,3105,true\n")
    with pytest.raises(ValueError, match="frozen checksum"):
        load_frozen_test(path)


def test_unreviewed_rows_are_refused(tmp_path: Path) -> None:
    path = _frozen_file(tmp_path, b"id,text,position,reviewed\nt1,ureia,3102,false\n")
    with pytest.raises(ValueError, match="not reviewed"):
        load_frozen_test(path)


def test_text_hash_ignores_line_endings(tmp_path: Path) -> None:
    unix, windows = tmp_path / "unix.csv", tmp_path / "windows.csv"
    unix.write_bytes(b"id,text\n1,ureia\n")
    windows.write_bytes(b"id,text\r\n1,ureia\r\n")
    assert sha256_text(unix) == sha256_text(windows)
    assert sha256_bytes(unix) != sha256_bytes(windows)
