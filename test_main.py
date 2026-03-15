"""
Smoke tests for the QMS-Graph backend API.
Requires: pip install httpx pytest
Run with: pytest test_main.py -v
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the root endpoint returns a healthy status message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "QMS Tool API running"}


def test_stereotypes_endpoint():
    """Test that the stereotypes endpoint returns SysML relationship types."""
    response = client.get("/requirements/stereotypes")
    assert response.status_code == 200
    data = response.json()
    assert "stereotypes" in data
    assert "block_types" in data
    assert "trace" in data["stereotypes"]
