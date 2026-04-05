"""Tests for API key authentication."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import config
from core.database import DatabaseManager
from core.security.auth import create_api_key, deactivate_api_key, hash_key, list_api_keys

_db = DatabaseManager()
_db.create_tables()

from api.main import app

client = TestClient(app)


def _make_key(label: str = "test") -> tuple[str, str]:
    """Helper — create a key and return (key_id, raw_key)."""
    return create_api_key(client_id="ramy_client_001", label=label)


# --- Health is public ---


class TestPublicEndpoints:
    def test_health_no_auth(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200


# --- Protected endpoints require auth ---


class TestProtectedEndpoints:
    def test_no_key_returns_422(self):
        resp = client.get("/api/dashboard/summary")
        # FastAPI returns 422 when a required header is missing
        assert resp.status_code == 422

    def test_bad_key_returns_401(self):
        resp = client.get(
            "/api/dashboard/summary",
            headers={"X-API-Key": "rpk_00000000000000000000000000000000"},
        )
        assert resp.status_code == 401

    def test_valid_key_passes(self):
        _, raw_key = _make_key("protected_test")
        resp = client.get(
            "/api/dashboard/summary",
            headers={"X-API-Key": raw_key},
        )
        # Should NOT be 401/422 — the auth passed even if the endpoint
        # returns 500 due to missing data, that's fine.
        assert resp.status_code not in (401, 422)

    def test_deactivated_key_returns_401(self):
        key_id, raw_key = _make_key("deactivate_test")
        deactivate_api_key(key_id)
        resp = client.get(
            "/api/dashboard/summary",
            headers={"X-API-Key": raw_key},
        )
        assert resp.status_code == 401


# --- Key CRUD endpoints ---


class TestKeyCRUD:
    def _auth_header(self) -> dict:
        _, raw_key = _make_key("crud_auth")
        return {"X-API-Key": raw_key}

    def test_create_key(self):
        resp = client.post(
            "/api/auth/keys",
            json={"client_id": "ramy_client_001", "label": "new_key"},
            headers=self._auth_header(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "api_key" in data
        assert data["api_key"].startswith("rpk_")
        assert data["warning"]
        assert data["key_id"]

    def test_list_keys(self):
        resp = client.get(
            "/api/auth/keys",
            headers=self._auth_header(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Verify no hash or raw key is exposed
        for key in data:
            assert "key_hash" not in key
            assert "api_key" not in key

    def test_delete_key(self):
        key_id, _ = _make_key("to_delete")
        resp = client.delete(
            f"/api/auth/keys/{key_id}",
            headers=self._auth_header(),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deactivated"

    def test_delete_nonexistent_key(self):
        resp = client.delete(
            "/api/auth/keys/key-nonexistent",
            headers=self._auth_header(),
        )
        assert resp.status_code == 404


# --- Core auth functions ---


class TestAuthFunctions:
    def test_hash_key_deterministic(self):
        assert hash_key("test") == hash_key("test")
        assert hash_key("a") != hash_key("b")

    def test_create_returns_rpk_prefix(self):
        _, raw_key = _make_key("prefix_test")
        assert raw_key.startswith("rpk_")
        assert len(raw_key) == 36  # rpk_ + 32 hex

    def test_list_keys_no_hash(self):
        keys = list_api_keys()
        for key in keys:
            assert "key_hash" not in key

    def test_last_used_at_updated(self):
        key_id, raw_key = _make_key("last_used_test")
        # Make a request to a protected endpoint to trigger last_used_at
        client.get(
            "/api/dashboard/summary",
            headers={"X-API-Key": raw_key},
        )
        # Verify last_used_at was updated
        conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT last_used_at FROM api_keys WHERE key_id = ?",
            (key_id,),
        ).fetchone()
        conn.close()
        assert row["last_used_at"] is not None
