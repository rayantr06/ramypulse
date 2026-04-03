import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "degraded"]
    
def test_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    assert "health_score" in response.json()

def test_dashboard_alerts():
    response = client.get("/api/dashboard/alerts-critical")
    assert response.status_code == 200
    assert "critical_alerts" in response.json()
    
def test_dashboard_actions():
    response = client.get("/api/dashboard/top-actions")
    assert response.status_code == 200
    assert "top_actions" in response.json()

def test_providers():
    response = client.get("/api/recommendations/providers")
    assert response.status_code == 200
    assert "providers" in response.json()

def test_list_campaigns():
    response = client.get("/api/campaigns")
    assert response.status_code == 200

def test_context_preview():
    response = client.get("/api/recommendations/context-preview")
    assert response.status_code == 200
    
def test_explorer_search():
    # Will likely return 200 with 0 results if no index
    response = client.get("/api/explorer/search?q=test")
    assert response.status_code == 200
