"""Rule of position 31.05: Chapter 31 goods in packages of 10 kg or less.

The heading text of 31.05 includes "mercadorias do presente Capítulo apresentadas
em tabletes ou formas semelhantes, ou ainda em embalagens com peso bruto não
superior a 10 kg". So urea in a 5 kg bag is 31.05, not 31.02, and the same holds
for every fertilizer of Chapter 31.

A text classifier cannot do this comparison reliably (it sees "1 kg" as a token,
not as a number below 10), so the rule is applied after the model:

* the text must state at least one weight, and every stated weight must be
  10 kg or less ("saco 25 kg e big bag 1000 kg" is not a small package);
* the model's first suggestion must be a Chapter 31 position;
* then all the probability the model gave to Chapter 31 moves to 31.05, because
  under this rule any Chapter 31 position becomes 31.05. Other chapters keep
  their probabilities, so the output still sums to one.

Only weights count. A volume ("1 L") is not a gross weight and does not trigger
the rule, which keeps it conservative.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray

from ncm_classifier.text import normalize_text

TARGET: Final = "3105"
CHAPTER: Final = "31"
LIMIT_KG: Final = 10.0
_KG_PER_UNIT: Final = {"kg": 1.0, "g": 0.001}
# normalize_text writes every weight as "<number> kg" or "<number> g".
_WEIGHT: Final = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?) (kg|g)\b")


def package_weights_kg(text: str) -> list[float]:
    """Return every weight stated in the text, in kilograms."""
    return [
        float(value) * _KG_PER_UNIT[unit] for value, unit in _WEIGHT.findall(normalize_text(text))
    ]


def is_small_package(text: str) -> bool:
    weights = package_weights_kg(text)
    return bool(weights) and max(weights) <= LIMIT_KG


def apply_small_package_rule(
    texts: Sequence[str],
    proba: NDArray[np.float64],
    classes: Sequence[str] | NDArray[np.str_],
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Return the adjusted probabilities and a mask of the rows the rule changed."""
    labels = np.asarray(classes, dtype=str)
    if TARGET not in labels:
        raise ValueError(f"{TARGET} must be one of the classes")
    if proba.shape != (len(texts), len(labels)):
        raise ValueError("proba must have one row per text and one column per class")

    in_chapter = np.char.startswith(labels, CHAPTER)
    target = int(np.flatnonzero(labels == TARGET)[0])
    adjusted = proba.copy()
    applied = np.zeros(len(texts), dtype=bool)

    for row, text in enumerate(texts):
        top = int(np.argmax(proba[row]))
        if not in_chapter[top] or labels[top] == TARGET or not is_small_package(text):
            continue
        mass = adjusted[row, in_chapter].sum()
        adjusted[row, in_chapter] = 0.0
        adjusted[row, target] = mass
        applied[row] = True
    return adjusted, applied
