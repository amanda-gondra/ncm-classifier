"""Training-loop checks on a tiny random BERT, on CPU, without downloads.

Skipped when the `train` extra (torch, transformers) is not installed, as in CI.
They check behaviour the Kaggle notebook relies on, not model quality.
"""

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from ncm_classifier.models.bertimbau import (  # noqa: E402
    FineTuneConfig,
    fine_tune,
    load_model,
    predict_proba,
    save_model,
    truncation_rate,
)

VOCAB = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "ureia", "saco", "kg", "arame", "grampo"]
CLASSES = ["3102", "7313"]
TEXTS = ["ureia saco", "ureia kg", "arame grampo", "grampo arame", "ureia", "grampo"]
LABELS = ["3102", "3102", "7313", "7313", "3102", "7313"]


@pytest.fixture(scope="module")
def tiny_checkpoint(tmp_path_factory: pytest.TempPathFactory) -> str:
    directory = tmp_path_factory.mktemp("tiny_bert")
    vocab_file = directory / "vocab.txt"
    vocab_file.write_text("\n".join(VOCAB) + "\n", encoding="utf-8")
    transformers.BertTokenizerFast(vocab_file=str(vocab_file)).save_pretrained(directory)
    config = transformers.BertConfig(
        vocab_size=len(VOCAB),
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
        max_position_embeddings=32,
    )
    transformers.BertModel(config).save_pretrained(directory)
    return str(directory)


def _config(checkpoint: str) -> FineTuneConfig:
    return FineTuneConfig(
        pretrained=checkpoint, max_length=16, batch_size=2, max_epochs=2, learning_rate=1e-3
    )


def test_fine_tune_returns_probabilities_after_every_epoch(tiny_checkpoint: str) -> None:
    result = fine_tune(TEXTS, LABELS, CLASSES, _config(tiny_checkpoint), eval_texts=TEXTS[:3])
    assert [log.epoch for log in result.history] == [1, 2]
    assert len(result.eval_proba_by_epoch) == 2
    for proba in result.eval_proba_by_epoch:
        assert proba.shape == (3, len(CLASSES))
        assert np.allclose(proba.sum(axis=1), 1.0)
    assert result.model.config.id2label == {0: "3102", 1: "7313"}


def test_stopping_early_reproduces_the_same_epoch_of_a_full_run(tiny_checkpoint: str) -> None:
    config = _config(tiny_checkpoint)
    full = fine_tune(TEXTS, LABELS, CLASSES, config, eval_texts=TEXTS)
    stopped = fine_tune(TEXTS, LABELS, CLASSES, config, stop_after_epoch=1)
    stopped_proba = predict_proba(stopped.model, stopped.tokenizer, TEXTS, config.max_length)
    assert len(stopped.history) == 1
    assert np.allclose(stopped_proba, full.eval_proba_by_epoch[0], atol=1e-6)


def test_saved_model_predicts_the_same(tiny_checkpoint: str, tmp_path: Path) -> None:
    config = _config(tiny_checkpoint)
    result = fine_tune(TEXTS, LABELS, CLASSES, config, stop_after_epoch=1)
    before = predict_proba(result.model, result.tokenizer, TEXTS, config.max_length)
    save_model(result, tmp_path / "model")
    model, tokenizer, classes = load_model(tmp_path / "model")
    assert classes == CLASSES
    assert np.allclose(predict_proba(model, tokenizer, TEXTS, config.max_length), before)


def test_truncation_rate(tiny_checkpoint: str) -> None:
    tokenizer = transformers.AutoTokenizer.from_pretrained(tiny_checkpoint)
    # [CLS] + 2 words + [SEP] = 4 tokens.
    assert truncation_rate(tokenizer, ["ureia saco", "ureia"], max_length=3) == 0.5


def test_invalid_stop_epoch_is_rejected(tiny_checkpoint: str) -> None:
    with pytest.raises(ValueError, match="stop_after_epoch"):
        fine_tune(TEXTS, LABELS, CLASSES, _config(tiny_checkpoint), stop_after_epoch=3)
