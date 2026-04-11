"""TDD — Tests pour POST /api/recommendations/bulk-status.

Workflow : RED (ces tests échouent) → implémentation → GREEN (4/4 passent).
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import config
from core.database import DatabaseManager
from core.security.auth import create_api_key

# Init schema + test key
_db = DatabaseManager()
_db.create_tables()

from api.main import app  # noqa: E402

_key_id, _raw_key = create_api_key(client_id="ramy_client_001", label="bulk_test")
_HEADERS = {"X-API-Key": _raw_key, "Content-Type": "application/json"}

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _insert_rec(rec_id: str, status: str = "active") -> None:
    """Insert a minimal recommendation row directly into the DB."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.execute(
        """INSERT OR REPLACE INTO recommendations
           (recommendation_id, client_id, trigger_type, status, created_at)
           VALUES (?, 'ramy_client_001', 'manual', ?, datetime('now'))""",
        (rec_id, status),
    )
    conn.commit()
    conn.close()


def _get_status(rec_id: str) -> str | None:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    row = conn.execute(
        "SELECT status FROM recommendations WHERE recommendation_id = ?", (rec_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_bulk_status_archive_multiple():
    """Archive 3 recommendations in one call, verify all have status=archived."""
    ids = ["bulk-test-001", "bulk-test-002", "bulk-test-003"]
    for rec_id in ids:
        _insert_rec(rec_id, status="active")

    resp = client.post(
        "/api/recommendations/bulk-status",
        json={"ids": ids, "status": "archived"},
        headers=_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated"] == 3
    assert set(body["ids"]) == set(ids)

    for rec_id in ids:
        assert _get_status(rec_id) == "archived", f"{rec_id} should be archived"


def test_bulk_status_ignores_unknown_ids():
    """Unknown IDs are silently ignored — no error, updated=0."""
    resp = client.post(
        "/api/recommendations/bulk-status",
        json={"ids": ["nonexistent-aaa", "nonexistent-bbb"], "status": "dismissed"},
        headers=_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated"] == 0
    assert body["ids"] == []


def test_bulk_status_invalid_status():
    """Invalid status value returns HTTP 422."""
    resp = client.post(
        "/api/recommendations/bulk-status",
        json={"ids": ["any-id"], "status": "INVALID"},
        headers=_HEADERS,
    )

    assert resp.status_code == 422


def test_bulk_status_empty_list():
    """Empty ids list returns updated=0 without error."""
    resp = client.post(
        "/api/recommendations/bulk-status",
        json={"ids": [], "status": "archived"},
        headers=_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated"] == 0
    assert body["ids"] == []
