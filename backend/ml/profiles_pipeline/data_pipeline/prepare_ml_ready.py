"""Prépare ml_ready_profiles à partir de raw_profiles.

Cette chaîne historique reste séparée du workflow CV–poste prioritaire. La cible
`recrute` est dérivée de `nombrestage >= 2` et ne représente pas un recrutement
réel ; elle ne doit pas être interprétée comme une vérité terrain RH.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import psycopg2
from sklearn.preprocessing import LabelEncoder

from db_utils import database_connection


def main() -> None:
    with database_connection() as connection:
        frame = pd.read_sql("SELECT * FROM raw_profiles", connection)
        if frame.empty:
            raise ValueError("raw_profiles est vide : aucun dataset à préparer.")

        required = {"id", "jobtitle", "company", "location", "school", "schooldegree",
                    "anneediplome", "nombrestage", "motorise", "skills"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError("Colonnes manquantes dans raw_profiles : " + ", ".join(missing))

        frame["skills"] = frame["skills"].fillna("").astype(str).str.strip()
        # Compatibilité historique : cette variable mesure le temps depuis le diplôme,
        # pas l'expérience professionnelle réelle.
        current_year = datetime.now().year
        frame["annee_experience"] = (current_year - pd.to_numeric(
            frame["anneediplome"], errors="coerce"
        ).fillna(current_year)).clip(lower=0)

        def is_mobile(row):
            location = str(row["location"]).casefold()
            motorized = str(row["motorise"]).casefold()
            return 1 if "tunis" not in location or motorized == "oui" else 0

        frame["mobilite"] = frame.apply(is_mobile, axis=1)

        encoders = {}
        for column in ("jobtitle", "company", "location", "school", "schooldegree", "motorise"):
            encoder = LabelEncoder()
            frame[column] = encoder.fit_transform(frame[column].fillna("").astype(str))
            encoders[column] = encoder

        def simplify_degree(code):
            try:
                text = encoders["schooldegree"].inverse_transform([int(code)])[0].casefold()
            except (ValueError, TypeError, IndexError):
                return "Autre"
            if "licence" in text:
                return "Licence"
            if any(term in text for term in ("master", "mba", "ingénieur", "ingenieur")):
                return "Master"
            return "Autre"

        frame["niveau_etude"] = frame["schooldegree"].map(simplify_degree)
        frame["profil_senior"] = (
            (frame["annee_experience"] >= 3) & (pd.to_numeric(frame["nombrestage"], errors="coerce") >= 2)
        ).astype(int)
        # Cible héritée d'une règle métier, et non d'une décision de recrutement observée.
        frame["recrute"] = (pd.to_numeric(frame["nombrestage"], errors="coerce") >= 2).astype(int)

        columns = [
            "id", "jobtitle", "company", "location", "school", "schooldegree",
            "anneediplome", "nombrestage", "motorise", "annee_experience", "mobilite",
            "niveau_etude", "profil_senior", "recrute", "skills",
        ]
        prepared = frame[columns].copy()
        prepared["anneediplome"] = pd.to_numeric(prepared["anneediplome"], errors="coerce").fillna(0).astype(int)
        prepared["nombrestage"] = pd.to_numeric(prepared["nombrestage"], errors="coerce").fillna(0).astype(int)

        with connection.cursor() as cursor:
            for row in prepared.itertuples(index=False, name=None):
                cursor.execute("""
                    INSERT INTO ml_ready_profiles (
                        id, jobtitle, company, location, school,
                        schooldegree, anneediplome, nombrestage, motorise,
                        annee_experience, mobilite, niveau_etude, profil_senior, recrute, skills
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        jobtitle = EXCLUDED.jobtitle,
                        company = EXCLUDED.company,
                        location = EXCLUDED.location,
                        school = EXCLUDED.school,
                        schooldegree = EXCLUDED.schooldegree,
                        anneediplome = EXCLUDED.anneediplome,
                        nombrestage = EXCLUDED.nombrestage,
                        motorise = EXCLUDED.motorise,
                        annee_experience = EXCLUDED.annee_experience,
                        mobilite = EXCLUDED.mobilite,
                        niveau_etude = EXCLUDED.niveau_etude,
                        profil_senior = EXCLUDED.profil_senior,
                        recrute = EXCLUDED.recrute,
                        skills = EXCLUDED.skills;
                """, row)

    print(f"Préparation terminée : {len(prepared)} ligne(s) insérée(s) ou mises à jour.")


if __name__ == "__main__":
    main()
