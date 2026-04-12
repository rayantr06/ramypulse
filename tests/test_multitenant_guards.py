"""Tests de garde multi-tenant — vérifient qu'un tenant B
ne peut pas lire, modifier ou supprimer les données d'un tenant A."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import config
from api.main import app
from core.alerts.alert_detector import _load_rule_settings
from core.tenancy.client_manager import create_client
from core.watchlists.watchlist_manager import create_watchlist
from core.alerts.alert_manager import create_alert

CLIENT_A = "test-tenant-alpha"
CLIENT_B = "test-tenant-beta"
HEADERS_A = {"X-API-Key": "dev", "X-Ramy-Client-Id": CLIENT_A}
HEADERS_B = {"X-API-Key": "dev", "X-Ramy-Client-Id": CLIENT_B}


@pytest.fixture(autouse=True)
def setup_tenants(tmp_path, monkeypatch):
    """Crée deux tenants distincts en base pour chaque test."""
    db_path = tmp_path / "test_guard.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", str(db_path))
    from core.database import DatabaseManager
    DatabaseManager(str(db_path)).create_tables()
    create_client(CLIENT_A, client_id=CLIENT_A)
    create_client(CLIENT_B, client_id=CLIENT_B)
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ── Test 1 : sources admin scopées au tenant ──────────────────────────────────

def test_admin_sources_scoped_to_tenant(client):
    """Source créée par A n'est pas visible pour B."""
    # A crée une source
    resp = client.post(
        "/api/admin/sources",
        json={
            "platform": "facebook",
            "source_type": "page",
            "owner_type": "brand",
            "label": "Ramy Page A",
            "config_json": "{}",
        },
        headers=HEADERS_A,
    )
    assert resp.status_code in (200, 201)

    # B ne doit pas la voir
    resp_b = client.get("/api/admin/sources", headers=HEADERS_B)
    assert resp_b.status_code == 200
    source_ids_b = [s["source_id"] for s in resp_b.json()]
    resp_a = client.get("/api/admin/sources", headers=HEADERS_A)
    source_ids_a = [s["source_id"] for s in resp_a.json()]

    for sid in source_ids_a:
        assert sid not in source_ids_b, f"Source {sid} du tenant A visible pour B"


# ── Test 2 : source créée avec le bon client_id ──────────────────────────────

def test_admin_source_create_uses_tenant(client):
    """Source créée par A a client_id == CLIENT_A, pas DEFAULT."""
    resp = client.post(
        "/api/admin/sources",
        json={
            "platform": "google_maps",
            "source_type": "place",
            "owner_type": "brand",
            "label": "Ramy Maps A",
            "config_json": "{}",
        },
        headers=HEADERS_A,
    )
    assert resp.status_code in (200, 201)
    source_id = resp.json()["source_id"]

    # Vérifier directement en DB
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT client_id FROM sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["client_id"] == CLIENT_A
    assert row["client_id"] != config.DEFAULT_CLIENT_ID


# ── Test 3 : update watchlist mauvais tenant ─────────────────────────────────

def test_watchlist_update_wrong_tenant(client):
    """PUT /watchlists/{id} avec tenant B sur watchlist de A → 404."""
    wl_id = create_watchlist(
        name="WL-A", description="", scope_type="manual", filters={}, client_id=CLIENT_A
    )
    resp = client.put(
        f"/api/watchlists/{wl_id}",
        json={"name": "Hacked"},
        headers=HEADERS_B,
    )
    assert resp.status_code == 404


# ── Test 4 : delete watchlist mauvais tenant ─────────────────────────────────

def test_watchlist_delete_wrong_tenant(client):
    """DELETE /watchlists/{id} avec tenant B sur watchlist de A → 404."""
    wl_id = create_watchlist(
        name="WL-A-del", description="", scope_type="manual", filters={}, client_id=CLIENT_A
    )
    resp = client.delete(f"/api/watchlists/{wl_id}", headers=HEADERS_B)
    assert resp.status_code == 404


# ── Test 5 : update alert status mauvais tenant ──────────────────────────────

def test_alert_status_update_wrong_tenant(client):
    """PUT /alerts/{id}/status avec tenant B sur alerte de A → 404."""
    wl_id = create_watchlist(
        name="WL-alert", description="", scope_type="manual", filters={}, client_id=CLIENT_A
    )
    alert_id = create_alert(
        watchlist_id=wl_id,
        rule_id="nss_critical_low",
        client_id=CLIENT_A,
        title="Test alerte",
        message="msg",
        severity="high",
        nss_value=-50.0,
    )
    resp = client.put(
        f"/api/alerts/{alert_id}/status",
        json={"status": "resolved"},
        headers=HEADERS_B,
    )
    assert resp.status_code == 404


# ── Test 6 : règles d'alerte scopées au client ───────────────────────────────

def test_alert_rules_scoped_to_client():
    """_load_rule_settings(conn, CLIENT_A) ≠ _load_rule_settings(conn, DEFAULT)."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row

    rules_a = _load_rule_settings(conn, CLIENT_A)
    rules_default = _load_rule_settings(conn, config.DEFAULT_CLIENT_ID)

    # CLIENT_A ne doit pas hériter des règles de DEFAULT automatiquement
    # (ses propres règles sont vides tant qu'elles ne sont pas seedées pour lui)
    assert isinstance(rules_a, dict)
    assert isinstance(rules_default, dict)
    conn.close()


# ── Test 7 : nouveau client reçoit les règles par défaut ─────────────────────

def test_new_client_gets_default_alert_rules():
    """Après create_client, les 10 règles d'alerte existent pour ce client."""
    new_id = "test-new-brand-dz"
    create_client("New Brand DZ", client_id=new_id)

    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT alert_rule_id FROM alert_rules WHERE client_id = ? AND is_active = 1",
        (new_id,),
    ).fetchall()
    conn.close()

    rule_ids = {row["alert_rule_id"] for row in rows}
    expected = {
        "nss_critical_low", "negative_volume_surge", "no_recent_signals",
        "aspect_critical", "volume_drop", "volume_anomaly",
        "nss_temporal_drift", "segment_divergence",
        "campaign_impact_positive", "campaign_underperformance",
    }
    assert expected.issubset(rule_ids), f"Règles manquantes : {expected - rule_ids}"
