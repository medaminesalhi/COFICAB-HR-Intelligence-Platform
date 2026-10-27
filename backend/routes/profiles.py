"""Recherche, filtres et persistance des profils historiques."""
import math

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from db_utils import database_connection

profiles_bp = Blueprint("profiles", __name__, url_prefix="/api")


def _text_filter(data: dict, key: str) -> str:
    value = data.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _nonnegative_float(value, field_name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Le champ '{field_name}' doit être numérique.") from exc
    if result < 0 or result > 1:
        raise ValueError(f"Le champ '{field_name}' doit être compris entre 0 et 1.")
    return result


@profiles_bp.post("/recherche-profils")
@jwt_required()
def recherche_profils():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, message="Corps JSON invalide."), 400

    try:
        min_score = _nonnegative_float(data.get("score", 0), "score")
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400

    skills = data.get("skills", [])
    if not isinstance(skills, list) or any(not isinstance(skill, str) for skill in skills):
        return jsonify(success=False, message="Le champ 'skills' doit être une liste de textes."), 400

    query = """
        SELECT fullname, jobtitle, location, schooldegree, score, prediction, competences
        FROM scored_profiles
        WHERE LOWER(COALESCE(fullname, '')) LIKE %s
          AND LOWER(COALESCE(jobtitle, '')) LIKE %s
          AND LOWER(COALESCE(location, '')) LIKE %s
          AND LOWER(COALESCE(schooldegree, '')) LIKE %s
          AND COALESCE(score, 0) >= %s
    """
    params = [
        f"%{_text_filter(data, 'nom').casefold()}%",
        f"%{_text_filter(data, 'jobtitle').casefold()}%",
        f"%{_text_filter(data, 'location').casefold()}%",
        f"%{_text_filter(data, 'schooldegree').casefold()}%",
        min_score,
    ]

    # Une case décochée signifie "ne pas filtrer", pas "ne montrer que les non-recommandés".
    if data.get("recommande") is True:
        query += " AND prediction = %s"
        params.append(1)

    for skill in skills:
        normalized_skill = skill.strip()
        if normalized_skill:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM unnest(string_to_array(COALESCE(competences, ''), ',')) AS skill_item(value)
                    WHERE LOWER(BTRIM(skill_item.value)) = LOWER(%s)
                )
            """
            params.append(normalized_skill)

    query += " ORDER BY score DESC NULLS LAST, fullname ASC NULLS LAST LIMIT 1000;"

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

    profiles = []
    for row in rows:
        skills_value = row[6] or ""
        profiles.append({
            "fullname": row[0] or "Non renseigné",
            "jobtitle": row[1] or "Non renseigné",
            "location": row[2] or "Non renseigné",
            "schooldegree": row[3] or "Non renseigné",
            "score": float(row[4] or 0),
            "prediction": bool(row[5]),
            "competences": [item.strip() for item in str(skills_value).split(",") if item.strip()],
        })
    return jsonify(profils=profiles)


@profiles_bp.get("/metiers")
@jwt_required()
def get_metiers():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT jobtitle FROM scored_profiles
                WHERE jobtitle IS NOT NULL AND BTRIM(jobtitle) <> ''
                ORDER BY jobtitle ASC;
            """)
            jobs = [row[0] for row in cursor.fetchall()]
    return jsonify(metiers=jobs)


@profiles_bp.get("/diplomes")
@jwt_required()
def get_diplomes():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT schooldegree FROM scored_profiles
                WHERE schooldegree IS NOT NULL AND BTRIM(schooldegree) <> ''
                ORDER BY schooldegree ASC;
            """)
            degrees = [row[0] for row in cursor.fetchall()]
    return jsonify(diplomes=degrees)


@profiles_bp.post("/save_profile")
@jwt_required()
def save_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, message="Corps JSON invalide."), 400

    def field(name: str, limit: int = 5000) -> str:
        value = data.get(name, "")
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        if value is None:
            return ""
        if not isinstance(value, (str, int, float)):
            raise ValueError(f"Champ invalide : {name}.")
        value = str(value).strip()
        if len(value) > limit:
            raise ValueError(f"Le champ '{name}' dépasse la taille autorisée.")
        return value

    try:
        nom = field("nom", 255)
        jobtitle = field("jobtitle", 255).lower()
        email = field("email", 255).lower()
        telephone = field("telephone", 80)
        adresse = field("adresse", 500)
        competences = field("competences", 5000).lower()
        formation = field("formation")
        experience = field("experience")
        langues = field("langues")
        centres = field("centres")
        poste_rh = field("poste_rh", 255)
        skills_rh = field("skills_rh", 2000)
        location_rh = field("location_rh", 255)
        exp_min = float(data.get("exp_min", 0) or 0)
        exp_candidat = float(data.get("exp_candidat", 0) or 0)
        if (
            not math.isfinite(exp_min) or not math.isfinite(exp_candidat)
            or exp_min < 0 or exp_candidat < 0
        ):
            raise ValueError("Les années d'expérience doivent être des nombres positifs ou nuls.")
    except (ValueError, TypeError) as exc:
        return jsonify(success=False, message=str(exc)), 400

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO scraped_profiles
                    (nom, jobtitle, email, telephone, adresse, competences, formation, experience, langues, centres,
                     poste_rh, skills_rh, location_rh, exp_min, exp_candidat)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    nom, jobtitle, email, telephone, adresse, competences, formation, experience,
                    langues, centres, poste_rh, skills_rh, location_rh, exp_min, exp_candidat,
                ))
                # Le CV extrait n'est pas injecté dans ml_ready_temp :
                # les critères et labels RH ne sont pas encore validés à cette étape.
    except Exception:
        current_app.logger.exception("Échec de persistance d'un profil CV.")
        return jsonify(success=False, message="Impossible d'enregistrer le profil pour le moment."), 500

    return jsonify(success=True, message="Profil extrait enregistré. Les critères du poste seront associés à l’évaluation."), 201
