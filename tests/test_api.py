"""Tests E2E pour l'API FastAPI RamyPulse.

Couvre tous les routeurs Phase 2 : health, dashboard, campaigns,
alerts, watchlists, recommendations, explorer.
Utilise la base SQLite du projet avec initialisation complète du schema.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import config

# Ensure all tables exist before importing the app
from core.database import DatabaseManager

_db = DatabaseManager()
_db.create_tables()

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Connexion directe à la DB de test pour setup/teardown."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _seed_campaign(name: str = "Test Campaign", status: str = "planned") -> str:
    """Insère une campagne directement en base et retourne son ID."""
    from core.campaigns.campaign_manager import create_campaign
    return create_campaign({
        "campaign_name": name,
        "campaign_type": "influencer",
        "platform": "instagram",
        "status": status,
    })


def _seed_alert(
    title: str = "Test Alert",
    severity: str = "critical",
) -> str | None:
    """Insère une alerte directement en base et retourne son ID."""
    from core.alerts.alert_manager import create_alert
    return create_alert(
        title=title,
        description="Alerte de test pour le suite E2E",
        severity=severity,
        alert_payload={"metric": "nss", "value": -40},
        dedup_key=str(uuid.uuid4()),
    )


def _seed_watchlist(name: str = "Test Watchlist") -> str:
    """Insère une watchlist en base et retourne son ID."""
    from core.watchlists.watchlist_manager import create_watchlist
    return create_watchlist(
        name=name,
        description="Watchlist de test",
        scope_type="product",
        filters={"aspect": "goût"},
    )


def _seed_recommendation() -> str:
    """Insère une recommandation en base et retourne son ID."""
    from core.recommendation.recommendation_manager import save_recommendation
    return save_recommendation(
        result={
            "analysis_summary": "NSS en baisse sur disponibilité.",
            "recommendations": [
                {"id": "rec_001", "priority": "high", "title": "Campagne Instagram"},
            ],
            "watchlist_priorities": ["NSS Oran"],
            "confidence_score": 0.8,
            "data_quality_note": "Données suffisantes.",
            "provider_used": "ollama_local",
            "model_used": "qwen2.5:14b",
            "generation_ms": 3200,
            "parse_success": True,
        },
        trigger_type="manual",
        trigger_id=None,
    )


# ===========================================================================
# Health
# ===========================================================================

class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "degraded")


# ===========================================================================
# Dashboard
# ===========================================================================

class TestDashboard:
    def test_summary_structure(self):
        r = client.get("/api/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert "health_score" in data
        assert "health_trend" in data
        assert data["health_trend"] in ("up", "down", "flat")
        assert "nss_progress_pts" in data
        assert "summary_text" in data

    def test_summary_graceful_on_empty_db(self):
        """Un DB vide doit retourner un fallback propre, pas un 500."""
        r = client.get("/api/dashboard/summary")
        assert r.status_code == 200
        assert isinstance(r.json()["health_score"], int)

    def test_critical_alerts_structure(self):
        r = client.get("/api/dashboard/alerts-critical")
        assert r.status_code == 200
        data = r.json()
        assert "critical_alerts" in data
        assert isinstance(data["critical_alerts"], list)

    def test_top_actions_structure(self):
        r = client.get("/api/dashboard/top-actions")
        assert r.status_code == 200
        data = r.json()
        assert "top_actions" in data
        assert isinstance(data["top_actions"], list)


# ===========================================================================
# Campaigns
# ===========================================================================

class TestCampaigns:
    def test_create_campaign(self):
        r = client.post("/api/campaigns", json={
            "campaign_name": "API Test Campaign",
            "campaign_type": "paid_ad",
            "platform": "facebook",
        })
        assert r.status_code == 200
        data = r.json()
        assert "campaign_id" in data
        assert data["status"] == "created"

    def test_list_campaigns(self):
        _seed_campaign("List Test")
        r = client.get("/api/campaigns")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_campaigns_filter_status(self):
        _seed_campaign("Active Camp", status="active")
        r = client.get("/api/campaigns?status=active")
        assert r.status_code == 200
        for c in r.json():
            assert c["status"] == "active"

    def test_get_campaign_detail(self):
        cid = _seed_campaign("Detail Test")
        r = client.get(f"/api/campaigns/{cid}")
        assert r.status_code == 200
        assert r.json()["campaign_id"] == cid

    def test_get_campaign_404(self):
        r = client.get("/api/campaigns/nonexistent-uuid")
        assert r.status_code == 404

    def test_update_campaign_status(self):
        cid = _seed_campaign("Status Test")
        r = client.put(f"/api/campaigns/{cid}/status", json={"status": "active"})
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_delete_campaign(self):
        cid = _seed_campaign("Delete Test")
        r = client.delete(f"/api/campaigns/{cid}")
        assert r.status_code == 200
        # Verify it's actually gone
        r2 = client.get(f"/api/campaigns/{cid}")
        assert r2.status_code == 404


# ===========================================================================
# Alerts
# ===========================================================================

class TestAlerts:
    def test_list_alerts(self):
        _seed_alert("List Alert")
        r = client.get("/api/alerts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_alerts_filter_severity(self):
        _seed_alert("Critical Alert", severity="critical")
        r = client.get("/api/alerts?severity=critical")
        assert r.status_code == 200
        for a in r.json():
            assert a["severity"] == "critical"

    def test_list_alerts_filter_status(self):
        r = client.get("/api/alerts?status=new")
        assert r.status_code == 200

    def test_list_alerts_invalid_status_returns_400(self):
        r = client.get("/api/alerts?status=INVALID_STATUS")
        assert r.status_code == 400

    def test_get_alert_detail(self):
        aid = _seed_alert("Detail Alert")
        assert aid is not None
        r = client.get(f"/api/alerts/{aid}")
        assert r.status_code == 200
        assert r.json()["alert_id"] == aid

    def test_get_alert_404(self):
        r = client.get("/api/alerts/nonexistent-uuid")
        assert r.status_code == 404

    def test_update_alert_status(self):
        aid = _seed_alert("Update Alert")
        assert aid is not None
        r = client.put(f"/api/alerts/{aid}/status", json={"status": "acknowledged"})
        assert r.status_code == 200
        assert r.json()["status"] == "acknowledged"

    def test_update_alert_invalid_status(self):
        aid = _seed_alert("Invalid Status Alert")
        assert aid is not None
        r = client.put(f"/api/alerts/{aid}/status", json={"status": "BOGUS"})
        assert r.status_code == 400


# ===========================================================================
# Watchlists
# ===========================================================================

class TestWatchlists:
    def test_list_watchlists(self):
        _seed_watchlist("List WL")
        r = client.get("/api/watchlists")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_watchlists_inactive(self):
        r = client.get("/api/watchlists?is_active=false")
        assert r.status_code == 200

    def test_get_watchlist_detail(self):
        wid = _seed_watchlist("Detail WL")
        r = client.get(f"/api/watchlists/{wid}")
        assert r.status_code == 200
        assert r.json()["watchlist_id"] == wid

    def test_get_watchlist_404(self):
        r = client.get("/api/watchlists/nonexistent-uuid")
        assert r.status_code == 404

    def test_get_watchlist_metrics_404(self):
        """Pas de snapshot pour cette watchlist — doit retourner 404."""
        wid = _seed_watchlist("No Metrics WL")
        r = client.get(f"/api/watchlists/{wid}/metrics")
        assert r.status_code == 404


# ===========================================================================
# Recommendations
# ===========================================================================

class TestRecommendations:
    def test_get_providers(self):
        r = client.get("/api/recommendations/providers")
        assert r.status_code == 200
        assert "providers" in r.json()

    def test_context_preview(self):
        r = client.get("/api/recommendations/context-preview")
        assert r.status_code == 200
        data = r.json()
        assert "estimated_tokens" in data
        assert "trigger" in data

    def test_list_recommendations(self):
        r = client.get("/api/recommendations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_recommendations_filter_status(self):
        _seed_recommendation()
        r = client.get("/api/recommendations?status=active")
        assert r.status_code == 200
        for rec in r.json():
            assert rec["status"] == "active"

    def test_get_recommendation_detail(self):
        rid = _seed_recommendation()
        r = client.get(f"/api/recommendations/{rid}")
        assert r.status_code == 200
        assert r.json()["recommendation_id"] == rid
        assert isinstance(r.json()["recommendations"], list)

    def test_get_recommendation_404(self):
        r = client.get("/api/recommendations/nonexistent-uuid")
        assert r.status_code == 404

    def test_update_recommendation_status(self):
        rid = _seed_recommendation()
        r = client.put(
            f"/api/recommendations/{rid}/status",
            json={"status": "archived"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "archived"

    def test_update_recommendation_invalid_status(self):
        rid = _seed_recommendation()
        r = client.put(
            f"/api/recommendations/{rid}/status",
            json={"status": "INVALID"},
        )
        assert r.status_code == 400

    def test_generate_recommendations_mock(self):
        """Test de génération avec mock du LLM et mock du Parquet."""
        mock_result = {
            "analysis_summary": "Test résumé.",
            "recommendations": [{"id": "rec_mock", "priority": "high", "title": "Mock"}],
            "watchlist_priorities": [],
            "confidence_score": 0.75,
            "data_quality_note": "Test data.",
            "provider_used": "ollama_local",
            "model_used": "test-model",
            "generation_ms": 100,
            "parse_success": True,
        }

        # Create a minimal mock DataFrame for the Parquet loader
        mock_df = pd.DataFrame({
            "text": ["bon produit"] * 10,
            "sentiment_label": ["positif"] * 5 + ["négatif"] * 5,
            "channel": ["facebook"] * 10,
            "aspect": ["goût"] * 10,
            "timestamp": pd.date_range("2026-01-01", periods=10, freq="D"),
            "source_url": [""] * 10,
            "confidence": [0.9] * 10,
        })

        with patch("api.routers.recommendations.load_annotated", return_value=mock_df), \
             patch(
                 "core.recommendation.agent_client.generate_recommendations",
                 return_value=mock_result,
             ):
            r = client.post("/api/recommendations/generate", json={
                "trigger_type": "manual",
                "provider": "ollama_local",
            })

        assert r.status_code == 200
        data = r.json()
        assert data["result"] == "success"
        assert "recommendation_id" in data


# ===========================================================================
# Explorer
# ===========================================================================

class TestExplorer:
    def test_search_returns_results(self):
        r = client.get("/api/explorer/search?q=ramy")
        assert r.status_code == 200
        data = r.json()
        assert "query" in data
        assert "results" in data
        assert data["query"] == "ramy"

    def test_search_empty_query_returns_400(self):
        r = client.get("/api/explorer/search?q=")
        assert r.status_code == 400

    def test_verbatims_default_pagination(self):
        r = client.get("/api/explorer/verbatims")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1

    def test_verbatims_with_filters(self):
        r = client.get("/api/explorer/verbatims?channel=facebook&page=1&page_size=10")
        assert r.status_code == 200
        data = r.json()
        assert data["page_size"] == 10

    def test_verbatims_pagination(self):
        r1 = client.get("/api/explorer/verbatims?page=1&page_size=5")
        r2 = client.get("/api/explorer/verbatims?page=2&page_size=5")
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Pages should be different (if enough data) or both valid
        assert r1.json()["page"] == 1
        assert r2.json()["page"] == 2
