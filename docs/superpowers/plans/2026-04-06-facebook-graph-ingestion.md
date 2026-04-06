# Facebook Graph Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `fetch_mode="api"` to `FacebookConnector` (posts + comments → raw_documents for ABSA) and create `facebook_graph_collector.py` (engagement metrics → post_engagement_metrics for campaign tracking).

**Architecture:** `FacebookConnector._fetch_from_graph_api()` calls `/{page_id}/posts` with nested comment fields via the existing `meta_graph_client.meta_graph_paginate()`, producing one raw_document per post and one per comment. `facebook_graph_collector.py` mirrors `instagram_graph_collector.py` but uses `meta_graph_get()` instead of its own HTTP code. All credential wiring, token refresh, and orchestrator integration are already in place from the Instagram sprint — zero changes needed there.

**Tech Stack:** Python 3.10+, urllib.request (via meta_graph_client), SQLite, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `core/connectors/facebook_connector.py` | Rewrite stub | Fetch posts + comments from Meta Graph API |
| `core/social_metrics/facebook_graph_collector.py` | Create | Collect engagement metrics for a known Facebook post_id |
| `tests/test_facebook_connector.py` | Create | TDD coverage for FacebookConnector API mode |
| `tests/test_facebook_graph_collector.py` | Create | TDD coverage for facebook_graph_collector |

**Do not touch:** `meta_graph_client.py`, `token_refresh.py`, `orchestrator.py`, `credential_manager.py`, `database.py`, `instagram_connector.py`, `platform_snapshot_connector.py`.

---

## Context for implementers

Before starting, read these files to understand the patterns you must follow:

- `core/connectors/instagram_connector.py` — the exact model for FacebookConnector
- `core/connectors/meta_graph_client.py` — `meta_graph_get()` and `meta_graph_paginate()` signatures
- `core/connectors/source_config.py` — `parse_source_config()` usage
- `core/social_metrics/instagram_graph_collector.py` — the model for facebook_graph_collector

Key facts:
- `meta_graph_paginate(endpoint, *, access_token, fields, max_pages)` returns `list[dict]`
- `meta_graph_get(endpoint, *, access_token, fields, params, timeout)` returns `dict`
- `parse_source_config(source)` returns a dict from `source["config_json"]`
- The `post_engagement_metrics` table columns: `metric_id, post_id, collected_at, likes, comments, shares, views, reach, impressions, saves, collection_mode, raw_response`

---

## Task 1: FacebookConnector — fetch_mode="api"

**Files:**
- Modify: `core/connectors/facebook_connector.py`
- Create: `tests/test_facebook_connector.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_facebook_connector.py
"""Tests pour FacebookConnector avec fetch_mode='api'."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.connectors.facebook_connector import FacebookConnector


def _source(fetch_mode: str = "api", page_id: str = "111222333") -> dict:
    return {
        "source_id": "src-fb-001",
        "platform": "facebook",
        "config_json": {"fetch_mode": fetch_mode, "page_id": page_id},
    }


def _creds(access_token: str = "tok123") -> dict:
    return {"access_token": access_token}


_SAMPLE_POST = {
    "id": "post_001",
    "message": "Nouveau jus citron disponible",
    "created_time": "2026-04-01T10:00:00+0000",
    "permalink_url": "https://facebook.com/ramy/posts/post_001",
    "reactions": {"summary": {"total_count": 42}},
    "comments": {
        "data": [
            {
                "id": "comment_001",
                "message": "Vraiment délicieux",
                "created_time": "2026-04-01T11:00:00+0000",
                "like_count": 3,
            },
            {
                "id": "comment_002",
                "message": "Trop sucré pour moi",
                "created_time": "2026-04-01T12:00:00+0000",
                "like_count": 0,
            },
        ],
        "summary": {"total_count": 2},
    },
}


class TestFacebookConnectorApiMode:
    def test_returns_post_and_comments_as_separate_documents(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        # 1 post + 2 comments = 3 documents
        assert len(docs) == 3

    def test_post_document_structure(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        post_docs = [d for d in docs if d["raw_metadata"].get("document_type") == "post"]
        assert len(post_docs) == 1
        doc = post_docs[0]
        assert doc["external_document_id"] == "post_001"
        assert doc["raw_text"] == "Nouveau jus citron disponible"
        assert doc["source_url"] == "https://facebook.com/ramy/posts/post_001"
        assert doc["raw_metadata"]["reactions_total"] == 42
        assert doc["raw_metadata"]["comments_total"] == 2
        assert "collected_at" in doc

    def test_comment_documents_structure(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        comment_docs = [d for d in docs if d["raw_metadata"].get("document_type") == "comment"]
        assert len(comment_docs) == 2
        c1 = next(d for d in comment_docs if d["external_document_id"] == "comment_001")
        assert c1["raw_text"] == "Vraiment délicieux"
        assert c1["raw_metadata"]["parent_post_id"] == "post_001"
        assert c1["raw_metadata"]["like_count"] == 3
        assert c1["source_url"] == "https://facebook.com/ramy/posts/post_001"

    def test_post_with_no_comments_returns_only_post_document(self):
        connector = FacebookConnector()
        post_no_comments = {
            "id": "post_002",
            "message": "Post sans commentaires",
            "created_time": "2026-04-01T10:00:00+0000",
            "permalink_url": "https://facebook.com/ramy/posts/post_002",
        }
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [post_no_comments]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        assert len(docs) == 1
        assert docs[0]["raw_metadata"]["document_type"] == "post"

    def test_missing_access_token_raises_value_error(self):
        connector = FacebookConnector()
        with pytest.raises(ValueError, match="access_token"):
            connector.fetch_documents(_source(), credentials={})

    def test_missing_page_id_raises_value_error(self):
        connector = FacebookConnector()
        source_no_page = {
            "source_id": "src-fb-002",
            "platform": "facebook",
            "config_json": {"fetch_mode": "api"},
        }
        with pytest.raises(ValueError, match="page_id"):
            connector.fetch_documents(source_no_page, credentials=_creds())

    def test_snapshot_mode_delegates_to_parent(self):
        connector = FacebookConnector()
        with patch(
            "core.connectors.platform_snapshot_connector.SnapshotPlatformConnector.fetch_documents"
        ) as mock_parent:
            mock_parent.return_value = []
            result = connector.fetch_documents(_source(fetch_mode="snapshot"), credentials=_creds())
        mock_parent.assert_called_once()
        assert result == []

    def test_default_mode_is_snapshot(self):
        """Sans fetch_mode explicite, le connecteur délègue au parent (snapshot)."""
        connector = FacebookConnector()
        source_no_mode = {
            "source_id": "src-fb-003",
            "platform": "facebook",
            "config_json": {"page_id": "111222333"},
        }
        with patch(
            "core.connectors.platform_snapshot_connector.SnapshotPlatformConnector.fetch_documents"
        ) as mock_parent:
            mock_parent.return_value = []
            connector.fetch_documents(source_no_mode, credentials=_creds())
        mock_parent.assert_called_once()

    def test_api_error_propagates(self):
        """Une erreur HTTP (rate limit, token invalide) est remontée à l'orchestrateur."""
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.side_effect = Exception("HTTP 429 Too Many Requests")
            with pytest.raises(Exception, match="429"):
                connector.fetch_documents(_source(), credentials=_creds())
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```
python -m pytest tests/test_facebook_connector.py -v
```

Expected: `ImportError` or `AttributeError` — `_fetch_from_graph_api` does not exist yet.

- [ ] **Step 3: Implement FacebookConnector**

Replace the entire content of `core/connectors/facebook_connector.py`:

```python
"""Connecteur Facebook Pages Wave 5.3 — snapshot + API Graph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.connectors.meta_graph_client import meta_graph_paginate
from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector
from core.connectors.source_config import parse_source_config

logger = logging.getLogger(__name__)

_POSTS_FIELDS = (
    "id,message,story,created_time,permalink_url,"
    "reactions.summary(true),"
    "comments.limit(100){id,message,created_time,like_count}"
)


class FacebookConnector(SnapshotPlatformConnector):
    """Connecteur Facebook Pages via snapshot local, scraper, ou API Graph officielle."""

    def __init__(self) -> None:
        super().__init__(
            platform="facebook",
            default_snapshot_names=("facebook_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_facebook",),
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
        """Récupère les documents Facebook selon le mode de collecte configuré."""
        source_config = parse_source_config(source)
        fetch_mode = str(source_config.get("fetch_mode") or "snapshot").strip().lower()

        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials or {})

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
        """Collecte les posts et commentaires d'une Page Facebook via Meta Graph API."""
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError(
                "Facebook API mode requires 'access_token' in credentials. "
                "Ensure the source has a valid credential_id linked to platform_credentials."
            )

        source_config = parse_source_config(source)
        page_id = str(source_config.get("page_id") or "").strip()
        if not page_id:
            raise ValueError(
                "Facebook API mode requires 'page_id' in config_json. "
                "Set page_id in the source configuration."
            )

        max_pages = int(source_config.get("max_pages", 10))

        posts = meta_graph_paginate(
            f"{page_id}/posts",
            access_token=access_token,
            fields=_POSTS_FIELDS,
            max_pages=max_pages,
        )

        now = datetime.now(timezone.utc).isoformat()
        documents: list[dict] = []

        for post in posts:
            permalink = post.get("permalink_url")
            documents.append({
                "external_document_id": post["id"],
                "raw_text": post.get("message") or post.get("story") or "",
                "raw_payload": post,
                "raw_metadata": {
                    "document_type": "post",
                    "permalink": permalink,
                    "timestamp": post.get("created_time"),
                    "reactions_total": (
                        post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                    ),
                    "comments_total": (
                        post.get("comments", {}).get("summary", {}).get("total_count", 0)
                    ),
                },
                "source_url": permalink,
                "collected_at": now,
            })

            for comment in post.get("comments", {}).get("data", []):
                documents.append({
                    "external_document_id": comment["id"],
                    "raw_text": comment.get("message") or "",
                    "raw_payload": comment,
                    "raw_metadata": {
                        "document_type": "comment",
                        "parent_post_id": post["id"],
                        "timestamp": comment.get("created_time"),
                        "like_count": comment.get("like_count", 0),
                    },
                    "source_url": permalink,
                    "collected_at": now,
                })

        logger.info(
            "Facebook API: fetched %d documents (posts + comments) for page %s",
            len(documents),
            page_id,
        )
        return documents
```

- [ ] **Step 4: Run tests — verify they all PASS**

```
python -m pytest tests/test_facebook_connector.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/connectors/facebook_connector.py tests/test_facebook_connector.py
git commit -m "feat(facebook): add fetch_mode=api — posts + comments via Meta Graph API"
```

---

## Task 2: facebook_graph_collector — engagement metrics

**Files:**
- Create: `core/social_metrics/facebook_graph_collector.py`
- Create: `tests/test_facebook_graph_collector.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_facebook_graph_collector.py
"""Tests pour facebook_graph_collector."""
from __future__ import annotations

import sqlite3
from unittest import mock

import pytest

from core.social_metrics import facebook_graph_collector


def _make_db() -> sqlite3.Connection:
    """Base de données en mémoire avec la table post_engagement_metrics."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE post_engagement_metrics (
            metric_id        TEXT PRIMARY KEY,
            post_id          TEXT NOT NULL,
            collected_at     TEXT NOT NULL,
            likes            INTEGER DEFAULT 0,
            comments         INTEGER DEFAULT 0,
            shares           INTEGER DEFAULT 0,
            views            INTEGER DEFAULT 0,
            reach            INTEGER DEFAULT 0,
            impressions      INTEGER DEFAULT 0,
            saves            INTEGER DEFAULT 0,
            collection_mode  TEXT DEFAULT 'api',
            raw_response     TEXT DEFAULT '{}'
        )
    """)
    conn.commit()
    return conn


class TestCollectPostMetrics:
    def test_returns_metrics_from_api(self):
        api_response = {
            "id": "fb_post_001",
            "reactions": {"summary": {"total_count": 42}},
            "comments": {"summary": {"total_count": 5}},
            "shares": {"count": 3},
        }
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.return_value = api_response
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_001", access_token="tok123"
            )
        assert metrics["likes"] == 42
        assert metrics["comments"] == 5
        assert metrics["shares"] == 3

    def test_returns_empty_dict_on_api_error(self):
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.side_effect = Exception("Network error")
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_001", access_token="tok123"
            )
        assert metrics == {}

    def test_missing_fields_return_zero(self):
        """Une réponse API sans shares/reactions ne lève pas d'erreur."""
        api_response = {"id": "fb_post_002"}
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.return_value = api_response
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_002", access_token="tok123"
            )
        assert isinstance(metrics, dict)


class TestSaveMetrics:
    def test_writes_to_post_engagement_metrics(self):
        conn = _make_db()
        metrics = {"likes": 10, "comments": 3, "shares": 1}
        with mock.patch(
            "core.social_metrics.facebook_graph_collector._get_conn",
            return_value=conn,
        ):
            metric_id = facebook_graph_collector.save_metrics("post_001", metrics)

        row = conn.execute(
            "SELECT * FROM post_engagement_metrics WHERE metric_id = ?", [metric_id]
        ).fetchone()
        assert row is not None
        assert row["likes"] == 10
        assert row["comments"] == 3
        assert row["shares"] == 1
        assert row["post_id"] == "post_001"
        assert row["collection_mode"] == "api"

    def test_returns_metric_id_with_correct_prefix(self):
        conn = _make_db()
        with mock.patch(
            "core.social_metrics.facebook_graph_collector._get_conn",
            return_value=conn,
        ):
            metric_id = facebook_graph_collector.save_metrics("post_001", {"likes": 5})
        assert metric_id.startswith("met-")
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```
python -m pytest tests/test_facebook_graph_collector.py -v
```

Expected: `ModuleNotFoundError` — `facebook_graph_collector` does not exist yet.

- [ ] **Step 3: Implement facebook_graph_collector.py**

Create `core/social_metrics/facebook_graph_collector.py`:

```python
"""Collecte de métriques d'engagement Facebook via Meta Graph API."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

import config
from core.connectors.meta_graph_client import meta_graph_get

logger = logging.getLogger(__name__)

_FIELDS = "id,reactions.summary(true),comments.summary(true),shares"


def _get_conn() -> sqlite3.Connection:
    """Retourne une connexion à la base de données."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def collect_post_metrics(
    post_id: str,
    *,
    access_token: str,
) -> dict[str, int]:
    """Collecte les métriques d'engagement d'un post Facebook connu."""
    try:
        data = meta_graph_get(post_id, access_token=access_token, fields=_FIELDS)
    except Exception:
        logger.exception("Erreur de collecte Graph API pour le post Facebook %s", post_id)
        return {}

    metrics: dict[str, int] = {}

    reactions_total = data.get("reactions", {}).get("summary", {}).get("total_count")
    if reactions_total is not None:
        try:
            metrics["likes"] = int(reactions_total)
        except (TypeError, ValueError):
            pass

    comments_total = data.get("comments", {}).get("summary", {}).get("total_count")
    if comments_total is not None:
        try:
            metrics["comments"] = int(comments_total)
        except (TypeError, ValueError):
            pass

    shares = data.get("shares", {}).get("count")
    if shares is not None:
        try:
            metrics["shares"] = int(shares)
        except (TypeError, ValueError):
            pass

    return metrics


def save_metrics(
    post_id: str,
    metrics: dict[str, int],
    *,
    collection_mode: str = "api",
    raw_response: dict | None = None,
) -> str:
    """Persiste un snapshot de métriques pour un post Facebook."""
    metric_id = f"met-{uuid.uuid4().hex[:12]}"

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO post_engagement_metrics (
                metric_id, post_id, collected_at,
                likes, comments, shares, views, reach, impressions, saves,
                collection_mode, raw_response
            ) VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric_id,
                post_id,
                metrics.get("likes", 0),
                metrics.get("comments", 0),
                metrics.get("shares", 0),
                metrics.get("views", 0),
                metrics.get("reach", 0),
                metrics.get("impressions", 0),
                metrics.get("saves", 0),
                collection_mode,
                json.dumps(raw_response or metrics, ensure_ascii=False),
            ),
        )
        conn.commit()

    return metric_id


def collect_and_save(
    post_id: str,
    *,
    access_token: str,
) -> dict[str, Any]:
    """Collecte les métriques d'un post Facebook puis les persiste."""
    metrics = collect_post_metrics(post_id, access_token=access_token)
    if not metrics:
        raise ValueError(f"Aucune métrique collectée pour le post Facebook {post_id}")

    metric_id = save_metrics(post_id, metrics, collection_mode="api")
    return {"metric_id": metric_id, **metrics}
```

- [ ] **Step 4: Run tests — verify they all PASS**

```
python -m pytest tests/test_facebook_graph_collector.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/social_metrics/facebook_graph_collector.py tests/test_facebook_graph_collector.py
git commit -m "feat(facebook): add facebook_graph_collector — engagement metrics via Meta Graph API"
```

---

## Task 3: Full regression

**Files:** none (read-only verification)

- [ ] **Step 1: Run the full test suite**

```
python -m pytest tests/ -q --tb=short
```

Expected: all 764+ existing tests PASS, plus the 13 new tests = 777+ total.

If any pre-existing test fails, do NOT proceed — investigate and fix before merging.

- [ ] **Step 2: Commit if anything needed fixing**

Only if Step 1 required a fix:

```bash
git add <fixed files>
git commit -m "fix: resolve regression from Facebook connector implementation"
```
