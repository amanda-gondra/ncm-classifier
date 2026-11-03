"""Experimental protocol shared by every model of the project.

All models choose their hyperparameters and fit their calibration on the same
five stratified folds of the training set, so their out-of-fold predictions can
be compared row by row. The folds fingerprint lets a run on another machine
(Kaggle, for instance) prove that it used exactly the same folds.

Checksums:
    sha256_text   for CSV files; line endings are normalized to LF first, so a
                  Windows checkout (CRLF) and a Linux one give the same hash.
    sha256_bytes  for binary files such as Parquet, hashed as they are.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import StratifiedKFold

FOLDS: Final = 5
SEED: Final = 0


def make_folds(seed: int = SEED) -> StratifiedKFold:
    return StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=seed)


def fold_ids(labels: Sequence[str], seed: int = SEED) -> NDArray[np.int_]:
    """Return, for each training row, the fold in which it is used for validation."""
    targets = np.asarray(labels, dtype=str)
    ids = np.full(len(targets), -1, dtype=int)
    splits = make_folds(seed).split(np.zeros(len(targets)), targets)
    for fold, (_, validation) in enumerate(splits):
        ids[validation] = fold
    return ids


def folds_fingerprint(example_ids: Sequence[str], labels: Sequence[str], seed: int = SEED) -> str:
    """Hash the pair (example id, validation fold) of every training row."""
    folds = fold_ids(labels, seed)
    lines = "".join(
        f"{example_id}\t{fold}\n" for example_id, fold in zip(example_ids, folds, strict=True)
    )
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
