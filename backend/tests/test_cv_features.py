import pandas as pd
import pytest

from ml.cv_matching.features import build_feature_frame, normalize_skill_list
from ml.cv_matching.train_cv import validate_dataset


def _valid_frame(rows=4):
    return pd.DataFrame({
        "jobtitle": ["Data Engineer"] * rows,
        "skills": ["python, sql"] * rows,
        "location": ["Tunis"] * rows,
        "experience": [2, 3, 1, 4][:rows],
        "poste_rh": ["data engineer"] * rows,
        "skills_rh": ["python, spark"] * rows,
        "location_rh": ["Tunis"] * rows,
        "exp_min": [2] * rows,
        "recrute": [0, 1, 0, 1][:rows],
    })


def test_validate_dataset_checks_required_columns_and_binary_labels():
    frame = validate_dataset(_valid_frame())
    assert len(frame) == 4
    assert set(frame["recrute"]) == {0, 1}


def test_validate_dataset_rejects_missing_column():
    frame = _valid_frame().drop(columns=["skills_rh"])
    with pytest.raises(ValueError, match="skills_rh"):
        validate_dataset(frame)


def test_build_feature_frame_creates_expected_columns():
    frame = validate_dataset(_valid_frame())
    features = build_feature_frame(frame)
    assert list(features.columns) == [
        "skills_text", "job_text", "location_text", "experience", "exp_min"
    ]
    assert features.loc[0, "skills_text"] == "python sql python spark"
    assert features.loc[0, "job_text"] == "data engineer data engineer"


def test_skill_matching_uses_complete_skill_phrases():
    skills = normalize_skill_list(["Power BI", "SQL", "Node.js"])
    assert "power bi" in skills
    assert "node.js" in skills
    assert "java" not in skills
