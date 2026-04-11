from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import config
from api.main import app
from core.database import DatabaseManager
from core.security.auth import create_api_key
from core.tenancy.client_manager import create_client


client = TestClient(app)


def _prepare_isolated_db(monkeypatch, tmp_path: Path) -> dict[str, dict[str, str] | str]:
    """Configure an isolated SQLite DB and seed operator/non-operator auth contexts."""
    db_path = tmp_path / "clients-api.sqlite"
    operator_client_id = "ramy-demo"
    other_client_id = "client-other"

    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", operator_client_id, raising=False)

    DatabaseManager(str(db_path)).create_tables()
    create_client(client_name="Safe Expo", client_id=operator_client_id)
    create_client(client_name="Other Tenant", client_id=other_client_id)

    _, operator_raw_key = create_api_key(client_id=operator_client_id, label="clients_api_operator")
    _, non_operator_raw_key = create_api_key(client_id=other_client_id, label="clients_api_other")

    return {
        "operator_headers": {"X-API-Key": operator_raw_key},
        "non_operator_headers": {"X-API-Key": non_operator_raw_key},
        "operator_client_id": operator_client_id,
    }


def test_clients_routes_require_api_key(monkeypatch, tmp_path: Path) -> None:
    _prepare_isolated_db(monkeypatch, tmp_path)

    missing = client.post("/api/clients", json={"client_name": "Cevital Elio", "industry": "FMCG"})
    invalid = client.post(
        "/api/clients",
        json={"client_name": "Cevital Elio", "industry": "FMCG"},
        headers={"X-API-Key": "invalid-key"},
    )

    assert missing.status_code == 422
    assert invalid.status_code == 401


def test_operator_key_can_create_client_and_set_active_tenant(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    headers = ctx["operator_headers"]

    created = client.post(
        "/api/clients",
        json={"client_name": "Cevital Elio", "industry": "FMCG"},
        headers=headers,
    )
    assert created.status_code == 201

    client_id = created.json()["client_id"]

    switched = client.put("/api/clients/active", json={"client_id": client_id}, headers=headers)
    assert switched.status_code == 200

    current = client.get("/api/clients/active", headers=headers)
    assert current.status_code == 200
    assert current.json()["client_id"] == client_id
    assert current.json()["client_name"] == "Cevital Elio"

    spoofed = client.get(
        "/api/clients/active",
        headers={**headers, "X-Ramy-Client-Id": "tenant-spoof"},
    )
    assert spoofed.status_code == 200
    assert spoofed.json()["client_id"] == client_id


def test_non_operator_key_gets_403_on_client_management_routes(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    headers = ctx["non_operator_headers"]

    created = client.post(
        "/api/clients",
        json={"client_name": "Unauthorized", "industry": "Retail"},
        headers=headers,
    )
    switched = client.put("/api/clients/active", json={"client_id": "ramy-demo"}, headers=headers)
    current = client.get("/api/clients/active", headers=headers)

    assert created.status_code == 403
    assert switched.status_code == 403
    assert current.status_code == 403


def test_get_active_client_falls_back_to_safe_expo_tenant(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    headers = ctx["operator_headers"]

    current = client.get("/api/clients/active", headers=headers)
    assert current.status_code == 200
    assert current.json()["client_id"] == ctx["operator_client_id"]
