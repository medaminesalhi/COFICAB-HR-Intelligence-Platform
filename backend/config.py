"""Configuration commune du backend COFICAB.

Les secrets doivent être configurés dans un fichier .env local (non versionné)
ou dans les variables d’environnement du système d’exécution.
"""
from pathlib import Path
from urllib.parse import quote_plus
import os
import secrets
import warnings

BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # Les variables d'environnement système restent utilisables sans python-dotenv.
    pass

DATA_DIR = BASE_DIR / "data"
CV_TRAINING_DATA_DIR = DATA_DIR / "cv_matching" / "training"
PROFILE_RAW_DATA_DIR = DATA_DIR / "profiles" / "raw"
PROFILE_PROCESSED_DATA_DIR = DATA_DIR / "profiles" / "processed"
CV_MATCHING_DIR = BASE_DIR / "ml" / "cv_matching"
CV_MODEL_DIR = CV_MATCHING_DIR / "artifacts"
PROFILE_PIPELINE_DIR = BASE_DIR / "ml" / "profiles_pipeline"
PROFILE_MODEL_DIR = PROFILE_PIPELINE_DIR / "artifacts"
STORAGE_DIR = BASE_DIR / "storage"
TEMP_CV_DIR = STORAGE_DIR / "temp_cv"
OUTPUTS_DIR = STORAGE_DIR / "outputs"

for _directory in (CV_TRAINING_DATA_DIR, PROFILE_RAW_DATA_DIR, PROFILE_PROCESSED_DATA_DIR,
                   CV_MODEL_DIR, PROFILE_MODEL_DIR, TEMP_CV_DIR, OUTPUTS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

DATABASE_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "projet_rh"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
}

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    _user = quote_plus(DATABASE_CONFIG["user"])
    _password = quote_plus(DATABASE_CONFIG["password"])
    _host = DATABASE_CONFIG["host"]
    _port = DATABASE_CONFIG["port"]
    _dbname = quote_plus(DATABASE_CONFIG["dbname"])
    DATABASE_URL = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_dbname}"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    JWT_SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn(
        "JWT_SECRET_KEY absent : une clé temporaire est générée. Configurez .env "
        "pour conserver la validité des tokens entre redémarrages.",
        RuntimeWarning,
    )

JWT_TOKEN_LIFETIME_HOURS = int(os.getenv("JWT_TOKEN_LIFETIME_HOURS", "1"))
DEBUG = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
