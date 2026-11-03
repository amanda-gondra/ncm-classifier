"""Inference with the published baseline: the same steps as the evaluation.

    raw probabilities -> temperature -> 31.05 rule -> top 3 + manual review flag

A model directory holds:
    model.skops                    the TF-IDF + logistic regression pipeline
    calibration/calibration.json   temperature and manual review threshold

The pipeline is stored with skops instead of pickle: loading a pickle can run
arbitrary code, while skops only loads types it is told to trust. The only
type outside scikit-learn and NumPy is the project's own text normalization,
listed in TRUSTED_TYPES; any other unexpected type makes loading fail.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import numpy as np
import skops.io as sio
from numpy.typing import NDArray
from sklearn.pipeline import Pipeline

from ncm_classifier.models.calibration import apply_temperature
from ncm_classifier.rules.small_package import apply_small_package_rule

MODEL_FILE: Final = "model.skops"
CALIBRATION_FILE: Final = "calibration/calibration.json"
TRUSTED_TYPES: Final = ("ncm_classifier.text.normalize.normalize_text",)
TOP_K: Final = 3


@dataclass(frozen=True)
class Suggestion:
    position: str
    probability: float


@dataclass(frozen=True)
class Prediction:
    suggestions: list[Suggestion]
    confidence: float
    needs_review: bool
    rule_31_05: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_pipeline(path: Path) -> Pipeline:
    """Load a skops pipeline, refusing every type not trusted by default or listed here."""
    unexpected = sorted(set(sio.get_untrusted_types(file=path)) - set(TRUSTED_TYPES))
    if unexpected:
        raise ValueError(f"{path.name} contains untrusted types: {unexpected}")
    return sio.load(path, trusted=list(TRUSTED_TYPES))


class NcmPredictor:
    def __init__(self, pipeline: Pipeline, temperature: float, review_threshold: float) -> None:
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self._pipeline = pipeline
        self._temperature = temperature
        self._review_threshold = review_threshold
        self.classes: NDArray[np.str_] = np.asarray(pipeline.classes_, dtype=str)

    @classmethod
    def from_directory(cls, directory: str | Path) -> NcmPredictor:
        root = Path(directory)
        calibration = json.loads((root / CALIBRATION_FILE).read_text(encoding="utf-8"))
        return cls(
            load_pipeline(root / MODEL_FILE),
            float(calibration["temperature"]),
            float(calibration["review_threshold"]),
        )

    def predict_proba(self, texts: Sequence[str]) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
        """Final probabilities (calibrated, after the 31.05 rule) and the rule mask."""
        raw = self._pipeline.predict_proba(list(texts))
        calibrated = apply_temperature(raw, self._temperature)
        return apply_small_package_rule(list(texts), calibrated, self.classes)

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        if isinstance(texts, str):
            raise TypeError("texts must be a sequence of strings, not a single string")
        final, rule_applied = self.predict_proba(texts)
        order = np.argsort(-final, axis=1, kind="stable")[:, :TOP_K]
        predictions = []
        for row, columns in enumerate(order):
            suggestions = [
                Suggestion(str(self.classes[c]), round(float(final[row, c]), 6)) for c in columns
            ]
            confidence = float(final[row, columns[0]])
            predictions.append(
                Prediction(
                    suggestions=suggestions,
                    confidence=round(confidence, 6),
                    needs_review=confidence < self._review_threshold,
                    rule_31_05=bool(rule_applied[row]),
                )
            )
        return predictions
