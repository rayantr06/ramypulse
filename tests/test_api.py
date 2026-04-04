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

    def test_summary_exposes_stitch_fields_when_annotated_available(self):
        mock_df = pd.DataFrame(
            {
                "timestamp": [
                    "2026-03-01T10:00:00",
                    "2026-03-02T11:00:00",
                    "2026-03-03T12:00:00",
                    "2026-03-04T13:00:00",
                ],
                "wilaya": ["Alger", "Oran", "Alger", "Bejaia"],
                "product": ["Ramy Citron", "Ramy Citron", "Ramy Orange", "Ramy Fraise"],
                "sentiment_label": ["positif", "negatif", "positif", "positif"],
            }
        )

        with patch("api.routers.dashboard.load_annotated", return_value=mock_df):
            r = client.get("/api/dashboard/summary")

        assert r.status_code == 200
        data = r.json()
        assert data["total_mentions"] == 4
        assert isinstance(data["regional_distribution"], list)
        assert data["regional_distribution"][0]["wilaya"] == "Alger"
        assert isinstance(data["product_performance"], list)
        assert data["product_performance"][0]["product"]

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
        if data["top_actions"]:
            assert "description" in data["top_actions"][0]
            assert "confidence_score" in data["top_actions"][0]


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

    def test_get_campaign_impact(self):
        cid = _seed_campaign("Impact Test")
        with _get_connection() as conn:
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, end_date = ?
                WHERE campaign_id = ?
                """,
                ("2026-01-10", "2026-01-15", cid),
            )
            conn.commit()

        mock_df = pd.DataFrame(
            {
                "text": ["bon produit", "produit moyen", "super gout"],
                "sentiment_label": ["positif", "neutre", "positif"],
                "channel": ["instagram", "instagram", "instagram"],
                "aspect": ["goût", "goût", "goût"],
                "timestamp": ["2026-01-11", "2026-01-12", "2026-01-18"],
                "source_url": ["", "", ""],
                "confidence": [0.9, 0.7, 0.95],
            }
        )

        impact_client = TestClient(app, raise_server_exceptions=False)
        with patch("api.routers.campaigns.load_annotated", return_value=mock_df):
            r = impact_client.get(f"/api/campaigns/{cid}/impact")

        assert r.status_code == 200
        data = r.json()
        assert data["campaign_id"] == cid
        assert "phases" in data
        assert "pre" in data["phases"]
        assert "active" in data["phases"]
        assert "post" in data["phases"]


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

    def test_create_watchlist(self):
        r = client.post("/api/watchlists", json={
            "name": "Watchlist Alger Sud",
            "description": "Suivi NSS Alger Sud",
            "scope_type": "region",
            "filters": {"wilaya": "alger"},
        })
        assert r.status_code == 201
        data = r.json()
        assert "watchlist_id" in data
        assert data["status"] == "created"

    def test_create_watchlist_missing_name(self):
        r = client.post("/api/watchlists", json={
            "name": "",
            "scope_type": "product",
        })
        assert r.status_code == 422

    def test_update_watchlist(self):
        wid = _seed_watchlist("To Update")
        r = client.put(f"/api/watchlists/{wid}", json={"name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["status"] == "updated"
        detail = client.get(f"/api/watchlists/{wid}").json()
        assert detail["watchlist_name"] == "Updated Name"

    def test_update_watchlist_404(self):
        r = client.put("/api/watchlists/nonexistent-uuid", json={"name": "X"})
        assert r.status_code == 404

    def test_deactivate_watchlist(self):
        wid = _seed_watchlist("To Deactivate")
        r = client.delete(f"/api/watchlists/{wid}")
        assert r.status_code == 204
        detail = client.get(f"/api/watchlists/{wid}").json()
        assert not detail["is_active"]

    def test_deactivate_watchlist_404(self):
        r = client.delete("/api/watchlists/nonexistent-uuid")
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


# ===========================================================================
# Admin
# ===========================================================================

class TestAdmin:
    def test_create_source(self):
        r = client.post("/api/admin/sources", json={
            "source_name": "Test Facebook Page",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        assert r.status_code == 200
        data = r.json()
        assert "source_id" in data
        assert data["source_name"] == "Test Facebook Page"

    def test_list_sources(self):
        r = client.get("/api/admin/sources")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_source_trace(self):
        # Create one first
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Detail Source",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]

        r = client.get(f"/api/admin/sources/{sid}")
        assert r.status_code == 200
        data = r.json()
        assert data["source_id"] == sid
        assert "latest_sync_run" in data

    def test_get_source_404(self):
        r = client.get("/api/admin/sources/nonexistent-source")
        assert r.status_code == 404

    def test_update_source(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Update Source",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]

        r = client.put(f"/api/admin/sources/{sid}", json={
            "is_active": False,
            "sync_frequency_minutes": 120
        })
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] == 0 # SQLite returns 0 for False
        assert data["sync_frequency_minutes"] == 120

    def test_trigger_source_health(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Health Source",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]

        r = client.post(f"/api/admin/sources/{sid}/health")
        assert r.status_code == 200
        data = r.json()
        assert "snapshot_id" in data
        assert "health_score" in data

    def test_trigger_source_sync_mock(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Sync Source",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]

        mock_docs = [
            {
                "external_document_id": "doc1",
                "raw_text": "text1",
                "raw_payload": {},
                "raw_metadata": {},
                "collected_at": "2026-01-01T00:00:00Z",
                "checksum_sha256": "hash1"
            }
        ]

        with patch("core.connectors.batch_import_connector.BatchImportConnector.fetch_documents", return_value=mock_docs):
            r = client.post(f"/api/admin/sources/{sid}/sync", json={
                "run_mode": "manual"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "success"
            assert data["records_inserted"] == 1

    def test_trigger_source_sync_failure_mock(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Sync Fail Source",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]

        with patch("core.connectors.batch_import_connector.BatchImportConnector.fetch_documents", side_effect=Exception("API limit reached")):
            r = client.post(f"/api/admin/sources/{sid}/sync", json={})
            # FastAPI returns 500 when orchestrator raises the error
            assert r.status_code == 500
            assert "API limit" in r.json()["detail"]

    def test_list_sync_runs(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Run List",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]
        r = client.get(f"/api/admin/sources/{sid}/runs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_health_snapshots(self):
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Snap List",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
        })
        sid = r_create.json()["source_id"]
        r = client.get(f"/api/admin/sources/{sid}/snapshots")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_trigger_normalization(self):
        with patch("api.routers.admin.IngestionOrchestrator.run_normalization_cycle", return_value={"status": "success", "processed": 5}):
            r = client.post("/api/admin/normalization", json={
                "batch_size": 200
            })
            assert r.status_code == 200
            assert r.json()["status"] == "success"
