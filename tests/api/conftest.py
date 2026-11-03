"""Fixtures of the API tests: a fake model, so no test downloads anything."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app
from ncm_classifier.api.services.predictor_service import ModelBundle, PredictorService
from ncm_classifier.inference.predictor import Prediction, Suggestion

CLASSES = ["3102", "3105", "7313"]
REVIEW_MARKER = "revisar"
FAILURE_MARKER = "explodir"
SMALL_PACKAGE_MARKER = "1 kg"


class FakePredictor:
    """Answers like NcmPredictor; markers in the text choose the outcome."""

    def __init__(self) -> None:
        self.classes = np.asarray(CLASSES)
        self.calls: list[list[str]] = []

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        self.calls.append(list(texts))
        results = []
        for text in texts:
            if FAILURE_MARKER in text:
                raise RuntimeError("fake predictor failure")
            small = SMALL_PACKAGE_MARKER in text
            order = ["3105", "3102", "7313"] if small else ["3102", "3105", "7313"]
            confidence = 0.4 if REVIEW_MARKER in text else 0.9
            probabilities = [confidence, (1 - confidence) * 0.75, (1 - confidence) * 0.25]
            results.append(
                Prediction(
                    suggestions=[
                        Suggestion(c, p) for c, p in zip(order, probabilities, strict=True)
                    ],
                    confidence=confidence,
                    needs_review=confidence < 0.6,
                    rule_31_05=small,
                )
            )
        return results


def interval(value: float) -> dict[str, float]:
    return {"value": value, "low": value - 0.05, "high": min(value + 0.05, 1.0)}


def fake_metadata() -> dict[str, dict[str, Any]]:
    test = {
        "file": "test_v1.csv",
        "metrics_calibrated_with_rules": {
            "rows": 146,
            "top1": interval(0.9),
            "top3": interval(0.95),
            "macro_f1": interval(0.88),
            "ece": 0.07,
        },
        "review": {"review_rate": interval(0.1), "accepted_top1": interval(0.97)},
    }
    return {
        "metrics": {"model": "fake_model", "tests": [test]},
        "manifest": {
            "version": "v0.1.0",
            "date": "2026-11-03",
            "code_commit": "a" * 40,
            "github": "https://github.com/amanda-gondra/ncm-classifier",
        },
        "calibration": {
            "method": "temperature scaling: softmax(log(p) / T)",
            "temperature": 0.4,
            "review_threshold": 0.6,
            "review_target_accuracy": 0.95,
            "fitted_on": "out-of-fold predictions of the training set",
        },
        "preprocessing": {"rule_31_05": {"limit_kg": 10.0, "target": "3105"}},
    }


class Calls:
    def __init__(self) -> None:
        self.downloads: list[Settings] = []
        self.loads: list[Path] = []


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, allowed_origins=["https://app.example"])


@pytest.fixture
def calls() -> Calls:
    return Calls()


@pytest.fixture
def predictor() -> FakePredictor:
    return FakePredictor()


@pytest.fixture
def make_service(calls: Calls, predictor: FakePredictor) -> Callable[..., PredictorService]:
    def build(
        settings: Settings,
        fail: bool = False,
        release: threading.Event | None = None,
    ) -> PredictorService:
        def downloader(current: Settings) -> Path:
            calls.downloads.append(current)
            if release is not None:
                release.wait(5)
            if fail:
                raise OSError("network down at C:/secret/path")
            return Path("fake-model-dir")

        def loader(directory: Path) -> ModelBundle:
            calls.loads.append(directory)
            return ModelBundle(predictor=predictor, **fake_metadata())

        return PredictorService(settings, downloader=downloader, loader=loader)

    return build


@pytest.fixture
def client(
    settings: Settings, make_service: Callable[..., PredictorService]
) -> Iterator[TestClient]:
    service = make_service(settings)
    # Answer like a real server: an unhandled error becomes the standard 500 response.
    with TestClient(create_app(settings, service), raise_server_exceptions=False) as test_client:
        assert service.wait_until_loaded(5)
        yield test_client
