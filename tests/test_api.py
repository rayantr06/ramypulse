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
from datetime import date
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

# Create a test API key for authenticated requests
from core.security.auth import create_api_key as _create_test_key
_test_key_id, _test_raw_key = _create_test_key(client_id="ramy_client_001", label="test_suite")
_AUTH_HEADERS = {"X-API-Key": _test_raw_key}

_raw_client = TestClient(app)


class _AuthClient:
    """Wrapper that auto-injects X-API-Key on every request."""

    def __init__(self, tc: TestClient, headers: dict):
        self._tc = tc
        self._headers = headers

    def _merge(self, kwargs: dict) -> dict:
        h = dict(self._headers)
        h.update(kwargs.pop("headers", {}))
        kwargs["headers"] = h
        return kwargs

    def get(self, url, **kw):
        return self._tc.get(url, **self._merge(kw))

    def post(self, url, **kw):
        return self._tc.post(url, **self._merge(kw))

    def put(self, url, **kw):
        return self._tc.put(url, **self._merge(kw))

    def patch(self, url, **kw):
        return self._tc.patch(url, **self._merge(kw))

    def delete(self, url, **kw):
        return self._tc.delete(url, **self._merge(kw))


client = _AuthClient(_raw_client, _AUTH_HEADERS)


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

    def test_status_returns_real_monitoring_fields(self):
        r = client.get("/api/status")
        assert r.status_code == 200
        data = r.json()
        assert data["api_status"] in ("Normal", "Dégradé", "Erreur")
        assert data["db_status"] in ("connected", "missing", "error", "unreachable")
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0


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

    def test_campaign_stats_returns_quarterly_budget_fields(self):
        baseline = client.get("/api/campaigns/stats")
        assert baseline.status_code == 200
        baseline_data = baseline.json()

        today = date.today()
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        quarter_date = today.replace(month=quarter_start_month, day=1).isoformat()

        previous_quarter_month = 12 if quarter_start_month == 1 else quarter_start_month - 1
        previous_quarter_year = today.year - 1 if quarter_start_month == 1 else today.year
        previous_quarter_date = date(previous_quarter_year, previous_quarter_month, 1).isoformat()

        active_id = _seed_campaign("Quarter Active", status="active")
        planned_id = _seed_campaign("Quarter Planned", status="planned")
        archived_id = _seed_campaign("Previous Quarter", status="completed")

        with _get_connection() as conn:
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, budget_dza = ?
                WHERE campaign_id = ?
                """,
                (quarter_date, 1000000, active_id),
            )
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, budget_dza = ?
                WHERE campaign_id = ?
                """,
                (quarter_date, 250000, planned_id),
            )
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, budget_dza = ?
                WHERE campaign_id = ?
                """,
                (previous_quarter_date, 999999, archived_id),
            )
            conn.commit()

        r = client.get("/api/campaigns/stats")
        assert r.status_code == 200
        data = r.json()
        assert (
            data["quarterly_budget_committed"] - baseline_data["quarterly_budget_committed"]
            == 1000000
        )
        assert (
            data["quarterly_budget_allocation"] - baseline_data["quarterly_budget_allocation"]
            == 1250000
        )
        assert "quarter_label" in data

    def test_campaign_overview_returns_top_performer_bundle(self):
        today = date.today()
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        quarter_date = today.replace(month=quarter_start_month, day=1).isoformat()

        top_id = _seed_campaign("Overview Winner", status="active")
        other_id = _seed_campaign("Overview Secondary", status="active")
        _seed_campaign("Overview Planned", status="planned")

        with _get_connection() as conn:
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, budget_dza = ?, influencer_handle = ?, platform = ?
                WHERE campaign_id = ?
                """,
                (quarter_date, 1500000, "@winner", "instagram", top_id),
            )
            conn.execute(
                """
                UPDATE campaigns
                SET start_date = ?, budget_dza = ?, influencer_handle = ?, platform = ?
                WHERE campaign_id = ?
                """,
                (quarter_date, 500000, "@secondary", "facebook", other_id),
            )
            conn.commit()

        r = client.get("/api/campaigns/overview")
        assert r.status_code == 200
        data = r.json()
        assert "quarterly_budget_committed" in data
        assert "quarterly_budget_allocation" in data
        assert "quarter_label" in data
        assert data["active_campaigns_count"] >= 2
        assert data["top_performer"]["campaign_id"] == top_id
        assert data["top_performer"]["influencer_handle"] == "@winner"
        assert data["top_performer"]["platform"] == "instagram"
        assert data["top_performer"]["budget_dza"] == 1500000
        assert data["top_performer"]["roi_pct"] is None
        assert data["top_performer"]["engagement_rate"] is None

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
            r = impact_client.get(f"/api/campaigns/{cid}/impact", headers=_AUTH_HEADERS)

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

    def test_context_preview_estimates_prompt_cost_for_selected_model(self):
        mock_ctx = {
            "estimated_tokens": 4000,
            "current_metrics": {"nss_global": 18.5, "volume_total": 240},
            "active_alerts": [{"id": "a1"}],
            "active_watchlists": [{"id": "w1"}, {"id": "w2"}],
            "recent_campaigns": [{"id": "c1"}],
        }

        with patch(
            "api.routers.recommendations.context_builder.build_recommendation_context",
            return_value=mock_ctx,
        ), patch(
            "api.routers.recommendations.load_annotated",
            return_value=pd.DataFrame(),
        ):
            r = client.get(
                "/api/recommendations/context-preview"
                "?trigger_type=manual&provider=openai&model=gpt-4o"
            )

        assert r.status_code == 200
        data = r.json()
        assert data["estimated_tokens"] == 4000
        assert data["estimated_cost_usd"] == 0.01

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

    def test_search_falls_back_to_annotated_corpus_when_faiss_is_missing(self):
        mock_df = pd.DataFrame(
            {
                "text": ["gout excellent ramy", "prix trop eleve"],
                "sentiment_label": ["positif", "negatif"],
                "channel": ["facebook", "facebook"],
                "aspect": ["gout", "prix"],
                "timestamp": ["2026-04-01T10:00:00Z", "2026-04-01T11:00:00Z"],
                "source_url": ["https://fb/1", "https://fb/2"],
            }
        )

        from api.routers import explorer as explorer_router

        previous = explorer_router._retriever
        explorer_router._retriever = None
        try:
            with patch("api.routers.explorer.os.path.exists", return_value=False), patch(
                "api.routers.explorer.load_annotated", return_value=mock_df
            ):
                r = client.get("/api/explorer/search?q=gout")
        finally:
            explorer_router._retriever = previous

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert data["results"][0]["aspect"] == "gout"
        assert data["results"][0]["sentiment_label"] == "positif"
        assert data["results"][0]["source_url"] == "https://fb/1"

    def test_get_retriever_recharge_l_index_si_faiss_apparait_apres_un_fallback(self):
        mock_df = pd.DataFrame(
            {
                "text": ["gout excellent ramy"],
                "sentiment_label": ["positif"],
                "channel": ["facebook"],
                "aspect": ["gout"],
                "timestamp": ["2026-04-01T10:00:00Z"],
                "source_url": ["https://fb/fallback"],
            }
        )

        from api.routers import explorer as explorer_router
        from core.rag.vector_store import VectorStore

        previous = explorer_router._retriever
        previous_signature = getattr(explorer_router, "_retriever_signature", None)
        explorer_router._retriever = None
        if hasattr(explorer_router, "_retriever_signature"):
            explorer_router._retriever_signature = None

        dense_store = VectorStore()
        dense_store.metadata = [
            {
                "text": "dense faiss result",
                "channel": "facebook",
                "source_url": "https://fb/dense",
                "timestamp": "2026-04-02T08:00:00Z",
            }
        ]

        created = []

        class FakeRetriever:
            def __init__(self, *, vector_store, embedder):
                self.vector_store = vector_store
                self.embedder = embedder
                created.append(self)

        exists_side_effect = [False, True, True, True, True]

        try:
            with patch("api.routers.explorer.load_annotated", return_value=mock_df), patch(
                "api.routers.explorer.os.path.exists", side_effect=exists_side_effect
            ), patch("api.routers.explorer.VectorStore.load", return_value=dense_store), patch(
                "api.routers.explorer.Embedder", return_value=object()
            ), patch("api.routers.explorer.Retriever", FakeRetriever):
                first = explorer_router._get_retriever()
                second = explorer_router._get_retriever()
        finally:
            explorer_router._retriever = previous
            if hasattr(explorer_router, "_retriever_signature"):
                explorer_router._retriever_signature = previous_signature

        assert len(created) == 2
        assert first is not second
        assert first.vector_store.ntotal == 0
        assert second.vector_store is dense_store

    def test_get_retriever_reutilise_le_cache_fallback_si_la_signature_finale_est_stable(self):
        mock_df = pd.DataFrame(
            {
                "text": ["gout excellent ramy"],
                "sentiment_label": ["positif"],
                "channel": ["facebook"],
                "aspect": ["gout"],
                "timestamp": ["2026-04-01T10:00:00Z"],
                "source_url": ["https://fb/fallback"],
            }
        )

        from api.routers import explorer as explorer_router

        previous = explorer_router._retriever
        previous_signature = getattr(explorer_router, "_retriever_signature", None)
        explorer_router._retriever = None
        if hasattr(explorer_router, "_retriever_signature"):
            explorer_router._retriever_signature = None

        created = []

        class FakeRetriever:
            def __init__(self, *, vector_store, embedder):
                self.vector_store = vector_store
                self.embedder = embedder
                created.append(self)

        try:
            with patch("api.routers.explorer.os.path.exists", return_value=False), patch(
                "api.routers.explorer.load_annotated", return_value=mock_df
            ), patch(
                "api.routers.explorer._get_fallback_signature",
                side_effect=[("fallback", 1, 1), ("fallback", 2, 2), ("fallback", 2, 2)],
            ), patch("api.routers.explorer.Embedder", return_value=object()), patch(
                "api.routers.explorer.Retriever", FakeRetriever
            ):
                first = explorer_router._get_retriever()
                second = explorer_router._get_retriever()
        finally:
            explorer_router._retriever = previous
            if hasattr(explorer_router, "_retriever_signature"):
                explorer_router._retriever_signature = previous_signature

        assert len(created) == 1
        assert first is second

    def test_get_retriever_reessaie_faiss_apres_un_echec_de_load_transitoire(self):
        mock_df = pd.DataFrame(
            {
                "text": ["gout excellent ramy"],
                "sentiment_label": ["positif"],
                "channel": ["facebook"],
                "aspect": ["gout"],
                "timestamp": ["2026-04-01T10:00:00Z"],
                "source_url": ["https://fb/fallback"],
            }
        )

        from api.routers import explorer as explorer_router
        from core.rag.vector_store import VectorStore

        previous = explorer_router._retriever
        previous_signature = getattr(explorer_router, "_retriever_signature", None)
        explorer_router._retriever = None
        if hasattr(explorer_router, "_retriever_signature"):
            explorer_router._retriever_signature = None

        dense_store = VectorStore()
        dense_store.metadata = [
            {
                "text": "dense faiss result",
                "channel": "facebook",
                "source_url": "https://fb/dense",
                "timestamp": "2026-04-02T08:00:00Z",
            }
        ]

        created = []

        class FakeRetriever:
            def __init__(self, *, vector_store, embedder):
                self.vector_store = vector_store
                self.embedder = embedder
                created.append(self)

        try:
            with patch("api.routers.explorer.os.path.exists", return_value=True), patch(
                "api.routers.explorer.load_annotated", return_value=mock_df
            ), patch(
                "api.routers.explorer.VectorStore.load",
                side_effect=[RuntimeError("faiss load failed"), dense_store],
            ), patch("api.routers.explorer.Embedder", return_value=object()), patch(
                "api.routers.explorer.Retriever", FakeRetriever
            ):
                first = explorer_router._get_retriever()
                second = explorer_router._get_retriever()
        finally:
            explorer_router._retriever = previous
            if hasattr(explorer_router, "_retriever_signature"):
                explorer_router._retriever_signature = previous_signature

        assert len(created) == 2
        assert first is not second
        assert first.vector_store.ntotal == 0
        assert second.vector_store is dense_store

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
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": "owned:facebook:test-facebook-page",
        })
        assert r.status_code == 200
        data = r.json()
        assert "source_id" in data
        assert data["source_name"] == "Test Facebook Page"
        assert data["source_purpose"] == "owned_content"
        assert data["source_priority"] == 1
        assert data["coverage_key"] == "owned:facebook:test-facebook-page"

    def test_list_sources(self):
        r = client.get("/api/admin/sources")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_sources_and_trace_expose_governance_fields(self):
        coverage_key = f"owned:instagram:gov-{uuid.uuid4().hex[:8]}"
        r_create = client.post("/api/admin/sources", json={
            "source_name": "Governed Source",
            "platform": "instagram",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": coverage_key,
            "credential_id": "cred-governed-001",
        })
        assert r_create.status_code == 200
        source_id = r_create.json()["source_id"]

        r_list = client.get("/api/admin/sources")
        assert r_list.status_code == 200
        row = next(item for item in r_list.json() if item["source_id"] == source_id)
        assert row["source_purpose"] == "owned_content"
        assert row["source_priority"] == 1
        assert row["coverage_key"] == coverage_key
        assert row["credential_id"] == "cred-governed-001"

        r_trace = client.get(f"/api/admin/sources/{source_id}")
        assert r_trace.status_code == 200
        trace = r_trace.json()
        assert trace["source_purpose"] == "owned_content"
        assert trace["source_priority"] == 1
        assert trace["coverage_key"] == coverage_key
        assert trace["credential_id"] == "cred-governed-001"

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
            "sync_frequency_minutes": 120,
            "source_priority": 2,
            "coverage_key": "owned:facebook:update-source",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] == 0 # SQLite returns 0 for False
        assert data["sync_frequency_minutes"] == 120
        assert data["source_priority"] == 2
        assert data["coverage_key"] == "owned:facebook:update-source"

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
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": "owned:facebook:sync-source",
        })
        sid = r_create.json()["source_id"]
        external_document_id = f"{sid}-doc1"

        mock_docs = [
            {
                "external_document_id": external_document_id,
                "raw_text": "text1",
                "raw_payload": {},
                "raw_metadata": {"source_url": f"https://facebook.com/posts/{external_document_id}"},
                "collected_at": "2026-01-01T00:00:00Z",
                "checksum_sha256": "hash1"
            }
        ]

        with patch("core.connectors.facebook_connector.FacebookConnector.fetch_documents", return_value=mock_docs):
            r = client.post(f"/api/admin/sources/{sid}/sync", json={
                "run_mode": "manual"
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "success"
            assert data["records_inserted"] == 1

        with _get_connection() as conn:
            raw_row = conn.execute(
                """
                SELECT content_item_id, platform, canonical_url, canonical_key
                FROM raw_documents
                WHERE source_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [sid],
            ).fetchone()
            item_row = conn.execute(
                """
                SELECT platform, coverage_key, external_content_id, canonical_key
                FROM content_items
                WHERE content_item_id = ?
                """,
                [raw_row["content_item_id"]],
            ).fetchone()

        assert raw_row["platform"] == "facebook"
        assert raw_row["canonical_url"] == f"https://facebook.com/posts/{external_document_id}"
        assert raw_row["canonical_key"] == f"facebook:{external_document_id}"
        assert item_row["platform"] == "facebook"
        assert item_row["coverage_key"] == "owned:facebook:sync-source"
        assert item_row["external_content_id"] == external_document_id
        assert item_row["canonical_key"] == f"facebook:{external_document_id}"

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

    def test_runtime_cycle_endpoint(self):
        with patch(
            "api.routers.admin.run_automation_cycle",
            return_value={
                "client_id": "client-runtime",
                "sync": {"status": "skipped"},
                "normalization": {"status": "success", "processed_count": 5},
                "health": {"status": "success", "sources_checked": 2, "alerts_created": 1},
                "alerts": {"status": "success", "alerts_created": 3},
            },
        ) as mocked_run:
            r = client.post("/api/admin/runtime/cycle", json={
                "client_id": "client-runtime",
                "run_sync": False,
                "run_normalization": True,
                "run_health": True,
                "run_alerts": True,
                "batch_size": 50,
                "now": "2026-04-05T10:00:00+00:00",
            })

        assert r.status_code == 200
        data = r.json()
        assert data["client_id"] == "client-runtime"
        assert data["health"]["alerts_created"] == 1
        mocked_run.assert_called_once_with(
            client_id="client-runtime",
            run_sync=False,
            run_normalization=True,
            run_health=True,
            run_alerts=True,
            batch_size=50,
            now="2026-04-05T10:00:00+00:00",
        )

    def test_scheduler_tick_runs_due_priority_source_only(self):
        client_id = f"client-{uuid.uuid4().hex[:8]}"
        coverage_key = f"owned:facebook:scheduler-priority-{uuid.uuid4().hex[:8]}"
        r_primary = client.post("/api/admin/sources", json={
            "client_id": client_id,
            "source_name": "Scheduler Primary",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": coverage_key,
        })
        r_fallback = client.post("/api/admin/sources", json={
            "client_id": client_id,
            "source_name": "Scheduler Fallback",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 2,
            "coverage_key": coverage_key,
        })
        primary_id = r_primary.json()["source_id"]
        fallback_id = r_fallback.json()["source_id"]

        with patch(
            "core.ingestion.scheduler.IngestionOrchestrator.run_source_sync",
            return_value={
                "status": "success",
                "records_fetched": 1,
                "records_inserted": 1,
                "records_failed": 0,
            },
        ) as mocked_run:
            r = client.post(f"/api/admin/scheduler/tick?client_id={client_id}")

        assert r.status_code == 200
        data = r.json()
        assert data["groups_processed"] == 1
        assert data["sources_scheduled"] == 1
        assert data["groups"][0]["coverage_key"] == coverage_key
        assert data["groups"][0]["winner_source_id"] == primary_id
        assert [call.kwargs["source_id"] for call in mocked_run.call_args_list] == [primary_id]
        assert fallback_id not in [call.kwargs["source_id"] for call in mocked_run.call_args_list]

    def test_scheduler_tick_falls_back_when_primary_fails(self):
        client_id = f"client-{uuid.uuid4().hex[:8]}"
        coverage_key = f"owned:facebook:scheduler-fallback-{uuid.uuid4().hex[:8]}"
        r_primary = client.post("/api/admin/sources", json={
            "client_id": client_id,
            "source_name": "Fallback Primary",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": coverage_key,
        })
        r_fallback = client.post("/api/admin/sources", json={
            "client_id": client_id,
            "source_name": "Fallback Secondary",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 2,
            "coverage_key": coverage_key,
        })
        primary_id = r_primary.json()["source_id"]
        fallback_id = r_fallback.json()["source_id"]

        def _run_source_sync(*, source_id, **kwargs):
            if source_id == primary_id:
                raise RuntimeError("API unavailable")
            return {
                "status": "success",
                "records_fetched": 1,
                "records_inserted": 1,
                "records_failed": 0,
            }

        with patch(
            "core.ingestion.scheduler.IngestionOrchestrator.run_source_sync",
            side_effect=_run_source_sync,
        ) as mocked_run:
            r = client.post(f"/api/admin/scheduler/tick?client_id={client_id}")

        assert r.status_code == 200
        data = r.json()
        assert data["sources_scheduled"] == 1
        assert data["groups"][0]["winner_source_id"] == fallback_id
        assert [call.kwargs["source_id"] for call in mocked_run.call_args_list] == [primary_id, fallback_id]
        assert data["groups"][0]["attempts"][0]["status"] == "failed"
        assert "API unavailable" in data["groups"][0]["attempts"][0]["error"]

    def test_scheduler_tick_skips_not_due_sources(self):
        client_id = f"client-{uuid.uuid4().hex[:8]}"
        coverage_key = f"owned:facebook:scheduler-fresh-{uuid.uuid4().hex[:8]}"
        r_source = client.post("/api/admin/sources", json={
            "client_id": client_id,
            "source_name": "Fresh Source",
            "platform": "facebook",
            "source_type": "managed_page",
            "owner_type": "owned",
            "source_purpose": "owned_content",
            "source_priority": 1,
            "coverage_key": coverage_key,
            "sync_frequency_minutes": 120,
        })
        source_id = r_source.json()["source_id"]
        with _get_connection() as conn:
            conn.execute(
                "UPDATE sources SET last_sync_at = ? WHERE source_id = ? AND client_id = ?",
                ["2026-04-03T11:50:00+00:00", source_id, client_id],
            )
            conn.commit()

        with patch("core.ingestion.scheduler.IngestionOrchestrator.run_source_sync") as mocked_run:
            r = client.post(f"/api/admin/scheduler/tick?client_id={client_id}&now=2026-04-03T12:00:00%2B00:00")

        assert r.status_code == 200
        data = r.json()
        assert data["groups_processed"] == 0
        assert data["sources_scheduled"] == 0
        assert mocked_run.call_count == 0

    def test_trigger_source_sync_same_content_across_sources_shares_content_item(self):
        coverage_key = f"owned:facebook:shared-content-{uuid.uuid4().hex[:8]}"
        source_ids = []
        for name, priority in (("Shared A", 1), ("Shared B", 2)):
            response = client.post("/api/admin/sources", json={
                "source_name": name,
                "platform": "facebook",
                "source_type": "managed_page",
                "owner_type": "owned",
                "source_purpose": "owned_content",
                "source_priority": priority,
                "coverage_key": coverage_key,
            })
            source_ids.append(response.json()["source_id"])

        shared_doc = {
            "external_document_id": f"{coverage_key}-post-1",
            "raw_text": "shared text",
            "raw_payload": {},
            "raw_metadata": {"source_url": f"https://facebook.com/posts/{coverage_key}-post-1"},
            "collected_at": "2026-01-01T00:00:00Z",
            "checksum_sha256": f"hash-{coverage_key}",
        }

        with patch("core.connectors.facebook_connector.FacebookConnector.fetch_documents", return_value=[shared_doc]):
            for source_id in source_ids:
                response = client.post(f"/api/admin/sources/{source_id}/sync", json={"run_mode": "manual"})
                assert response.status_code == 200

        with _get_connection() as conn:
            content_items = conn.execute(
                """
                SELECT content_item_id
                FROM content_items
                WHERE canonical_key = ?
                """,
                [f"facebook:{shared_doc['external_document_id']}"],
            ).fetchall()
            raw_documents = conn.execute(
                """
                SELECT DISTINCT content_item_id
                FROM raw_documents
                WHERE canonical_key = ?
                """,
                [f"facebook:{shared_doc['external_document_id']}"],
            ).fetchall()

        assert len(content_items) == 1
        assert len(raw_documents) == 1


# ---------------------------------------------------------------------------
# Social Metrics
# ---------------------------------------------------------------------------

class TestSocialMetrics:
    """Tests des endpoints /api/social-metrics/."""

    def test_create_credential(self):
        """Crée un credential Instagram brand."""
        r = client.post("/api/social-metrics/credentials", json={
            "entity_type": "brand",
            "entity_name": "Ramy Official",
            "platform": "instagram",
            "account_id": "12345678",
            "access_token": "EAAtest123",
            "app_id": "app-001",
        })
        assert r.status_code == 201
        data = r.json()
        assert "credential_id" in data
        assert data["status"] == "created"

    def test_list_credentials(self):
        """Liste les credentials actifs."""
        client.post("/api/social-metrics/credentials", json={
            "entity_type": "influencer",
            "entity_name": "Influenceur Test",
            "platform": "instagram",
        })
        r = client.get("/api/social-metrics/credentials")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_deactivate_credential(self):
        """Désactive un credential."""
        r_create = client.post("/api/social-metrics/credentials", json={
            "entity_type": "brand",
            "entity_name": "Ramy TikTok",
            "platform": "tiktok",
        })
        cid = r_create.json()["credential_id"]
        r = client.delete(f"/api/social-metrics/credentials/{cid}")
        assert r.status_code == 204

    def test_deactivate_credential_404(self):
        """Retourne 404 pour un credential inexistant."""
        r = client.delete("/api/social-metrics/credentials/cred-inexistant")
        assert r.status_code == 404

    def test_add_campaign_post(self):
        """Lie un post Instagram à une campagne."""
        campaign_id = _seed_campaign("Test Social Campaign")
        r = client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "instagram",
            "post_platform_id": "17854360229135492",
            "post_url": "https://www.instagram.com/p/ABC123/",
            "entity_type": "brand",
            "entity_name": "Ramy Official",
        })
        assert r.status_code == 201
        data = r.json()
        assert "post_id" in data
        assert data["campaign_id"] == campaign_id

    def test_list_campaign_posts(self):
        """Liste les posts liés à une campagne."""
        campaign_id = _seed_campaign("Campaign Posts List")
        client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "instagram",
            "post_platform_id": "post-abc-001",
        })
        r = client.get(f"/api/social-metrics/campaigns/{campaign_id}/posts")
        assert r.status_code == 200
        posts = r.json()
        assert isinstance(posts, list)
        assert len(posts) == 1
        assert posts[0]["post_platform_id"] == "post-abc-001"

    def test_delete_campaign_post_removes_post_and_metrics(self):
        campaign_id = _seed_campaign("Delete Campaign Post")
        r_post = client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "instagram",
            "post_platform_id": "delete-post-001",
            "post_url": "https://instagram.com/p/delete-post-001",
        })
        assert r_post.status_code == 201
        post_id = r_post.json()["post_id"]

        r_metric = client.post(f"/api/social-metrics/posts/{post_id}/metrics/manual", json={
            "likes": 10,
            "comments": 5,
            "shares": 1,
            "reach": 100,
        })
        assert r_metric.status_code == 200

        r_delete = client.delete(f"/api/social-metrics/posts/{post_id}")
        assert r_delete.status_code == 204

        r_posts = client.get(f"/api/social-metrics/campaigns/{campaign_id}/posts")
        assert r_posts.status_code == 200
        assert r_posts.json() == []

        with _get_connection() as conn:
            metric_rows = conn.execute(
                "SELECT COUNT(*) AS count FROM post_engagement_metrics WHERE post_id = ?",
                [post_id],
            ).fetchone()
        assert metric_rows["count"] == 0

    def test_delete_campaign_post_404(self):
        r = client.delete("/api/social-metrics/posts/post-does-not-exist")
        assert r.status_code == 404

    def test_get_campaign_engagement_empty(self):
        """Retourne une structure vide si aucun post lié."""
        campaign_id = _seed_campaign("Empty Engagement Campaign")
        r = client.get(f"/api/social-metrics/campaigns/{campaign_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["campaign_id"] == campaign_id
        assert data["post_count"] == 0
        assert data["engagement_rate"] is None
        assert data["roi_pct"] is None

    def test_get_campaign_engagement_404(self):
        """Retourne 404 pour une campagne inexistante."""
        r = client.get("/api/social-metrics/campaigns/camp-does-not-exist")
        assert r.status_code == 404

    def test_add_manual_metrics(self):
        """Saisie manuelle des métriques sur un post existant."""
        campaign_id = _seed_campaign("Manual Metrics Campaign")
        r_post = client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "instagram",
            "post_platform_id": "manual-post-001",
        })
        post_id = r_post.json()["post_id"]

        r = client.post(f"/api/social-metrics/posts/{post_id}/metrics/manual", json={
            "likes": 1500,
            "comments": 120,
            "shares": 45,
            "reach": 28000,
            "impressions": 35000,
        })
        assert r.status_code == 200
        data = r.json()
        assert "metric_id" in data
        assert data["post_id"] == post_id

    def test_engagement_rate_calculated(self):
        """Engagement rate calculé correctement après saisie manuelle."""
        campaign_id = _seed_campaign("Engagement Rate Test")
        r_post = client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "instagram",
            "post_platform_id": "engrate-post-001",
        })
        post_id = r_post.json()["post_id"]

        client.post(f"/api/social-metrics/posts/{post_id}/metrics/manual", json={
            "likes": 100,
            "comments": 20,
            "shares": 5,
            "reach": 5000,
        })

        r = client.get(f"/api/social-metrics/campaigns/{campaign_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["engagement_rate"] == pytest.approx(2.5, abs=0.01)

    def test_set_campaign_revenue(self):
        """Renseigne le revenue_dza d'une campagne."""
        campaign_id = _seed_campaign("Revenue Campaign")
        r = client.patch(f"/api/social-metrics/campaigns/{campaign_id}/revenue", json={
            "revenue_dza": 5_000_000
        })
        assert r.status_code == 200
        data = r.json()
        assert data["revenue_dza"] == 5_000_000

    def test_roi_calculated_after_revenue(self):
        """ROI calculé correctement quand budget et revenue sont renseignés."""
        campaign_id = _seed_campaign("ROI Campaign")
        with _get_connection() as conn:
            conn.execute(
                "UPDATE campaigns SET budget_dza = 1000000 WHERE campaign_id = ?",
                [campaign_id],
            )
            conn.commit()

        client.patch(f"/api/social-metrics/campaigns/{campaign_id}/revenue", json={
            "revenue_dza": 1_500_000
        })

        r = client.get(f"/api/social-metrics/campaigns/{campaign_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["roi_pct"] == pytest.approx(50.0, abs=0.1)

    def test_get_campaign_engagement_includes_sentiment_context(self):
        """Le résumé campagne doit joindre engagement et signaux enrichis du même post."""
        campaign_id = _seed_campaign("Campaign Sentiment Join")
        post_platform_id = f"fb-sent-{uuid.uuid4().hex[:8]}"
        post_url = f"https://facebook.com/posts/{post_platform_id}"

        r_post = client.post(f"/api/social-metrics/campaigns/{campaign_id}/posts", json={
            "platform": "facebook",
            "post_platform_id": post_platform_id,
            "post_url": post_url,
            "entity_type": "brand",
            "entity_name": "Ramy Official",
        })
        post_id = r_post.json()["post_id"]

        client.post(f"/api/social-metrics/posts/{post_id}/metrics/manual", json={
            "likes": 200,
            "comments": 40,
            "shares": 10,
            "reach": 4000,
        })

        source_id = f"src-sent-{uuid.uuid4().hex[:8]}"
        content_item_id = f"cnt-sent-{uuid.uuid4().hex[:8]}"
        raw_document_id = f"raw-sent-{uuid.uuid4().hex[:8]}"
        normalized_record_id = f"norm-sent-{uuid.uuid4().hex[:8]}"

        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sources (
                    source_id, client_id, source_name, platform, source_type, owner_type,
                    auth_mode, config_json, is_active, sync_frequency_minutes,
                    freshness_sla_hours, source_purpose, source_priority, coverage_key,
                    credential_id, last_sync_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    "ramy_client_001",
                    "Sentiment Source",
                    "facebook",
                    "managed_page",
                    "owned",
                    None,
                    "{}",
                    1,
                    60,
                    24,
                    "owned_content",
                    1,
                    "owned:facebook:campaign-sentiment",
                    None,
                    None,
                    "2026-04-03T10:00:00Z",
                    "2026-04-03T10:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO content_items (
                    content_item_id, client_id, platform, external_content_id,
                    canonical_url, canonical_key, owner_type, coverage_key,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_item_id,
                    "ramy_client_001",
                    "facebook",
                    post_platform_id,
                    post_url,
                    f"facebook:{post_platform_id}",
                    "owned",
                    "owned:facebook:campaign-sentiment",
                    "2026-04-03T10:00:00Z",
                    "2026-04-03T10:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO raw_documents (
                    raw_document_id, client_id, source_id, sync_run_id, external_document_id,
                    raw_payload, raw_text, raw_metadata, checksum_sha256,
                    content_item_id, platform, canonical_url, canonical_key,
                    collected_at, is_normalized, normalizer_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_document_id,
                    "ramy_client_001",
                    source_id,
                    "run-sent-1",
                    post_platform_id,
                    "{}",
                    "Le goût est mauvais",
                    json.dumps({"source_url": post_url}),
                    f"sha-{post_platform_id}",
                    content_item_id,
                    "facebook",
                    post_url,
                    f"facebook:{post_platform_id}",
                    "2026-04-03T10:00:00Z",
                    1,
                    "wave5.2-local",
                    "2026-04-03T10:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO normalized_records (
                    normalized_record_id, client_id, source_id, raw_document_id,
                    text, text_original, channel, source_url, published_at, language,
                    script_detected, normalized_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_record_id,
                    "ramy_client_001",
                    source_id,
                    raw_document_id,
                    "Le goût est mauvais",
                    "Le goût est mauvais",
                    "facebook",
                    post_url,
                    "2026-04-03T10:00:00Z",
                    "fr",
                    "latin",
                    "{}",
                    "2026-04-03T10:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO enriched_signals (
                    signal_id, client_id, normalized_record_id, source_id, sentiment_label,
                    confidence, aspect, aspects, aspect_sentiments, brand, competitor,
                    product, product_line, sku, wilaya, region_id, distributor_id,
                    source_url, channel, event_timestamp, normalizer_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"sig-sent-{uuid.uuid4().hex[:8]}",
                    "ramy_client_001",
                    normalized_record_id,
                    source_id,
                    "negatif",
                    0.88,
                    "gout",
                    '["gout"]',
                    "[]",
                    "Ramy",
                    None,
                    "Ramy Citron",
                    "Citron",
                    None,
                    "Alger",
                    None,
                    None,
                    post_url,
                    "facebook",
                    "2026-04-03T10:00:00Z",
                    "wave5.2-local",
                    "2026-04-03T10:00:00Z",
                ),
            )
            conn.commit()

        r = client.get(f"/api/social-metrics/campaigns/{campaign_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["signal_count"] == 1
        assert data["sentiment_breakdown"]["negatif"] == 1
        assert "gout" in data["negative_aspects"]
        assert data["top_performer"]["signal_count"] == 1
        assert data["top_performer"]["sentiment_breakdown"]["negatif"] == 1
