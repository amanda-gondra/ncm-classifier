"""CORS, body limits, logs without texts or credentials."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app

URL = "/v1/predictions"


def _preflight(client: TestClient, origin: str):
    return client.options(
        URL,
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_cors_allows_a_configured_origin(client) -> None:
    response = _preflight(client, "https://app.example")
    assert response.headers.get("access-control-allow-origin") == "https://app.example"


def test_cors_ignores_other_origins(client) -> None:
    response = _preflight(client, "https://evil.example")
    assert "access-control-allow-origin" not in response.headers
    simple = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_cors_is_closed_by_default(make_service) -> None:
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == []
    with TestClient(create_app(settings, make_service(settings))) as client:
        response = _preflight(client, "https://app.example")
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_origin_is_refused() -> None:
    with pytest.raises(ValidationError, match="explicitly"):
        Settings(_env_file=None, allowed_origins="*")


def test_origins_are_read_as_a_comma_separated_list() -> None:
    settings = Settings(_env_file=None, allowed_origins="https://a.example, https://b.example")
    assert settings.allowed_origins == ["https://a.example", "https://b.example"]


def test_declared_body_above_the_limit_is_a_413(client, predictor) -> None:
    body = b'{"description": "' + b"x" * 70_000 + b'"}'
    response = client.post(URL, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert predictor.calls == []


def test_streamed_body_above_the_limit_is_a_413(client, predictor) -> None:
    def chunks():
        yield b'{"description": "'
        for _ in range(20):
            yield b"x" * 4_096
        yield b'"}'

    response = client.post(URL, content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert predictor.calls == []


def test_logs_have_no_description_text(client, caplog) -> None:
    marker = "Adubo-Marcador-Unico-XYZ"
    with caplog.at_level(logging.DEBUG):
        client.post(URL, json={"descriptions": [marker, f"{marker} 1 kg"]})
        client.post(URL, json={"description": f"{marker} explodir"})
        client.post(URL, json={"description": marker * 100})
    assert marker not in caplog.text
    assert "count=2" in caplog.text


def test_logs_and_responses_have_no_token(make_service, caplog) -> None:
    token = "hf_ThisIsNotARealTokenButMustNeverAppear"  # noqa: S105 - fake value for the test
    settings = Settings(_env_file=None, hf_token=token)
    service = make_service(settings, fail=True)
    with caplog.at_level(logging.DEBUG), TestClient(create_app(settings, service)) as client:
        service.wait_until_loaded(5)
        texts = client.get("/health").text + client.post(URL, json={"description": "a"}).text
    assert token not in caplog.text
    assert token not in texts
    assert token not in repr(settings)


def test_every_response_carries_a_request_id(client) -> None:
    ids = {client.get("/health").headers["X-Request-ID"] for _ in range(3)}
    assert len(ids) == 3
