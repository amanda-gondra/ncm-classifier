"""GET /health: is the API able to classify right now?

200 status=ok           model loaded, predictions are served
503 status=starting     model still downloading or loading
503 status=unavailable  model failed to load (reason only in the server log)
"""

from __future__ import annotations

from typing import Final, Literal

from fastapi import APIRouter, Response

from ncm_classifier.api.dependencies import ServiceDep
from ncm_classifier.api.schemas.responses import HealthModel, HealthResponse
from ncm_classifier.api.services.predictor_service import ModelState

router = APIRouter(tags=["health"])

ApiStatus = Literal["ok", "starting", "unavailable"]
StateName = Literal["loading", "ready", "unavailable"]

_STATUS: Final[dict[ModelState, tuple[ApiStatus, StateName, int]]] = {
    ModelState.READY: ("ok", "ready", 200),
    ModelState.LOADING: ("starting", "loading", 503),
    ModelState.UNAVAILABLE: ("unavailable", "unavailable", 503),
}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Operational state of the API and the model",
    responses={503: {"model": HealthResponse, "description": "Model loading or unavailable."}},
)
def health(service: ServiceDep, response: Response) -> HealthResponse:
    state = service.state
    status, state_name, code = _STATUS[state]
    response.status_code = code
    version = service.settings.model_revision if state is ModelState.READY else None
    return HealthResponse(status=status, model=HealthModel(state=state_name, version=version))
