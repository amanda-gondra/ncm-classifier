"""GET /v1/model and the automatic documentation."""

from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from ncm_classifier.api.main import create_app

from .conftest import CLASSES


def test_model_info_comes_from_the_published_metadata(client) -> None:
    body = client.get("/v1/model").json()
    assert body["name"] == "ncm-classifier"
    assert body["repo_id"] == "AmandaGondra/ncm-classifier"
    assert body["revision"] == body["version"] == "v0.1.0"
    assert body["architecture"] == "fake_model"
    assert [p["ncm"] for p in body["scope"]["positions"]] == CLASSES
    assert body["scope"]["level"] == "position"
    [metrics] = body["metrics"]
    assert metrics["test_set"] == "test_v1"
    assert metrics["top1"]["value"] == 0.9
    assert body["calibration"]["temperature"] == 0.4
    assert body["rule_3105"]["limit_kg"] == 10.0
    assert body["release"]["code_commit"] == "a" * 40
    assert "responsabilidade" in body["disclaimer"]


def test_model_info_waits_for_the_model(settings, make_service) -> None:
    release = threading.Event()
    service = make_service(settings, release=release)
    with TestClient(create_app(settings, service)) as client:
        response = client.get("/v1/model")
        release.set()
        service.wait_until_loaded(5)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"


def test_documentation_is_served(client) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    schema = client.get("/openapi.json").json()
    assert {"/v1/predictions", "/v1/model", "/health"} <= set(schema["paths"])
    request = schema["components"]["schemas"]["PredictionRequest"]
    batch = next(
        v for v in request["properties"]["descriptions"]["anyOf"] if v.get("type") == "array"
    )
    assert batch["maxItems"] == 20
    assert batch["items"]["maxLength"] == 500
    responses = schema["paths"]["/v1/predictions"]["post"]["responses"]
    assert {"200", "400", "413", "422", "500", "503"} <= set(responses)
    assert "Aviso fiscal" in schema["info"]["description"]
