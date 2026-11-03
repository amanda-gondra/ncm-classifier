"""FastAPI dependencies shared by the routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ncm_classifier.api.services.predictor_service import (
    ModelState,
    ModelUnavailableError,
    PredictorService,
)


def get_service(request: Request) -> PredictorService:
    service: PredictorService = request.app.state.predictor_service
    return service


def get_ready_service(
    service: Annotated[PredictorService, Depends(get_service)],
) -> PredictorService:
    """The service, only when the model can serve; otherwise the request gets 503."""
    if service.state is not ModelState.READY:
        raise ModelUnavailableError(service.state.value)
    return service


def get_request_id(request: Request) -> str:
    request_id: str = request.state.request_id
    return request_id


ServiceDep = Annotated[PredictorService, Depends(get_service)]
ReadyServiceDep = Annotated[PredictorService, Depends(get_ready_service)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
