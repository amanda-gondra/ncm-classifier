"""POST /v1/predictions: contract, validation and errors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ncm_classifier.api.config import Settings
from ncm_classifier.api.errors import _detail_message
from ncm_classifier.api.main import create_app
from ncm_classifier.data.positions import load_positions

from .conftest import FAILURE_MARKER, REVIEW_MARKER, SMALL_PACKAGE_MARKER

URL = "/v1/predictions"


def test_single_description(client) -> None:
    response = client.post(URL, json={"description": "Ureia agrícola saco 50 kg"})
    body = response.json()
    assert response.status_code == 200
    assert body["model_version"] == "v0.1.0"
    assert body["request_id"] == response.headers["X-Request-ID"]
    [result] = body["results"]
    assert result["index"] == 0
    assert [s["rank"] for s in result["predictions"]] == [1, 2, 3]
    first = result["predictions"][0]
    assert first["ncm"] == "3102"
    assert first["level"] == "position"
    assert first["formatted"] == "31.02"
    assert first["official_description"] == load_positions().describe("3102").description
    assert first["confidence"] == pytest.approx(0.9)
    assert result["requires_manual_review"] is False
    assert result["rule_3105_applied"] is False
    assert result["applied_rule"] is None


def test_batch_keeps_order_and_flags(client) -> None:
    texts = ["Ureia saco 50 kg", f"Ureia {SMALL_PACKAGE_MARKER}", f"item para {REVIEW_MARKER}"]
    results = client.post(URL, json={"descriptions": texts}).json()["results"]
    assert [r["index"] for r in results] == [0, 1, 2]
    assert results[1]["rule_3105_applied"] is True
    assert results[1]["applied_rule"] == "ncm-3105-small-package"
    assert results[1]["predictions"][0]["ncm"] == "3105"
    assert results[2]["requires_manual_review"] is True
    assert all(len(r["predictions"]) <= 3 for r in results)


def test_texts_reach_the_predictor_unchanged(client, predictor) -> None:
    text = "  ADUBO NPK 20 05 20  SC 50KG "
    client.post(URL, json={"description": text})
    assert predictor.calls[-1] == [text]


@pytest.mark.parametrize(
    "payload",
    [
        {"description": ""},
        {"description": "   "},
        {"description": "x" * 501},
        {"descriptions": []},
        {"descriptions": ["ok", "  "]},
        {"descriptions": ["ureia"] * 21},
        {"description": "a", "descriptions": ["b"]},
        {},
        {"text": "ureia"},
        {"description": 42},
        {"descriptions": "ureia"},
    ],
)
def test_invalid_requests_are_refused_before_the_model(client, predictor, payload) -> None:
    response = client.post(URL, json=payload)
    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "validation_error"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert error["details"]
    assert predictor.calls == []


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"description": "x" * 501}, "description", "Texto com mais de 500 caracteres."),
        ({"descriptions": ["ureia"] * 21}, "descriptions", "Envie no máximo 20 descrições."),
        (
            {"descriptions": ["ok", "  ", " "]},
            "descriptions",
            "Descrições vazias ou só com espaços nas posições 2, 3.",
        ),
        (
            {"description": "a", "descriptions": ["b"]},
            None,
            "Envie exatamente um dos campos: 'description' ou 'descriptions'.",
        ),
        ({"text": "ureia"}, "text", "Campo não aceito."),
        ({"description": 42}, "description", "Deve ser um texto."),
    ],
)
def test_validation_messages_are_in_portuguese(client, payload, field, message) -> None:
    # The web interface shows these messages to people as they come.
    error = client.post(URL, json=payload).json()["error"]
    assert error["message"] == "A requisição não segue o formato ou os limites esperados."
    assert {"field": field, "message": message} in error["details"]


def test_unexpected_validation_errors_get_a_generic_message() -> None:
    assert _detail_message({"type": "bool_parsing", "msg": "Input should be a valid boolean"}) == (
        "Valor inválido."
    )
    # A known type whose context lacks the number keeps the message generic, never half-filled.
    assert _detail_message({"type": "string_too_long", "ctx": {}}) == "Valor inválido."


def test_limits_come_from_the_settings(make_service) -> None:
    settings = Settings(_env_file=None, max_text_length=10, max_batch_size=2)
    service = make_service(settings)
    with TestClient(create_app(settings, service)) as client:
        assert service.wait_until_loaded(5)
        assert client.post(URL, json={"description": "x" * 10}).status_code == 200
        assert client.post(URL, json={"description": "x" * 11}).status_code == 422
        assert client.post(URL, json={"descriptions": ["a", "b", "c"]}).status_code == 422


def test_invalid_json_is_a_400(client) -> None:
    response = client.post(URL, content=b"{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_json"


def test_predictor_failure_is_a_standard_500(client) -> None:
    response = client.post(URL, json={"description": f"vai {FAILURE_MARKER}"})
    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "Erro interno.",
        "request_id": response.json()["error"]["request_id"],
        "details": [],
    }
    assert "fake predictor failure" not in response.text


def test_unknown_route_uses_the_error_format(client) -> None:
    response = client.get("/v1/unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["message"] == "Rota não encontrada."


def test_wrong_method_uses_the_error_format(client) -> None:
    response = client.get(URL)
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert response.json()["error"]["message"] == "Método não permitido nesta rota."
