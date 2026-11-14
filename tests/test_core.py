"""Tests for core API and web endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_healthz() -> None:
    """Test that /healthz returns status 200 and {'status': 'ok'}."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page() -> None:
    """Test that GET / returns 200 and contains the expected base UI elements."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Trailmark" in response.text
    assert "Demo uses synthetic data. Do not upload confidential files." in response.text
