"""Point d'entrée Flask de COFICAB.

Lancement local depuis le dossier backend : python app.py
Les endpoints historiques sont conservés via des Blueprints.
"""
from __future__ import annotations

import logging
import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from config import (
    CORS_ORIGINS,
    DATABASE_URL,
    DEBUG,
    JWT_SECRET_KEY,
    JWT_TOKEN_LIFETIME_HOURS,
    MAX_CONTENT_LENGTH,
)
from extensions import db, jwt


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        JWT_SECRET_KEY=JWT_SECRET_KEY,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=JWT_TOKEN_LIFETIME_HOURS),
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    CORS(
        app,
        resources={r"/api/*": {"origins": CORS_ORIGINS}},
        supports_credentials=False,
    )
    db.init_app(app)
    jwt.init_app(app)

    @jwt.unauthorized_loader
    def handle_missing_jwt(_reason):
        return jsonify(success=False, message="Authentification requise."), 401

    @jwt.invalid_token_loader
    def handle_invalid_jwt(_reason):
        return jsonify(success=False, message="Session invalide. Veuillez vous reconnecter."), 401

    @jwt.expired_token_loader
    def handle_expired_jwt(_header, _payload):
        return jsonify(success=False, message="Session expirée. Veuillez vous reconnecter."), 401

    # Import des modèles et blueprints après initialisation des extensions.
    from models import Recruteur  # noqa: F401
    from routes.auth import auth_bp
    from routes.cv_matching import cv_matching_bp
    from routes.dashboard import dashboard_bp
    from routes.profiles import profiles_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(cv_matching_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profiles_bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="coficab-backend"), 200

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        return jsonify(
            success=False,
            message=f"La requête dépasse la taille maximale autorisée ({MAX_CONTENT_LENGTH // (1024 * 1024)} Mo).",
        ), 413

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        message = "Ressource introuvable." if error.code == 404 else error.description
        return jsonify(success=False, message=message), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        app.logger.exception("Erreur non gérée pendant le traitement de la requête.")
        return jsonify(success=False, message="Erreur interne du serveur."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=DEBUG,
    )
