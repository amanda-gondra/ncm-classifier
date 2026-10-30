"""Baseline classifier: TF-IDF features and logistic regression.

Two TF-IDF views of the normalized text are combined:

* word unigrams and bigrams capture product names ("arame farpado", "sal mineral");
* character 3-5 grams inside words survive typos, abbreviations and units
  ("ordenhadeira" vs "ordenha", "kcl", "npk 20-05-20").

Logistic regression returns calibrated-ish probabilities, which the top-3
suggestions and the confidence shown to the user depend on. Classes are
weighted by inverse frequency so that 38.08, with many official subitems, does
not dominate positions with few examples.
"""

from __future__ import annotations

from typing import Final

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from ncm_classifier.text import normalize_text

DEFAULT_C: Final = 10.0
MAX_ITERATIONS: Final = 5000


def build_baseline(c: float = DEFAULT_C, seed: int = 0) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "words",
                TfidfVectorizer(preprocessor=normalize_text, ngram_range=(1, 2), sublinear_tf=True),
            ),
            (
                "chars",
                TfidfVectorizer(
                    preprocessor=normalize_text,
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    classifier = LogisticRegression(
        C=c, class_weight="balanced", max_iter=MAX_ITERATIONS, random_state=seed
    )
    return Pipeline([("features", features), ("classifier", classifier)])
