"""Suggest NCM positions for product descriptions with this model.

Usage (from the downloaded model folder):
    pip install -r requirements.txt
    python inference/predict.py "Ureia agrícola saco 50 kg" "Arame farpado 500 m"

Each description gets the three most likely positions, the calibrated
confidence of the first one, whether it should go to manual review and
whether the 31.05 small-package rule changed it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ncm_classifier.inference.predictor import NcmPredictor

EXAMPLES = ["Ureia agrícola granulada, saco 50 kg", "Ureia agrícola, pacote 1 kg"]


def main() -> None:
    texts = sys.argv[1:] or EXAMPLES
    predictor = NcmPredictor.from_directory(Path(__file__).resolve().parents[1])
    for text, prediction in zip(texts, predictor.predict(texts), strict=True):
        print(json.dumps({"text": text, **prediction.to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
