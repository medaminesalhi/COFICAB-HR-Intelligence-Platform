"""Nettoie le CSV du workflow historique de profils sans toucher à PostgreSQL."""
from __future__ import annotations

import pandas as pd

from config import PROFILE_RAW_DATA_DIR, PROFILE_PROCESSED_DATA_DIR

INPUT_PATH = PROFILE_RAW_DATA_DIR / "profils_final_avec_skills.csv"
REQUIRED_COLUMNS = [
    "fullName", "jobTitle", "company", "location", "school", "schoolDegree",
    "anneeDiplome", "nombreStage", "motorise", "skills",
]
TEXT_COLUMNS = [
    "fullName", "jobTitle", "company", "location", "school", "schoolDegree",
    "motorise", "skills",
]


def main() -> None:
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {INPUT_PATH}")
    frame = pd.read_csv(INPUT_PATH)
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError("Colonnes obligatoires absentes : " + ", ".join(missing))

    frame = frame.drop_duplicates().copy()
    frame = frame.dropna(subset=REQUIRED_COLUMNS).copy()
    for column in TEXT_COLUMNS:
        frame[column] = frame[column].astype(str).str.strip()
    frame["motorise"] = frame["motorise"].str.casefold().map(
        {"oui": "Oui", "non": "Non"}
    ).fillna(frame["motorise"])
    for column in ("anneeDiplome", "nombreStage"):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"La colonne {column} contient des valeurs non numériques.")
        frame[column] = numeric.astype(int)
    frame = frame.fillna("")

    PROFILE_PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROFILE_PROCESSED_DATA_DIR / "profils_nettoyes.csv"
    frame.to_csv(output_path, index=False)
    print(f"Nettoyage terminé : {len(frame)} ligne(s) écrite(s) dans {output_path}")


if __name__ == "__main__":
    main()
