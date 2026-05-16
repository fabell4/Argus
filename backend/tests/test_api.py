from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_power_summary() -> None:
    response = client.get("/api/v1/power/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "daily_kwh" in payload
    assert "weekly_kwh" in payload
    assert "monthly_kwh" in payload
