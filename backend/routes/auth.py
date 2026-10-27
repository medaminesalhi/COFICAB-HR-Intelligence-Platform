"""Endpoints d'authentification RH."""
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from flask_jwt_extended import create_access_token

from models import Recruteur

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, message="Corps JSON invalide."), 400

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify(success=False, message="Adresse e-mail et mot de passe requis."), 400

    email = email.strip().casefold()
    if not email or not password or len(email) > 255 or len(password) > 1024:
        return jsonify(success=False, message="Adresse e-mail ou mot de passe invalide."), 400

    recruiter = Recruteur.query.filter(func.lower(Recruteur.email) == email).first()
    if not recruiter or not recruiter.verify_password(password):
        return jsonify(success=False, message="Identifiants incorrects."), 401

    token = create_access_token(identity=str(recruiter.email))
    return jsonify(
        success=True,
        token=token,
        user={"nom": recruiter.nom or "", "role": recruiter.role or ""},
    ), 200
