"""Application lifespan: load the model once, in the background, at startup.

Loading runs in a worker thread so the server starts answering right away:
/health reports "loading" while the model downloads (useful on a cold start of
a hosted container) and predictions return 503 until it is ready. The model is
loaded a single time; requests reuse the same NcmPredictor instance.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ncm_classifier.api.services.predictor_service import PredictorService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service: PredictorService = app.state.predictor_service
    loading = asyncio.create_task(asyncio.to_thread(service.load))
    try:
        yield
    finally:
        # A download still running at shutdown is abandoned, not awaited, so the
        # server stops promptly; the worker thread ends with the process.
        loading.cancel()
        service.close()
