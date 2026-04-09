from __future__ import annotations

from fastapi.testclient import TestClient

import config
from api.main import app


client = TestClient(app)


def test_create_client_and_set_active_tenant() -> None:
    created = client.post(
        "/api/clients",
        json={"client_name": "Cevital Elio", "industry": "FMCG"},
    )
    assert created.status_code == 201

    client_id = created.json()["client_id"]

    switched = client.put("/api/clients/active", json={"client_id": client_id})
    assert switched.status_code == 200

    current = client.get("/api/clients/active")
    assert current.status_code == 200
    assert current.json()["client_id"] == client_id
    assert current.json()["client_name"] == "Cevital Elio"


def test_get_active_client_falls_back_to_safe_expo_tenant(monkeypatch) -> None:
    monkeypatch.setattr("api.deps.tenant.get_runtime_setting", lambda key: None)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    current = client.get("/api/clients/active")
    assert current.status_code == 200
    assert current.json()["client_id"] == "ramy-demo"
