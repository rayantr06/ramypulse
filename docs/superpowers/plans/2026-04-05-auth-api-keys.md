# Auth API Keys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real API key authentication to all non-public FastAPI endpoints, with key management CRUD and seed key on first startup.

**Architecture:** A single `X-API-Key` header is verified against hashed keys in an `api_keys` SQLite table. A `Depends(get_current_client)` dependency injects `AuthContext(client_id, key_id, scopes)` into protected routes. Key CRUD is exposed via `/api/auth/keys`.

**Tech Stack:** FastAPI Depends, hashlib SHA-256, secrets module for key generation, SQLite.

**Spec:** `docs/superpowers/specs/2026-04-05-auth-api-keys-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `core/database.py` | Modify (lines ~472, ~1305) | Add `api_keys` table to schema + seed key function |
| `core/security/auth.py` | Create | `get_current_client` FastAPI dependency |
| `api/schemas.py` | Modify (append) | `ApiKeyCreate`, `ApiKeyResponse`, `ApiKeyCreatedResponse` |
| `api/routers/auth.py` | Create | Key CRUD endpoints |
| `api/main.py` | Modify | Wire auth router + protect routers with `Depends` |
| `tests/test_auth.py` | Create | All auth tests |

---

### Task 1: Add `api_keys` table to database schema

**Files:**
- Modify: `core/database.py:472` (add to `_SCHEMA_STATEMENTS`)

- [ ] **Step 1: Add `api_keys` to `_SCHEMA_STATEMENTS` dict**

In `core/database.py`, insert before the closing `}` of `_SCHEMA_STATEMENTS` (after the `content_items` entry at line 472):

```python
    "api_keys": """
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id       TEXT PRIMARY KEY,
            client_id    TEXT NOT NULL,
            key_hash     TEXT NOT NULL,
            key_prefix   TEXT NOT NULL,
            label        TEXT,
            scopes       TEXT DEFAULT '["*"]',
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT NOT NULL,
            last_used_at TEXT
        )
    """,
```

- [ ] **Step 2: Verify table is created on startup**

Run:
```bash
cd g:/ramypulse && python -c "from core.database import DatabaseManager; db = DatabaseManager(); db.create_tables(); print('OK')"
```
Expected: `OK` with no errors.

- [ ] **Step 3: Commit**

```bash
git add core/database.py
git commit -m "feat(auth): add api_keys table to schema"
```

---

### Task 2: Create `core/security/auth.py` — the auth dependency

**Files:**
- Create: `core/security/auth.py`

- [ ] **Step 1: Write the auth module**

Create `core/security/auth.py`:

```python
"""FastAPI auth dependency — API key verification."""

from __future__ import annotations

import hashlib
import logging
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import NamedTuple

from fastapi import Header, HTTPException

import config

logger = logging.getLogger(__name__)

KEY_PREFIX = "rpk_"


class AuthContext(NamedTuple):
    """Resolved identity from a valid API key."""
    client_id: str
    key_id: str
    scopes: list[str]


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_raw_key() -> str:
    """Generate a new raw API key: rpk_ + 32 hex chars."""
    return f"{KEY_PREFIX}{secrets.token_hex(16)}"


def get_current_client(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> AuthContext:
    """FastAPI dependency. Validates the API key and returns the auth context.

    Raises HTTPException 401 if the key is missing, invalid, or inactive.
    """
    key_hash = hash_key(x_api_key)
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT key_id, client_id, scopes
            FROM api_keys
            WHERE key_hash = ? AND is_active = 1
            """,
            (key_hash,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )

        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
            (datetime.now().isoformat(), row["key_id"]),
        )
        conn.commit()

    import json
    scopes = json.loads(row["scopes"]) if row["scopes"] else ["*"]
    return AuthContext(
        client_id=row["client_id"],
        key_id=row["key_id"],
        scopes=scopes,
    )


def create_api_key(
    client_id: str,
    label: str | None = None,
) -> tuple[str, str]:
    """Create a new API key in the database.

    Returns (key_id, raw_key). The raw key is never stored.
    """
    raw_key = generate_raw_key()
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_keys (
                key_id, client_id, key_hash, key_prefix, label,
                scopes, is_active, created_at, last_used_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)
            """,
            (
                key_id,
                client_id,
                hash_key(raw_key),
                raw_key[:12],
                label or "",
                '["*"]',
                now,
            ),
        )
        conn.commit()

    return key_id, raw_key


def list_api_keys(client_id: str | None = None) -> list[dict]:
    """List API keys (never exposes hash or raw key)."""
    with _get_connection() as conn:
        if client_id:
            rows = conn.execute(
                """
                SELECT key_id, client_id, key_prefix, label, is_active,
                       created_at, last_used_at
                FROM api_keys WHERE client_id = ?
                ORDER BY created_at DESC
                """,
                (client_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT key_id, client_id, key_prefix, label, is_active,
                       created_at, last_used_at
                FROM api_keys
                ORDER BY created_at DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def deactivate_api_key(key_id: str) -> bool:
    """Soft-delete an API key by setting is_active = 0."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_id = ?",
            (key_id,),
        )
        conn.commit()
    return cursor.rowcount > 0
```

- [ ] **Step 2: Verify import works**

Run:
```bash
cd g:/ramypulse && python -c "from core.security.auth import AuthContext, get_current_client, create_api_key; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add core/security/auth.py
git commit -m "feat(auth): add auth dependency and key management functions"
```

---

### Task 3: Add Pydantic schemas for auth

**Files:**
- Modify: `api/schemas.py` (append at end)

- [ ] **Step 1: Add auth schemas**

Append to `api/schemas.py` after the last class:

```python


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    client_id: str = "ramy_client_001"
    label: str | None = None


class ApiKeyResponse(BaseModel):
    key_id: str
    client_id: str
    key_prefix: str
    label: str | None = None
    is_active: bool = True
    created_at: str | None = None
    last_used_at: str | None = None


class ApiKeyCreatedResponse(BaseModel):
    key_id: str
    client_id: str
    key_prefix: str
    label: str | None = None
    api_key: str
    warning: str = "Store this key securely. It will not be shown again."
```

- [ ] **Step 2: Commit**

```bash
git add api/schemas.py
git commit -m "feat(auth): add API key Pydantic schemas"
```

---

### Task 4: Create `api/routers/auth.py` — key CRUD endpoints

**Files:**
- Create: `api/routers/auth.py`

- [ ] **Step 1: Write the auth router**

Create `api/routers/auth.py`:

```python
"""Routeur FastAPI pour la gestion des cles API RamyPulse."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from core.security.auth import (
    AuthContext,
    create_api_key,
    deactivate_api_key,
    get_current_client,
    list_api_keys,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_key(
    payload: ApiKeyCreate,
    auth: AuthContext = Depends(get_current_client),
):
    """Create a new API key. Returns the raw key ONCE."""
    key_id, raw_key = create_api_key(
        client_id=payload.client_id,
        label=payload.label,
    )
    return ApiKeyCreatedResponse(
        key_id=key_id,
        client_id=payload.client_id,
        key_prefix=raw_key[:12],
        label=payload.label,
        api_key=raw_key,
    )


@router.get("/keys", response_model=list[ApiKeyResponse])
def list_keys(
    auth: AuthContext = Depends(get_current_client),
):
    """List all API keys (never exposes hash or raw key)."""
    rows = list_api_keys()
    return [ApiKeyResponse(**row) for row in rows]


@router.delete("/keys/{key_id}")
def delete_key(
    key_id: str,
    auth: AuthContext = Depends(get_current_client),
):
    """Deactivate an API key (soft delete)."""
    if not deactivate_api_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deactivated", "key_id": key_id}
```

- [ ] **Step 2: Commit**

```bash
git add api/routers/auth.py
git commit -m "feat(auth): add key CRUD router"
```

---

### Task 5: Wire auth into `api/main.py`

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Add auth import and protect routers**

Replace the content of `api/main.py` with:

```python
"""
RamyPulse FastAPI Entrypoint.
Exposes the RamyPulse core analytics engine as a REST API.
"""
import os
import sys
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root project path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import health, dashboard, alerts, watchlists, campaigns, recommendations, explorer, admin, social_metrics, auth
from core.security.auth import get_current_client

app = FastAPI(
    title="RamyPulse Engine API",
    description="API REST pour la plateforme d'intelligence marketing RamyPulse",
    version="1.0.0"
)

# Enable CORS for the frontend (Google Labs Stitch / Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root redirect to docs
@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

# --- Public routes (no auth) ---
app.include_router(health.router, prefix="/api")

# --- Protected routes (require X-API-Key) ---
_auth = [Depends(get_current_client)]
app.include_router(dashboard.router, prefix="/api", dependencies=_auth)
app.include_router(alerts.router, prefix="/api", dependencies=_auth)
app.include_router(watchlists.router, prefix="/api", dependencies=_auth)
app.include_router(campaigns.router, prefix="/api", dependencies=_auth)
app.include_router(recommendations.router, prefix="/api", dependencies=_auth)
app.include_router(explorer.router, prefix="/api", dependencies=_auth)
app.include_router(social_metrics.router, prefix="/api", dependencies=_auth)
app.include_router(auth.router, prefix="/api", dependencies=_auth)

# --- Admin routes (no auth in this lot — will be added at integration) ---
app.include_router(admin.router, prefix="/api")
```

- [ ] **Step 2: Verify app starts**

Run:
```bash
cd g:/ramypulse && python -c "from api.main import app; print('Routes:', len(app.routes))"
```
Expected: prints route count without errors.

- [ ] **Step 3: Commit**

```bash
git add api/main.py
git commit -m "feat(auth): wire auth dependency into protected routers"
```

---

### Task 6: Seed key on first startup

**Files:**
- Modify: `core/database.py` (~line 1305, inside `create_tables`)

- [ ] **Step 1: Add `_seed_default_api_key` function**

Add this function in `core/database.py` near the other `_seed_default_*` functions (around line 1079):

```python
def _seed_default_api_key(connection: sqlite3.Connection) -> None:
    """Generate an initial API key for ramy_client_001 if none exists."""
    row = connection.execute("SELECT 1 FROM api_keys LIMIT 1").fetchone()
    if row is not None:
        return

    from core.security.auth import create_api_key
    key_id, raw_key = create_api_key(
        client_id=DEFAULT_CLIENT_ID,
        label="initial_seed_key",
    )
    logger.warning(
        "Initial API key generated for %s: %s — Store it securely.",
        DEFAULT_CLIENT_ID,
        raw_key,
    )
```

- [ ] **Step 2: Call it from `create_tables`**

In `create_tables()`, add `_seed_default_api_key(connection)` after `_seed_default_client_agent_config(connection)` (line ~1307):

```python
            _seed_default_client_agent_config(connection)
            _seed_default_api_key(connection)
            connection.commit()
```

- [ ] **Step 3: Verify seed key is generated**

Run:
```bash
cd g:/ramypulse && python -c "
from core.database import DatabaseManager
db = DatabaseManager()
db.create_tables()
import sqlite3, config
conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
count = conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0]
print(f'api_keys count: {count}')
"
```
Expected: `api_keys count: 1`

- [ ] **Step 4: Commit**

```bash
git add core/database.py
git commit -m "feat(auth): seed initial API key on first startup"
```

---

### Task 7: Write auth tests

**Files:**
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the test file**

Create `tests/test_auth.py`:

```python
"""Tests for API key authentication."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import config
from core.database import DatabaseManager
from core.security.auth import create_api_key, hash_key, list_api_keys, deactivate_api_key

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
    def test_no_key_returns_401(self):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code in (401, 422)

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
        assert resp.status_code != 401
        assert resp.status_code != 422

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
        # Make a request to trigger last_used_at update
        client.get(
            "/api/health",  # won't update because health is public
        )
        resp = client.get(
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
```

- [ ] **Step 2: Run auth tests**

Run:
```bash
cd g:/ramypulse && python -m pytest tests/test_auth.py -v
```
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth.py
git commit -m "test(auth): add comprehensive auth tests"
```

---

### Task 8: Fix existing tests (add auth headers)

**Files:**
- Modify: `tests/test_api.py` (add auth header to existing test client)

- [ ] **Step 1: Add a test API key to the existing test setup**

In `tests/test_api.py`, after `client = TestClient(app)` (line 32), add:

```python
# Create a test API key for authenticated requests
from core.security.auth import create_api_key as _create_test_key
_test_key_id, _test_raw_key = _create_test_key(client_id="ramy_client_001", label="test_suite")
_AUTH_HEADERS = {"X-API-Key": _test_raw_key}
```

- [ ] **Step 2: Update the `client` calls to include auth headers**

All existing tests that call protected endpoints need the auth header. The cleanest way: replace the plain `client` with a wrapper or add `headers=_AUTH_HEADERS` to each call.

In `tests/test_api.py`, replace the line:

```python
client = TestClient(app)
```

with:

```python
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
```

Then after the `_create_test_key` lines, set:

```python
client = _AuthClient(_raw_client, _AUTH_HEADERS)
```

This ensures every existing test call automatically includes the auth header without changing any test method.

- [ ] **Step 3: Run full test suite**

Run:
```bash
cd g:/ramypulse && python -m pytest tests/ -q --tb=short
```
Expected: All tests pass (including both test_auth.py and test_api.py).

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test(auth): add auth headers to existing test suite"
```

---

### Task 9: Final regression check

- [ ] **Step 1: Run full test suite**

```bash
cd g:/ramypulse && python -m pytest tests/ -v --tb=short
```
Expected: All tests pass.

- [ ] **Step 2: Verify app starts cleanly**

```bash
cd g:/ramypulse && python -c "from api.main import app; print('App OK, routes:', len(app.routes))"
```

- [ ] **Step 3: Spot-check seed key**

```bash
cd g:/ramypulse && python -c "
from core.security.auth import list_api_keys
keys = list_api_keys('ramy_client_001')
print(f'Keys for ramy_client_001: {len(keys)}')
for k in keys:
    print(f'  {k[\"key_prefix\"]} — {k[\"label\"]} — active={k[\"is_active\"]}')
"
```
