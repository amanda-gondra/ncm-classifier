import json
from pathlib import Path

import pytest
import skops.io as sio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ncm_classifier.inference.predictor import CALIBRATION_FILE, MODEL_FILE, NcmPredictor
from ncm_classifier.text import normalize_text

TEXTS = ["ureia saco 50 kg", "ureia granulada", "arame farpado", "grampo cerca", "kcl potassio"]
LABELS = ["3102", "3102", "7313", "7317", "3105"]


def _untrusted_preprocessor(text: str) -> str:
    return text.lower()


def _save(directory: Path, preprocessor, threshold: float = 0.0) -> Path:
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(preprocessor=preprocessor)),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    ).fit(TEXTS, LABELS)
    sio.dump(pipeline, directory / MODEL_FILE)
    (directory / CALIBRATION_FILE).parent.mkdir(parents=True)
    (directory / CALIBRATION_FILE).write_text(
        json.dumps({"temperature": 1.0, "review_threshold": threshold}), encoding="utf-8"
    )
    return directory


def test_predictions_have_three_ordered_suggestions(tmp_path: Path) -> None:
    predictor = NcmPredictor.from_directory(_save(tmp_path, normalize_text))
    [prediction] = predictor.predict(["arame farpado rolo"])
    probabilities = [s.probability for s in prediction.suggestions]
    assert len(prediction.suggestions) == 3
    assert probabilities == sorted(probabilities, reverse=True)
    assert prediction.confidence == probabilities[0]
    assert not prediction.needs_review


def test_small_package_rule_is_applied(tmp_path: Path) -> None:
    predictor = NcmPredictor.from_directory(_save(tmp_path, normalize_text))
    [prediction] = predictor.predict(["ureia saco 1 kg"])
    assert prediction.suggestions[0].position == "3105"
    assert prediction.rule_31_05


def test_low_confidence_goes_to_review(tmp_path: Path) -> None:
    predictor = NcmPredictor.from_directory(_save(tmp_path, normalize_text, threshold=1.0))
    assert all(p.needs_review for p in predictor.predict(TEXTS))


def test_untrusted_function_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="untrusted types"):
        NcmPredictor.from_directory(_save(tmp_path, _untrusted_preprocessor))


def test_a_single_string_is_rejected(tmp_path: Path) -> None:
    predictor = NcmPredictor.from_directory(_save(tmp_path, normalize_text))
    with pytest.raises(TypeError, match="sequence of strings"):
        predictor.predict("ureia")
