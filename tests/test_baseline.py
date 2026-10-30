import pickle

from ncm_classifier.models.baseline import build_baseline

TEXTS = [
    "arame farpado rolo 500 m",
    "ARAME FARPADO 250M",
    "arame farpado galvanizado",
    "sal mineral para gado 30 kg",
    "SAL MINERAL 80 P SC 25KG",
    "suplemento mineral bovinos",
]
LABELS = ["7313", "7313", "7313", "2309", "2309", "2309"]


def test_learns_and_returns_probabilities() -> None:
    model = build_baseline(c=10.0).fit(TEXTS, LABELS)
    proba = model.predict_proba(["Arame Farpado Motto 500 metros", "sal mineral cria"])
    assert proba.shape == (2, 2)
    assert list(model.predict(["arame farpado", "sal mineral"])) == ["7313", "2309"]


def test_model_survives_pickling() -> None:
    model = build_baseline().fit(TEXTS, LABELS)
    restored = pickle.loads(pickle.dumps(model))  # noqa: S301 - object created in this test
    assert list(restored.predict(["arame farpado"])) == ["7313"]
