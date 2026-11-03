"""429 above the configured requests per minute, per client, on /v1/ routes only."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from ncm_classifier.api.config import Settings
from ncm_classifier.api.main import create_app
from ncm_classifier.api.middleware.rate_limit import RateLimitMiddleware

URL = "/v1/predictions"
BODY = {"description": "Ureia agrícola saco 50 kg"}


def _client(make_service, limit: int, address: str = "203.0.113.10") -> TestClient:
    settings = Settings(_env_file=None, rate_limit_per_minute=limit)
    service = make_service(settings)
    client = TestClient(create_app(settings, service), client=(address, 50_000))
    client.__enter__()
    service.wait_until_loaded(5)
    return client


def test_requests_above_the_limit_get_a_standard_429(make_service, predictor) -> None:
    client = _client(make_service, limit=3)
    statuses = [client.post(URL, json=BODY).status_code for _ in range(4)]
    refused = client.post(URL, json=BODY)
    client.__exit__(None, None, None)
    assert statuses == [200, 200, 200, 429]
    assert refused.json()["error"]["code"] == "rate_limited"
    assert refused.json()["error"]["request_id"] == refused.headers["X-Request-ID"]
    assert 1 <= int(refused.headers["Retry-After"]) <= 60
    assert len(predictor.calls) == 3


def test_health_and_docs_are_never_limited(make_service) -> None:
    client = _client(make_service, limit=1)
    statuses = {client.get("/health").status_code for _ in range(5)}
    statuses |= {client.get("/openapi.json").status_code for _ in range(5)}
    client.__exit__(None, None, None)
    assert statuses == {200}


def test_zero_turns_the_limit_off(make_service) -> None:
    client = _client(make_service, limit=0)
    statuses = {client.post(URL, json=BODY).status_code for _ in range(30)}
    client.__exit__(None, None, None)
    assert statuses == {200}


async def _ok(scope, receive, send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _scope(address: str) -> dict:
    return {"type": "http", "method": "POST", "path": URL, "client": (address, 1), "headers": []}


class _Clock:
    def __init__(self) -> None:
        self.now = 120.0

    def __call__(self) -> float:
        return self.now


def _status(middleware: RateLimitMiddleware, address: str) -> int:
    sent: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(middleware(_scope(address), receive, send))
    return sent[0]["status"]


def test_clients_are_counted_separately_and_windows_reset() -> None:
    clock = _Clock()
    middleware = RateLimitMiddleware(_ok, requests_per_minute=1, clock=clock)
    assert _status(middleware, "198.51.100.1") == 200
    assert _status(middleware, "198.51.100.1") == 429
    assert _status(middleware, "198.51.100.2") == 200
    clock.now += 60
    assert _status(middleware, "198.51.100.1") == 200


def test_tracked_clients_are_bounded() -> None:
    middleware = RateLimitMiddleware(_ok, requests_per_minute=5, clock=_Clock(), max_clients=2)
    assert _status(middleware, "a") == 200
    assert _status(middleware, "b") == 200
    assert _status(middleware, "c") == 429
    assert _status(middleware, "a") == 200
