"""Upload the folders built by export_hf.py to the Hugging Face Hub and tag them.

Usage (after `hf auth login` in your own terminal):
    python scripts/publish_hf.py --owner <hugging-face-user>

Authentication comes only from the Hugging Face login cache or the HF_TOKEN
environment variable set by the owner; this script never reads, prints or
stores a token. Each repository gets one commit and the tag of the release, so
earlier versions stay available by revision. An existing tag is never moved:
publishing the same version twice stops with an error.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Final

from huggingface_hub import HfApi

logger = logging.getLogger(__name__)

REPOSITORIES: Final = {
    "ncm-classifier": "model",
    "ncm-classifier-bertimbau": "model",
    "ncm-classifier-dataset": "dataset",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--source", type=Path, default=Path("dist/huggingface"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    api = HfApi()
    user = api.whoami()["name"]
    if user != args.owner:
        raise SystemExit(f"Logged in as {user!r}, but --owner is {args.owner!r}")

    for name, repo_type in REPOSITORIES.items():
        folder = args.source / name
        version = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        tag = version.get("dataset_version", version["version"])
        repo_id = f"{args.owner}/{name}"
        api.create_repo(repo_id, repo_type=repo_type, exist_ok=True)
        existing = {ref.name for ref in api.list_repo_refs(repo_id, repo_type=repo_type).tags}
        if tag in existing:
            raise SystemExit(f"{repo_id} already has tag {tag}; bump the version instead")
        commit = api.upload_folder(
            repo_id=repo_id,
            repo_type=repo_type,
            folder_path=folder,
            commit_message=f"Release {tag} (code {version['code_commit'][:7]})",
        )
        api.create_tag(repo_id, repo_type=repo_type, tag=tag, revision=commit.oid)
        logger.info("%s %s: %s", repo_id, tag, commit.commit_url)


if __name__ == "__main__":
    main()
