"""Model loading: once, at the pinned revision, with failures reported honestly."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ncm_classifier.api.config import APPROVED_MODEL_REPO, APPROVED_MODEL_REVISION, Settings
from ncm_classifier.api.main import create_app
from ncm_classifier.api.services.predictor_service import ModelState

SINGLE = {"description": "Ureia agrícola saco 50 kg"}


def test_model_loads_once_and_the_instance_is_reused(client, calls, predictor) -> None:
    for _ in range(3):
        assert client.post("/v1/predictions", json=SINGLE).status_code == 200
    client.app.state.predictor_service.load()  # a second call does nothing
    assert len(calls.downloads) == 1
    assert len(calls.loads) == 1
    assert len(predictor.calls) == 3


def test_the_approved_release_is_used_by_default(client, calls) -> None:
    downloaded = calls.downloads[0]
    assert downloaded.model_repo_id == APPROVED_MODEL_REPO == "AmandaGondra/ncm-classifier"
    assert downloaded.model_revision == APPROVED_MODEL_REVISION == "v0.1.0"


@pytest.mark.parametrize("revision", ["main", "latest", "v0.1", "refs/heads/main"])
def test_mutable_revisions_are_refused(revision: str) -> None:
    with pytest.raises(ValidationError, match="MODEL_REVISION"):
        Settings(_env_file=None, model_revision=revision)


def test_a_commit_hash_is_accepted() -> None:
    assert Settings(_env_file=None, model_revision="f" * 40).model_revision == "f" * 40


def test_load_failure_makes_the_api_unavailable(settings, make_service) -> None:
    service = make_service(settings, fail=True)
    with TestClient(create_app(settings, service)) as client:
        assert service.wait_until_loaded(5)
        health = client.get("/health")
        prediction = client.post("/v1/predictions", json=SINGLE)
    assert service.state is ModelState.UNAVAILABLE
    assert health.status_code == 503
    assert health.json() == {
        "status": "unavailable",
        "model": {"state": "unavailable", "version": None},
    }
    assert prediction.status_code == 503
    assert "secret" not in health.text + prediction.text


def test_health_reports_starting_while_the_model_loads(settings, make_service) -> None:
    release = threading.Event()
    service = make_service(settings, release=release)
    with TestClient(create_app(settings, service)) as client:
        starting = client.get("/health")
        early_prediction = client.post("/v1/predictions", json=SINGLE)
        release.set()
        assert service.wait_until_loaded(5)
        ready = client.get("/health")
    assert starting.status_code == 503
    assert starting.json()["status"] == "starting"
    assert early_prediction.status_code == 503
    assert early_prediction.headers["Retry-After"] == "30"
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "model": {"state": "ready", "version": "v0.1.0"}}


def test_classes_without_official_description_are_refused(
    settings, make_service, predictor
) -> None:
    predictor.classes = predictor.classes.copy()
    predictor.classes[0] = "9999"
    service = make_service(settings)
    service.load()
    assert service.state is ModelState.UNAVAILABLE
