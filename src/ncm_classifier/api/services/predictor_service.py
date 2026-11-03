"""Owns the published model inside the API: download, load once, serve.

States:
    loading      the app started and the model is being downloaded or loaded
    ready        predictions can be served
    unavailable  loading failed; the reason is logged, never sent to clients

All classification work (normalization, probabilities, calibration, ranking,
31.05 rule, review flag) stays in NcmPredictor. This service only decides
whether a request can be served and hands the texts over.

Downloading and loading are injectable, so tests use a fake model and never
touch the network.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from huggingface_hub import snapshot_download
from numpy.typing import NDArray

from ncm_classifier.api.config import Settings
from ncm_classifier.data.positions import PositionCatalog, load_positions
from ncm_classifier.inference.predictor import CALIBRATION_FILE, NcmPredictor, Prediction

logger = logging.getLogger(__name__)

METRICS_FILE = "metrics/evaluation.json"
MANIFEST_FILE = "manifest.json"
PREPROCESSING_FILE = "preprocessing/configuration.json"


class ModelState(StrEnum):
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"


class ModelUnavailableError(RuntimeError):
    """The model is still loading or failed to load."""


class Predictor(Protocol):
    classes: NDArray[np.str_]

    def predict(self, texts: Sequence[str]) -> list[Prediction]: ...


@dataclass(frozen=True)
class ModelBundle:
    """A loaded model and the metadata published with it."""

    predictor: Predictor
    metrics: dict[str, Any]
    manifest: dict[str, Any]
    calibration: dict[str, Any]
    preprocessing: dict[str, Any]


Downloader = Callable[[Settings], Path]
BundleLoader = Callable[[Path], ModelBundle]


def download_from_hub(settings: Settings) -> Path:
    """Download (or reuse from cache) the model files at the pinned revision."""
    token = settings.hf_token.get_secret_value() if settings.hf_token else None
    return Path(
        snapshot_download(
            settings.model_repo_id,
            revision=settings.model_revision,
            cache_dir=settings.model_cache_dir,
            token=token,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    content: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return content


def load_bundle(directory: Path) -> ModelBundle:
    return ModelBundle(
        predictor=NcmPredictor.from_directory(directory),
        metrics=_read_json(directory / METRICS_FILE),
        manifest=_read_json(directory / MANIFEST_FILE),
        calibration=_read_json(directory / CALIBRATION_FILE),
        preprocessing=_read_json(directory / PREPROCESSING_FILE),
    )


class PredictorService:
    def __init__(
        self,
        settings: Settings,
        downloader: Downloader = download_from_hub,
        loader: BundleLoader = load_bundle,
        positions: PositionCatalog | None = None,
    ) -> None:
        self.settings = settings
        self.positions = positions or load_positions()
        self._downloader = downloader
        self._loader = loader
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._state = ModelState.LOADING
        self._bundle: ModelBundle | None = None

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def bundle(self) -> ModelBundle:
        if self._state is not ModelState.READY or self._bundle is None:
            raise ModelUnavailableError(self._state.value)
        return self._bundle

    def load(self) -> None:
        """Load the model once; later calls do nothing."""
        with self._lock:
            if self._finished.is_set():
                return
            try:
                bundle = self._loader(self._downloader(self.settings))
                missing = sorted(set(bundle.predictor.classes) - set(self.positions.positions))
                if missing:
                    raise ValueError(f"model classes without official description: {missing}")
                self._bundle = bundle
                self._state = ModelState.READY
                logger.info(
                    "model ready: repo=%s revision=%s classes=%d",
                    self.settings.model_repo_id,
                    self.settings.model_revision,
                    len(bundle.predictor.classes),
                )
            except Exception:
                self._state = ModelState.UNAVAILABLE
                logger.exception(
                    "model failed to load: repo=%s revision=%s",
                    self.settings.model_repo_id,
                    self.settings.model_revision,
                )
            finally:
                self._finished.set()

    def wait_until_loaded(self, timeout: float | None = None) -> bool:
        return self._finished.wait(timeout)

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        return self.bundle.predictor.predict(texts)

    def close(self) -> None:
        self._bundle = None
