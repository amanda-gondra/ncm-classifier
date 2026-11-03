# NCM Classifier API: serves the published model (AmandaGondra/ncm-classifier @ v0.1.0).
#
#   docker build -t ncm-classifier-api .
#   docker run --rm -p 7860:7860 ncm-classifier-api
#   open http://localhost:7860/docs
#
# Compatible with a Hugging Face Docker Space: the app listens on 7860 and runs
# as UID 1000. The model is downloaded at build time at the pinned revision, so
# a restart does not download it again (Spaces reset the disk on restart).
# No secret is needed: the model repository is public. If HF_TOKEN is ever
# required, pass it at run time (or as a Space secret), never in this file.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 1000 user
WORKDIR /home/user/app

# Pinned dependencies first, so this layer is reused while only the code changes.
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps . && rm -rf src

USER user
ENV HOME=/home/user \
    MODEL_REPO_ID=AmandaGondra/ncm-classifier \
    MODEL_REVISION=v0.1.0 \
    MODEL_CACHE_DIR=/home/user/model-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    LOG_LEVEL=INFO \
    PORT=7860

RUN python -c "from ncm_classifier.api.config import Settings; \
from ncm_classifier.api.services.predictor_service import download_from_hub; \
print(download_from_hub(Settings()))"

EXPOSE 7860

# 503 while the model loads or if it failed: the container is reported unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; \
urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/health\", timeout=4)"

CMD ["sh", "-c", "exec uvicorn ncm_classifier.api.main:create_app --factory --host 0.0.0.0 --port ${PORT} --no-server-header"]
