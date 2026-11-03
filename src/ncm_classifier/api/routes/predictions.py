"""POST /v1/predictions: classify one description or a batch.

The route validates the request, passes the texts to NcmPredictor through the
service, and maps each Prediction to the response schema, adding the official
description of each position. Probabilities, calibration, ranking, the 31.05
rule and the review flag all come from NcmPredictor unchanged.

The module does not use `from __future__ import annotations`: FastAPI reads the
annotation of `body` at run time, and it is a model class built from settings.
"""

import logging
from typing import Any, cast

from fastapi import APIRouter

from ncm_classifier.api.dependencies import ReadyServiceDep, RequestIdDep
from ncm_classifier.api.schemas.errors import ErrorResponse
from ncm_classifier.api.schemas.requests import PredictionRequestBase
from ncm_classifier.api.schemas.responses import (
    RULE_3105_ID,
    PredictionResponse,
    PredictionResult,
    Suggestion,
)
from ncm_classifier.api.services.predictor_service import PredictorService
from ncm_classifier.inference.predictor import Prediction

logger = logging.getLogger(__name__)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Body is not valid JSON."},
    413: {"model": ErrorResponse, "description": "Body larger than the configured limit."},
    422: {"model": ErrorResponse, "description": "Empty text, text or batch over the limits."},
    500: {"model": ErrorResponse, "description": "Unexpected internal error."},
    503: {"model": ErrorResponse, "description": "Model still loading or unavailable."},
}


def to_result(index: int, prediction: Prediction, service: PredictorService) -> PredictionResult:
    suggestions = []
    for rank, suggestion in enumerate(prediction.suggestions, start=1):
        position = service.positions.describe(suggestion.position)
        suggestions.append(
            Suggestion(
                rank=rank,
                ncm=position.code,
                formatted=position.formatted,
                official_description=position.description,
                confidence=suggestion.probability,
            )
        )
    return PredictionResult(
        index=index,
        predictions=suggestions,
        requires_manual_review=prediction.needs_review,
        rule_3105_applied=prediction.rule_31_05,
        applied_rule=RULE_3105_ID if prediction.rule_31_05 else None,
    )


def build_predictions_router(request_model: type[PredictionRequestBase]) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["predictions"])

    @router.post(
        "/predictions",
        response_model=PredictionResponse,
        summary="Suggest NCM positions for product descriptions",
        description=(
            "Send exactly one of `description` (one text) or `descriptions` (a batch). "
            "Each result has up to three NCM positions with calibrated confidence, "
            "a manual review flag and whether the 31.05 small-package rule applied. "
            "Suggestions support, and do not replace, the fiscal classification."
        ),
        responses=ERROR_RESPONSES,
    )
    def create_predictions(
        body: request_model,  # type: ignore[valid-type]  # built from settings at startup
        service: ReadyServiceDep,
        request_id: RequestIdDep,
    ) -> PredictionResponse:
        texts = cast(PredictionRequestBase, body).texts()
        lengths = [len(text) for text in texts]
        logger.info(
            "predictions request_id=%s count=%d chars_min=%d chars_max=%d chars_total=%d",
            request_id,
            len(texts),
            min(lengths),
            max(lengths),
            sum(lengths),
        )
        predictions = service.predict(texts)
        return PredictionResponse(
            request_id=request_id,
            model_version=service.settings.model_revision,
            results=[to_result(i, p, service) for i, p in enumerate(predictions)],
        )

    return router
