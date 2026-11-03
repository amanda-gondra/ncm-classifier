"""Verify a running deployment of the API against the recorded evaluation.

Usage:
    python scripts/verify_deployment.py --url https://<service>.onrender.com
    python scripts/verify_deployment.py --url http://localhost:7860

Checks that /health is ready (waiting while a free instance wakes up), that
/v1/model reports the approved release, and that the predictions for every
row of test_v1 have the recorded top-1 and 31.05 flags. Only the public API is
used; no credentials are needed.
"""

from __future__ import annotations

import argparse
import logging
import time
from typing import Final

import httpx
import pandas as pd

from ncm_classifier.api.config import APPROVED_MODEL_REVISION, Settings

logger = logging.getLogger(__name__)

WAKE_UP_SECONDS: Final = 180


def _wait_for_health(client: httpx.Client) -> None:
    deadline = time.monotonic() + WAKE_UP_SECONDS
    while time.monotonic() < deadline:
        try:
            response = client.get("/health")
            if response.status_code == 200 and response.json().get("status") == "ok":
                return
            logger.info("waiting: /health answered %s", response.status_code)
        except httpx.TransportError as error:
            logger.info("waiting: %s", type(error).__name__)
        time.sleep(5)
    raise SystemExit("/health did not become ready")


def verify(base_url: str) -> None:
    test = pd.read_csv("data/labeled/test_v1.csv", dtype=str, keep_default_na=False)
    recorded = pd.read_csv("reports/predictions/baseline_v1__test_v1.csv", dtype=str)
    batch = Settings(_env_file=None).max_batch_size
    with httpx.Client(base_url=base_url, timeout=60) as client:
        _wait_for_health(client)
        version = client.get("/v1/model").json()["version"]
        if version != APPROVED_MODEL_REVISION:
            raise SystemExit(f"unexpected model version {version}")
        top1, rule = [], []
        texts = test["text"].tolist()
        for start in range(0, len(texts), batch):
            chunk = texts[start : start + batch]
            response = client.post("/v1/predictions", json={"descriptions": chunk})
            response.raise_for_status()
            for result in response.json()["results"]:
                top1.append(result["predictions"][0]["ncm"])
                rule.append(str(result["rule_3105_applied"]))
    if top1 != recorded["top1"].tolist() or rule != recorded["rule_31_05"].tolist():
        raise SystemExit("deployed predictions differ from the recorded evaluation")
    logger.info(
        "verified %s: model %s, test_v1 reproduced on %d rows", base_url, version, len(top1)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    verify(args.url.rstrip("/"))


if __name__ == "__main__":
    main()
