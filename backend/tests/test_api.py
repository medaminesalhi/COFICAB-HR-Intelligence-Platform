"""Tests de fumée API ; ignorés si les dépendances Flask ne sont pas installées."""
import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_cors")
pytest.importorskip("flask_sqlalchemy")
pytest.importorskip("flask_jwt_extended")
pytest.importorskip("passlib")
pytest.importorskip("psycopg2")

from app import create_app


@pytest.fixture()
def client():
    app = create_app({
        "TESTING": True,
        "JWT_SECRET_KEY": "test-secret-key-not-for-production",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_is_available(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/api/scrape_cv", "/api/predict_match", "/api/save_profile"])
def test_cv_endpoints_require_authentication(client, path):
    response = client.post(path, json={})
    assert response.status_code == 401
