from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_run_rejects_empty_task():
    response = client.post("/api/v1/runs", json={"task": ""})
    assert response.status_code == 422


def test_run_rejects_missing_task():
    response = client.post("/api/v1/runs", json={})
    assert response.status_code == 422


def test_run_rejects_oversized_task():
    response = client.post("/api/v1/runs", json={"task": "x" * 10001})
    assert response.status_code == 422
