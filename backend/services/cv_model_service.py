"""Chargement et inférence du modèle CV–poste.

La version actuelle sait utiliser le pipeline unifié futur, et conserve un mode
compatibilité pour les quatre artefacts historiques livrés avec le projet.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack

from config import CV_MODEL_DIR
from ml.cv_matching.features import (
    as_text, build_feature_frame, clean_model_text, normalize_skill_list,
)


class ModelUnavailableError(RuntimeError):
    """Raised when the current model artifacts cannot be loaded safely."""


@lru_cache(maxsize=1)
def _load_artifacts() -> dict[str, Any]:
    pipeline_path = CV_MODEL_DIR / "cv_matching_pipeline.joblib"
    manifest_path = CV_MODEL_DIR / "model_metadata.json"

    if pipeline_path.is_file():
        manifest = {}
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
        try:
            pipeline = joblib.load(pipeline_path)
        except Exception as exc:
            raise ModelUnavailableError(
                "Le pipeline actif ne peut pas être chargé ; vérifiez la version de scikit-learn."
            ) from exc
        return {
            "kind": "pipeline",
            "pipeline": pipeline,
            "version": str(manifest.get("model_version", "pipeline-without-metadata")),
        }

    legacy_files = {
        "model": CV_MODEL_DIR / "ia_recrutement_model.joblib",
        "skills": CV_MODEL_DIR / "skills_vectorizer2.joblib",
        "job": CV_MODEL_DIR / "job_vectorizer2.joblib",
        "location": CV_MODEL_DIR / "location_vectorizer2.joblib",
    }
    missing = [str(path.name) for path in legacy_files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Artefacts du modèle CV–poste absents : " + ", ".join(missing)
        )
    try:
        loaded = {
            "kind": "legacy",
            "model": joblib.load(legacy_files["model"]),
            "skills_vectorizer": joblib.load(legacy_files["skills"]),
            "job_vectorizer": joblib.load(legacy_files["job"]),
            "location_vectorizer": joblib.load(legacy_files["location"]),
            "version": "legacy-unversioned",
        }
    except Exception as exc:
        raise ModelUnavailableError(
            "Les artefacts historiques ne peuvent pas être chargés ; vérifiez leurs versions."
        ) from exc
    return loaded


def reload_model() -> None:
    """Vide le cache après un changement contrôlé d'artefact (puis redémarrage conseillé)."""
    _load_artifacts.cache_clear()


def _nonnegative_number(value: Any, field_name: str) -> float:
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Le champ {field_name} doit être numérique.") from exc
    if not np.isfinite(number) or number < 0:
        raise ValueError(f"Le champ {field_name} doit être un nombre positif ou nul.")
    return number


def _positive_class_probability(model: Any, features: Any) -> tuple[int, float]:
    prediction = int(model.predict(features)[0])
    if not hasattr(model, "predict_proba"):
        raise RuntimeError("Le modèle ne fournit pas de score probabiliste.")
    probabilities = model.predict_proba(features)[0]
    classes = list(getattr(model, "classes_", []))
    if 1 not in classes:
        raise RuntimeError("Le modèle n'a pas de classe positive (label 1).")
    probability = float(probabilities[classes.index(1)])
    return prediction, min(1.0, max(0.0, probability))


def predict_cv_match(candidate: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    candidate_skills = candidate.get("competences", [])
    required_skills = criteria.get("skills", "")
    candidate_skill_set = normalize_skill_list(candidate_skills)
    required_skill_set = normalize_skill_list(required_skills)
    matching_skills = sorted(candidate_skill_set & required_skill_set)

    experience = _nonnegative_number(candidate.get("experience", 0), "experience candidat")
    min_experience = _nonnegative_number(criteria.get("experience", 0), "experience requise")

    skills_text = clean_model_text(
        as_text(candidate_skills) + " " + as_text(required_skills)
    )
    job_text = clean_model_text(
        as_text(candidate.get("jobtitle", "")) + " " + as_text(criteria.get("poste", ""))
    )
    # Ne pas réutiliser une adresse personnelle comme ville de résidence :
    # l'extraction actuelle ne garantit pas un champ location normalisé.
    location_text = clean_model_text(
        as_text(candidate.get("location", ""))
        + " " + as_text(criteria.get("location", ""))
    )

    artifacts = _load_artifacts()
    if artifacts["kind"] == "pipeline":
        features = pd.DataFrame([{
            "skills_text": skills_text,
            "job_text": job_text,
            "location_text": location_text,
            "experience": experience,
            "exp_min": min_experience,
        }])
        prediction, probability = _positive_class_probability(artifacts["pipeline"], features)
    else:
        x_skills = artifacts["skills_vectorizer"].transform([skills_text])
        x_job = artifacts["job_vectorizer"].transform([job_text])
        x_location = artifacts["location_vectorizer"].transform([location_text])
        features = hstack([x_skills, x_job, x_location, np.array([[experience, min_experience]])])
        prediction, probability = _positive_class_probability(artifacts["model"], features)

    # Règle historique conservée séparément de la prédiction ML.
    business_rule_match = len(matching_skills) >= 3
    recommended_for_review = bool(prediction) or business_rule_match
    score_percent = round(probability * 100)

    message_parts = [
        f"Score indicatif du modèle : {score_percent}%.",
        f"Compétences exactes communes : {len(matching_skills)} sur {len(required_skill_set)} critères saisis.",
        "Ce résultat est une aide à l'examen du dossier, pas une décision automatique de recrutement.",
    ]
    if matching_skills:
        message_parts.append("Compétences communes : " + ", ".join(matching_skills) + ".")
    if business_rule_match:
        message_parts.append("La règle historique des trois compétences communes est satisfaite.")
    if not prediction and not business_rule_match:
        message_parts.append("Le modèle et la règle historique ne déclenchent pas de recommandation prioritaire ; une revue humaine reste possible.")

    return {
        "success": True,
        "recommande": recommended_for_review,  # conservé pour compatibilité frontend
        "score": score_percent,
        "model_score_probability": round(probability, 6),
        "model_prediction": prediction,
        "model_version": artifacts["version"],
        "matching_skills": matching_skills,
        "missing_or_unverified_skills": sorted(required_skill_set - candidate_skill_set),
        "business_rule_match": business_rule_match,
        "message": "\n".join(message_parts),
        "decision_notice": "La décision finale appartient au recruteur.",
    }
