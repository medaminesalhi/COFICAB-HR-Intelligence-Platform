"""Préparation commune des variables CV–poste pour train et inference."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

FEATURE_COLUMNS = (
    "skills_text", "job_text", "location_text", "experience", "exp_min"
)
TRAINING_COLUMNS = (
    "jobtitle", "skills", "location", "experience",
    "poste_rh", "skills_rh", "location_rh", "exp_min", "recrute",
)


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value if item is not None)
    return str(value).strip().lower()


def clean_model_text(value: Any) -> str:
    text = as_text(value)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def build_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Construit les variables attendues par le pipeline, sans ajuster de transformateur."""
    required = set(TRAINING_COLUMNS) - {"recrute"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Colonnes manquantes : " + ", ".join(missing))

    result = pd.DataFrame(index=frame.index)
    result["skills_text"] = (
        frame["skills"].map(as_text) + " " + frame["skills_rh"].map(as_text)
    ).map(clean_model_text)
    result["job_text"] = (
        frame["jobtitle"].map(as_text) + " " + frame["poste_rh"].map(as_text)
    ).map(clean_model_text)
    result["location_text"] = (
        frame["location"].map(as_text) + " " + frame["location_rh"].map(as_text)
    ).map(clean_model_text)
    for column in ("experience", "exp_min"):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        result[column] = numeric.fillna(0).clip(lower=0)
    return result.loc[:, list(FEATURE_COLUMNS)].reset_index(drop=True)


def normalize_skill_list(value: Any) -> set[str]:
    """Normalise des compétences en éléments complets, pas en mots isolés."""
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = re.split(r"[,;\n|•\u2022]", str(value))
    normalized = {
        re.sub(r"\s+", " ", str(item)).strip().casefold()
        for item in values
        if item is not None and str(item).strip()
    }
    return normalized
