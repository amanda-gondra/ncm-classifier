"""Request schema of POST /v1/predictions.

A request carries exactly one of:
    description    one product description
    descriptions   a batch of product descriptions

Limits come from the settings, so the request model is built when the app is
created (build_prediction_request). The OpenAPI documentation then shows the
limits actually in force. Texts are validated but never modified: the model
receives exactly what the client sent.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    create_model,
    field_validator,
    model_validator,
)

SINGLE_EXAMPLE: dict[str, JsonValue] = {"description": "Adubo NPK 20-05-20 saco 50kg"}
BATCH_EXAMPLE: dict[str, JsonValue] = {
    "descriptions": [
        "Adubo NPK 20-05-20 saco 50kg",
        "Ureia agrícola, pacote 1 kg",
        "Arame farpado 500 m",
    ]
}


class PredictionRequestBase(BaseModel):
    """Common validation; the field limits are added by build_prediction_request."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [SINGLE_EXAMPLE, BATCH_EXAMPLE]},
    )

    description: str | None = None
    descriptions: list[str] | None = None

    @field_validator("description")
    @classmethod
    def _description_has_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("description must not be empty or only spaces")
        return value

    @field_validator("descriptions")
    @classmethod
    def _descriptions_have_text(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            blank = [i for i, text in enumerate(value) if not text.strip()]
            if blank:
                raise ValueError(f"descriptions at positions {blank} are empty or only spaces")
        return value

    @model_validator(mode="after")
    def _exactly_one_field(self) -> PredictionRequestBase:
        if (self.description is None) == (self.descriptions is None):
            raise ValueError("send exactly one of 'description' or 'descriptions'")
        return self

    def texts(self) -> list[str]:
        if self.description is not None:
            return [self.description]
        return list(self.descriptions or [])


def build_prediction_request(
    max_text_length: int, max_batch_size: int
) -> type[PredictionRequestBase]:
    text = Annotated[str, Field(min_length=1, max_length=max_text_length)]
    fields: dict[str, Any] = {
        "description": (
            text | None,
            Field(default=None, description=f"One description, up to {max_text_length} chars."),
        ),
        "descriptions": (
            list[text] | None,
            Field(
                default=None,
                min_length=1,
                max_length=max_batch_size,
                description=f"1 to {max_batch_size} descriptions of up to {max_text_length} chars.",
            ),
        ),
    }
    return create_model("PredictionRequest", __base__=PredictionRequestBase, **fields)
