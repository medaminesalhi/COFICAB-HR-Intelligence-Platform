from config import (
    CV_MODEL_DIR, CV_TRAINING_DATA_DIR, DATABASE_CONFIG, OUTPUTS_DIR,
    PROFILE_MODEL_DIR, PROFILE_PROCESSED_DATA_DIR, PROFILE_RAW_DATA_DIR, TEMP_CV_DIR
)


def test_project_directories_exist():
    for path in (CV_MODEL_DIR, CV_TRAINING_DATA_DIR, PROFILE_MODEL_DIR,
                 PROFILE_RAW_DATA_DIR, PROFILE_PROCESSED_DATA_DIR, OUTPUTS_DIR, TEMP_CV_DIR):
        assert path.is_dir()


def test_database_config_has_required_keys():
    assert {"dbname", "user", "password", "host", "port"}.issubset(DATABASE_CONFIG)
