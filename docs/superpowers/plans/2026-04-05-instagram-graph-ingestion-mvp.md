# Instagram Graph Ingestion MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Instagram content discovery and ingestion via Meta Graph API through the existing orchestrator pipeline.

**Architecture:** Extend `InstagramConnector` with a `fetch_mode="api"` path that calls Meta Graph API to list media. Wire `sources.credential_id` into the orchestrator's credential resolution. Add token refresh before each sync cycle. All existing modes (snapshot, collector) remain untouched.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, urllib.request (Meta Graph API), unittest.mock for HTTP mocking.

**Spec:** `docs/superpowers/specs/2026-04-05-instagram-graph-ingestion-mvp-design.md`

**Invariants (must hold after every task):**
1. `fetch_mode="snapshot"` works exactly as before
2. `fetch_mode="collector"` works exactly as before
3. `fetch_mode="api"` for Instagram is a new path, does not modify other platforms
4. `coverage_key` / `source_priority` / scheduler remain unchanged
5. `content_items` deduplication unchanged
6. `credential_ref` in `config_json` continues to function
7. `credential_id` supported, never mandatory
8. No regression on existing 739 tests

**Forbidden files:** `scheduler.py`, `content_identity.py`, `platform_snapshot_connector.py`, other connectors (facebook, youtube, google_maps), `source_config.py`, `core/social_metrics/*`, `frontend/`, `core/alerts/*`, `core/notifications/*`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `core/connectors/instagram_connector.py` | Rewrite | Route `fetch_mode="api"` to Graph API, delegate other modes to parent |
| `core/connectors/meta_graph_client.py` | Create | HTTP client for Meta Graph API (GET + pagination) |
| `core/connectors/token_refresh.py` | Create | Refresh Meta long-lived tokens before expiry |
| `core/social_metrics/credential_manager.py` | Modify | Add `update_credential_token()` function |
| `core/ingestion/orchestrator.py` | Modify | Add `credential_id` resolution + token refresh call |
| `tests/test_instagram_connector.py` | Create | Tests for all fetch_modes + Graph API mocking |
| `tests/test_meta_graph_client.py` | Create | Tests for HTTP client + pagination |
| `tests/test_token_refresh.py` | Create | Tests for token refresh logic |
| `tests/test_orchestrator_credentials.py` | Create | Tests for credential_id resolution chain |

---

### Task 1: Meta Graph HTTP client

**Files:**
- Create: `core/connectors/meta_graph_client.py`
- Create: `tests/test_meta_graph_client.py`

- [ ] **Step 1: Write the failing test for single-page fetch**

```python
# tests/test_meta_graph_client.py
"""Tests for Meta Graph API HTTP client."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest


def _mock_urlopen_response(data: dict) -> MagicMock:
    """Create a mock urllib response that returns JSON data."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(data).encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestMetaGraphGet:
    def test_single_page_returns_data(self):
        from core.connectors.meta_graph_client import meta_graph_get

        api_response = {
            "data": [
                {"id": "111", "caption": "Hello"},
                {"id": "222", "caption": "World"},
            ]
        }

        with patch("core.connectors.meta_graph_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _mock_urlopen_response(api_response)
            result = meta_graph_get("12345/media", access_token="fake_token", fields="id,caption")

        assert result == api_response
        call_url = mock_urlopen.call_args[0][0].full_url
        assert "12345/media" in call_url
        assert "access_token=fake_token" in call_url
        assert "fields=id%2Ccaption" in call_url or "fields=id,caption" in call_url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_meta_graph_client.py::TestMetaGraphGet::test_single_page_returns_data -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.connectors.meta_graph_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/connectors/meta_graph_client.py
"""HTTP client for Meta Graph API."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def meta_graph_get(
    endpoint: str,
    *,
    access_token: str,
    fields: str | None = None,
    params: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Execute a GET request against the Meta Graph API.

    Args:
        endpoint: Path after the base URL, e.g. "12345/media".
        access_token: Valid Meta access token.
        fields: Comma-separated field list for the ?fields= parameter.
        params: Additional query parameters.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        urllib.error.HTTPError: On HTTP errors (rate limit, auth failure, etc.)
    """
    query_params: dict[str, str] = {"access_token": access_token}
    if fields:
        query_params["fields"] = fields
    if params:
        query_params.update(params)

    url = f"{_GRAPH_API_BASE}/{endpoint}?{urllib.parse.urlencode(query_params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "RamyPulse/1.0"})

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_meta_graph_client.py::TestMetaGraphGet::test_single_page_returns_data -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for paginated fetch**

```python
# Append to tests/test_meta_graph_client.py

class TestMetaGraphPaginate:
    def test_follows_cursor_pagination(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page1 = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor_abc"}, "next": "https://graph.facebook.com/v21.0/next"},
        }
        page2 = {
            "data": [{"id": "222"}],
            "paging": {"cursors": {"after": "cursor_def"}},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.side_effect = [page1, page2]
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id")

        assert len(items) == 2
        assert items[0]["id"] == "111"
        assert items[1]["id"] == "222"
        assert mock_get.call_count == 2
        # Second call should include the after cursor
        second_call_params = mock_get.call_args_list[1][1].get("params", {})
        assert second_call_params.get("after") == "cursor_abc"

    def test_respects_max_pages(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor"}, "next": "https://graph.facebook.com/v21.0/next"},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.return_value = page
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id", max_pages=2)

        assert len(items) == 2
        assert mock_get.call_count == 2

    def test_empty_response(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.return_value = {"data": []}
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id")

        assert items == []
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_meta_graph_client.py::TestMetaGraphPaginate -v`
Expected: FAIL with `ImportError: cannot import name 'meta_graph_paginate'`

- [ ] **Step 7: Implement pagination**

Append to `core/connectors/meta_graph_client.py`:

```python
def meta_graph_paginate(
    endpoint: str,
    *,
    access_token: str,
    fields: str | None = None,
    max_pages: int = 20,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    """Fetch all items from a paginated Meta Graph API endpoint.

    Follows cursor-based pagination until no more pages or max_pages reached.

    Args:
        endpoint: Path after the base URL, e.g. "12345/media".
        access_token: Valid Meta access token.
        fields: Comma-separated field list.
        max_pages: Maximum number of pages to fetch (safety limit).
        timeout: Request timeout per page.

    Returns:
        Flat list of all items across all pages.
    """
    all_items: list[dict[str, Any]] = []
    extra_params: dict[str, str] = {}

    for page_num in range(max_pages):
        response = meta_graph_get(
            endpoint,
            access_token=access_token,
            fields=fields,
            params=extra_params if extra_params else None,
            timeout=timeout,
        )
        items = response.get("data", [])
        if not items:
            break

        all_items.extend(items)

        paging = response.get("paging", {})
        if "next" not in paging:
            break
        after_cursor = paging.get("cursors", {}).get("after")
        if not after_cursor:
            break
        extra_params = {"after": after_cursor}

    logger.info("Fetched %d items in %d pages from %s", len(all_items), page_num + 1, endpoint)
    return all_items
```

- [ ] **Step 8: Run all tests to verify they pass**

Run: `python -m pytest tests/test_meta_graph_client.py -v`
Expected: 4 PASSED

- [ ] **Step 9: Write test for HTTP error handling**

```python
# Append to tests/test_meta_graph_client.py
import urllib.error


class TestMetaGraphErrors:
    def test_http_error_propagates(self):
        from core.connectors.meta_graph_client import meta_graph_get

        with patch("core.connectors.meta_graph_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://graph.facebook.com/v21.0/test",
                code=401,
                msg="Invalid OAuth access token",
                hdrs=None,
                fp=None,
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                meta_graph_get("test", access_token="bad_token")
            assert exc_info.value.code == 401

    def test_paginate_stops_on_error(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page1 = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor"}, "next": "https://..."},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.side_effect = [
                page1,
                urllib.error.HTTPError("url", 429, "Rate limited", None, None),
            ]
            with pytest.raises(urllib.error.HTTPError):
                meta_graph_paginate("12345/media", access_token="fake", fields="id")
```

- [ ] **Step 10: Run all tests to verify they pass**

Run: `python -m pytest tests/test_meta_graph_client.py -v`
Expected: 6 PASSED

- [ ] **Step 11: Commit**

```bash
git add core/connectors/meta_graph_client.py tests/test_meta_graph_client.py
git commit -m "feat(connectors): add Meta Graph API HTTP client with pagination"
```

---

### Task 2: Instagram connector `fetch_mode="api"`

**Files:**
- Modify: `core/connectors/instagram_connector.py`
- Create: `tests/test_instagram_connector.py`

- [ ] **Step 1: Write failing tests for the API fetch mode**

```python
# tests/test_instagram_connector.py
"""Tests for InstagramConnector fetch_mode='api'."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from core.connectors.instagram_connector import InstagramConnector


def _make_source(fetch_mode: str = "api", credential_id: str | None = None) -> dict:
    """Create a minimal source dict for testing."""
    return {
        "source_id": "src-test-ig",
        "client_id": "test_client",
        "platform": "instagram",
        "source_type": "api",
        "owner_type": "brand",
        "credential_id": credential_id,
        "config_json": json.dumps({
            "fetch_mode": fetch_mode,
            "profile_id": "17841400123456789",
        }),
    }


def _make_media_item(media_id: str, caption: str = "Test caption") -> dict:
    return {
        "id": media_id,
        "caption": caption,
        "timestamp": "2026-03-15T10:30:00+0000",
        "media_type": "IMAGE",
        "media_url": f"https://scontent.cdninstagram.com/{media_id}.jpg",
        "permalink": f"https://www.instagram.com/p/{media_id}/",
        "like_count": 42,
        "comments_count": 5,
    }


class TestInstagramConnectorApiMode:
    def test_fetch_mode_api_calls_graph_api(self):
        connector = InstagramConnector()
        source = _make_source("api")
        credentials = {"access_token": "fake_token", "account_id": "17841400123456789"}
        media_items = [_make_media_item("111"), _make_media_item("222")]

        with patch("core.connectors.instagram_connector.meta_graph_paginate") as mock_paginate:
            mock_paginate.return_value = media_items
            documents = connector.fetch_documents(source, credentials=credentials)

        assert len(documents) == 2
        assert documents[0]["external_document_id"] == "111"
        assert documents[0]["raw_text"] == "Test caption"
        assert documents[0]["source_url"] == "https://www.instagram.com/p/111/"
        assert "raw_payload" in documents[0]
        assert "raw_metadata" in documents[0]
        assert documents[0]["raw_metadata"]["media_type"] == "IMAGE"

    def test_fetch_mode_api_no_credentials_raises(self):
        connector = InstagramConnector()
        source = _make_source("api")

        with pytest.raises(ValueError, match="access_token"):
            connector.fetch_documents(source, credentials={})

    def test_fetch_mode_api_no_account_id_raises(self):
        connector = InstagramConnector()
        source = _make_source("api")

        with pytest.raises(ValueError, match="account_id"):
            connector.fetch_documents(source, credentials={"access_token": "tok"})

    def test_fetch_mode_api_empty_results(self):
        connector = InstagramConnector()
        source = _make_source("api")
        credentials = {"access_token": "fake_token", "account_id": "17841400123456789"}

        with patch("core.connectors.instagram_connector.meta_graph_paginate") as mock_paginate:
            mock_paginate.return_value = []
            documents = connector.fetch_documents(source, credentials=credentials)

        assert documents == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_instagram_connector.py::TestInstagramConnectorApiMode -v`
Expected: FAIL (connector still uses SnapshotPlatformConnector, no API mode)

- [ ] **Step 3: Rewrite the connector**

```python
# core/connectors/instagram_connector.py
"""Connecteur Instagram Wave 5.2 — snapshot + API Graph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.connectors.meta_graph_client import meta_graph_paginate
from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector
from core.connectors.source_config import parse_source_config

logger = logging.getLogger(__name__)

_MEDIA_FIELDS = (
    "id,caption,timestamp,media_type,media_url,"
    "permalink,like_count,comments_count"
)


class InstagramConnector(SnapshotPlatformConnector):
    """Connecteur Instagram via snapshot local, scraper, ou API Graph officielle."""

    def __init__(self) -> None:
        super().__init__(
            platform="instagram",
            default_snapshot_names=("instagram_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_instagram",),
        )

    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        file_path=None,
        column_mapping=None,
        **kwargs,
    ) -> list[dict]:
        source_config = parse_source_config(source)
        fetch_mode = str(source_config.get("fetch_mode") or "snapshot").strip().lower()

        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials or {})

        # Existing behavior: snapshot + scraper fallback
        return super().fetch_documents(
            source,
            credentials=credentials,
            file_path=file_path,
            column_mapping=column_mapping,
            **kwargs,
        )

    def _fetch_from_graph_api(
        self,
        source: dict,
        credentials: dict,
    ) -> list[dict]:
        """Discover and fetch media via Meta Graph API."""
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError(
                "Instagram API mode requires 'access_token' in credentials. "
                "Ensure the source has a valid credential_id linked to platform_credentials."
            )

        account_id = credentials.get("account_id")
        if not account_id:
            raise ValueError(
                "Instagram API mode requires 'account_id' (IG Business User ID) in credentials. "
                "Set account_id in the platform_credentials record."
            )

        source_config = parse_source_config(source)
        max_pages = int(source_config.get("max_pages", 20))

        media_items = meta_graph_paginate(
            f"{account_id}/media",
            access_token=access_token,
            fields=_MEDIA_FIELDS,
            max_pages=max_pages,
        )

        now = datetime.now(timezone.utc).isoformat()
        documents: list[dict] = []
        for media in media_items:
            documents.append({
                "external_document_id": media["id"],
                "raw_text": media.get("caption") or "",
                "raw_payload": media,
                "raw_metadata": {
                    "media_type": media.get("media_type"),
                    "permalink": media.get("permalink"),
                    "timestamp": media.get("timestamp"),
                    "like_count": media.get("like_count"),
                    "comments_count": media.get("comments_count"),
                },
                "source_url": media.get("permalink"),
                "collected_at": now,
            })

        logger.info(
            "Instagram API: fetched %d media for account %s",
            len(documents),
            account_id,
        )
        return documents
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_instagram_connector.py::TestInstagramConnectorApiMode -v`
Expected: 4 PASSED

- [ ] **Step 5: Write test to verify snapshot mode is unchanged**

```python
# Append to tests/test_instagram_connector.py

class TestInstagramConnectorSnapshotMode:
    """Verify that snapshot and collector modes still delegate to the parent."""

    def test_fetch_mode_snapshot_delegates_to_parent(self):
        connector = InstagramConnector()
        source = _make_source("snapshot")

        with patch.object(
            connector.__class__.__bases__[0],  # SnapshotPlatformConnector
            "fetch_documents",
            return_value=[{"external_document_id": "snap-1"}],
        ) as mock_parent:
            documents = connector.fetch_documents(source, credentials=None)

        mock_parent.assert_called_once()
        assert documents == [{"external_document_id": "snap-1"}]

    def test_fetch_mode_default_is_snapshot(self):
        connector = InstagramConnector()
        source = {
            "source_id": "src-test",
            "platform": "instagram",
            "config_json": "{}",
        }

        with patch.object(
            connector.__class__.__bases__[0],
            "fetch_documents",
            return_value=[],
        ) as mock_parent:
            connector.fetch_documents(source, credentials=None)

        mock_parent.assert_called_once()
```

- [ ] **Step 6: Run all connector tests**

Run: `python -m pytest tests/test_instagram_connector.py -v`
Expected: 6 PASSED

- [ ] **Step 7: Commit**

```bash
git add core/connectors/instagram_connector.py tests/test_instagram_connector.py
git commit -m "feat(instagram): add fetch_mode=api via Meta Graph API"
```

---

### Task 3: Credential ID resolution in orchestrator

**Files:**
- Modify: `core/ingestion/orchestrator.py:196-203`
- Create: `tests/test_orchestrator_credentials.py`

- [ ] **Step 1: Write failing tests for credential_id resolution**

```python
# tests/test_orchestrator_credentials.py
"""Tests for credential_id resolution in the orchestrator."""

from __future__ import annotations

import json
import sqlite3

import pytest

import config
from core.database import DatabaseManager
from core.ingestion.orchestrator import IngestionOrchestrator
from core.social_metrics.credential_manager import create_credential

_db = DatabaseManager()
_db.create_tables()


def _create_test_credential(access_token: str = "test_token_123") -> str:
    """Create a credential and return its credential_id."""
    return create_credential(
        entity_type="brand",
        entity_name="test_brand",
        platform="instagram",
        account_id="17841400123456789",
        access_token=access_token,
        app_id="app_123",
        app_secret="secret_456",
    )


class TestCredentialIdResolution:
    def test_credential_id_resolves_token(self):
        """When source has credential_id, orchestrator should resolve it."""
        cred_id = _create_test_credential("my_real_token")
        orchestrator = IngestionOrchestrator()

        # Create a source with credential_id and fetch_mode=api
        source = orchestrator.create_source({
            "source_name": "IG API Test",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
        })

        # Patch the connector to capture what credentials it receives
        captured_credentials = {}

        def fake_fetch(src, *, credentials=None, **kw):
            captured_credentials.update(credentials or {})
            return []  # Return empty — we just want to inspect credentials

        from unittest.mock import patch
        with patch.object(orchestrator._connectors["instagram"], "fetch_documents", side_effect=fake_fetch):
            orchestrator.run_source_sync(source["source_id"])

        assert captured_credentials.get("access_token") == "my_real_token"
        assert captured_credentials.get("account_id") == "17841400123456789"

    def test_null_credential_id_uses_old_path(self):
        """When source has no credential_id, the old credential_ref path still works."""
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG Snapshot Test",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        captured_credentials = {}

        def fake_fetch(src, *, credentials=None, **kw):
            captured_credentials.update(credentials or {})
            return []

        from unittest.mock import patch
        with patch.object(orchestrator._connectors["instagram"], "fetch_documents", side_effect=fake_fetch):
            orchestrator.run_source_sync(source["source_id"])

        # No access_token from credential_id — should not crash
        assert "access_token" not in captured_credentials or captured_credentials.get("access_token") is None

    def test_other_platform_unaffected(self):
        """Facebook connector should not be affected by credential_id changes."""
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "FB Test",
            "platform": "facebook",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        def fake_fetch(src, *, credentials=None, **kw):
            return []

        from unittest.mock import patch
        with patch.object(orchestrator._connectors["facebook"], "fetch_documents", side_effect=fake_fetch):
            result = orchestrator.run_source_sync(source["source_id"])

        assert result["status"] == "success"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_orchestrator_credentials.py::TestCredentialIdResolution::test_credential_id_resolves_token -v`
Expected: FAIL (credential_id not resolved — captured_credentials won't have access_token)

- [ ] **Step 3: Modify orchestrator to resolve credential_id**

In `core/ingestion/orchestrator.py`, replace lines 200-203:

```python
            # Old code (lines 200-203):
            credentials_payload = {
                **resolve_credentials(source_config),
                **(credentials or {}),
            }
```

With:

```python
            # Resolve credentials: credential_id > credential_ref > runtime
            resolved_from_credential_id = {}
            credential_id = source.get("credential_id")
            if credential_id:
                from core.social_metrics.credential_manager import get_credential
                cred_record = get_credential(credential_id)
                if cred_record:
                    resolved_from_credential_id = {
                        k: v for k, v in {
                            "access_token": cred_record.get("access_token"),
                            "account_id": cred_record.get("account_id"),
                            "app_id": cred_record.get("app_id"),
                            "app_secret": cred_record.get("app_secret"),
                        }.items() if v is not None
                    }
            credentials_payload = {
                **resolve_credentials(source_config),
                **resolved_from_credential_id,
                **(credentials or {}),
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_orchestrator_credentials.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Run full regression**

Run: `python -m pytest tests/ -q --tb=short`
Expected: 739+ passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add core/ingestion/orchestrator.py tests/test_orchestrator_credentials.py
git commit -m "feat(orchestrator): resolve credential_id from platform_credentials"
```

---

### Task 4: Update credential token function

**Files:**
- Modify: `core/social_metrics/credential_manager.py`
- No separate test file — tested via token refresh tests in Task 5

- [ ] **Step 1: Write failing test for update_credential_token**

```python
# tests/test_token_refresh.py  (start of file — we'll add refresh tests in Task 5)
"""Tests for credential token update and Meta token refresh."""

from __future__ import annotations

import json

import pytest

from core.database import DatabaseManager
from core.social_metrics.credential_manager import (
    create_credential,
    get_credential,
    update_credential_token,
)

_db = DatabaseManager()
_db.create_tables()


class TestUpdateCredentialToken:
    def test_updates_token_and_extra_config(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="update_test",
            platform="instagram",
            access_token="old_token",
            extra_config={"expires_at": "2026-04-01T00:00:00Z"},
        )

        update_credential_token(
            cred_id,
            new_access_token="new_token_abc",
            extra_config_updates={"expires_at": "2026-06-01T00:00:00Z", "last_refreshed_at": "2026-04-05T00:00:00Z"},
        )

        cred = get_credential(cred_id)
        assert cred["access_token"] == "new_token_abc"
        assert cred["extra_config"]["expires_at"] == "2026-06-01T00:00:00Z"
        assert cred["extra_config"]["last_refreshed_at"] == "2026-04-05T00:00:00Z"

    def test_nonexistent_credential_returns_false(self):
        result = update_credential_token("cred-nonexistent", new_access_token="tok")
        assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_token_refresh.py::TestUpdateCredentialToken -v`
Expected: FAIL with `ImportError: cannot import name 'update_credential_token'`

- [ ] **Step 3: Implement update_credential_token**

Append to `core/social_metrics/credential_manager.py`:

```python
def update_credential_token(
    credential_id: str,
    *,
    new_access_token: str,
    extra_config_updates: dict | None = None,
) -> bool:
    """Update the access token (and optionally extra_config fields) for a credential.

    Returns True if the credential was found and updated, False otherwise.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT extra_config FROM platform_credentials WHERE credential_id = ?",
            [credential_id],
        ).fetchone()
        if not row:
            return False

        # Store the new token via secret_manager
        new_token_ref = store_secret(
            new_access_token,
            label=f"refreshed_token:{credential_id}",
        )

        # Merge extra_config updates
        try:
            existing_extra = json.loads(row["extra_config"] or "{}")
        except (TypeError, ValueError):
            existing_extra = {}
        if extra_config_updates:
            existing_extra.update(extra_config_updates)

        now = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE platform_credentials
            SET access_token_ref = ?, extra_config = ?, updated_at = ?
            WHERE credential_id = ?
            """,
            [new_token_ref, json.dumps(existing_extra, ensure_ascii=False), now, credential_id],
        )
        conn.commit()

    logger.info("Token updated for credential %s", credential_id)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_token_refresh.py::TestUpdateCredentialToken -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/social_metrics/credential_manager.py tests/test_token_refresh.py
git commit -m "feat(credentials): add update_credential_token for token refresh"
```

---

### Task 5: Token refresh module

**Files:**
- Create: `core/connectors/token_refresh.py`
- Modify: `tests/test_token_refresh.py` (append tests)

- [ ] **Step 1: Write failing tests for refresh logic**

Append to `tests/test_token_refresh.py`:

```python
from unittest.mock import patch, MagicMock
from core.connectors.token_refresh import refresh_if_needed


class TestRefreshIfNeeded:
    def test_no_refresh_when_far_from_expiry(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_far",
            platform="instagram",
            access_token="valid_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-06-01T00:00:00Z"},
        )
        # Token expires in ~57 days — no refresh needed
        result = refresh_if_needed(cred_id)
        assert result is False

    def test_refresh_when_near_expiry(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_near",
            platform="instagram",
            access_token="expiring_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-04-07T00:00:00Z"},  # ~2 days from now (2026-04-05)
        )

        new_token_response = {
            "access_token": "refreshed_token_xyz",
            "token_type": "bearer",
            "expires_in": 5184000,
        }

        with patch("core.connectors.token_refresh.meta_graph_get", return_value=new_token_response):
            result = refresh_if_needed(cred_id)

        assert result is True
        cred = get_credential(cred_id)
        assert cred["access_token"] == "refreshed_token_xyz"

    def test_no_refresh_when_expires_at_missing(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_no_expiry",
            platform="instagram",
            access_token="token_no_expiry",
            extra_config={},
        )
        result = refresh_if_needed(cred_id)
        assert result is False

    def test_refresh_failure_returns_false(self):
        import urllib.error
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_fail",
            platform="instagram",
            access_token="failing_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-04-07T00:00:00Z"},
        )

        with patch("core.connectors.token_refresh.meta_graph_get") as mock_get:
            mock_get.side_effect = urllib.error.HTTPError("url", 400, "Invalid token", None, None)
            result = refresh_if_needed(cred_id)

        assert result is False
        # Token should NOT have been changed
        cred = get_credential(cred_id)
        assert cred["access_token"] == "failing_token"

    def test_nonexistent_credential_returns_false(self):
        result = refresh_if_needed("cred-nonexistent-xyz")
        assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_token_refresh.py::TestRefreshIfNeeded -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.connectors.token_refresh'`

- [ ] **Step 3: Implement token refresh**

```python
# core/connectors/token_refresh.py
"""Meta token refresh for long-lived Facebook/Instagram tokens."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from core.connectors.meta_graph_client import meta_graph_get
from core.social_metrics.credential_manager import get_credential, update_credential_token

logger = logging.getLogger(__name__)

_REFRESH_THRESHOLD_DAYS = 5


def refresh_if_needed(credential_id: str) -> bool:
    """Refresh a Meta long-lived token if it expires within the threshold.

    Args:
        credential_id: The credential to check and potentially refresh.

    Returns:
        True if the token was refreshed, False otherwise (not needed, failed, or not found).
    """
    cred = get_credential(credential_id)
    if not cred:
        logger.warning("Token refresh: credential %s not found", credential_id)
        return False

    extra_config = cred.get("extra_config") or {}
    expires_at_str = extra_config.get("expires_at")
    if not expires_at_str:
        logger.debug("Token refresh: no expires_at for credential %s, skipping", credential_id)
        return False

    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        logger.warning("Token refresh: invalid expires_at '%s' for %s", expires_at_str, credential_id)
        return False

    now = datetime.now(timezone.utc)
    remaining = expires_at - now
    if remaining > timedelta(days=_REFRESH_THRESHOLD_DAYS):
        logger.debug(
            "Token refresh: credential %s has %d days remaining, no refresh needed",
            credential_id,
            remaining.days,
        )
        return False

    # Token needs refresh
    access_token = cred.get("access_token")
    app_id = cred.get("app_id")
    app_secret = cred.get("app_secret")

    if not access_token or not app_id or not app_secret:
        logger.warning(
            "Token refresh: credential %s missing access_token, app_id, or app_secret — cannot refresh",
            credential_id,
        )
        return False

    try:
        response = meta_graph_get(
            "oauth/access_token",
            access_token=access_token,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": access_token,
            },
        )
    except Exception:
        logger.exception("Token refresh failed for credential %s", credential_id)
        return False

    new_token = response.get("access_token")
    if not new_token:
        logger.warning("Token refresh: Meta response missing access_token for %s", credential_id)
        return False

    expires_in = int(response.get("expires_in", 5184000))
    new_expires_at = (now + timedelta(seconds=expires_in)).isoformat()

    update_credential_token(
        credential_id,
        new_access_token=new_token,
        extra_config_updates={
            "expires_at": new_expires_at,
            "last_refreshed_at": now.isoformat(),
        },
    )

    logger.info(
        "Token refreshed for credential %s — new expiry: %s",
        credential_id,
        new_expires_at,
    )
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_token_refresh.py -v`
Expected: 7 PASSED (2 from Task 4 + 5 new)

- [ ] **Step 5: Commit**

```bash
git add core/connectors/token_refresh.py tests/test_token_refresh.py
git commit -m "feat(connectors): add Meta token refresh before expiry"
```

---

### Task 6: Wire token refresh into orchestrator

**Files:**
- Modify: `core/ingestion/orchestrator.py:196-203` (the section modified in Task 3)

- [ ] **Step 1: Write failing test for token refresh call during sync**

Append to `tests/test_orchestrator_credentials.py`:

```python
from unittest.mock import patch


class TestTokenRefreshDuringSync:
    def test_refresh_called_for_instagram_api_source(self):
        cred_id = _create_test_credential("token_to_refresh")
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG Refresh Test",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
        })

        with (
            patch("core.ingestion.orchestrator.refresh_if_needed") as mock_refresh,
            patch.object(orchestrator._connectors["instagram"], "fetch_documents", return_value=[]),
        ):
            mock_refresh.return_value = False
            orchestrator.run_source_sync(source["source_id"])

        mock_refresh.assert_called_once_with(cred_id)

    def test_refresh_not_called_without_credential_id(self):
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG No Cred Test",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        with (
            patch("core.ingestion.orchestrator.refresh_if_needed") as mock_refresh,
            patch.object(orchestrator._connectors["instagram"], "fetch_documents", return_value=[]),
        ):
            orchestrator.run_source_sync(source["source_id"])

        mock_refresh.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_orchestrator_credentials.py::TestTokenRefreshDuringSync -v`
Expected: FAIL (refresh_if_needed not imported or called)

- [ ] **Step 3: Add token refresh call to orchestrator**

In `core/ingestion/orchestrator.py`, add the import at the top with the other imports (after line 17):

```python
from core.connectors.token_refresh import refresh_if_needed
```

Then in `run_source_sync()`, add the refresh call right after `sync_run_id = self._start_sync_run(...)` (after line 196), before the connector call:

```python
        sync_run_id = self._start_sync_run(source_id, run_mode)
        try:
            # Refresh Meta token if needed before fetching
            credential_id = source.get("credential_id")
            if credential_id:
                refresh_if_needed(credential_id)

            connector = self._select_connector(source)
```

Note: the `credential_id` variable is now read once at this point, and reused in the credential resolution block added in Task 3. Adjust Task 3's code to use this variable instead of reading `source.get("credential_id")` again:

```python
            # Resolve credentials: credential_id > credential_ref > runtime
            resolved_from_credential_id = {}
            if credential_id:
                from core.social_metrics.credential_manager import get_credential
                cred_record = get_credential(credential_id)
                if cred_record:
                    resolved_from_credential_id = {
                        k: v for k, v in {
                            "access_token": cred_record.get("access_token"),
                            "account_id": cred_record.get("account_id"),
                            "app_id": cred_record.get("app_id"),
                            "app_secret": cred_record.get("app_secret"),
                        }.items() if v is not None
                    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_orchestrator_credentials.py -v`
Expected: 5 PASSED (3 from Task 3 + 2 new)

- [ ] **Step 5: Run full regression**

Run: `python -m pytest tests/ -q --tb=short`
Expected: 739+ passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add core/ingestion/orchestrator.py tests/test_orchestrator_credentials.py
git commit -m "feat(orchestrator): call token refresh before Instagram API sync"
```

---

### Task 7: Content deduplication integration test

**Files:**
- Create: `tests/test_instagram_dedup.py`

- [ ] **Step 1: Write the dedup integration test**

```python
# tests/test_instagram_dedup.py
"""Integration test: same Instagram post via API and import → single content_item."""

from __future__ import annotations

import json
import sqlite3

import config
from core.database import DatabaseManager
from core.ingestion.orchestrator import IngestionOrchestrator
from core.social_metrics.credential_manager import create_credential
from unittest.mock import patch

_db = DatabaseManager()
_db.create_tables()


class TestInstagramDedup:
    def test_api_then_import_same_post_single_content_item(self):
        """A post fetched via API and then via import should resolve to one content_item."""
        cred_id = create_credential(
            entity_type="brand",
            entity_name="dedup_test",
            platform="instagram",
            account_id="17841400123456789",
            access_token="dedup_token",
        )

        orchestrator = IngestionOrchestrator()

        # Source 1: API (priority 1)
        api_source = orchestrator.create_source({
            "source_name": "IG API Dedup",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
            "source_priority": 1,
            "coverage_key": "instagram:dedup_test",
        })

        # Source 2: Import (priority 2)
        import_source = orchestrator.create_source({
            "source_name": "IG Import Dedup",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
            "source_priority": 2,
            "coverage_key": "instagram:dedup_test",
        })

        permalink = "https://www.instagram.com/p/ABC123/"

        # Sync via API — returns one post
        api_media = [{
            "id": "media_ABC123",
            "caption": "Test dedup post",
            "timestamp": "2026-03-15T10:30:00+0000",
            "media_type": "IMAGE",
            "permalink": permalink,
            "like_count": 10,
            "comments_count": 2,
        }]

        with patch("core.connectors.instagram_connector.meta_graph_paginate", return_value=api_media):
            api_result = orchestrator.run_source_sync(api_source["source_id"])

        assert api_result["records_inserted"] == 1

        # Sync via import — returns same post (same permalink)
        import_docs = [{
            "external_document_id": "media_ABC123",
            "raw_text": "Test dedup post",
            "raw_payload": {"id": "media_ABC123", "permalink": permalink},
            "raw_metadata": {"media_type": "IMAGE"},
            "source_url": permalink,
            "collected_at": "2026-03-16T00:00:00Z",
        }]

        with patch.object(orchestrator._connectors["instagram"], "fetch_documents", return_value=import_docs):
            import_result = orchestrator.run_source_sync(import_source["source_id"])

        assert import_result["records_inserted"] == 1

        # Both raw_documents should point to the same content_item
        conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT content_item_id
            FROM raw_documents
            WHERE source_id IN (?, ?)
            AND content_item_id IS NOT NULL
            """,
            [api_source["source_id"], import_source["source_id"]],
        ).fetchall()
        conn.close()

        content_item_ids = [row["content_item_id"] for row in rows]
        # Should be exactly 1 unique content_item_id (dedup worked)
        assert len(content_item_ids) == 1
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_instagram_dedup.py -v`
Expected: PASS (content_identity already handles this — we're just proving it)

- [ ] **Step 3: Commit**

```bash
git add tests/test_instagram_dedup.py
git commit -m "test(instagram): verify API + import dedup to single content_item"
```

---

### Task 8: Full regression and final verification

**Files:**
- No new files

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -q --tb=short`
Expected: 739+ passed (original) + ~18 new tests = 757+ passed, 0 failed

- [ ] **Step 2: Verify invariant — existing snapshot connector tests still pass**

Run: `python -m pytest tests/test_api.py -q --tb=short`
Expected: All existing API tests pass (they use snapshot/import modes, not API mode)

- [ ] **Step 3: Verify invariant — auth tests still pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: 13 passed

- [ ] **Step 4: Verify invariant — database tests still pass**

Run: `python -m pytest tests/test_database.py -v`
Expected: All passed

- [ ] **Step 5: Commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: final verification — Instagram Graph Ingestion MVP complete"
```

---

## Self-Review

**1. Spec coverage:**
- Content discovery via Graph API → Task 1 + Task 2
- `credential_id` → `platform_credentials` bridge → Task 3
- Token lifecycle / refresh → Task 4 + Task 5 + Task 6
- Invariant: snapshot/collector unchanged → Task 2 (Step 5-6)
- Invariant: content dedup → Task 7
- Invariant: full regression → Task 8
- Source configuration contract → covered by test fixtures in Task 3

**2. Placeholder scan:** No TBD, TODO, or "add appropriate handling" found.

**3. Type consistency:**
- `meta_graph_get()` — same signature in Task 1 and used in Task 5
- `meta_graph_paginate()` — same signature in Task 1 and used in Task 2
- `get_credential()` — existing function, same return type used in Task 3, 4, 5
- `update_credential_token()` — defined in Task 4, used in Task 5
- `refresh_if_needed()` — defined in Task 5, used in Task 6
- `credentials` dict keys (`access_token`, `account_id`, `app_id`, `app_secret`) — consistent across all tasks
