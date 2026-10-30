"""Near-duplicate detection between text collections.

Used to keep the training set from leaking into the frozen test set: a training
row that is almost the same text as a test row (same ad copied to another site,
a different price, a typo fixed) would inflate the metrics.

Similarity is the Jaccard index of character 5-grams over normalized text. It
catches copies with small edits and is cheap enough for a few thousand rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from ncm_classifier.text import normalize_text

DEFAULT_SHINGLE_SIZE: Final = 5
DEFAULT_THRESHOLD: Final = 0.8


def shingles(text: str, size: int = DEFAULT_SHINGLE_SIZE) -> frozenset[str]:
    """Return the set of character n-grams of the normalized text."""
    if size < 1:
        raise ValueError("size must be at least 1")
    normalized = normalize_text(text)
    if len(normalized) <= size:
        return frozenset({normalized}) if normalized else frozenset()
    return frozenset(normalized[i : i + size] for i in range(len(normalized) - size + 1))


def jaccard(first: frozenset[str], second: frozenset[str]) -> float:
    """Jaccard index of two sets; two empty sets are not considered similar."""
    union = len(first | second)
    return len(first & second) / union if union else 0.0


def near_duplicate_mask(
    candidates: Sequence[str],
    references: Sequence[str],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[bool]:
    """Flag each candidate whose similarity to any reference reaches the threshold."""
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    reference_sets = [shingles(text) for text in references]
    flags = []
    for text in candidates:
        candidate = shingles(text)
        flags.append(any(jaccard(candidate, ref) >= threshold for ref in reference_sets))
    return flags
