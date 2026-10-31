"""Temperature scaling: make the shown confidence match how often the model is right.

A class-weighted logistic regression over 37 classes spreads its probability
mass, so it is right more often than its confidence says. Temperature scaling
fixes this with a single number T fitted on out-of-fold predictions of the
training set (never on a test set):

    calibrated = softmax(log(p) / T)

T < 1 sharpens the distribution, T > 1 flattens it. Only one parameter is
fitted, so it cannot overfit small classes, and the ranking of classes (and so
top-1 and top-3 accuracy) does not change.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar

_EPSILON: Final = 1e-12
_BOUNDS: Final = (0.05, 10.0)


def apply_temperature(proba: NDArray[np.float64], temperature: float) -> NDArray[np.float64]:
    """Rescale probabilities with a temperature; each row still sums to one."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    logits = np.log(np.clip(proba, _EPSILON, 1.0)) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    scaled = np.exp(logits)
    return scaled / scaled.sum(axis=1, keepdims=True)


def fit_temperature(
    proba: NDArray[np.float64], y_true: Sequence[str], classes: Sequence[str]
) -> float:
    """Find the temperature that minimizes the negative log-likelihood of the labels."""
    index = {label: i for i, label in enumerate(classes)}
    try:
        columns = np.array([index[label] for label in y_true])
    except KeyError as exc:
        raise ValueError(f"label {exc.args[0]!r} is not one of the classes") from exc
    rows = np.arange(len(columns))

    def negative_log_likelihood(temperature: float) -> float:
        scaled = apply_temperature(proba, temperature)
        return float(-np.log(np.clip(scaled[rows, columns], _EPSILON, 1.0)).mean())

    result = minimize_scalar(negative_log_likelihood, bounds=_BOUNDS, method="bounded")
    return float(result.x)
