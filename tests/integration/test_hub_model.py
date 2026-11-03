"""Real model from the Hugging Face Hub, served by the API (opt-in).

Run with:  NCM_RUN_HUB_TESTS=1 pytest -m hub

Downloads AmandaGondra/ncm-classifier at v0.1.0 (about 26 MB, public, no token)
and checks that the API answers exactly as the recorded evaluation of test_v1.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app
from ncm_classifier.api.services.predictor_service import ModelState, PredictorService

pytestmark = [
    pytest.mark.hub,
    pytest.mark.skipif(
        os.environ.get("NCM_RUN_HUB_TESTS") != "1", reason="set NCM_RUN_HUB_TESTS=1 to run"
    ),
]


def test_published_model_through_the_api() -> None:
    settings = Settings(_env_file=None)
    service = PredictorService(settings)
    test = pd.read_csv("data/labeled/test_v1.csv", dtype=str, keep_default_na=False)
    recorded = pd.read_csv("reports/predictions/baseline_v1__test_v1.csv", dtype=str)

    with TestClient(create_app(settings, service)) as client:
        assert service.wait_until_loaded(300)
        assert service.state is ModelState.READY
        top1, rule = [], []
        texts = test["text"].tolist()
        for start in range(0, len(texts), settings.max_batch_size):
            batch = texts[start : start + settings.max_batch_size]
            response = client.post("/v1/predictions", json={"descriptions": batch})
            assert response.status_code == 200
            for result in response.json()["results"]:
                top1.append(result["predictions"][0]["ncm"])
                rule.append(str(result["rule_3105_applied"]))
        info = client.get("/v1/model").json()

    assert top1 == recorded["top1"].tolist()
    assert rule == recorded["rule_31_05"].tolist()
    assert info["version"] == "v0.1.0"
    assert info["metrics"][0]["top1"]["value"] == 0.9452
