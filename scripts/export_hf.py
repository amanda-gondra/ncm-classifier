"""Build the folders published on the Hugging Face Hub, and check them before upload.

Usage:
    python scripts/export_hf.py --owner <hugging-face-user>

Writes dist/huggingface/<repo>/ for three repositories:

    ncm-classifier            the approved model (baseline, skops format)
    ncm-classifier-bertimbau  the BERTimbau experiment, documented, not served
    ncm-classifier-dataset    the redistributable part of the training data

Nothing is uploaded here (see scripts/publish_hf.py). Every number in the cards
is rendered from the experiment reports, never typed by hand. Test texts, test
ids and per-row errors are never copied: only aggregate metrics are published.

Each folder is verified after it is built:
    * the skops model gives the same probabilities as the trained joblib model
      and the same top-1 as the recorded test predictions;
    * the BERTimbau copy gives the same raw top-1 as the Kaggle predictions;
    * the dataset has only official and synthetic rows and no test text.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
from datetime import date
from pathlib import Path
from string import Template
from typing import Final

import joblib
import numpy as np
import pandas as pd
import skops.io as sio

from ncm_classifier.data.dedup import near_duplicate_mask
from ncm_classifier.data.scope import load_scope
from ncm_classifier.evaluation.protocol import load_frozen_test, sha256_bytes
from ncm_classifier.inference.predictor import CALIBRATION_FILE, MODEL_FILE, NcmPredictor
from ncm_classifier.models.calibration import apply_temperature
from ncm_classifier.rules.small_package import apply_small_package_rule

logger = logging.getLogger(__name__)

VERSION: Final = "v0.1.0"
GITHUB: Final = "https://github.com/amanda-gondra/ncm-classifier"
TEMPLATES: Final = Path("publishing/templates")
TESTS: Final = (Path("data/labeled/test_v1.csv"), Path("data/labeled/test_v2.csv"))
PUBLIC_SOURCES: Final = ("ncm_official", "synthetic")
# Only aggregates leave the project: no test texts, ids or per-row errors.
PUBLIC_TEST_KEYS: Final = (
    "file",
    "sha256",
    "metrics_raw",
    "metrics_calibrated",
    "metrics_calibrated_with_rules",
    "review",
    "by_chapter",
    "f1_by_position",
)


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_json(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render(template: str, destination: Path, **values: str) -> None:
    text = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
    destination.write_text(text, encoding="utf-8")


def _manifest(folder: Path, provenance: dict[str, object]) -> None:
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.name != "manifest.json")
    _write_json(
        folder / "manifest.json",
        {
            **provenance,
            "files": {
                p.relative_to(folder).as_posix(): {
                    "sha256": sha256_bytes(p),
                    "bytes": p.stat().st_size,
                }
                for p in files
            },
        },
    )


def public_metrics(report: dict) -> dict[str, object]:
    keys = ("model", "train_rows", "train_rows_by_source", "protocol", "selection")
    return {
        **{key: report[key] for key in keys},
        "rule_31_05_out_of_fold": report["rule_31_05_out_of_fold"],
        "review_out_of_fold": report["review_out_of_fold"],
        "tests": [{key: test[key] for key in PUBLIC_TEST_KEYS} for test in report["tests"]],
    }


def _fmt(interval: dict) -> str:
    return f"{interval['value']:.4f} [{interval['low']:.4f}–{interval['high']:.4f}]"


def metrics_table(report: dict) -> str:
    rows = [
        ("top-1", "top1"),
        ("top-3", "top3"),
        ("macro F1", "macro_f1"),
        ("macro precisão", "macro_precision"),
        ("macro recall", "macro_recall"),
    ]
    tests = report["tests"]
    header = "| Métrica | " + " | ".join(t["file"].removesuffix(".csv") for t in tests) + " |"
    lines = [header, "|---|" + "---|" * len(tests)]
    for label, key in rows:
        values = [_fmt(t["metrics_calibrated_with_rules"][key]) for t in tests]
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines.append(
        "| ECE bruto → calibrado | "
        + " | ".join(
            f"{t['metrics_raw']['ece']:.4f} → {t['metrics_calibrated_with_rules']['ece']:.4f}"
            for t in tests
        )
        + " |"
    )
    lines.append(
        "| Enviado para revisão | "
        + " | ".join(_fmt(t["review"]["review_rate"]) for t in tests)
        + " |"
    )
    lines.append(
        "| top-1 dos aceitos | "
        + " | ".join(
            _fmt(t["review"]["accepted_top1"]) if t["review"]["accepted_top1"] else "—"
            for t in tests
        )
        + " |"
    )
    rows_line = " | ".join(str(t["metrics_raw"]["rows"]) for t in tests)
    lines.append(f"| Linhas | {rows_line} |")
    return "\n".join(lines)


def chapter_table(report: dict) -> str:
    tests = report["tests"]
    chapters = sorted({c for t in tests for c in t["by_chapter"]})
    names = [t["file"].removesuffix(".csv") for t in tests]
    lines = [
        "| Capítulo | " + " | ".join(f"{n}: linhas / posição / capítulo" for n in names) + " |",
        "|---|" + "---|" * len(tests),
    ]
    for chapter in chapters:
        cells = []
        for test in tests:
            item = test["by_chapter"].get(chapter)
            if item is None:
                cells.append("—")
                continue
            accuracies = f"{item['position_accuracy']:.3f} / {item['chapter_accuracy']:.3f}"
            cells.append(f"{item['rows']} / {accuracies}")
        lines.append(f"| {chapter} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def scope_table() -> str:
    scope = load_scope(Path("configs/scope.json"))
    raw = json.loads(Path("configs/scope.json").read_text(encoding="utf-8"))
    lines = ["| Grupo | Posições |", "|---|---|"]
    for group in raw["groups"].values():
        positions = ", ".join(f"{p[:2]}.{p[2:]}" for p in group["positions"])
        lines.append(f"| {group['label']} | {positions} |")
    lines.append(f"\n{len(scope.positions)} posições no total.")
    return "\n".join(lines)


def distribution_table(frame: pd.DataFrame) -> str:
    counts = frame.groupby([frame["position"].str[:2], "source_type"]).size().unstack(fill_value=0)
    counts["total"] = counts.sum(axis=1)
    columns = counts.columns.tolist()
    lines = ["| Capítulo | " + " | ".join(columns) + " |", "|---|" + "---|" * len(columns)]
    for chapter, row in counts.iterrows():
        lines.append(f"| {chapter} | " + " | ".join(str(int(row[c])) for c in columns) + " |")
    total = counts.sum()
    lines.append("| **total** | " + " | ".join(f"**{int(total[c])}**" for c in columns) + " |")
    return "\n".join(lines)


def build_model(out: Path, owner: str, provenance: dict) -> None:
    trained = joblib.load("models/baseline_v1.joblib")
    report = json.loads(Path("reports/baseline_v1.json").read_text(encoding="utf-8"))
    folder = out / "ncm-classifier"
    folder.mkdir(parents=True)

    sio.dump(trained["pipeline"], folder / MODEL_FILE)
    review = report["review_out_of_fold"]
    _write_json(
        folder / CALIBRATION_FILE,
        {
            "method": "temperature scaling: softmax(log(p) / T)",
            "temperature": trained["temperature"],
            "review_threshold": trained["review_threshold"],
            "review_rule": "needs_review when the final top-1 probability < review_threshold",
            "review_target_accuracy": review["target_accuracy"],
            "review_target_reached": review["target_reached"],
            "fitted_on": "out-of-fold predictions of the training set (5 stratified folds)",
            "applied_before": "31.05 small-package rule",
        },
    )
    _write_json(
        folder / "preprocessing/configuration.json",
        {
            "normalization": "ncm_classifier.text.normalize.normalize_text",
            "applied_by": "both TF-IDF vectorizers of the pipeline (preprocessor)",
            "steps": [
                "Unicode NFKC, lowercase, accents removed",
                "fertilizer formulas standardized (NPK 20 05 20 -> npk 20-05-20)",
                "decimal commas, units and abbreviations standardized",
                "punctuation and extra spaces removed",
            ],
            "rule_31_05": {
                "module": "ncm_classifier.rules.small_package",
                "applied_after": "calibration",
                "limit_kg": 10.0,
                "target": "3105",
            },
            "package": f"ncm-classifier @ git+{GITHUB}@{VERSION}",
        },
    )
    _write_json(folder / "metrics/evaluation.json", public_metrics(report))
    (folder / "inference").mkdir()
    shutil.copy(TEMPLATES / "predict.py", folder / "inference/predict.py")
    (folder / "requirements.txt").write_text(
        f"ncm-classifier @ git+{GITHUB}@{VERSION}\n"
        f"scikit-learn=={provenance['scikit_learn']}\n"
        f"skops=={provenance['skops']}\n"
        "huggingface_hub>=0.34\n",
        encoding="utf-8",
    )
    selection = report["selection"]
    _render(
        "model_card.md",
        folder / "README.md",
        repo_id=f"{owner}/ncm-classifier",
        dataset_repo=f"{owner}/ncm-classifier-dataset",
        bertimbau_repo=f"{owner}/ncm-classifier-bertimbau",
        version=VERSION,
        date=provenance["date"],
        commit=provenance["code_commit"],
        github=GITHUB,
        scope_table=scope_table(),
        train_rows=str(report["train_rows"]),
        train_sources=", ".join(f"{k}: {v}" for k, v in report["train_rows_by_source"].items()),
        train_sha=report["train_sha256"],
        folds_sha=report["protocol"]["folds_sha256"],
        best_c=str(selection["best_C"]),
        cv_f1=f"{selection['cv_macro_f1']:.4f}",
        temperature=f"{trained['temperature']:.4f}",
        threshold=f"{trained['review_threshold']:.4f}",
        oof_review=_fmt(review["review_rate"]),
        oof_accepted=_fmt(review["accepted_top1"]),
        metrics_table=metrics_table(report),
        chapter_table=chapter_table(report),
        sklearn=provenance["scikit_learn"],
    )
    _manifest(
        folder, {**provenance, "model": "baseline_v1", "train_sha256": report["train_sha256"]}
    )
    _verify_model(folder, trained)


def _verify_model(folder: Path, trained: dict) -> None:
    predictor = NcmPredictor.from_directory(folder)
    for test_path in TESTS:
        test = load_frozen_test(test_path)
        texts = test["text"].tolist()
        calibrated = apply_temperature(
            trained["pipeline"].predict_proba(texts), trained["temperature"]
        )
        expected, _ = apply_small_package_rule(texts, calibrated, predictor.classes)
        published, _ = predictor.predict_proba(texts)
        if not np.allclose(published, expected, rtol=0, atol=1e-12):
            raise SystemExit(f"{test_path.name}: skops model differs from the trained model")
        recorded = pd.read_csv(f"reports/predictions/baseline_v1__{test_path.stem}.csv", dtype=str)[
            "top1"
        ].tolist()
        top1 = [p.suggestions[0].position for p in predictor.predict(texts)]
        if top1 != recorded:
            raise SystemExit(f"{test_path.name}: published top-1 differs from the report")
        logger.info("%s: published model reproduces the evaluation", test_path.name)


def build_bertimbau(out: Path, owner: str, provenance: dict) -> None:
    report = json.loads(
        Path("experiments/bertimbau/metrics/bertimbau_v1.json").read_text(encoding="utf-8")
    )
    config = json.loads(Path("experiments/bertimbau/config.json").read_text(encoding="utf-8"))
    folder = out / "ncm-classifier-bertimbau"
    shutil.copytree("models/bertimbau_v1", folder)
    shutil.copy("experiments/bertimbau/calibration.json", folder / "calibration.json")
    _write_json(folder / "training/config.json", config)
    _write_json(folder / "metrics/evaluation.json", public_metrics(report))
    selection = report["selection"]
    _render(
        "bertimbau_card.md",
        folder / "README.md",
        repo_id=f"{owner}/ncm-classifier-bertimbau",
        model_repo=f"{owner}/ncm-classifier",
        version=VERSION,
        date=provenance["date"],
        github=GITHUB,
        revision=config["pretrained_revision"],
        best_mode=selection["best_mode"],
        best_epoch=str(selection["best_epoch"]),
        cv_f1=f"{selection['cv_macro_f1']:.4f}",
        temperature=f"{selection['temperature']:.4f}",
        metrics_table=metrics_table(report),
        gpu=config["hardware"].get("gpu", "—"),
        minutes=f"{sum(config['timing_seconds'].values()) / 60:.0f}",
    )
    _manifest(
        folder,
        {
            **provenance,
            "model": "bertimbau_v1",
            "kaggle_code_commit": json.loads(
                Path("experiments/bertimbau/data_version.json").read_text(encoding="utf-8")
            )["repo_commit"],
            "train_sha256": report["train_sha256"],
        },
    )
    _verify_bertimbau(folder, selection, config)


def _verify_bertimbau(folder: Path, selection: dict, config: dict) -> None:
    import torch

    from ncm_classifier.models.bertimbau import load_model, predict_proba
    from ncm_classifier.models.transformer_support import prepare_input

    model, tokenizer, classes = load_model(folder, device=torch.device("cpu"))
    test = load_frozen_test(TESTS[0])
    raw = predict_proba(
        model,
        tokenizer,
        prepare_input(test["text"].tolist(), selection["best_mode"]),
        config["fine_tune"]["max_length"],
    )
    top1 = np.asarray(classes)[raw.argmax(axis=1)].tolist()
    recorded = pd.read_csv(
        "experiments/bertimbau/predictions/bertimbau_v1__test_v1.csv", dtype=str
    )["raw_top1"].tolist()
    agreement = float(np.mean([a == b for a, b in zip(top1, recorded, strict=True)]))
    # Kaggle ran on a GPU in float16; on CPU tiny numeric differences are expected,
    # but they must not change the first suggestion.
    if agreement < 1.0:
        raise SystemExit(f"BERTimbau copy agrees with Kaggle on {agreement:.1%} of test_v1 only")
    logger.info("test_v1.csv: BERTimbau copy reproduces the Kaggle raw top-1 on every row")


def build_dataset(out: Path, owner: str, provenance: dict) -> None:
    train = pd.read_parquet("data/processed/train_v1.parquet")
    public = train[train["source_type"].isin(PUBLIC_SOURCES)].reset_index(drop=True)
    public.insert(3, "chapter", public["position"].str[:2])

    test_texts = [t for path in TESTS for t in load_frozen_test(path)["text"]]
    if any(near_duplicate_mask(public["text"].tolist(), test_texts)):
        raise SystemExit("public dataset has near-duplicates of test texts")
    if set(public["source_type"]) - set(PUBLIC_SOURCES):
        raise SystemExit("public dataset has non-redistributable sources")

    folder = out / "ncm-classifier-dataset"
    (folder / "data").mkdir(parents=True)
    public.to_parquet(folder / "data/train_public-v1.parquet", index=False)
    (folder / "stats").mkdir()
    public.groupby(["chapter", "source_type"]).size().rename("rows").to_csv(
        folder / "stats/rows_by_chapter_and_source.csv"
    )
    public.groupby(["position", "source_type"]).size().rename("rows").to_csv(
        folder / "stats/rows_by_position_and_source.csv"
    )
    examples = pd.concat(
        [public[public["source_type"] == s].head(3) for s in PUBLIC_SOURCES], ignore_index=True
    )
    example_lines = ["| example_id | text | position | source_type |", "|---|---|---|---|"]
    example_lines += [
        f"| {r.example_id} | {r.text} | {r.position} | {r.source_type} |"
        for r in examples.itertuples()
    ]
    metadata = json.loads(Path("data/interim/ncm_table_metadata.json").read_text(encoding="utf-8"))
    _render(
        "dataset_card.md",
        folder / "README.md",
        repo_id=f"{owner}/ncm-classifier-dataset",
        model_repo=f"{owner}/ncm-classifier",
        version="v1.0.0",
        date=provenance["date"],
        github=GITHUB,
        ncm_version=f"{metadata['last_update']} ({metadata['legal_act']})",
        rows=str(len(public)),
        full_rows=str(len(train)),
        full_sources=", ".join(
            f"{k}: {v}" for k, v in train["source_type"].value_counts().sort_index().items()
        ),
        positions=str(public["position"].nunique()),
        distribution_table=distribution_table(public),
        examples_table="\n".join(example_lines),
        scope_table=scope_table(),
    )
    _manifest(
        folder,
        {
            **provenance,
            "dataset_version": "v1.0.0",
            "built_from": "data/processed/train_v1.parquet",
            "built_from_sha256": sha256_bytes(Path("data/processed/train_v1.parquet")),
            "sources": list(PUBLIC_SOURCES),
        },
    )
    logger.info("dataset: %d public rows of %d training rows", len(public), len(train))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="Hugging Face user or organization")
    parser.add_argument("--out", type=Path, default=Path("dist/huggingface"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if _git("status", "--porcelain", "--", "src", "scripts", "publishing"):
        raise SystemExit("Commit the code first: the cards must point to a committed revision")
    import sklearn
    import skops

    provenance = {
        "version": VERSION,
        "date": date.today().isoformat(),
        "code_commit": _git("rev-parse", "HEAD"),
        "github": GITHUB,
        "scikit_learn": sklearn.__version__,
        "skops": skops.__version__,
    }
    if args.out.exists():
        shutil.rmtree(args.out)
    build_model(args.out, args.owner, provenance)
    build_bertimbau(args.out, args.owner, provenance)
    build_dataset(args.out, args.owner, provenance)
    logger.info("Built and verified %s", args.out)


if __name__ == "__main__":
    main()
