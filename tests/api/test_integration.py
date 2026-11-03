"""FastAPI + the real NcmPredictor + calibration + 31.05 rule, without network.

A tiny pipeline is trained here and saved exactly like the published model
(skops + calibration + metadata), then served through the real load_bundle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import skops.io as sio
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app
from ncm_classifier.api.services.predictor_service import PredictorService
from ncm_classifier.inference.predictor import NcmPredictor
from ncm_classifier.text import normalize_text

from .conftest import fake_metadata

TEXTS = ["ureia saco 50 kg", "ureia granulada", "arame farpado", "grampo cerca", "kcl potassio"]
LABELS = ["3102", "3102", "7313", "7317", "3105"]


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(preprocessor=normalize_text)),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    ).fit(TEXTS, LABELS)
    sio.dump(pipeline, tmp_path / "model.skops")
    metadata = fake_metadata()
    metadata["calibration"]["temperature"] = 0.5
    files = {
        "calibration/calibration.json": metadata["calibration"],
        "metrics/evaluation.json": metadata["metrics"],
        "manifest.json": metadata["manifest"],
        "preprocessing/configuration.json": metadata["preprocessing"],
    }
    for name, content in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
    return tmp_path


def test_api_returns_exactly_what_the_predictor_computes(model_dir: Path) -> None:
    settings = Settings(_env_file=None)
    service = PredictorService(settings, downloader=lambda _: model_dir)
    texts = ["ureia saco 1 kg", "arame farpado rolo", "grampo"]
    expected = NcmPredictor.from_directory(model_dir).predict(texts)

    with TestClient(create_app(settings, service)) as client:
        assert service.wait_until_loaded(10)
        results = client.post("/v1/predictions", json={"descriptions": texts}).json()["results"]

    for result, prediction in zip(results, expected, strict=True):
        assert [s["ncm"] for s in result["predictions"]] == [
            s.position for s in prediction.suggestions
        ]
        assert [s["confidence"] for s in result["predictions"]] == [
            s.probability for s in prediction.suggestions
        ]
        assert result["requires_manual_review"] == prediction.needs_review
        assert result["rule_3105_applied"] == prediction.rule_31_05
    # Small package of a Chapter 31 product: the rule moved it to 31.05.
    assert results[0]["predictions"][0]["ncm"] == "3105"
    assert results[0]["rule_3105_applied"] is True
