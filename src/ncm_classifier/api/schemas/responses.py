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
    rank: int = Field(ge=1, description="1 é a posição mais provável.")
    ncm: str = Field(description="Posição NCM, 4 dígitos.", examples=["3105"])
    level: Literal["position"] = "position"
    formatted: str = Field(examples=["31.05"])
    official_description: str = Field(description="Texto da posição na tabela oficial.")
    confidence: float = Field(ge=0.0, le=1.0, description="Probabilidade calibrada.")


class PredictionResult(BaseModel):
    index: int = Field(ge=0, description="Posição da descrição no pedido, a partir de 0.")
    predictions: list[Suggestion] = Field(
        description="Até três sugestões, a mais provável primeiro."
    )
    requires_manual_review: bool = Field(
        description="Verdadeiro quando a confiança da primeira sugestão fica abaixo do limiar."
    )
    rule_3105_applied: bool = Field(
        description="Verdadeiro quando a regra 31.05 (embalagens até 10 kg) mudou o resultado."
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
        description=(
            "Testes congelados, com calibração e regra 31.05; intervalos de 95% por bootstrap."
        )
    )
    calibration: CalibrationInfo
    rule_3105: RuleInfo
    release: ReleaseInfo
    disclaimer: str = DISCLAIMER
