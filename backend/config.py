"""Configuration centralisée du backend COFICAB."""
from __future__ import annotations

import os
import secrets
import warnings
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} doit être un entier.") from exc
    if value <= 0:
        raise ValueError(f"{name} doit être strictement positif.")
    return value


def _parse_database_config() -> tuple[dict[str, object], str]:
    # Utilise la même configuration pour SQLAlchemy et psycopg2.
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
            raise ValueError("DATABASE_URL doit désigner une base PostgreSQL.")
        config: dict[str, object] = {
            "dbname": unquote(parsed.path.lstrip("/")),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
        }
        return config, database_url.replace("postgresql+psycopg2://", "postgresql://", 1)

    config = {
        "dbname": os.getenv("POSTGRES_DB", "projet_rh"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": _positive_int("POSTGRES_PORT", 5432),
    }
    url = (
        f"postgresql://{quote_plus(str(config['user']))}:"
        f"{quote_plus(str(config['password']))}@{config['host']}:"
        f"{config['port']}/{quote_plus(str(config['dbname']))}"
    )
    return config, url


DATABASE_CONFIG, DATABASE_URL = _parse_database_config()

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DEBUG = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
JWT_TOKEN_LIFETIME_HOURS = _positive_int("JWT_TOKEN_LIFETIME_HOURS", 1)
MAX_CONTENT_LENGTH = _positive_int("MAX_CONTENT_LENGTH_MB", 10) * 1024 * 1024

_secret = os.getenv("JWT_SECRET_KEY", "").strip()
if not _secret or _secret.lower() in {
    "replace_with_a_long_random_secret", "change-me", "secret"
}:
    if APP_ENV == "production":
        raise RuntimeError("JWT_SECRET_KEY doit être défini avec une valeur forte en production.")
    _secret = secrets.token_urlsafe(48)
    warnings.warn(
        "JWT_SECRET_KEY non configuré : une clé temporaire est utilisée. "
        "Définissez une clé stable dans backend/.env.",
        RuntimeWarning,
        stacklevel=2,
    )
JWT_SECRET_KEY = _secret
if APP_ENV == "production" and len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY doit contenir au moins 32 caractères en production.")
if APP_ENV == "production" and DEBUG:
    raise RuntimeError("FLASK_DEBUG doit être désactivé en production.")

_default_origins = "http://localhost:4200,http://127.0.0.1:4200"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

DATA_DIR = BASE_DIR / "data"
CV_TRAINING_DATA_DIR = DATA_DIR / "cv_matching" / "training"
PROFILE_RAW_DATA_DIR = DATA_DIR / "profiles" / "raw"
PROFILE_PROCESSED_DATA_DIR = DATA_DIR / "profiles" / "processed"
CV_MATCHING_DIR = BASE_DIR / "ml" / "cv_matching"
CV_MODEL_DIR = CV_MATCHING_DIR / "artifacts"
CV_CANDIDATES_DIR = CV_MODEL_DIR / "candidates"
PROFILE_PIPELINE_DIR = BASE_DIR / "ml" / "profiles_pipeline"
PROFILE_MODEL_DIR = PROFILE_PIPELINE_DIR / "artifacts"
STORAGE_DIR = BASE_DIR / "storage"
TEMP_CV_DIR = STORAGE_DIR / "temp_cv"
OUTPUTS_DIR = STORAGE_DIR / "outputs"

for _directory in (
    CV_TRAINING_DATA_DIR,
    PROFILE_RAW_DATA_DIR,
    PROFILE_PROCESSED_DATA_DIR,
    CV_MODEL_DIR,
    CV_CANDIDATES_DIR,
    PROFILE_MODEL_DIR,
    TEMP_CV_DIR,
    OUTPUTS_DIR,
):
    _directory.mkdir(parents=True, exist_ok=True)
