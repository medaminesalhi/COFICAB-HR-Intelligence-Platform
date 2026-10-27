"""Entraînement candidat du workflow historique de profils.

Ce workflow est déprécié pour la recommandation RH : sa cible `recrute` est
construite à partir du nombre de stages et ne correspond pas à un résultat réel
de recrutement. Le script exige donc une confirmation explicite et n'écrit ni
dans le registre actif ni dans scored_profiles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from config import PROFILE_MODEL_DIR
from db_utils import database_connection

LOGGER = logging.getLogger("coficab.legacy_profiles_training")
NUMERIC_FEATURES = [
    "jobtitle", "company", "location", "school", "schooldegree",
    "anneediplome", "motorise", "annee_experience", "mobilite",
]
CATEGORICAL_FEATURES = ["niveau_etude"]
REQUIRED_COLUMNS = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["skills", "recrute"])


def split_skills(value: str) -> list[str]:
    if not isinstance(value, str):
        return []
    return [item.strip().casefold() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Entraînement expérimental du pipeline historique de profils.")
    parser.add_argument(
        "--allow-rule-derived-target",
        action="store_true",
        help="Confirmez que vous comprenez que `recrute` est dérivé d'une règle, pas d'un recrutement observé.",
    )
    args = parser.parse_args()
    if not args.allow_rule_derived_target:
        parser.error(
            "Entraînement bloqué : la cible historique `recrute` est dérivée du nombre de stages. "
            "Examinez la cible puis passez --allow-rule-derived-target uniquement pour une expérience pédagogique."
        )

    with database_connection() as connection:
        frame = pd.read_sql("SELECT * FROM ml_ready_profiles", connection)

    if frame.empty:
        raise ValueError("ml_ready_profiles est vide.")
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("Colonnes manquantes : " + ", ".join(missing))

    y = pd.to_numeric(frame["recrute"], errors="coerce")
    if y.isna().any() or set(y.unique()) != {0, 1}:
        raise ValueError("La cible recrute doit contenir uniquement les classes 0 et 1.")

    # `nombrestage` et `profil_senior` sont exclus car ils sont directement utilisés
    # dans la règle qui crée la cible : les conserver créerait une fuite de cible.
    X = frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["skills"]].copy()
    for column in NUMERIC_FEATURES:
        X[column] = pd.to_numeric(X[column], errors="coerce").fillna(0)
    for column in CATEGORICAL_FEATURES:
        X[column] = X[column].fillna("Autre").astype(str)
    X["skills"] = X["skills"].fillna("").astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y.astype(int), test_size=0.2, random_state=42, stratify=y.astype(int)
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("skills", TfidfVectorizer(tokenizer=split_skills, token_pattern=None, max_features=200), "skills"),
            ("degree_level", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ],
        remainder="drop",
    )
    pipeline = Pipeline([
        ("preprocess", preprocess),
        ("classifier", RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_split=5,
            min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train, y_train)
    prediction = pipeline.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, prediction)),
        "precision_positive": float(precision_score(y_test, prediction, zero_division=0)),
        "recall_positive": float(recall_score(y_test, prediction, zero_division=0)),
        "f1_positive": float(f1_score(y_test, prediction, zero_division=0)),
        "classification_report": classification_report(y_test, prediction, output_dict=True, zero_division=0),
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
    }

    timestamp = datetime.now(timezone.utc)
    version = "legacy-candidate-" + timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = PROFILE_MODEL_DIR / "candidates" / version
    output_dir.mkdir(parents=True, exist_ok=False)
    joblib.dump(pipeline, output_dir / "model_rh_candidate.joblib")
    metadata = {
        "model_name": "coficab_legacy_profiles",
        "model_version": version,
        "created_at_utc": timestamp.isoformat(),
        "target_column": "recrute",
        "target_semantics": "Rule-derived from nombrestage >= 2; not a verified hiring outcome.",
        "target_leakage_features_excluded": ["nombrestage", "profil_senior"],
        "sklearn_version": sklearn.__version__,
        "dataset_rows": int(len(frame)),
        "metrics": metrics,
        "status": "candidate_not_promoted",
    }
    (output_dir / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    LOGGER.info("Candidat historique créé : %s", version)
    LOGGER.warning("Ce modèle est pédagogique uniquement et ne doit pas servir à des décisions de recrutement.")
    print(f"Artefacts candidats écrits dans : {output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
