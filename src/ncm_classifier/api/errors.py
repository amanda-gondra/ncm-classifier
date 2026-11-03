"""Standard error responses and the exception handlers that produce them.

    400 invalid_json        body is not valid JSON
    404 not_found           unknown route
    405 method_not_allowed  wrong method for the route
    413 payload_too_large   body above MAX_REQUEST_BODY_BYTES (see middleware)
    422 validation_error    body does not match the schema or the limits
    429 rate_limited        above RATE_LIMIT_PER_MINUTE (see middleware), with Retry-After
    500 internal_error      unexpected failure; details stay in the server log
    503 model_unavailable   the model is loading or failed to load

Messages never include the submitted text, file paths or stack traces.
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ncm_classifier.api.schemas.errors import ErrorBody, ErrorDetail, ErrorResponse
from ncm_classifier.api.services.predictor_service import ModelUnavailableError

logger = logging.getLogger(__name__)

RETRY_AFTER_SECONDS: Final = "30"
_HTTP_CODES: Final = {404: "not_found", 405: "method_not_allowed"}


def error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, request_id=request_id, details=details or [])
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers=headers)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101 - registered for this type
    errors = exc.errors()
    if any(error.get("type") == "json_invalid" for error in errors):
        return error_response(
            400, "invalid_json", "Request body is not valid JSON.", _request_id(request)
        )
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error.get("loc", ())[1:]) or None,
            message=str(error.get("msg", "invalid value")),
        )
        for error in errors
    ]
    return error_response(
        422,
        "validation_error",
        "The request does not match the expected schema or limits.",
        _request_id(request),
        details,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101 - registered for this type
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
    return error_response(exc.status_code, code, message, _request_id(request))


async def _model_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        503,
        "model_unavailable",
        "The model is not ready (still loading or failed to load). Try again later.",
        _request_id(request),
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def _internal_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "internal error: request_id=%s type=%s", _request_id(request), type(exc).__name__
    )
    return error_response(500, "internal_error", "Internal error.", _request_id(request))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(ModelUnavailableError, _model_unavailable)
    app.add_exception_handler(Exception, _internal_error)
