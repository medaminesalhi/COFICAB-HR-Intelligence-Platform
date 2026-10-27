"""Import idempotent des profils dans raw_profiles.

Le script n'efface plus les lignes existantes. La déduplication utilise une clé
métier approximative (nom, poste, entreprise, localisation) en attendant qu'un
identifiant source stable et une contrainte UNIQUE soient définis.
"""
from __future__ import annotations

import pandas as pd

from config import PROFILE_PROCESSED_DATA_DIR
from db_utils import database_connection

INPUT_PATH = PROFILE_PROCESSED_DATA_DIR / "profils_nettoyes.csv"
REQUIRED_COLUMNS = {
    "fullName", "jobTitle", "company", "location", "school", "schoolDegree",
    "anneeDiplome", "nombreStage", "motorise", "skills",
}


def main() -> None:
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {INPUT_PATH}")
    frame = pd.read_csv(INPUT_PATH)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("Colonnes manquantes : " + ", ".join(missing))

    inserted = 0
    skipped = 0
    with database_connection() as connection:
        with connection.cursor() as cursor:
            for row in frame.to_dict(orient="records"):
                name = str(row.get("fullName") or "").strip()
                job = str(row.get("jobTitle") or "").strip()
                company = str(row.get("company") or "").strip()
                location = str(row.get("location") or "").strip()
                if not name or not job:
                    skipped += 1
                    continue

                diploma_year = pd.to_numeric(row.get("anneeDiplome"), errors="coerce")
                internship_count = pd.to_numeric(row.get("nombreStage"), errors="coerce")
                diploma_year = int(diploma_year) if pd.notna(diploma_year) else 0
                internship_count = int(internship_count) if pd.notna(internship_count) else 0

                cursor.execute("""
                    INSERT INTO raw_profiles (
                        fullname, jobtitle, company, location, jobdaterange,
                        school, schooldegree, schooldaterange,
                        anneediplome, nombrestage, motorise, skills
                    )
                    SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM raw_profiles
                        WHERE LOWER(BTRIM(COALESCE(fullname, ''))) = LOWER(BTRIM(%s))
                          AND LOWER(BTRIM(COALESCE(jobtitle, ''))) = LOWER(BTRIM(%s))
                          AND LOWER(BTRIM(COALESCE(company, ''))) = LOWER(BTRIM(%s))
                          AND LOWER(BTRIM(COALESCE(location, ''))) = LOWER(BTRIM(%s))
                    );
                """, (
                    name, job, company, location, str(row.get("jobDateRange") or ""),
                    str(row.get("school") or ""), str(row.get("schoolDegree") or ""),
                    str(row.get("schoolDateRange") or ""),
                    diploma_year,
                    internship_count,
                    str(row.get("motorise") or ""), str(row.get("skills") or ""),
                    name, job, company, location,
                ))
                inserted += cursor.rowcount

    print(f"Import terminé : {inserted} nouveau(x) profil(s), {skipped} ligne(s) ignorée(s).")


if __name__ == "__main__":
    main()
