from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from core.demo.ramy_seed import issue_demo_api_key, resolve_ramy_seed_dataset_path, seed_ramy_demo

pytestmark = [pytest.mark.integration, pytest.mark.smoke]


@pytest.fixture(scope="module")
def demo_client() -> tuple[TestClient, dict[str, str]]:
    dataset_path = resolve_ramy_seed_dataset_path()
    seed_ramy_demo(
        csv_path=dataset_path,
        client_id="ramy-demo",
        client_name="Ramy Demo",
        reset=True,
    )
    api_key_info = issue_demo_api_key(client_id="ramy-demo")
    headers = {
        "X-API-Key": api_key_info["api_key"],
        "X-Ramy-Client-Id": "ramy-demo",
    }
    return TestClient(app), headers


def test_health_endpoint_is_ok(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, _headers = demo_client
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db_status"] == "connected"


def test_dashboard_summary_is_populated(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client
    response = client.get("/api/dashboard/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert int(payload["total_mentions"]) > 0
    assert payload["product_performance"]
    assert payload["regional_distribution"]


def test_dashboard_critical_alerts_are_available(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client
    response = client.get("/api/dashboard/alerts-critical", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["critical_alerts"]


def test_watchlists_and_metrics_are_available(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client
    response = client.get("/api/watchlists?is_active=true", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    watchlist_id = payload[0]["watchlist_id"]

    metrics_response = client.get(f"/api/watchlists/{watchlist_id}/metrics", headers=headers)
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert int(metrics.get("volume_total") or metrics.get("volume_current") or 0) > 0
    assert "aspect_breakdown" in metrics


def test_alerts_include_navigation_or_source_links(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client
    response = client.get("/api/alerts?limit=10", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert any(
        alert.get("navigation_url")
        or (alert.get("alert_payload") or {}).get("source_urls")
        for alert in payload
    )


def test_recommendations_context_and_list_are_populated(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client

    context_response = client.get("/api/recommendations/context-preview?client_id=ramy-demo", headers=headers)
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert int(context_payload["active_watchlists_count"]) >= 3
    assert int(context_payload["volume_total"]) > 0

    recommendations_response = client.get("/api/recommendations?limit=10", headers=headers)
    assert recommendations_response.status_code == 200
    recommendations = recommendations_response.json()
    assert recommendations


def test_campaigns_and_overview_are_available(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client

    campaigns_response = client.get("/api/campaigns", headers=headers)
    assert campaigns_response.status_code == 200
    campaigns = campaigns_response.json()
    assert len(campaigns) >= 2

    overview_response = client.get("/api/campaigns/overview", headers=headers)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert int(overview["active_campaigns_count"]) >= 1
    assert overview["top_performer"] is not None


def test_admin_sources_trace_and_snapshots_are_available(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client
    response = client.get("/api/admin/sources", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    source_id = payload[0]["source_id"]

    trace_response = client.get(f"/api/admin/sources/{source_id}", headers=headers)
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert int(trace_payload["raw_document_count"]) > 0

    snapshots_response = client.get(f"/api/admin/sources/{source_id}/snapshots", headers=headers)
    assert snapshots_response.status_code == 200
    snapshots_payload = snapshots_response.json()
    assert snapshots_payload


def test_explorer_verbatims_and_search_return_real_sources(demo_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = demo_client

    verbatims_response = client.get("/api/explorer/verbatims?page=1&page_size=5", headers=headers)
    assert verbatims_response.status_code == 200
    verbatims = verbatims_response.json()
    assert int(verbatims["total"]) > 0
    assert verbatims["results"][0]["source_url"].startswith("https://")

    search_response = client.get("/api/explorer/search?q=ramy", headers=headers)
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["results"]
    assert search_payload["results"][0]["source_url"].startswith("https://")
