"""Standard error responses and the exception handlers that produce them.

    400 invalid_json        body is not valid JSON
    404 not_found           unknown route
    405 method_not_allowed  wrong method for the route
    413 payload_too_large   body above MAX_REQUEST_BODY_BYTES (see middleware)
    422 validation_error    body does not match the schema or the limits
    429 rate_limited        above RATE_LIMIT_PER_MINUTE (see middleware), with Retry-After
    500 internal_error      unexpected failure; details stay in the server log
    503 model_unavailable   the model is loading or failed to load

`code` is for programs and stays in English; `message` is for people and is in
Brazilian Portuguese, because the web interface shows it as is. Validation details
from Pydantic are translated by error type (_DETAIL_MESSAGES).

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
_HTTP_ERRORS: Final = {
    404: ("not_found", "Rota não encontrada."),
    405: ("method_not_allowed", "Método não permitido nesta rota."),
}
# Pydantic error types that a client of this API can trigger, with the context keys they use.
_DETAIL_MESSAGES: Final = {
    "missing": "Campo obrigatório.",
    "extra_forbidden": "Campo não aceito.",
    "string_type": "Deve ser um texto.",
    "list_type": "Deve ser uma lista de textos.",
    "model_type": "O corpo deve ser um objeto JSON.",
    "model_attributes_type": "O corpo deve ser um objeto JSON.",
    "string_too_short": "O texto não pode ficar vazio.",
    "string_too_long": "Texto com mais de {max_length} caracteres.",
    "too_short": "Envie pelo menos {min_length} descrição.",
    "too_long": "Envie no máximo {max_length} descrições.",
}


def _detail_message(error: dict[str, object]) -> str:
    """The Portuguese message of one Pydantic error (our own validators already speak it)."""
    kind = error.get("type")
    context = error.get("ctx")
    context = context if isinstance(context, dict) else {}
    if kind == "value_error" and "error" in context:
        return str(context["error"])
    template = _DETAIL_MESSAGES.get(str(kind))
    if template is None:
        return "Valor inválido."
    try:
        return template.format(**context)
    except (KeyError, IndexError):
        return "Valor inválido."


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
            400, "invalid_json", "O corpo da requisição não é um JSON válido.", _request_id(request)
        )
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error.get("loc", ())[1:]) or None,
            message=_detail_message(dict(error)),
        )
        for error in errors
    ]
    return error_response(
        422,
        "validation_error",
        "A requisição não segue o formato ou os limites esperados.",
        _request_id(request),
        details,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101 - registered for this type
    code, message = _HTTP_ERRORS.get(exc.status_code, ("http_error", "Erro HTTP."))
    return error_response(exc.status_code, code, message, _request_id(request))


async def _model_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        503,
        "model_unavailable",
        "O modelo ainda não está pronto (carregando ou com falha ao carregar). "
        "Tente de novo em instantes.",
        _request_id(request),
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )


async def _internal_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "internal error: request_id=%s type=%s", _request_id(request), type(exc).__name__
    )
    return error_response(500, "internal_error", "Erro interno.", _request_id(request))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(ModelUnavailableError, _model_unavailable)
    app.add_exception_handler(Exception, _internal_error)
