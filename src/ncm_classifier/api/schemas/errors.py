"""Error schema shared by every error response.

    {"error": {"code": "...", "message": "...", "request_id": "...", "details": [...]}}

`code` is stable and meant for programs; `message` is for people. Details list
which field failed and why, never the submitted text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str = Field(examples=["validation_error"])
    message: str
    request_id: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
