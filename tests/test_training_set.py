import pandas as pd
import pytest

from ncm_classifier.data.training_set import TrainingSetError, assemble_training_set

SCOPE = ["7313", "1209", "2309"]
TEST_SET = pd.DataFrame(
    {
        "text": ["Arame farpado Gerdau Touro em rolo de 500m disponível na Lapa, PR."],
        "source_url": ["https://example.com/test-page"],
    }
)


def _source(rows: list[tuple[str, str, str, str]], source_type: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "example_id": example_id,
                "text": text,
                "position": position,
                "source_type": source_type,
                "source_ref": ref,
            }
            for example_id, text, position, ref in rows
        ]
    )


def test_drops_near_test_conflicts_and_repeats() -> None:
    real = _source(
        [
            ("r1", "Arame farpado Gerdau Touro rolo de 500m disponível na Lapa - PR", "7313", "u1"),
            ("r2", "Semente de capim Mombaça 20 kg", "1209", "u2"),
            ("r3", "Produto ambíguo", "2309", "u3"),
        ],
        "marketplace",
    )
    synthetic = _source(
        [
            ("s1", "SEMENTE DE CAPIM MOMBAÇA 20 KG", "1209", "llm"),
            ("s2", "produto ambiguo", "1209", "llm"),
            ("s3", "Sal mineral para bovinos 30 kg", "2309", "llm"),
        ],
        "synthetic",
    )

    train, report = assemble_training_set([real, synthetic], TEST_SET, SCOPE)

    assert list(train["example_id"]) == ["r2", "s3"]
    assert report.input_rows == 6
    assert report.dropped_near_test == 1
    assert report.dropped_label_conflict == 2
    assert report.dropped_repeated == 1
    assert report.rows_by_source == {"marketplace": 1, "synthetic": 1}


def test_position_outside_scope_is_an_error() -> None:
    source = _source([("r1", "Trator 75 cv", "8701", "u1")], "marketplace")
    with pytest.raises(TrainingSetError, match="outside the scope"):
        assemble_training_set([source], TEST_SET, SCOPE)


def test_url_shared_with_test_is_an_error() -> None:
    source = _source([("r1", "Outro texto", "7313", "https://example.com/test-page")], "web")
    with pytest.raises(TrainingSetError, match="shared with the test set"):
        assemble_training_set([source], TEST_SET, SCOPE)


def test_duplicated_ids_are_an_error() -> None:
    first = _source([("x1", "Semente de braquiária", "1209", "u1")], "marketplace")
    second = _source([("x1", "Sal mineral 25 kg", "2309", "u2")], "synthetic")
    with pytest.raises(TrainingSetError, match="unique"):
        assemble_training_set([first, second], TEST_SET, SCOPE)
