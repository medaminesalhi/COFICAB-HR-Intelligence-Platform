"""Entraîne un modèle candidat CV–poste sans remplacer le modèle actif.

Le dataset actuel utilise le label historique `recrute`, dont la provenance doit être
confirmée avant toute promotion en production. Le script écrit donc dans candidates/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from config import CV_CANDIDATES_DIR, CV_TRAINING_DATA_DIR
from ml.cv_matching.features import TRAINING_COLUMNS, build_feature_frame

LOGGER = logging.getLogger("coficab.training")


def validate_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Valide le schéma minimal et renvoie une copie propre du dataset."""
    missing = sorted(set(TRAINING_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError("Colonnes manquantes dans le dataset : " + ", ".join(missing))
    if frame.empty:
        raise ValueError("Le dataset d'entraînement est vide.")

    clean = frame.loc[:, list(TRAINING_COLUMNS)].copy()
    clean["recrute"] = pd.to_numeric(clean["recrute"], errors="coerce")
    if clean["recrute"].isna().any():
        raise ValueError("La cible 'recrute' contient des valeurs absentes ou non numériques.")
    labels = set(clean["recrute"].unique().tolist())
    if not labels.issubset({0, 1}) or len(labels) != 2:
        raise ValueError("La cible 'recrute' doit contenir les deux classes 0 et 1.")
    if clean["recrute"].value_counts().min() < 2:
        raise ValueError("Chaque classe doit contenir au moins deux exemples pour le découpage.")
    for column in ("experience", "exp_min"):
        clean[column] = pd.to_numeric(clean[column], errors="coerce").fillna(0).clip(lower=0)
    for column in ("jobtitle", "skills", "location", "poste_rh", "skills_rh", "location_rh"):
        clean[column] = clean[column].fillna("").astype(str).str.strip()
    return clean


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def train_candidate(
    data_path: Path | None = None,
    candidates_dir: Path | None = None,
    labels_verified: bool = False,
) -> dict[str, Any]:
    data_path = data_path or (CV_TRAINING_DATA_DIR / "profils_training_balanced.csv")
    candidates_dir = candidates_dir or CV_CANDIDATES_DIR
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset introuvable : {data_path}")

    source_frame = pd.read_csv(data_path)
    frame = validate_dataset(source_frame)
    X = build_feature_frame(frame)
    for text_column in ("skills_text", "job_text", "location_text"):
        if not X[text_column].str.strip().astype(bool).any():
            raise ValueError(f"Les données ne contiennent aucun texte exploitable dans '{text_column}'.")
    y = frame["recrute"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    preprocess = ColumnTransformer(
        transformers=[
            ("skills", CountVectorizer(), "skills_text"),
            ("job", CountVectorizer(), "job_text"),
            ("location", CountVectorizer(), "location_text"),
            ("numeric", "passthrough", ["experience", "exp_min"]),
        ],
        remainder="drop",
    )
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocess),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=42,
                    class_weight="balanced",
                    min_samples_leaf=2,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, list(pipeline.classes_).index(1)]
    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "precision_positive": float(precision_score(y_test, predictions, pos_label=1, zero_division=0)),
        "recall_positive": float(recall_score(y_test, predictions, pos_label=1, zero_division=0)),
        "f1_positive": float(f1_score(y_test, predictions, pos_label=1, zero_division=0)),
        "classification_report": classification_report(
            y_test, predictions, output_dict=True, zero_division=0
        ),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "test_rows": int(len(y_test)),
        "train_rows": int(len(y_train)),
    }

    timestamp = datetime.now(timezone.utc)
    model_version = "candidate-" + timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = candidates_dir / model_version
    output_dir.mkdir(parents=True, exist_ok=False)
    joblib.dump(pipeline, output_dir / "cv_matching_pipeline.joblib")

    metadata = {
        "model_name": "coficab_cv_match",
        "model_version": model_version,
        "created_at_utc": timestamp.isoformat(),
        "dataset_filename": data_path.name,
        "dataset_sha256": _sha256(data_path),
        "dataset_rows": int(len(frame)),
        "target_column": "recrute",
        "target_semantics": "Legacy label; business meaning and provenance must be confirmed.",
        "labels_verified": bool(labels_verified),
        "sklearn_version": sklearn.__version__,
        "feature_columns": list(X.columns),
        "metrics": metrics,
        "status": "candidate_not_promoted",
    }
    (output_dir / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    LOGGER.info("Candidat entraîné : %s", model_version)
    LOGGER.info("Métriques principales : %s", {
        key: metrics[key] for key in (
            "accuracy", "balanced_accuracy", "precision_positive", "recall_positive", "f1_positive", "roc_auc"
        )
    })
    if not labels_verified:
        LOGGER.warning(
            "La provenance du label 'recrute' n'est pas confirmée. "
            "Ce candidat ne doit pas être promu en production."
        )
    LOGGER.info("Artefacts écrits dans : %s", output_dir)
    return {"output_dir": output_dir, "metadata": metadata}


def main() -> None:
    parser = argparse.ArgumentParser(description="Entraîner un candidat de modèle CV–poste.")
    parser.add_argument("--data", type=Path, default=None, help="Chemin du CSV d'entraînement.")
    parser.add_argument(
        "--labels-verified",
        action="store_true",
        help="À utiliser uniquement après avoir vérifié et documenté l'origine des labels.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = train_candidate(data_path=args.data, labels_verified=args.labels_verified)
    print(f"Candidat créé : {result['metadata']['model_version']}")
    print(f"Répertoire : {result['output_dir']}")


if __name__ == "__main__":
    main()
