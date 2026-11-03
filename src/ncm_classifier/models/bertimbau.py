"""Fine-tuning of BERTimbau for the NCM position, sized for one free GPU.

Model: neuralmind/bert-base-portuguese-cased (BERTimbau Base, about 110M
parameters), pre-trained on Brazilian Portuguese. The Large variant (about 335M)
is not used: with ~900 training rows it is less stable to fine-tune, needs about
three times the memory and time, and would be slower to serve on a CPU behind
the API.

The training loop is plain PyTorch instead of the `Trainer` class because:
    * the loss is weighted by class, as in the baseline's logistic regression;
    * probabilities on a validation fold are needed after every epoch, to pick
      the number of epochs by cross-validation.

The learning-rate schedule always spans `config.max_epochs`. A run stopped after
epoch k is therefore identical to the k-th epoch of a full run, which is what
lets the final model reproduce the epoch chosen on the folds.

Requires the `train` extra (torch, transformers).
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
import torch
from numpy.typing import NDArray
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    get_linear_schedule_with_warmup,
)

from ncm_classifier.models.transformer_support import balanced_class_weights

PRETRAINED: Final = "neuralmind/bert-base-portuguese-cased"
# Biases and LayerNorm weights are not decayed, as in the original BERT recipe.
_NO_DECAY: Final = ("bias", "LayerNorm.weight")


@dataclass(frozen=True)
class FineTuneConfig:
    pretrained: str = PRETRAINED
    revision: str | None = None
    max_length: int = 128
    batch_size: int = 16
    gradient_accumulation: int = 1
    learning_rate: float = 3e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_epochs: int = 10
    max_grad_norm: float = 1.0
    mixed_precision: bool = True
    seed: int = 0

    def __post_init__(self) -> None:
        if self.max_epochs < 1 or self.batch_size < 1 or self.gradient_accumulation < 1:
            raise ValueError("max_epochs, batch_size and gradient_accumulation must be >= 1")
        if not 0.0 <= self.warmup_ratio < 1.0:
            raise ValueError("warmup_ratio must be in [0, 1)")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EpochLog:
    epoch: int
    train_loss: float
    seconds: float


@dataclass
class FineTuneResult:
    model: PreTrainedModel
    tokenizer: PreTrainedTokenizerBase
    history: list[EpochLog] = field(default_factory=list)
    eval_proba_by_epoch: list[NDArray[np.float64]] = field(default_factory=list)


class _EncodedTexts(Dataset):
    def __init__(self, encodings: dict[str, list], targets: Sequence[int] | None = None) -> None:
        self._encodings = encodings
        self._targets = targets

    def __len__(self) -> int:
        return len(self._encodings["input_ids"])

    def __getitem__(self, index: int) -> dict[str, object]:
        item = {key: values[index] for key, values in self._encodings.items()}
        if self._targets is not None:
            item["labels"] = self._targets[index]
        return item


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def default_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _encode(
    tokenizer: PreTrainedTokenizerBase, texts: Sequence[str], max_length: int
) -> dict[str, list]:
    return dict(tokenizer(list(texts), truncation=True, max_length=max_length))


def truncation_rate(
    tokenizer: PreTrainedTokenizerBase, texts: Sequence[str], max_length: int
) -> float:
    """Share of texts longer than max_length tokens (special tokens included)."""
    lengths = [len(ids) for ids in tokenizer(list(texts), truncation=False)["input_ids"]]
    return float(np.mean([length > max_length for length in lengths]))


def predict_proba(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    texts: Sequence[str],
    max_length: int,
    batch_size: int = 64,
    mixed_precision: bool = True,
) -> NDArray[np.float64]:
    """Class probabilities (softmax of the logits, in float64), one row per text."""
    device = next(model.parameters()).device
    loader = DataLoader(
        _EncodedTexts(_encode(tokenizer, texts, max_length)),
        batch_size=batch_size,
        shuffle=False,
        collate_fn=DataCollatorWithPadding(tokenizer),
    )
    use_amp = mixed_precision and device.type == "cuda"
    chunks = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            inputs = {key: value.to(device) for key, value in batch.items()}
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(**inputs).logits
            chunks.append(torch.softmax(logits.double(), dim=-1).cpu().numpy())
    return np.concatenate(chunks)


def _parameter_groups(model: PreTrainedModel, weight_decay: float) -> list[dict[str, object]]:
    decay, no_decay = [], []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            (no_decay if any(part in name for part in _NO_DECAY) else decay).append(parameter)
    return [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


def fine_tune(
    texts: Sequence[str],
    labels: Sequence[str],
    classes: Sequence[str],
    config: FineTuneConfig,
    *,
    eval_texts: Sequence[str] | None = None,
    stop_after_epoch: int | None = None,
    device: torch.device | None = None,
) -> FineTuneResult:
    """Fine-tune from the pre-trained checkpoint.

    eval_texts: if given, their probabilities are computed after every epoch.
    stop_after_epoch: stop early, keeping the schedule of a full run.
    """
    if stop_after_epoch is not None and not 1 <= stop_after_epoch <= config.max_epochs:
        raise ValueError("stop_after_epoch must be between 1 and config.max_epochs")
    names = [str(label) for label in classes]
    label_to_id = {label: i for i, label in enumerate(names)}
    unknown = sorted(set(labels) - set(names))
    if unknown:
        raise ValueError(f"labels missing from classes: {unknown}")

    device = device or default_device()
    set_seed(config.seed)
    tokenizer = AutoTokenizer.from_pretrained(config.pretrained, revision=config.revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.pretrained,
        revision=config.revision,
        num_labels=len(names),
        id2label=dict(enumerate(names)),
        label2id=label_to_id,
    ).to(device)

    loader = DataLoader(
        _EncodedTexts(
            _encode(tokenizer, texts, config.max_length), [label_to_id[y] for y in labels]
        ),
        batch_size=config.batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(config.seed),
        collate_fn=DataCollatorWithPadding(tokenizer),
    )
    updates_per_epoch = math.ceil(len(loader) / config.gradient_accumulation)
    total_updates = updates_per_epoch * config.max_epochs
    optimizer = torch.optim.AdamW(
        _parameter_groups(model, config.weight_decay), lr=config.learning_rate
    )
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(config.warmup_ratio * total_updates), total_updates
    )
    weights = torch.tensor(balanced_class_weights(labels, names), dtype=torch.float32)
    loss_function = torch.nn.CrossEntropyLoss(weight=weights.to(device))
    use_amp = config.mixed_precision and device.type == "cuda"
    scaler = torch.amp.GradScaler(device.type, enabled=use_amp)

    result = FineTuneResult(model=model, tokenizer=tokenizer)
    for epoch in range(1, (stop_after_epoch or config.max_epochs) + 1):
        model.train()
        started = time.perf_counter()
        running_loss = 0.0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, start=1):
            inputs = {key: value.to(device) for key, value in batch.items()}
            targets = inputs.pop("labels")
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(**inputs).logits
            loss = loss_function(logits.float(), targets)
            scaler.scale(loss / config.gradient_accumulation).backward()
            running_loss += loss.item()
            if step % config.gradient_accumulation == 0 or step == len(loader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
        result.history.append(
            EpochLog(epoch, running_loss / len(loader), time.perf_counter() - started)
        )
        if eval_texts is not None:
            result.eval_proba_by_epoch.append(
                predict_proba(
                    model,
                    tokenizer,
                    eval_texts,
                    config.max_length,
                    mixed_precision=config.mixed_precision,
                )
            )
    return result


def save_model(result: FineTuneResult, directory: Path) -> None:
    """Save weights (safetensors), configuration with the class names, and tokenizer."""
    directory.mkdir(parents=True, exist_ok=True)
    result.model.save_pretrained(directory, safe_serialization=True)
    result.tokenizer.save_pretrained(directory)


def load_model(
    directory: Path, device: torch.device | None = None
) -> tuple[PreTrainedModel, PreTrainedTokenizerBase, list[str]]:
    """Load a saved model; the class names come from its configuration."""
    model = AutoModelForSequenceClassification.from_pretrained(directory)
    model.to(device or default_device())
    tokenizer = AutoTokenizer.from_pretrained(directory)
    classes = [model.config.id2label[i] for i in range(model.config.num_labels)]
    return model, tokenizer, classes
