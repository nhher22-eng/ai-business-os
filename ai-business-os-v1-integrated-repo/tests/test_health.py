from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "running"
    assert body["version"] == "1.0.0"
    assert body["docs"] == "/docs"
