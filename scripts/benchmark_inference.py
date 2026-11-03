"""Measure the inference cost of the baseline and of BERTimbau on this machine (CPU).

Usage:
    python scripts/benchmark_inference.py

Each model runs in its own Python process, so imports and memory of one do not
count for the other. For each model:

    load_seconds        import of its libraries plus loading the saved model;
    memory_mb           resident memory added by the import and the model;
    single_ms           latency of one description at a time (median and p95),
                        the way an API request arrives;
    batch_ms_per_text   time per description when all are sent together;
    disk_mb             size of the saved model;
    libraries_mb        installed size of the libraries the model needs.

The descriptions of test_v1 are only used as realistic inputs; labels are not
read. Raw model probabilities are timed; calibration and the 31.05 rule cost the
same for both models and are left out.

Output: reports/comparison/inference_benchmark.json
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
import psutil

OUTPUT: Final = Path("reports/comparison/inference_benchmark.json")
WARM_UP: Final = 5
LIBRARIES: Final = {
    "baseline": ["scikit-learn", "scipy", "numpy", "joblib"],
    "bertimbau": ["torch", "transformers", "tokenizers", "safetensors", "huggingface-hub", "numpy"],
}


def _size_mb(path: Path) -> float:
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    return round(sum(p.stat().st_size for p in files) / 1e6, 1)


def _installed_mb(packages: Sequence[str]) -> float:
    total = 0
    for package in packages:
        distribution = metadata.distribution(package)
        for file in distribution.files or []:
            located = Path(distribution.locate_file(file))
            if located.is_file():
                total += located.stat().st_size
    return round(total / 1e6, 1)


def _load(model: str, path: Path) -> tuple[Callable[[list[str]], np.ndarray], dict]:
    if model == "baseline":
        import joblib

        pipeline = joblib.load(path)["pipeline"]
        return pipeline.predict_proba, {}

    import torch

    from ncm_classifier.models.bertimbau import load_model, predict_proba
    from ncm_classifier.models.transformer_support import prepare_input

    config = json.loads(Path("experiments/bertimbau/config.json").read_text(encoding="utf-8"))
    mode = config["selection"]["best_mode"]
    max_length = config["fine_tune"]["max_length"]
    network, tokenizer, _ = load_model(path, device=torch.device("cpu"))

    def predict(texts: list[str]) -> np.ndarray:
        inputs = prepare_input(texts, mode)
        return predict_proba(network, tokenizer, inputs, max_length, batch_size=len(texts))

    return predict, {"torch_threads": torch.get_num_threads(), "input_mode": mode}


def measure(model: str, path: Path, texts: list[str]) -> dict[str, object]:
    process = psutil.Process()
    memory_before = process.memory_info().rss
    started = time.perf_counter()
    predict, extra = _load(model, path)
    load_seconds = time.perf_counter() - started

    for text in texts[:WARM_UP]:
        predict([text])
    single = []
    for text in texts:
        started = time.perf_counter()
        predict([text])
        single.append(1000 * (time.perf_counter() - started))
    started = time.perf_counter()
    predict(texts)
    batch_ms = 1000 * (time.perf_counter() - started) / len(texts)

    return {
        "load_seconds": round(load_seconds, 2),
        "memory_mb": round((process.memory_info().rss - memory_before) / 1e6, 1),
        "single_ms": {
            "median": round(float(np.median(single)), 2),
            "p95": round(float(np.percentile(single, 95)), 2),
        },
        "batch_ms_per_text": round(batch_ms, 3),
        "disk_mb": _size_mb(path),
        "libraries_mb": _installed_mb(LIBRARIES[model]),
        "texts": len(texts),
        **extra,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("models/baseline_v1.joblib"))
    parser.add_argument("--bertimbau", type=Path, default=Path("models/bertimbau_v1"))
    parser.add_argument("--texts", type=Path, default=Path("data/labeled/test_v1.csv"))
    parser.add_argument("--only", choices=sorted(LIBRARIES), help=argparse.SUPPRESS)
    args = parser.parse_args()

    texts = pd.read_csv(args.texts, dtype=str, keep_default_na=False)["text"].tolist()
    if args.only:
        path = args.baseline if args.only == "baseline" else args.bertimbau
        print(json.dumps(measure(args.only, path, texts)))
        return

    results = {}
    for model in LIBRARIES:
        child = subprocess.run(  # noqa: S603 - this same script with fixed arguments
            [
                sys.executable,
                __file__,
                "--only",
                model,
                "--baseline",
                str(args.baseline),
                "--bertimbau",
                str(args.bertimbau),
                "--texts",
                str(args.texts),
            ],
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        results[model] = json.loads(child.stdout.strip().splitlines()[-1])
    machine = {
        "system": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "python": platform.python_version(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"machine": machine, "models": results}, indent=2), encoding="utf-8"
    )
    print(json.dumps({"machine": machine, "models": results}, indent=2))


if __name__ == "__main__":
    main()
