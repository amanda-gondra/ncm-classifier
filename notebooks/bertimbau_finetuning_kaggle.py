# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # NCM Classifier — fine-tuning do BERTimbau (etapa 5)
#
# Segunda abordagem do projeto, comparada diretamente com o baseline
# (TF-IDF + regressão logística). Tudo o que pode ser igual ao baseline é igual,
# e vem do mesmo código do repositório:
#
# | Item | Como é feito |
# |---|---|
# | Dados de treino | `train_v1.parquet` (900 linhas), conferido por SHA-256 |
# | Validação | as mesmas 5 dobras estratificadas do baseline (impressão digital conferida) |
# | Hiperparâmetros | maior macro F1 médio nas 5 dobras (épocas e modo de entrada) |
# | Calibração | escala de temperatura nas probabilidades fora da dobra |
# | Regra 31.05 | a mesma função, aplicada depois da calibração |
# | Revisão manual | limiar ajustado fora da dobra para 95% de acerto nos aceitos |
# | Métricas e intervalos | as mesmas funções, bootstrap de 1000 reamostragens, semente 0 |
#
# **Os testes congelados só são lidos na seção 12**, depois que o modelo, a
# temperatura e o limiar de revisão estão fixados.
#
# Antes de executar: *Settings → Accelerator → GPU T4 x2* (usa uma GPU),
# *Settings → Internet → On* e o dataset privado com `train_v1.parquet`
# adicionado em *Add Input*. Depois, *Run All*.

# %% [markdown]
# ## 1. Identificação do experimento
#
# Parâmetros do experimento. `REPO_COMMIT` fixa a versão exata do código e dos
# testes congelados usados nesta execução.

# %% tags=["parameters"]
EXPERIMENT = "bertimbau_v1"
REPO_URL = "https://github.com/amanda-gondra/ncm-classifier.git"
REPO_COMMIT = "REPLACE_WITH_COMMIT"
REPO_DIR = "/kaggle/working/ncm-classifier"
INPUT_ROOT = "/kaggle/input"
OUTPUT_DIR = "/kaggle/working/experiments/bertimbau"
TRAIN_FILE = "train_v1.parquet"
BASELINE_NAME = "baseline_v1"
TEST_FILES = ["data/labeled/test_v1.csv", "data/labeled/test_v2.csv"]

PRETRAINED = "neuralmind/bert-base-portuguese-cased"
PRETRAINED_REVISION = None  # None: resolved below to the current commit of the model
MAX_EPOCHS = 10
BATCH_SIZE = 16
GRADIENT_ACCUMULATION = 1
LEARNING_RATE = 3e-5
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
MAX_LENGTH = 128
MIXED_PRECISION = True
SEED = 0
REQUIRE_GPU = True

# %% [markdown]
# ## 2. Instalação e verificação das dependências
#
# O ambiente do Kaggle já tem PyTorch, Transformers, pandas e scikit-learn;
# nada é instalado. A célula só confere as versões mínimas do `pyproject.toml`
# e registra as versões usadas.

# %%
import importlib.metadata as metadata
import platform
import sys

from packaging.version import Version

MINIMUM_VERSIONS = {
    "torch": "2.3",
    "transformers": "4.44",
    "numpy": "1.26",
    "pandas": "2.2",
    "pyarrow": "15",
    "scikit-learn": "1.5",
    "scipy": "1.11",
}
if sys.version_info < (3, 11):
    raise RuntimeError(f"Python 3.11+ is required, found {platform.python_version()}")
library_versions = {"python": platform.python_version()}
for package, minimum in MINIMUM_VERSIONS.items():
    installed = metadata.version(package)
    if Version(installed) < Version(minimum):
        raise RuntimeError(f"{package} {installed} is older than {minimum}")
    library_versions[package] = installed
library_versions

# %% [markdown]
# ## 3. Configuração do ambiente e da GPU
#
# Clona o repositório público no commit fixado e usa o código de `src/`
# diretamente, sem instalar o pacote.

# %%
import subprocess
from pathlib import Path

import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if REQUIRE_GPU and device.type != "cuda":
    raise RuntimeError("No GPU found: enable Settings > Accelerator > GPU T4 x2 and restart.")
hardware = {"device": device.type, "cpu_threads": torch.get_num_threads()}
if device.type == "cuda":
    properties = torch.cuda.get_device_properties(device)
    hardware |= {"gpu": properties.name, "gpu_memory_gb": round(properties.total_memory / 1e9, 1)}

repo = Path(REPO_DIR)
if not repo.exists():
    subprocess.run(["git", "clone", "--quiet", REPO_URL, str(repo)], check=True)
subprocess.run(["git", "-C", str(repo), "checkout", "--quiet", REPO_COMMIT], check=True)
repo_head = subprocess.run(
    ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
).stdout.strip()
if not repo_head.startswith(REPO_COMMIT):
    raise RuntimeError(f"Repository is at {repo_head}, expected {REPO_COMMIT}")
sys.path.insert(0, str(repo / "src"))
hardware, repo_head

# %% [markdown]
# ## 4. Carregamento dos dados
#
# O treino vem do dataset privado do Kaggle. Os testes congelados e o relatório
# do baseline vêm do repositório, no commit fixado.

# %%
import json

import numpy as np
import pandas as pd

from ncm_classifier.evaluation.protocol import load_frozen_test

train_matches = sorted(Path(INPUT_ROOT).rglob(TRAIN_FILE))
if len(train_matches) != 1:
    raise FileNotFoundError(
        f"Expected exactly one {TRAIN_FILE} under {INPUT_ROOT}, found {train_matches}. "
        "Add the private dataset with Add Input."
    )
train_path = train_matches[0]
train = pd.read_parquet(train_path)
texts = train["text"].tolist()
labels = train["position"].to_numpy(dtype=str)
classes = np.unique(labels)

baseline_report = json.loads(
    (repo / "reports" / f"{BASELINE_NAME}.json").read_text(encoding="utf-8")
)
test_paths = [repo / name for name in TEST_FILES]
print(f"train: {len(train)} rows, {len(classes)} positions ({train_path})")
train["source_type"].value_counts()

# %% [markdown]
# ## 5. Verificação da integridade dos conjuntos
#
# A execução para se qualquer conferência falhar:
#
# * o arquivo de treino é byte a byte o mesmo usado pelo baseline;
# * as dobras são as mesmas do baseline (impressão digital de cada par linha-dobra);
# * as posições são as 37 do escopo;
# * cada teste confere com o checksum de quando foi congelado e com o do baseline;
# * nenhum texto de teste é quase duplicado de um texto de treino.
#
# Os testes são abertos aqui só para essas conferências: os textos não entram
# em nenhuma etapa de treino, escolha ou calibração.

# %%
from ncm_classifier.data.dedup import near_duplicate_mask
from ncm_classifier.data.scope import load_scope
from ncm_classifier.evaluation.protocol import (
    FOLDS,
    fold_ids,
    folds_fingerprint,
    sha256_bytes,
    sha256_text,
)

train_sha256 = sha256_bytes(train_path)
if train_sha256 != baseline_report["train_sha256"]:
    raise RuntimeError("Training file differs from the one used by the baseline")

folds_sha256 = folds_fingerprint(train["example_id"].tolist(), labels, SEED)
if folds_sha256 != baseline_report["protocol"]["folds_sha256"]:
    raise RuntimeError("Cross-validation folds differ from the baseline folds")

scope_positions = load_scope(repo / "configs" / "scope.json").positions
if classes.tolist() != scope_positions:
    raise RuntimeError("Training positions differ from the project scope")

baseline_tests = {test["file"]: test for test in baseline_report["tests"]}
tests = {}
for path in test_paths:
    test = load_frozen_test(path)  # also checks the frozen checksum
    if sha256_text(path) != baseline_tests[path.name]["sha256"]:
        raise RuntimeError(f"{path.name} differs from the file evaluated by the baseline")
    unknown = sorted(set(test["position"]) - set(classes))
    if unknown:
        raise RuntimeError(f"{path.name} has positions outside the model classes: {unknown}")
    if any(near_duplicate_mask(test["text"].tolist(), texts)):
        raise RuntimeError(f"{path.name} has near-duplicates of training texts")
    tests[path.name] = test

data_version = {
    "repo_commit": repo_head,
    "train_file": TRAIN_FILE,
    "train_sha256": train_sha256,
    "train_rows": len(train),
    "folds": FOLDS,
    "folds_sha256": folds_sha256,
    "tests": {name: sha256_text(repo / f) for name, f in zip(tests, TEST_FILES, strict=True)},
}
print("All integrity checks passed")
data_version

# %% [markdown]
# ## 6. Preparação do tokenizer
#
# O commit do modelo pré-treinado é fixado, para a execução ser reproduzível
# mesmo que o modelo seja atualizado no Hugging Face. Modelos públicos não
# precisam de autenticação.
#
# Dois modos de entrada são comparados na validação cruzada:
#
# * `raw`: texto original (só forma Unicode NFKC e espaços);
# * `normalized`: o mesmo `normalize_text` do baseline, que remove acentos e
#   maiúsculas — informação que o BERTimbau *cased* sabe usar.

# %%
from transformers import AutoTokenizer

from ncm_classifier.models.bertimbau import truncation_rate
from ncm_classifier.models.transformer_support import INPUT_MODES, prepare_input

if PRETRAINED_REVISION is None and not Path(PRETRAINED).exists():
    from huggingface_hub import HfApi

    PRETRAINED_REVISION = HfApi().model_info(PRETRAINED).sha
tokenizer = AutoTokenizer.from_pretrained(PRETRAINED, revision=PRETRAINED_REVISION)

token_stats = {}
for mode in INPUT_MODES:
    mode_texts = prepare_input(texts, mode)
    lengths = [len(ids) for ids in tokenizer(mode_texts)["input_ids"]]
    token_stats[mode] = {
        "p50": int(np.percentile(lengths, 50)),
        "p99": int(np.percentile(lengths, 99)),
        "max": int(max(lengths)),
        "truncated_share": truncation_rate(tokenizer, mode_texts, MAX_LENGTH),
    }
print("pretrained revision:", PRETRAINED_REVISION)
pd.DataFrame(token_stats).T

# %% [markdown]
# ## 7. Preparação dos datasets
#
# Cada linha do treino é validada em exatamente uma dobra, a mesma do baseline.

# %%
folds = fold_ids(labels, SEED)
inputs_by_mode = {mode: prepare_input(texts, mode) for mode in INPUT_MODES}
pd.crosstab(pd.Series(labels, name="position"), pd.Series(folds, name="fold")).describe().loc[
    ["min", "max"]
]

# %% [markdown]
# ## 8. Configuração do modelo
#
# BERTimbau Base (cerca de 110M de parâmetros). A variante Large (cerca de 335M)
# não é usada: com 900 exemplos ela é menos estável no fine-tuning, precisa de
# cerca de três vezes mais memória e tempo e seria mais lenta para servir em CPU
# atrás da API.
#
# * perda de entropia cruzada com pesos `balanced` por classe, como no baseline;
# * AdamW, warmup linear de 10% e decaimento linear até o fim de `MAX_EPOCHS`;
# * precisão mista (float16) na GPU e corte de gradiente em 1,0.
#
# O cronograma de learning rate sempre cobre `MAX_EPOCHS`, então parar na
# época *k* é igual à época *k* de um treino completo.

# %%
from ncm_classifier.models.bertimbau import FineTuneConfig

config = FineTuneConfig(
    pretrained=PRETRAINED,
    revision=PRETRAINED_REVISION,
    max_length=MAX_LENGTH,
    batch_size=BATCH_SIZE,
    gradient_accumulation=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    warmup_ratio=WARMUP_RATIO,
    max_epochs=MAX_EPOCHS,
    mixed_precision=MIXED_PRECISION,
    seed=SEED,
)
config.to_dict()

# %% [markdown]
# ## 9. Fine-tuning na validação cruzada
#
# Para cada modo de entrada e cada dobra, um modelo é treinado do zero em 4/5
# do treino e avaliado na dobra restante ao fim de cada época. São
# 2 modos × 5 dobras = 10 treinos de até `MAX_EPOCHS` épocas.
#
# O macro F1 de cada dobra é calculado como o `scoring="f1_macro"` usado pelo
# baseline na escolha do `C`.

# %%
import gc
import time

from sklearn.metrics import f1_score

from ncm_classifier.models.bertimbau import fine_tune

cv_records = []
out_of_fold = {}
peak_memory_gb = 0.0
cv_started = time.perf_counter()
for mode in INPUT_MODES:
    mode_inputs = inputs_by_mode[mode]
    for fold in range(FOLDS):
        train_rows = np.flatnonzero(folds != fold)
        valid_rows = np.flatnonzero(folds == fold)
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        result = fine_tune(
            [mode_inputs[i] for i in train_rows],
            labels[train_rows],
            classes,
            config,
            eval_texts=[mode_inputs[i] for i in valid_rows],
            device=device,
        )
        if device.type == "cuda":
            peak_memory_gb = max(peak_memory_gb, torch.cuda.max_memory_allocated(device) / 1e9)
        for log, proba in zip(result.history, result.eval_proba_by_epoch, strict=True):
            key = (mode, log.epoch)
            out_of_fold.setdefault(key, np.zeros((len(labels), len(classes))))
            out_of_fold[key][valid_rows] = proba
            predicted = classes[proba.argmax(axis=1)]
            cv_records.append(
                {
                    "mode": mode,
                    "fold": fold,
                    "epoch": log.epoch,
                    "macro_f1": f1_score(labels[valid_rows], predicted, average="macro"),
                    "train_loss": log.train_loss,
                    "seconds": log.seconds,
                }
            )
        fold_best = max(record["macro_f1"] for record in cv_records[-MAX_EPOCHS:])
        print(f"{mode} fold {fold}: best epoch macro F1 {fold_best:.4f}")
        del result
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()
cv_seconds = time.perf_counter() - cv_started
cv_scores = pd.DataFrame(cv_records)
print(f"cross-validation: {cv_seconds / 60:.1f} min, peak GPU memory {peak_memory_gb:.2f} GB")

# %% [markdown]
# ## 10. Seleção do melhor checkpoint
#
# A combinação (modo, época) com maior macro F1 médio nas 5 dobras é escolhida;
# em caso de empate, vence o modo `raw` e o menor número de épocas. Depois, o
# modelo final é treinado com os 900 exemplos e parado nessa época.
# Nenhum teste é usado aqui.

# %%
from ncm_classifier.models.bertimbau import save_model
from ncm_classifier.models.transformer_support import select_best

cv_summary = (
    cv_scores.groupby(["mode", "epoch"])["macro_f1"].agg(["mean", "std"]).round(4).reset_index()
)
scores = {
    (mode, epoch): cv_scores.query("mode == @mode and epoch == @epoch")["macro_f1"].tolist()
    for mode in INPUT_MODES
    for epoch in range(1, MAX_EPOCHS + 1)
}
best_mode, best_epoch = select_best(scores)
best_cv_f1 = float(np.mean(scores[(best_mode, best_epoch)]))
print(f"selected: mode={best_mode}, epochs={best_epoch}, CV macro F1={best_cv_f1:.4f}")

final_started = time.perf_counter()
final = fine_tune(
    inputs_by_mode[best_mode],
    labels,
    classes,
    config,
    stop_after_epoch=best_epoch,
    device=device,
)
final_seconds = time.perf_counter() - final_started
output = Path(OUTPUT_DIR)
save_model(final, output / "model")
cv_summary.pivot(index="epoch", columns="mode", values="mean")

# %% [markdown]
# ## 11. Calibração
#
# As probabilidades fora da dobra do modo e da época escolhidos passam pela
# mesma função do baseline (`calibrate_out_of_fold`):
#
# 1. a temperatura *T* minimiza a log-verossimilhança negativa dessas
#    probabilidades (`softmax(log p / T)`; não muda o ranking);
# 2. a regra 31.05 é aplicada depois da calibração, sobre o texto original;
# 3. o limiar de revisão manual é a menor confiança final para a qual os
#    aceitos acertam pelo menos 95% fora da dobra.
#
# *T* e o limiar ficam fixos e são aplicados sem novo ajuste nos testes.
# Probabilidade bruta (saída do softmax) e probabilidade calibrada são
# registradas separadamente.

# %%
from ncm_classifier.evaluation.report import calibrate_out_of_fold

calibration = calibrate_out_of_fold(
    texts, labels, out_of_fold[(best_mode, best_epoch)], classes, seed=SEED
)
calibration.summary

# %% [markdown]
# ## 12. Avaliação nos dois testes congelados
#
# Primeira e única leitura dos testes para predição. A avaliação usa
# `evaluate_split`, a mesma função do baseline: métricas brutas, calibradas e
# calibradas + regra 31.05, com intervalos de confiança, precisão, recall,
# métricas por capítulo, matriz de confusão e taxa de revisão manual.

# %%
from ncm_classifier.evaluation.report import evaluate_split
from ncm_classifier.models.bertimbau import predict_proba

predictions_dir = output / "predictions"
predictions_dir.mkdir(parents=True, exist_ok=True)
test_reports, evaluations = [], {}
for name, test in tests.items():
    raw_proba = predict_proba(
        final.model,
        final.tokenizer,
        prepare_input(test["text"].tolist(), best_mode),
        MAX_LENGTH,
        mixed_precision=MIXED_PRECISION,
    )
    evaluation = evaluate_split(
        name,
        test["id"].tolist(),
        test["text"].tolist(),
        test["position"].tolist(),
        raw_proba,
        classes,
        calibration,
        seed=SEED,
    )
    stem = f"{EXPERIMENT}__{Path(name).stem}"
    evaluation.predictions.to_csv(predictions_dir / f"{stem}.csv", index=False)
    evaluation.confusion.to_csv(predictions_dir / f"{stem}_confusion.csv")
    evaluations[name] = evaluation
    test_reports.append({"file": name, "sha256": data_version["tests"][name], **evaluation.summary})

# %% [markdown]
# ## 13. Comparação inicial com o baseline
#
# Visão rápida, lado a lado, com os números já gravados no relatório do
# baseline. A comparação completa (bootstrap pareado, análise de erros e custo
# operacional) é a etapa 6.

# %%


def headline(report: dict) -> dict[str, float]:
    final_metrics = report["metrics_calibrated_with_rules"]
    review = report["review"]
    return {
        "top1": final_metrics["top1"]["value"],
        "top3": final_metrics["top3"]["value"],
        "macro_f1": final_metrics["macro_f1"]["value"],
        "macro_precision": final_metrics["macro_precision"]["value"],
        "macro_recall": final_metrics["macro_recall"]["value"],
        "ece": final_metrics["ece"],
        "review_rate": review["review_rate"]["value"],
        "accepted_top1": (review["accepted_top1"] or {}).get("value"),
    }


rows = []
for report in test_reports:
    rows.append(
        {"test": report["file"], "model": "baseline", **headline(baseline_tests[report["file"]])}
    )
    rows.append({"test": report["file"], "model": "bertimbau", **headline(report)})
comparison = pd.DataFrame(rows).set_index(["test", "model"])

agreement = {}
for name, evaluation in evaluations.items():
    baseline_predictions = pd.read_csv(
        repo / "reports" / "predictions" / f"{BASELINE_NAME}__{Path(name).stem}.csv", dtype=str
    )
    merged = evaluation.predictions.merge(
        baseline_predictions[["id", "hit_top1"]], on="id", suffixes=("", "_baseline")
    )
    if len(merged) != len(evaluation.predictions):
        raise RuntimeError(f"{name}: prediction ids differ from the baseline ones")
    bert_hit = merged["hit_top1"].astype(bool)
    base_hit = merged["hit_top1_baseline"] == "True"
    agreement[name] = {
        "both_right": int((bert_hit & base_hit).sum()),
        "only_baseline": int((~bert_hit & base_hit).sum()),
        "only_bertimbau": int((bert_hit & ~base_hit).sum()),
        "both_wrong": int((~bert_hit & ~base_hit).sum()),
    }
display(comparison)  # noqa: F821 - provided by IPython
pd.DataFrame(agreement).T

# %% [markdown]
# Tempo de inferência, um texto por vez, na GPU e na CPU do Kaggle. É uma
# referência: a etapa 6 mede os dois modelos no mesmo computador.

# %%


def latency_ms(model, sample: list[str], repeats: int) -> float:
    predict_proba(model, final.tokenizer, sample[:2], MAX_LENGTH, batch_size=1)  # warm-up
    started = time.perf_counter()
    for text in sample[:repeats]:
        predict_proba(model, final.tokenizer, [text], MAX_LENGTH, batch_size=1)
    return 1000 * (time.perf_counter() - started) / min(repeats, len(sample))


sample = prepare_input(next(iter(tests.values()))["text"].tolist(), best_mode)
inference = {"model_size_mb": round(sum(p.numel() for p in final.model.parameters()) * 4 / 1e6)}
if device.type == "cuda":
    inference["gpu_ms_per_text"] = round(latency_ms(final.model, sample, 100), 2)
cpu_model = final.model.to("cpu")
inference["cpu_ms_per_text"] = round(latency_ms(cpu_model, sample, 30), 2)
inference

# %% [markdown]
# ## 14. Exportação dos resultados e artefatos
#
# Tudo vai para `OUTPUT_DIR` e é compactado em dois arquivos para download na
# aba *Output*:
#
# * `bertimbau_v1_results.zip`: configuração, calibração, métricas, predições,
#   erros, escores da validação cruzada e versão dos dados (vai para o Git);
# * `bertimbau_v1_model.zip`: pesos (safetensors), tokenizer e configuração do
#   modelo (vai para o Hugging Face na etapa 7, não para o Git).
#
# Mantenha este notebook **privado**: as saídas contêm os textos dos erros de teste.

# %%
import shutil

selection = {
    "input_modes": list(INPUT_MODES),
    "max_epochs": MAX_EPOCHS,
    "best_mode": best_mode,
    "best_epoch": best_epoch,
    "cv_macro_f1": round(best_cv_f1, 4),
    "temperature": calibration.summary["temperature"],
}
report = {
    "model": "bertimbau_base_cased_finetuned",
    "train_file": TRAIN_FILE,
    "train_sha256": train_sha256,
    "train_rows": len(train),
    "train_rows_by_source": train["source_type"].value_counts().sort_index().to_dict(),
    "protocol": {"folds": FOLDS, "folds_sha256": folds_sha256},
    "selection": selection,
    "rule_31_05_out_of_fold": calibration.summary["rule_31_05"],
    "review_out_of_fold": calibration.summary["review"],
    "tests": test_reports,
    "seed": SEED,
}
experiment_config = {
    "experiment": EXPERIMENT,
    "pretrained": PRETRAINED,
    "pretrained_revision": PRETRAINED_REVISION,
    "fine_tune": config.to_dict(),
    "selection": selection,
    "token_lengths": token_stats,
    "library_versions": library_versions,
    "hardware": hardware,
    "timing_seconds": {
        "cross_validation": round(cv_seconds),
        "final_training": round(final_seconds),
    },
    "peak_gpu_memory_gb": round(peak_memory_gb, 2),
    "inference": inference,
}
calibration_record = {
    "temperature": calibration.temperature,
    "review_threshold": calibration.review.value,
    "review_target_accuracy": calibration.review.target_accuracy,
    "review_target_reached": calibration.review.target_reached,
    "fitted_on": "out-of-fold predictions of the training set",
}
errors = pd.DataFrame(
    [
        {"test": r["file"], **e, "top3": " ".join(e["top3"])}
        for r in test_reports
        for e in r["errors"]
    ]
)


def write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


write_json(output / "config.json", experiment_config)
write_json(output / "calibration.json", calibration_record)
write_json(output / "data_version.json", data_version)
write_json(output / "metrics" / f"{EXPERIMENT}.json", report)
(output / "reports").mkdir(exist_ok=True)
errors.to_csv(output / "reports" / f"{EXPERIMENT}_errors.csv", index=False)
cv_scores.to_csv(output / "reports" / "cv_scores.csv", index=False)
np.save(output / "reports" / "out_of_fold_proba.npy", out_of_fold[(best_mode, best_epoch)])

results_dir = output.parent / f"{EXPERIMENT}_results_staging"
shutil.copytree(output, results_dir, ignore=shutil.ignore_patterns("model"), dirs_exist_ok=True)
shutil.make_archive(str(output.parent / f"{EXPERIMENT}_results"), "zip", results_dir)
shutil.make_archive(str(output.parent / f"{EXPERIMENT}_model"), "zip", output / "model")
shutil.rmtree(results_dir)
sorted(str(p.relative_to(output.parent)) for p in output.parent.glob("*.zip"))
