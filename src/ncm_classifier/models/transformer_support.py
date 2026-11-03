"""Helpers of the transformer model that do not need PyTorch, so CI can test them.

Input text. The baseline feeds `normalize_text` to TF-IDF, which lowercases and
removes accents. BERTimbau "cased" was pre-trained on text with case and
accents, so that normalization may remove information the model already knows
how to use. Two input modes are therefore compared by cross-validation on the
training set, and the better one is kept:

    raw         Unicode NFKC form and collapsed whitespace only;
    normalized  the same `normalize_text` used by the baseline.

The 31.05 rule always reads the original text, whatever the input mode.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Hashable, Mapping, Sequence
from typing import Final, TypeVar

import numpy as np
from numpy.typing import NDArray
from sklearn.utils.class_weight import compute_class_weight

from ncm_classifier.text import normalize_text

INPUT_MODES: Final = ("raw", "normalized")
_WHITESPACE: Final = re.compile(r"\s+")

Key = TypeVar("Key", bound=Hashable)


def prepare_input(texts: Sequence[str], mode: str) -> list[str]:
    if mode == "raw":
        return [_WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text)).strip() for text in texts]
    if mode == "normalized":
        return [normalize_text(text) for text in texts]
    raise ValueError(f"unknown input mode {mode!r}; expected one of {INPUT_MODES}")


def balanced_class_weights(labels: Sequence[str], classes: Sequence[str]) -> NDArray[np.float64]:
    """Inverse-frequency weights, the same `class_weight="balanced"` of the baseline."""
    names = np.asarray(classes, dtype=str)
    targets = np.asarray(labels, dtype=str)
    missing = sorted(set(names) - set(targets))
    if missing:
        raise ValueError(f"classes without training rows: {missing}")
    return compute_class_weight("balanced", classes=names, y=targets)


def select_best(scores: Mapping[Key, Sequence[float]]) -> Key:
    """Key with the highest mean score; ties go to the first key in iteration order."""
    if not scores:
        raise ValueError("scores is empty")
    best_key, best_mean = None, -np.inf
    for key, values in scores.items():
        mean = float(np.mean(values))
        if mean > best_mean:
            best_key, best_mean = key, mean
    return best_key
