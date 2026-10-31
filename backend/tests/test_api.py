"""
Integration Tests for REST API Endpoints.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"


def test_dashboard_summary_endpoint():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "overall_match_rate" in data
    assert "exceptions_by_category" in data


def test_audit_verify_endpoint():
    response = client.get("/api/v1/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert "is_valid" in data


def test_reconops_state_endpoint():
    response = client.get("/api/v1/reconops/state")
    assert response.status_code == 200
    data = response.json()
    assert "badges" in data
    assert "campaign_levels" in data
