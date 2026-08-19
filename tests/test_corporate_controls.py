from fastapi.testclient import TestClient

from api.main import app
from src.shared.models import init_db


def test_security_headers_and_request_id():
    init_db()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_audit_requires_privileged_role():
    init_db()
    client = TestClient(app)
    login = client.post("/api/v1/auth/dev-login", json={"email": "auditor-test@example.com", "display_name": "Auditor"})
    assert login.status_code == 200
    token = login.json()["token"]
    response = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
