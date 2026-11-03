"""Build the NCM Classifier API.

Run locally:
    uvicorn ncm_classifier.api.main:create_app --factory --port 8000

create_app is a factory, so settings are read when the app is built (not when
this module is imported) and tests can pass their own settings and service.

Middlewares, from the outside in:
    CORS            closed unless ALLOWED_ORIGINS lists origins
    RequestContext  request id, X-Request-ID header, one access log line
    BodyLimit       413 for bodies above MAX_REQUEST_BODY_BYTES
"""

from __future__ import annotations

import logging
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ncm_classifier.api.config import Settings, get_settings
from ncm_classifier.api.errors import register_exception_handlers
from ncm_classifier.api.lifespan import lifespan
from ncm_classifier.api.middleware.request_context import (
    REQUEST_ID_HEADER,
    RequestContextMiddleware,
)
from ncm_classifier.api.middleware.request_limits import RequestBodyLimitMiddleware
from ncm_classifier.api.routes import health, model
from ncm_classifier.api.routes.predictions import build_predictions_router
from ncm_classifier.api.schemas.requests import build_prediction_request
from ncm_classifier.api.schemas.responses import DISCLAIMER
from ncm_classifier.api.services.predictor_service import PredictorService

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def _description(settings: Settings) -> str:
    return f"""
Sugere posições NCM (4 dígitos) a partir de descrições comerciais de produtos agropecuários,
usando o modelo publicado [`{settings.model_repo_id}`](https://huggingface.co/{settings.model_repo_id})
na versão fixa **{settings.model_revision}**.

> **Aviso fiscal.** {DISCLAIMER}

**Limites:** até {settings.max_text_length} caracteres por descrição,
até {settings.max_batch_size} descrições por pedido e até
{settings.max_request_body_bytes} bytes no corpo da requisição.

**Erros** têm sempre o formato `{{"error": {{"code", "message", "request_id", "details"}}}}`:
400 JSON inválido · 413 corpo grande demais · 422 validação · 500 erro interno ·
503 modelo carregando ou indisponível. Toda resposta traz o cabeçalho `X-Request-ID`.
"""


def configure_logging(level: str) -> None:
    project_logger = logging.getLogger("ncm_classifier")
    project_logger.setLevel(level)
    if not project_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        project_logger.addHandler(handler)


def create_app(
    settings: Settings | None = None, service: PredictorService | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="NCM Classifier API",
        version=version("ncm-classifier"),
        description=_description(settings),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.predictor_service = service or PredictorService(settings)

    register_exception_handlers(app)
    request_model = build_prediction_request(settings.max_text_length, settings.max_batch_size)
    app.include_router(build_predictions_router(request_model))
    app.include_router(model.router)
    app.include_router(health.router)

    # add_middleware puts each new middleware outside the previous ones.
    app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=[REQUEST_ID_HEADER],
        allow_credentials=False,
    )
    return app
