from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_summary_endpoint():
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_accounts" in data
