"""GET /v1/model: what model is served, how it was evaluated and its limits.

Every number comes from the metadata published with the model on the Hub
(metrics/evaluation.json, calibration/calibration.json, manifest.json), never
from values typed in the code.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ncm_classifier.api.dependencies import ReadyServiceDep
from ncm_classifier.api.schemas.errors import ErrorResponse
from ncm_classifier.api.schemas.responses import (
    CalibrationInfo,
    Interval,
    ModelInfoResponse,
    PositionInfo,
    ReleaseInfo,
    RuleInfo,
    ScopeInfo,
    TestMetrics,
)

router = APIRouter(prefix="/v1", tags=["modelo"])

RULE_DESCRIPTION = (
    "Mercadorias do Capítulo 31 em embalagens de peso bruto não superior a 10 kg pertencem à "
    "posição 31.05. Quando o texto declara só pesos até esse limite e a primeira sugestão é do "
    "Capítulo 31, a probabilidade do capítulo passa para a 31.05."
)


def _interval(raw: dict[str, Any] | None) -> Interval | None:
    return Interval(**raw) if raw else None


def _test_metrics(test: dict[str, Any]) -> TestMetrics:
    final = test["metrics_calibrated_with_rules"]
    review = test["review"]
    return TestMetrics(
        test_set=test["file"].removesuffix(".csv"),
        rows=final["rows"],
        top1=Interval(**final["top1"]),
        top3=Interval(**final["top3"]),
        macro_f1=Interval(**final["macro_f1"]),
        ece=final["ece"],
        review_rate=Interval(**review["review_rate"]),
        accepted_top1=_interval(review["accepted_top1"]),
    )


@router.get(
    "/model",
    response_model=ModelInfoResponse,
    summary="Modelo em uso, resultados da avaliação e limites",
    responses={
        503: {"model": ErrorResponse, "description": "Modelo ainda carregando ou indisponível."}
    },
)
def model_info(service: ReadyServiceDep) -> ModelInfoResponse:
    bundle = service.bundle
    settings = service.settings
    catalog = service.positions
    rule = bundle.preprocessing["rule_31_05"]
    return ModelInfoResponse(
        name=settings.model_repo_id.split("/")[-1],
        version=bundle.manifest["version"],
        repo_id=settings.model_repo_id,
        revision=settings.model_revision,
        architecture=bundle.metrics["model"],
        scope=ScopeInfo(
            level=catalog.level,
            ncm_table=catalog.ncm_table,
            legal_act=catalog.legal_act,
            positions=[
                PositionInfo(
                    ncm=code,
                    formatted=catalog.describe(code).formatted,
                    official_description=catalog.describe(code).description,
                )
                for code in bundle.predictor.classes.tolist()
            ],
        ),
        metrics=[_test_metrics(test) for test in bundle.metrics["tests"]],
        calibration=CalibrationInfo(
            method=bundle.calibration["method"],
            temperature=bundle.calibration["temperature"],
            review_threshold=bundle.calibration["review_threshold"],
            review_target_accuracy=bundle.calibration["review_target_accuracy"],
            fitted_on=bundle.calibration["fitted_on"],
        ),
        rule_3105=RuleInfo(
            description=RULE_DESCRIPTION, limit_kg=rule["limit_kg"], target=rule["target"]
        ),
        release=ReleaseInfo(
            version=bundle.manifest["version"],
            date=bundle.manifest["date"],
            code_commit=bundle.manifest["code_commit"],
            github=bundle.manifest["github"],
        ),
    )
