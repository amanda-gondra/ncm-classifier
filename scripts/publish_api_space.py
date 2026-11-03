"""Deploy the API to a Hugging Face Docker Space, then verify the running Space.

Usage (after `hf auth login` in your own terminal, and only with approval):
    python scripts/publish_api_space.py --owner AmandaGondra
    python scripts/publish_api_space.py --owner AmandaGondra --verify-only

The code must be committed and pushed: the Space README records the commit it
was built from. Only what the image needs is uploaded (Dockerfile,
requirements-api.txt, pyproject.toml, src/ and the Space README); files from a
previous deploy that are no longer needed are deleted from the Space.

After the upload the script waits for the Space to run and checks it the same
way as the local container: /health is ready, /v1/model reports v0.1.0, and the
predictions for every row of test_v1 have the recorded top-1 and 31.05 flags.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from string import Template
from typing import Final

import httpx
import pandas as pd
from huggingface_hub import HfApi

from ncm_classifier.api.config import Settings

logger = logging.getLogger(__name__)

GITHUB: Final = "https://github.com/amanda-gondra/ncm-classifier"
FILES: Final = ("Dockerfile", "requirements-api.txt", "pyproject.toml")
TEMPLATE: Final = Path("publishing/templates/space_api_readme.md")
STARTUP_TIMEOUT_SECONDS: Final = 900


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _stage(folder: Path, host: str, commit: str) -> None:
    for name in FILES:
        shutil.copy(name, folder / name)
    shutil.copytree(
        "src", folder / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")
    )
    settings = Settings(_env_file=None)
    readme = Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        model_repo=settings.model_repo_id,
        model_revision=settings.model_revision,
        github=GITHUB,
        commit=commit,
        host=host,
        max_text_length=settings.max_text_length,
        max_batch_size=settings.max_batch_size,
        rate_limit=settings.rate_limit_per_minute,
    )
    (folder / "README.md").write_text(readme, encoding="utf-8")


def _wait_until_running(api: HfApi, repo_id: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        stage = api.get_space_runtime(repo_id).stage
        logger.info("Space stage: %s", stage)
        if stage == "RUNNING":
            return
        if stage in {"BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"}:
            raise SystemExit(f"Space failed: {stage}; see the logs on the Space page")
        time.sleep(15)
    raise SystemExit("Space did not start in time")


def verify(base_url: str) -> None:
    test = pd.read_csv("data/labeled/test_v1.csv", dtype=str, keep_default_na=False)
    recorded = pd.read_csv("reports/predictions/baseline_v1__test_v1.csv", dtype=str)
    batch = Settings(_env_file=None).max_batch_size
    with httpx.Client(base_url=base_url, timeout=60) as client:
        for _ in range(40):  # the model may still be loading right after startup
            health = client.get("/health")
            if health.status_code == 200:
                break
            time.sleep(3)
        if health.json().get("status") != "ok":
            raise SystemExit(f"/health is not ready: {health.json()}")
        info = client.get("/v1/model").json()
        if info["version"] != "v0.1.0":
            raise SystemExit(f"unexpected model version {info['version']}")
        top1, rule = [], []
        texts = test["text"].tolist()
        for start in range(0, len(texts), batch):
            response = client.post(
                "/v1/predictions", json={"descriptions": texts[start : start + batch]}
            )
            response.raise_for_status()
            for result in response.json()["results"]:
                top1.append(result["predictions"][0]["ncm"])
                rule.append(str(result["rule_3105_applied"]))
    if top1 != recorded["top1"].tolist() or rule != recorded["rule_31_05"].tolist():
        raise SystemExit("Space predictions differ from the recorded evaluation")
    logger.info("Space verified: health ok, model v0.1.0, test_v1 reproduced on %d rows", len(top1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--space", default="ncm-classifier-api")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    repo_id = f"{args.owner}/{args.space}"
    host = f"{args.owner.lower()}-{args.space}.hf.space"
    api = HfApi()
    if not args.verify_only:
        if _git("status", "--porcelain", "--", "src", "Dockerfile", "pyproject.toml"):
            raise SystemExit("Commit the code first: the Space records the commit it runs")
        if _git("rev-parse", "HEAD") != _git("rev-parse", "@{u}"):
            raise SystemExit("Push the commit first, so the Space links to code on GitHub")
        if api.whoami()["name"] != args.owner:
            raise SystemExit("Logged in with a different Hugging Face user")
        commit = _git("rev-parse", "HEAD")
        api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            _stage(folder, host, commit)
            result = api.upload_folder(
                repo_id=repo_id,
                repo_type="space",
                folder_path=folder,
                delete_patterns=["*"],  # the Space holds exactly what was staged
                commit_message=f"Deploy API from {commit[:7]}",
            )
        logger.info("Uploaded: %s", result.commit_url)
        _wait_until_running(api, repo_id)
    verify(f"https://{host}")


if __name__ == "__main__":
    main()
