from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import config
from api.main import app
from core.database import DatabaseManager
from core.security.auth import create_api_key


client = TestClient(app)


def _prepare_isolated_db(monkeypatch, tmp_path: Path) -> dict[str, str]:
    """Configure the app to use an isolated SQLite database and return auth headers."""
    db_path = tmp_path / "clients-api.sqlite"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)

    database = DatabaseManager(str(db_path))
    database.create_tables()
    _, raw_key = create_api_key(client_id=config.DEFAULT_CLIENT_ID, label="clients_api_test")

    return {"X-API-Key": raw_key}


def test_clients_routes_require_api_key(monkeypatch, tmp_path: Path) -> None:
    _prepare_isolated_db(monkeypatch, tmp_path)

    response = client.post(
        "/api/clients",
        json={"client_name": "Cevital Elio", "industry": "FMCG"},
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401


def test_create_client_and_set_active_tenant(monkeypatch, tmp_path: Path) -> None:
    headers = _prepare_isolated_db(monkeypatch, tmp_path)

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


def test_get_active_client_falls_back_to_safe_expo_tenant(monkeypatch, tmp_path: Path) -> None:
    headers = _prepare_isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("api.deps.tenant.get_runtime_setting", lambda key: None)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    current = client.get("/api/clients/active", headers=headers)
    assert current.status_code == 200
    assert current.json()["client_id"] == "ramy-demo"
