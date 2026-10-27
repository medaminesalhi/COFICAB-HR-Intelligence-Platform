"""Endpoints d'extraction et de scoring CV–poste."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from db_utils import database_connection
from services.cv_extraction import extract_cv_from_pdf
from services.cv_model_service import ModelUnavailableError, predict_cv_match

cv_matching_bp = Blueprint("cv_matching", __name__, url_prefix="/api")


def _as_text(value, limit: int = 5000) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = ", ".join(str(item) for item in value)
    if not isinstance(value, (str, int, float)):
        raise ValueError("Un champ du CV ou du poste possède un format invalide.")
    text = str(value).strip()
    if len(text) > limit:
        raise ValueError("Un champ du CV ou du poste dépasse la taille autorisée.")
    return text


@cv_matching_bp.post("/scrape_cv")
@jwt_required()
def scrape_cv():
    uploaded = request.files.get("cv")
    if uploaded is None or not uploaded.filename:
        return jsonify(success=False, message="Veuillez sélectionner un fichier PDF."), 400
    if not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(success=False, message="Seuls les fichiers PDF sont acceptés."), 415

    try:
        pdf_bytes = uploaded.read()
        extracted = extract_cv_from_pdf(pdf_bytes)
    except ValueError as exc:
        message = str(exc)
        status = 422 if "Aucun texte" in message else 400
        return jsonify(success=False, message=message), status
    except Exception:
        current_app.logger.exception("Erreur inattendue pendant l'extraction PDF.")
        return jsonify(success=False, message="L'extraction du CV a échoué."), 500

    return jsonify(success=True, **extracted), 200


@cv_matching_bp.post("/predict_match")
@jwt_required()
def predict_match():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, message="Corps JSON invalide."), 400

    candidate = data.get("candidat")
    criteria = data.get("criteres")
    if not isinstance(candidate, dict) or not isinstance(criteria, dict):
        return jsonify(success=False, message="Les objets 'candidat' et 'criteres' sont requis."), 400

    try:
        poste = _as_text(criteria.get("poste", ""), 255)
        if not poste:
            return jsonify(success=False, message="Veuillez préciser le poste à évaluer."), 400

        candidate_skills = candidate.get("competences", [])
        required_skills = criteria.get("skills", "")
        for label, value in (("competences du candidat", candidate_skills), ("competences requises", required_skills)):
            if isinstance(value, list):
                if len(value) > 100 or any(not isinstance(item, str) or len(item) > 100 for item in value):
                    raise ValueError(f"Le champ {label} contient trop d'éléments ou un élément invalide.")
            elif not isinstance(value, str):
                raise ValueError(f"Le champ {label} doit être un texte ou une liste de textes.")

        # Valide la taille/forme des champs reçus avant l'inférence.
        normalized_candidate = {
            key: _as_text(value, 5000) if key != "competences" else value
            for key, value in candidate.items()
        }
        normalized_criteria = {
            key: _as_text(value, 2000) if key not in {"experience", "skills"} else value
            for key, value in criteria.items()
        }
        normalized_criteria["poste"] = poste
        normalized_criteria["skills"] = _as_text(required_skills, 2000)
        result = predict_cv_match(normalized_candidate, normalized_criteria)
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except (FileNotFoundError, ModelUnavailableError):
        current_app.logger.exception("Artefacts du modèle CV–poste absents ou incompatibles.")
        return jsonify(
            success=False,
            message="Le modèle CV–poste n'est pas disponible ou incompatible. Vérifiez les artefacts et les versions Python.",
        ), 503
    except Exception:
        current_app.logger.exception("Erreur pendant l'inférence CV–poste.")
        return jsonify(success=False, message="L'évaluation du CV a échoué."), 500

    # La prédiction est renvoyée même si la persistance échoue ; le statut de
    # sauvegarde est explicitement indiqué pour ne pas masquer le problème.
    saved = False
    try:
        candidate_skills = normalized_candidate.get("competences", [])
        if isinstance(candidate_skills, list):
            candidate_skills = ", ".join(str(item) for item in candidate_skills)
        criteria_skills = normalized_criteria.get("skills", "")
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO evaluations_ia (
                        nom, jobtitle, email, telephone, adresse,
                        competences, formation, experience, langues, centres,
                        poste_rh, skills_rh, location_rh, exp_min, exp_candidat,
                        score_ia, recommande
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    normalized_candidate.get("nom", ""),
                    normalized_candidate.get("jobtitle", ""),
                    normalized_candidate.get("email", ""),
                    normalized_candidate.get("telephone", ""),
                    normalized_candidate.get("adresse", ""),
                    candidate_skills,
                    normalized_candidate.get("formation", ""),
                    str(normalized_candidate.get("experience", "")),
                    normalized_candidate.get("langues", ""),
                    normalized_candidate.get("centres", ""),
                    normalized_criteria.get("poste", ""),
                    criteria_skills,
                    normalized_criteria.get("location", ""),
                    float(normalized_criteria.get("experience", 0) or 0),
                    float(normalized_candidate.get("experience", 0) or 0),
                    result["score"],
                    result["recommande"],
                ))
        saved = True
    except Exception:
        current_app.logger.exception("La prédiction a réussi, mais l'enregistrement de l'évaluation a échoué.")

    result["evaluation_saved"] = saved
    if not saved:
        result["persistence_warning"] = "Le résultat a été calculé mais n'a pas pu être enregistré."
    return jsonify(result), 200
