"""Validate a release after it is on the Hugging Face Hub (without logging in).

Usage, ideally from a clean environment with only the published requirements:
    python -m venv <dir> && <dir>/Scripts/pip install -r <model>/requirements.txt
    <dir>/Scripts/python scripts/validate_hf.py --owner AmandaGondra [--with-bertimbau]

Checks, each one reported and any failure ending with exit code 1:
    1. the three repositories are public and the release tags exist;
    2. every downloaded file matches the SHA-256 of its manifest;
    3. the model loads from skops and its calibration file loads;
    4. its predictions on both frozen tests equal the recorded ones (top 3,
       confidence, 31.05 rule and review flag), and the published metrics are
       recomputed from them;
    5. inference/predict.py runs;
    6. the dataset has the documented rows and sources;
    7. optionally, the BERTimbau weights load and give the recorded raw top-1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from huggingface_hub import HfApi, snapshot_download

from ncm_classifier.evaluation.metrics import evaluate
from ncm_classifier.inference.predictor import NcmPredictor

TESTS: Final = (Path("data/labeled/test_v1.csv"), Path("data/labeled/test_v2.csv"))
RELEASES: Final = {
    "ncm-classifier": ("model", "v0.1.0"),
    "ncm-classifier-bertimbau": ("model", "v0.1.0"),
    "ncm-classifier-dataset": ("dataset", "v1.0.0"),
}


class Checks:
    def __init__(self) -> None:
        self.failed: list[str] = []

    def __call__(self, name: str, passed: bool, detail: str = "") -> None:
        print(f"{'PASS' if passed else 'FAIL'} {name} {detail}".rstrip())
        if not passed:
            self.failed.append(name)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _download(owner: str, name: str, root: Path) -> Path:
    repo_type, tag = RELEASES[name]
    return Path(
        snapshot_download(
            f"{owner}/{name}",
            repo_type=repo_type,
            revision=tag,
            local_dir=root / name,
            token=False,
        )
    )


def check_access(owner: str, check: Checks) -> None:
    api = HfApi(token=False)  # anonymous: proves the repositories are public
    for name, (repo_type, tag) in RELEASES.items():
        refs = api.list_repo_refs(f"{owner}/{name}", repo_type=repo_type)
        check(f"{name}: public, tag {tag}", tag in {ref.name for ref in refs.tags})


def check_manifest(folder: Path, check: Checks) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    mismatched = [
        name for name, item in manifest["files"].items() if _sha256(folder / name) != item["sha256"]
    ]
    check(f"{folder.name}: files match the manifest", not mismatched, str(mismatched or ""))
    return manifest


def check_model(folder: Path, check: Checks) -> None:
    predictor = NcmPredictor.from_directory(folder)
    check("ncm-classifier: skops model and calibration load", True)
    published = json.loads((folder / "metrics/evaluation.json").read_text(encoding="utf-8"))
    metrics = {test["file"]: test for test in published["tests"]}
    for test_path in TESTS:
        test = pd.read_csv(test_path, dtype=str, keep_default_na=False)
        recorded = pd.read_csv(f"reports/predictions/baseline_v1__{test_path.stem}.csv", dtype=str)
        predictions = predictor.predict(test["text"].tolist())
        top3 = [[s.position for s in p.suggestions] for p in predictions]
        check(
            f"{test_path.name}: top 3 equal the recorded predictions",
            top3 == recorded[["top1", "top2", "top3"]].values.tolist(),
        )
        confidence = np.array([p.confidence for p in predictions])
        check(
            f"{test_path.name}: confidence equals the recorded one",
            np.allclose(confidence, recorded["p_top1"].astype(float), atol=1e-6),
        )
        rule = [str(p.rule_31_05) for p in predictions]
        review = [str(p.needs_review) for p in predictions]
        check(
            f"{test_path.name}: 31.05 rule rows unchanged", rule == recorded["rule_31_05"].tolist()
        )
        check(
            f"{test_path.name}: review flags unchanged", review == recorded["needs_review"].tolist()
        )
        final, _ = predictor.predict_proba(test["text"].tolist())
        top1 = evaluate(test["position"], final, predictor.classes).top1.value
        expected = metrics[test_path.name]["metrics_calibrated_with_rules"]["top1"]["value"]
        check(f"{test_path.name}: published top-1 metric reproduced", top1 == expected, f"{top1}")

    demo = subprocess.run(  # noqa: S603 - the downloaded example with a fixed input
        [sys.executable, str(folder / "inference/predict.py"), "Ureia agrícola, pacote 1 kg"],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    output = json.loads(demo.stdout) if demo.returncode == 0 else {}
    check(
        "inference/predict.py runs and applies the 31.05 rule",
        output.get("suggestions", [{}])[0].get("position") == "3105",
        demo.stderr.strip()[-200:],
    )


def check_dataset(folder: Path, manifest: dict, check: Checks) -> None:
    data = pd.read_parquet(folder / "data/train_public-v1.parquet")
    sources = data["source_type"].value_counts().to_dict()
    check("dataset: 658 rows, official and synthetic only", len(data) == 658, str(sources))
    check("dataset: no missing values", int(data.isna().sum().sum()) == 0)
    check("dataset: built from the training file", "built_from_sha256" in manifest)


def check_bertimbau(folder: Path, check: Checks) -> None:
    from ncm_classifier.models.bertimbau import load_model, predict_proba
    from ncm_classifier.models.transformer_support import prepare_input

    config = json.loads((folder / "training/config.json").read_text(encoding="utf-8"))
    model, tokenizer, classes = load_model(folder)
    test = pd.read_csv(TESTS[0], dtype=str, keep_default_na=False)
    raw = predict_proba(
        model,
        tokenizer,
        prepare_input(test["text"].tolist(), config["selection"]["best_mode"]),
        config["fine_tune"]["max_length"],
    )
    top1 = np.asarray(classes)[raw.argmax(axis=1)].tolist()
    recorded = pd.read_csv(
        "experiments/bertimbau/predictions/bertimbau_v1__test_v1.csv", dtype=str
    )["raw_top1"].tolist()
    check("ncm-classifier-bertimbau: weights load, raw top-1 reproduced", top1 == recorded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--with-bertimbau", action="store_true")
    args = parser.parse_args()

    check = Checks()
    check_access(args.owner, check)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        model = _download(args.owner, "ncm-classifier", root)
        check_manifest(model, check)
        check_model(model, check)
        dataset = _download(args.owner, "ncm-classifier-dataset", root)
        check_dataset(dataset, check_manifest(dataset, check), check)
        if args.with_bertimbau:
            bertimbau = _download(args.owner, "ncm-classifier-bertimbau", root)
            check_manifest(bertimbau, check)
            check_bertimbau(bertimbau, check)
    if check.failed:
        raise SystemExit(f"{len(check.failed)} check(s) failed: {check.failed}")
    print("All checks passed")


if __name__ == "__main__":
    main()
