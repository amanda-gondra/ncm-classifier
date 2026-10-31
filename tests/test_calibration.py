import numpy as np
import pytest

from ncm_classifier.models.calibration import apply_temperature, fit_temperature

CLASSES = ["a", "b", "c"]


def test_temperature_keeps_ranking_and_normalization() -> None:
    proba = np.array([[0.5, 0.3, 0.2], [0.1, 0.6, 0.3]])
    sharp = apply_temperature(proba, 0.5)
    assert np.allclose(sharp.sum(axis=1), 1.0)
    assert (sharp.argmax(axis=1) == proba.argmax(axis=1)).all()
    assert sharp.max() > proba.max()


def test_identity_at_temperature_one() -> None:
    proba = np.array([[0.7, 0.2, 0.1]])
    assert np.allclose(apply_temperature(proba, 1.0), proba)


def test_underconfident_model_gets_sharpened() -> None:
    # Always right, but only 40% confident: the fitted temperature must be below 1.
    proba = np.tile([0.4, 0.3, 0.3], (30, 1))
    assert fit_temperature(proba, ["a"] * 30, CLASSES) < 1.0


def test_overconfident_model_gets_flattened() -> None:
    # 90% confident in "a", but right only half of the time.
    proba = np.tile([0.9, 0.05, 0.05], (20, 1))
    labels = ["a", "b"] * 10
    assert fit_temperature(proba, labels, CLASSES) > 1.0


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        apply_temperature(np.array([[1.0]]), 0.0)
    with pytest.raises(ValueError, match="not one of the classes"):
        fit_temperature(np.array([[1.0, 0.0, 0.0]]), ["z"], CLASSES)
