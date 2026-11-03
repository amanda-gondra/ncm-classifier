"""API settings, read once from environment variables (or a local .env file).

Defaults are safe for production: the model is pinned to the approved release,
CORS allows no origin, and every limit is on. Nothing secret has a default.

Variables:
    MODEL_REPO_ID            Hugging Face repository of the approved model
    MODEL_REVISION           release tag or commit hash; branches such as
                             "main" are refused because they can change
    HF_TOKEN                 optional, only for private repositories
    MODEL_CACHE_DIR          where downloaded artifacts are kept (Hub default if empty)
    ALLOWED_ORIGINS          comma-separated origins allowed by CORS (none by default)
    MAX_TEXT_LENGTH          characters per description
    MAX_BATCH_SIZE           descriptions per request
    MAX_REQUEST_BODY_BYTES   size of the request body
    RATE_LIMIT_PER_MINUTE    requests per client per minute to /v1/ (0: no limit)
    LOG_LEVEL                logging level
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import Annotated, Final, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

APPROVED_MODEL_REPO: Final = "AmandaGondra/ncm-classifier"
APPROVED_MODEL_REVISION: Final = "v0.1.0"
_TAG: Final = re.compile(r"^v\d+\.\d+\.\d+$")
_COMMIT: Final = re.compile(r"^[0-9a-f]{40}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    model_repo_id: str = APPROVED_MODEL_REPO
    model_revision: str = APPROVED_MODEL_REVISION
    hf_token: SecretStr | None = None
    model_cache_dir: Path | None = None
    allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # 500 characters fit every training description (the longest has 71 words);
    # 20 descriptions keep one request under ~50 ms of CPU for the baseline.
    max_text_length: int = Field(default=500, ge=1, le=10_000)
    max_batch_size: int = Field(default=20, ge=1, le=1_000)
    # 20 x 500 characters x up to 4 bytes each in UTF-8 = 40 KB, plus JSON overhead.
    max_request_body_bytes: int = Field(default=65_536, ge=1_024)
    # Requests per client per minute to /v1/ routes; 0 turns the limit off.
    rate_limit_per_minute: int = Field(default=120, ge=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("model_revision")
    @classmethod
    def _fixed_revision(cls, value: str) -> str:
        if not (_TAG.fullmatch(value) or _COMMIT.fullmatch(value)):
            raise ValueError("MODEL_REVISION must be a release tag (vX.Y.Z) or a 40-char commit")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list) and "*" in value:
            raise ValueError("ALLOWED_ORIGINS must list origins explicitly; '*' is not allowed")
        return value

    @field_validator("hf_token", "model_cache_dir", mode="before")
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        # An empty variable in .env or docker means "not set", not an empty value.
        return None if value == "" else value


@cache
def get_settings() -> Settings:
    return Settings()
