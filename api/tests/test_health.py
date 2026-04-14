from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_includes_services():
    response = client.get("/health")
    data = response.json()
    assert "services" in data
    for svc in ("postgres", "redis", "minio"):
        assert svc in data["services"]
