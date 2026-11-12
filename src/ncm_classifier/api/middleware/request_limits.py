"""Reject request bodies above MAX_REQUEST_BODY_BYTES with 413.

Two checks, because a client can omit or misstate Content-Length:
    * a declared Content-Length above the limit is refused before reading;
    * the bytes actually received are counted, and reading stops as soon as
      they pass the limit.

Bodies within the limit are buffered (at most the limit, 64 KB by default) and
handed to the application unchanged.
"""

from __future__ import annotations

from typing import Final

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ncm_classifier.api.errors import error_response

_METHODS_WITH_BODY: Final = frozenset({"POST", "PUT", "PATCH"})


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _METHODS_WITH_BODY:
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_body_bytes):
            await self._reject(scope, receive, send)
            return

        chunks: list[bytes] = []
        size = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(body)
            more_body = message.get("more_body", False)

        buffered: Message = {"type": "http.request", "body": b"".join(chunks), "more_body": False}
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return buffered
            return await receive()

        await self.app(scope, replay, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        request_id = scope.get("state", {}).get("request_id")
        response = error_response(
            413,
            "payload_too_large",
            f"O corpo da requisição passa de {self.max_body_bytes} bytes.",
            request_id,
        )
        await response(scope, receive, send)
