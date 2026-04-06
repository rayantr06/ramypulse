# Facebook Graph Ingestion — Design Spec

## Goal

Enable RamyPulse to collect Facebook Page content (posts + comments) via the official Meta Graph API through the existing ingestion pipeline, AND collect post engagement metrics via a dedicated collector for campaign tracking.

## Context

### What exists today

- **`FacebookConnector`** (`core/connectors/facebook_connector.py`) — inherits `SnapshotPlatformConnector`, reads local parquet files or optional scraper modules. Does not call any API.
- **`meta_graph_client.py`** (`core/connectors/`) — `meta_graph_get()` + `meta_graph_paginate()` using `urllib.request`. Already built for Instagram.
- **`instagram_graph_collector.py`** (`core/social_metrics/`) — collects engagement metrics for a known `ig_media_id`. Model to mirror for Facebook.
- **`token_refresh.py`** (`core/connectors/`) — refresh Meta tokens if < 5 days before expiry. Works for Facebook tokens too (same Meta OAuth).
- **`orchestrator.py`** — `credential_id` resolution already wired.
- **`credential_manager.py`** — CRUD for `platform_credentials`, already supports any platform.
- **`post_engagement_metrics`** table — already exists in `database.py`.

### The two subsystems

| Subsystem | Purpose | Pipeline |
|---|---|---|
| Ingestion | Text content for ABSA sentiment analysis | `raw_documents` → `normalized_records` → `enriched_signals` |
| Social metrics | Engagement metrics for campaign tracking | `campaign_posts` → `post_engagement_metrics` |

These two subsystems are independent and serve different use cases. This sprint implements both via separate components, following the same pattern already in place for Instagram.

### The gap

1. `FacebookConnector` has no `fetch_mode="api"` — no content discovery from Graph API.
2. No `facebook_graph_collector.py` — no engagement metrics collection for Facebook posts.

## Architecture

### Two components

**Component 1 — `FacebookConnector` with `fetch_mode="api"`**

Mirrors the Instagram connector pattern. Adds a new mode alongside the existing two:
- `"snapshot"` — reads parquet/CSV files (existing, unchanged)
- `"collector"` — calls scraper modules (existing, unchanged)
- `"api"` — **NEW**: calls Meta Graph API to discover and fetch page posts + comments

**Component 2 — `facebook_graph_collector.py`**

Mirrors `instagram_graph_collector.py`. Collects engagement metrics for a known `post_id` and writes to `post_engagement_metrics`.

## Data Flow

### Component 1 — Ingestion

```
source (fetch_mode="api", credential_id="cred-xxx")
  |
  v
orchestrator.run_source_sync()
  |
  +-- token_refresh.refresh_if_needed(credential_id)  [already built]
  |
  +-- credential resolution via credential_id  [already built]
  |
  +-- FacebookConnector.fetch_documents(source, credentials)
      |
      +-- GET /{page_id}/posts
      |       ?fields=id,message,story,created_time,permalink_url,
      |               reactions.summary(true),
      |               comments.limit(100){id,message,created_time,like_count}
      |   +-- paginate via cursor (max_pages configurable, default 10)
      |
      +-- For each post:   1 raw_document (document_type="post")
      +-- For each comment: 1 raw_document (document_type="comment")
      |
      v
  raw_documents (inserted by existing orchestrator logic)
      |
      v
  normalizer → enriched_signals (existing pipeline, zero changes)
```

### Component 2 — Social metrics

```
campaign_post (known facebook_post_id + page_access_token)
  |
  v
facebook_graph_collector.collect_post_metrics(post_id, access_token)
  |
  +-- GET /{post_id}?fields=id,reactions.summary(true),
  |                          comments.summary(true),shares
  |
  v
post_engagement_metrics (insert/update)
```

## Components

### 1. FacebookConnector rewrite — `core/connectors/facebook_connector.py`

Override `fetch_documents()`:

```python
class FacebookConnector(SnapshotPlatformConnector):
    def fetch_documents(self, source, *, credentials=None, file_path=None,
                        column_mapping=None, **kwargs):
        fetch_mode = parse_source_config(source).get("fetch_mode", "snapshot")

        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials or {})

        # Existing behavior: snapshot + scraper fallback
        return super().fetch_documents(
            source, credentials=credentials,
            file_path=file_path, column_mapping=column_mapping, **kwargs
        )
```

`_fetch_from_graph_api(source, credentials)`:
- Reads `credentials["access_token"]` (Page Access Token) and `page_id` from `parse_source_config(source)`
- Raises `ValueError` if either is missing
- Calls `meta_graph_paginate()` with fields:
  `id,message,story,created_time,permalink_url,reactions.summary(true),comments.limit(100){id,message,created_time,like_count}`
- For each post, produces one raw_document (post) + one raw_document per comment

**raw_document for a post:**
```python
{
    "external_document_id": post["id"],
    "raw_text": post.get("message") or post.get("story", ""),
    "raw_payload": post,
    "raw_metadata": {
        "document_type": "post",
        "permalink": post.get("permalink_url"),
        "timestamp": post.get("created_time"),
        "reactions_total": post.get("reactions", {}).get("summary", {}).get("total_count", 0),
        "comments_total": post.get("comments", {}).get("summary", {}).get("total_count", 0),
    },
    "source_url": post.get("permalink_url"),
    "collected_at": now_iso(),
}
```

**raw_document for a comment:**
```python
{
    "external_document_id": comment["id"],
    "raw_text": comment.get("message", ""),
    "raw_payload": comment,
    "raw_metadata": {
        "document_type": "comment",
        "parent_post_id": post["id"],
        "timestamp": comment.get("created_time"),
        "like_count": comment.get("like_count", 0),
    },
    "source_url": post.get("permalink_url"),
    "collected_at": now_iso(),
}
```

HTTP calls use `meta_graph_client.meta_graph_paginate()` (no new HTTP code).
Graph API version: `v21.0`.

### 2. Facebook Graph Collector — `core/social_metrics/facebook_graph_collector.py` (new file)

Two public functions (same pattern as `instagram_graph_collector.py`):

```python
def collect_post_metrics(
    post_id: str,
    *,
    access_token: str,
) -> dict[str, int]:
    """Collecte les métriques d'engagement d'un post Facebook connu."""

def save_metrics(
    post_id: str,
    metrics: dict[str, int],
    *,
    collection_mode: str = "api",
    raw_response: dict | None = None,
) -> str:
    """Persiste un snapshot de métriques pour un post Facebook."""
```

Logic for `collect_post_metrics`:
1. Call `meta_graph_get(post_id, fields="id,reactions.summary(true),comments.summary(true),shares")` — uses `meta_graph_client.py`, not own HTTP code
2. Extract `reactions_total`, `comments_count`, `shares_count`
3. Return normalized metrics dict

Logic for `save_metrics`:
1. Insert row into `post_engagement_metrics` (same schema as Instagram)
2. Return `metric_id`

Note: unlike `instagram_graph_collector.py` which has its own `_http_get()`, this module uses `meta_graph_get()` from `meta_graph_client.py` to avoid duplication.

### 3. Source configuration contract

**Step 1 — A credential:**
```json
{
    "entity_type": "brand",
    "entity_name": "Ramy Juice",
    "platform": "facebook",
    "account_id": "123456789",
    "access_token": "EAAG...",
    "app_id": "123456789",
    "app_secret": "abc123...",
    "extra_config": {
        "expires_at": "2026-06-04T00:00:00Z"
    }
}
```

**Step 2 — A source:**
```json
{
    "source_name": "Facebook Page Ramy Official",
    "platform": "facebook",
    "source_type": "api",
    "owner_type": "brand",
    "credential_id": "cred-xxx",
    "config_json": {
        "fetch_mode": "api",
        "page_id": "123456789"
    },
    "sync_frequency_minutes": 360,
    "source_priority": 1
}
```

## Files

### Allowed modifications

| File | Change |
|---|---|
| `core/connectors/facebook_connector.py` | Rewrite stub — add `_fetch_from_graph_api()`, override `fetch_documents()` |
| `core/social_metrics/facebook_graph_collector.py` | **Create** — mirrors `instagram_graph_collector.py` |

### New test files

| File | Coverage |
|---|---|
| `tests/test_facebook_connector.py` | Mock HTTP tests for Graph API fetch, pagination, posts+comments structure, error handling; verify snapshot/collector modes unchanged |
| `tests/test_facebook_graph_collector.py` | Mock HTTP tests for metrics collection, upsert behavior, error handling |

### Forbidden (do not modify)

| File | Reason |
|---|---|
| `core/connectors/meta_graph_client.py` | Already works, same HTTP layer for all Meta APIs |
| `core/connectors/token_refresh.py` | Already works for Facebook tokens (same Meta OAuth) |
| `core/ingestion/orchestrator.py` | credential_id resolution already wired |
| `core/social_metrics/credential_manager.py` | No changes needed |
| `core/database.py` | No new tables needed |
| `core/connectors/instagram_connector.py` | Out of scope |
| `core/ingestion/scheduler.py` | Works correctly, zero changes needed |
| `core/ingestion/content_identity.py` | Works correctly, zero changes needed |
| `core/connectors/platform_snapshot_connector.py` | Shared base, do not modify |
| `frontend/` | No UI this sprint |

## Invariants

1. `fetch_mode="snapshot"` continues to work exactly as before
2. `fetch_mode="collector"` continues to work exactly as before
3. `fetch_mode="api"` for Facebook is a new path, does not modify other platforms
4. `InstagramConnector` behavior is completely unchanged
5. `credential_ref` in `config_json` continues to function (legacy fallback)
6. `credential_id` wiring works identically to Instagram (already implemented in orchestrator)
7. `token_refresh` works for Facebook tokens without modification
8. No regression on the existing test suite (764 tests pass)

## Required tests before merge

### Group 1 — FacebookConnector
- `fetch_mode="snapshot"` unchanged behavior
- `fetch_mode="collector"` unchanged behavior
- `fetch_mode="api"` calls Graph API with correct fields, returns posts as raw_documents
- `fetch_mode="api"` returns comments as separate raw_documents with correct `document_type` and `parent_post_id`
- `fetch_mode="api"` handles pagination correctly
- `fetch_mode="api"` handles posts with no comments (returns only post raw_document)
- `fetch_mode="api"` raises `ValueError` on missing `access_token`
- `fetch_mode="api"` raises `ValueError` on missing `page_id`
- `fetch_mode="api"` handles API errors gracefully (rate limit, invalid token, network error)

### Group 2 — FacebookGraphCollector
- `collect_post_metrics` calls correct Graph API endpoint
- `collect_post_metrics` writes to `post_engagement_metrics`
- `collect_post_metrics` handles API errors gracefully

### Group 3 — Full regression
- `python -m pytest tests/ -q --tb=no` → all existing tests still pass

## Out of scope

- OAuth flow / "Connecter Facebook" button (future sprint)
- Facebook Stories / Reels (not available on Pages API)
- Nested comment replies (level 2 comments)
- Influencer tracking (future module)
- YouTube, Google Maps connectors
- Frontend changes
