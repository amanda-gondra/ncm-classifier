"""Response schemas of the API.

The model classifies NCM positions (4 digits), so `ncm` holds a position such
as "3105" and `level` says so explicitly; the API never pads it to 8 digits.
Every confidence is the calibrated probability computed by NcmPredictor, after
the 31.05 rule; the HTTP layer only renames and annotates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = (
    "Sugestões de apoio, não decisões fiscais. A responsabilidade pela classificação fiscal "
    "permanece com quem emite a nota; a revisão por profissional habilitado pode ser necessária."
)
RULE_3105_ID = "ncm-3105-small-package"


class Suggestion(BaseModel):
    rank: int = Field(ge=1, description="1 is the most likely position.")
    ncm: str = Field(description="NCM position, 4 digits.", examples=["3105"])
    level: Literal["position"] = "position"
    formatted: str = Field(examples=["31.05"])
    official_description: str = Field(description="Text of the position in the official table.")
    confidence: float = Field(ge=0.0, le=1.0, description="Calibrated probability.")


class PredictionResult(BaseModel):
    index: int = Field(ge=0, description="Position of the description in the request.")
    predictions: list[Suggestion] = Field(description="Up to three suggestions, best first.")
    requires_manual_review: bool = Field(
        description="True when the first suggestion's confidence is below the review threshold."
    )
    rule_3105_applied: bool = Field(
        description="True when the 31.05 rule (packages of 10 kg or less) changed the result."
    )
    applied_rule: str | None = Field(default=None, examples=[RULE_3105_ID])


class PredictionResponse(BaseModel):
    request_id: str
    model_version: str
    results: list[PredictionResult]
    disclaimer: str = DISCLAIMER


class HealthModel(BaseModel):
    state: Literal["loading", "ready", "unavailable"]
    version: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "starting", "unavailable"]
    model: HealthModel


class Interval(BaseModel):
    value: float
    low: float
    high: float


class TestMetrics(BaseModel):
    test_set: str
    rows: int
    top1: Interval
    top3: Interval
    macro_f1: Interval
    ece: float
    review_rate: Interval
    accepted_top1: Interval | None


class PositionInfo(BaseModel):
    ncm: str
    formatted: str
    official_description: str


class ScopeInfo(BaseModel):
    level: str
    ncm_table: str
    legal_act: str
    positions: list[PositionInfo]


class CalibrationInfo(BaseModel):
    method: str
    temperature: float
    review_threshold: float
    review_target_accuracy: float
    fitted_on: str


class RuleInfo(BaseModel):
    id: str = RULE_3105_ID
    description: str
    limit_kg: float
    target: str


class ReleaseInfo(BaseModel):
    version: str
    date: str
    code_commit: str
    github: str


class ModelInfoResponse(BaseModel):
    name: str
    version: str
    repo_id: str
    revision: str
    architecture: str
    scope: ScopeInfo
    metrics: list[TestMetrics] = Field(
        description="Frozen test sets, calibrated + 31.05 rule, 95% bootstrap intervals."
    )
    calibration: CalibrationInfo
    rule_3105: RuleInfo
    release: ReleaseInfo
    disclaimer: str = DISCLAIMER
