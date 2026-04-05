# Instagram Graph Ingestion MVP — Design Spec

## Goal

Enable RamyPulse to collect Instagram content via the official Meta Graph API through the existing ingestion pipeline, so that clients can configure an Instagram API source and have posts automatically discovered, ingested, normalized, and analyzed without manual file imports.

## Context

### What exists today

- **`InstagramConnector`** (`core/connectors/instagram_connector.py`) — inherits `SnapshotPlatformConnector`, reads local parquet files or optional scraper modules. Does not call any API.
- **`instagram_graph_collector.py`** (`core/social_metrics/`) — calls `graph.facebook.com/v18.0` to collect engagement metrics for a **single known `ig_media_id`**. Does not discover content.
- **`credential_manager.py`** (`core/social_metrics/`) — CRUD for `platform_credentials` table, stores tokens via `secret_manager` (`local:` / `env:` references).
- **`orchestrator.py`** (`core/ingestion/`) — runs `connector.fetch_documents()` → inserts `raw_documents` → triggers normalization. Resolves credentials via `config_json.credential_ref`, **ignores `sources.credential_id`**.
- **`scheduler.py`** — `run_due_syncs()` iterates sources by `coverage_key` + `source_priority`, tries each source in order, stops at first success (fallback chain).
- **`content_identity.py`** — deduplicates content across sources via `resolve_or_create_content_item()`.
- **`automation_runtime.py`** — one-shot cycle: sync → normalization → health → alerts.

### The gap

1. **No content discovery** — nobody lists Instagram media from an account. The graph collector only works on a pre-known `ig_media_id`.
2. **`credential_id` not wired** — `sources.credential_id` column exists, `platform_credentials` table exists, but the orchestrator never reads `credential_id` to resolve tokens.
3. **No token lifecycle** — Meta long-lived tokens expire after 60 days. No refresh mechanism.

## Architecture

### Approach: extend `InstagramConnector` with `fetch_mode="api"`

The connector already inherits from `SnapshotPlatformConnector` which routes by `fetch_mode`. We add a third mode alongside the existing two:

- `"snapshot"` — reads parquet/CSV files (existing, unchanged)
- `"collector"` — calls scraper modules (existing, unchanged)  
- `"api"` — **NEW**: calls Meta Graph API to discover and fetch media

This preserves the multi-source architecture: a client can have an API source (priority 1), a scraper source (priority 2), and an import source (priority 3) for the same `coverage_key`. The scheduler handles fallback automatically.

## Data Flow

```
source (fetch_mode="api", credential_id="cred-xxx")
  |
  v
orchestrator.run_source_sync()
  |
  +-- reads sources.credential_id
  |   +-- credential_manager.get_credential(credential_id)
  |       +-- secret_manager.resolve_secret(access_token_ref)
  |           +-- raw access_token
  |
  +-- token_refresh.refresh_if_needed(credential_id)
  |   (refreshes token if < 5 days before expiry)
  |
  +-- InstagramConnector.fetch_documents(source, credentials={token, account_id})
  |   +-- GET /{account_id}/media?fields=id,caption,timestamp,...
  |   +-- paginate via cursor
  |   +-- return list[dict] (one dict = one raw_document)
  |
  v
raw_documents (inserted by existing orchestrator logic)
  |
  v
normalizer -> enriched_signals (existing pipeline, zero changes)
```

## Components

### 1. InstagramConnector rewrite — `core/connectors/instagram_connector.py`

Override `fetch_documents()`:

```python
class InstagramConnector(SnapshotPlatformConnector):
    def fetch_documents(self, source, *, credentials=None, **kwargs):
        fetch_mode = parse_source_config(source).get("fetch_mode", "snapshot")
        
        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials)
        
        # Existing behavior: snapshot + scraper fallback
        return super().fetch_documents(source, credentials=credentials, **kwargs)
```

`_fetch_from_graph_api(source, credentials)`:
- Reads `credentials["access_token"]` and `credentials["account_id"]` (the IG Business User ID)
- Calls `GET /{account_id}/media?fields=id,caption,timestamp,media_type,media_url,permalink,like_count,comments_count&limit=50`
- Follows pagination cursor (`paging.cursors.after`) until exhausted or configurable max pages
- For each media item, produces a raw_document dict:

```python
{
    "external_document_id": media["id"],          # Meta media ID
    "raw_text": media.get("caption", ""),
    "raw_payload": media,                          # Full API response
    "raw_metadata": {
        "media_type": media["media_type"],
        "permalink": media["permalink"],
        "timestamp": media["timestamp"],
    },
    "source_url": media.get("permalink"),
    "collected_at": now_iso(),
}
```

HTTP calls use `urllib.request` (same as existing `instagram_graph_collector.py`). No new dependency.

Graph API version: `v21.0` (current stable as of 2026).

### 2. Credential resolution in orchestrator — `core/ingestion/orchestrator.py`

In `run_source_sync()`, before calling `connector.fetch_documents()`, add credential_id resolution:

```python
# New: resolve via credential_id (source of truth)
resolved_from_credential_id = {}
credential_id = source.get("credential_id")
if credential_id:
    from core.social_metrics.credential_manager import get_credential
    cred = get_credential(credential_id)
    if cred:
        resolved_from_credential_id = {
            "access_token": cred.get("access_token"),
            "account_id": cred.get("account_id"),
            "app_id": cred.get("app_id"),
            "app_secret": cred.get("app_secret"),
        }

# Merge: credential_id > credential_ref > runtime
credentials_payload = {
    **resolve_credentials(source_config),      # old path (credential_ref)
    **resolved_from_credential_id,             # new path (credential_id)
    **(credentials or {}),                     # explicit runtime override
}
```

Priority order:
1. Runtime `credentials` kwarg (highest — useful for manual/test runs)
2. `credential_id` → `platform_credentials` (new canonical path)
3. `credential_ref` in `config_json` (legacy fallback, still works)

### 3. Token refresh — `core/connectors/token_refresh.py` (new file)

Single public function:

```python
def refresh_if_needed(credential_id: str) -> bool:
    """Refresh Meta token if expiring within 5 days. Returns True if refreshed."""
```

Logic:
1. Load credential via `credential_manager.get_credential(credential_id)`
2. Read `extra_config.expires_at` — if missing or > 5 days away, return False
3. Call Meta token exchange: `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={current_token}`
4. On success: update `platform_credentials` with new token + new `expires_at` (now + 60 days)
5. On failure: log warning, return False (the sync will fail naturally and health→alert pipeline handles it)

Called by orchestrator at the start of `run_source_sync()` when `source.credential_id` is set and `source.platform == "instagram"`.

No separate cron. Refresh happens during the normal sync cycle, which already runs periodically via `run_due_syncs()`.

### 4. Source configuration contract

To use Instagram Graph API ingestion, a client creates:

**Step 1 — A credential:**
```
POST /api/social-metrics/credentials
{
    "entity_type": "brand",
    "entity_name": "Ramy Juice",
    "platform": "instagram",
    "account_id": "17841400123456789",    # IG Business User ID
    "access_token": "EAAG...",             # Long-lived token
    "app_id": "123456789",
    "app_secret": "abc123...",
    "extra_config": {
        "expires_at": "2026-06-04T00:00:00Z"
    }
}
```

**Step 2 — A source:**
```
POST /api/admin/sources
{
    "source_name": "Instagram Ramy Official",
    "platform": "instagram",
    "source_type": "api",
    "owner_type": "brand",
    "credential_id": "cred-xxx",
    "config_json": {
        "fetch_mode": "api",
        "profile_id": "17841400123456789"
    },
    "sync_frequency_minutes": 360,
    "source_priority": 1
}
```

From there, `run_due_syncs()` picks it up automatically. The scheduler, normalizer, health checker, alert detector, and notification pipeline all work without any changes.

## Files

### Allowed modifications

| File | Change |
|---|---|
| `core/connectors/instagram_connector.py` | Add `_fetch_from_graph_api()`, override `fetch_documents()` to route `fetch_mode="api"` |
| `core/connectors/token_refresh.py` | **Create** — Meta token refresh logic |
| `core/ingestion/orchestrator.py` | Add `credential_id` resolution in `run_source_sync()` (~15 lines) |

### New test files

| File | Coverage |
|---|---|
| `tests/test_instagram_connector.py` | Mock HTTP tests for Graph API fetch, pagination, error handling; verify snapshot/collector modes unchanged |
| `tests/test_token_refresh.py` | Mock HTTP tests for token exchange, expiry logic, failure handling |
| `tests/test_orchestrator_credentials.py` | Test credential_id resolution, fallback chain, NULL credential_id |

### Forbidden (do not modify)

| File | Reason |
|---|---|
| `core/ingestion/scheduler.py` | Works correctly, zero changes needed |
| `core/ingestion/content_identity.py` | Works correctly, zero changes needed |
| `core/connectors/platform_snapshot_connector.py` | Shared base for all connectors |
| `core/connectors/facebook_connector.py` | Out of scope |
| `core/connectors/youtube_connector.py` | Out of scope |
| `core/connectors/google_maps_connector.py` | Out of scope |
| `core/connectors/source_config.py` | Works correctly, credential_ref stays as-is |
| `core/social_metrics/*` | No parallel ingestion path |
| `frontend/` | No UI this sprint |
| `core/alerts/*` | Works correctly via existing pipeline |
| `core/notifications/*` | Works correctly via existing pipeline |

## Invariants

These MUST hold true after implementation. Every invariant has a corresponding test.

1. `fetch_mode="snapshot"` continues to work exactly as before
2. `fetch_mode="collector"` continues to work exactly as before
3. `fetch_mode="api"` for Instagram is a new path, does not modify other platforms
4. `coverage_key` / `source_priority` / scheduler remain unchanged
5. `content_items` continues to deduplicate API + scraper + import for the same logical post
6. `credential_ref` in `config_json` continues to function
7. `credential_id` becomes supported without becoming mandatory anywhere
8. No regression on the existing test suite (739 tests pass)

## Required tests before merge

### Group 1 — InstagramConnector
- `fetch_mode="snapshot"` unchanged behavior
- `fetch_mode="collector"` unchanged behavior
- `fetch_mode="api"` calls Graph API, returns correct raw_document structure
- `fetch_mode="api"` handles pagination correctly
- `fetch_mode="api"` handles API errors gracefully (rate limit, invalid token, network error)

### Group 2 — Orchestrator credentials
- `credential_id` present → resolves via `credential_manager`
- `credential_id` NULL → falls back to `credential_ref` / no credentials
- Does not affect other platforms (facebook, youtube, google_maps sync still works)

### Group 3 — Content deduplication
- Same Instagram post ingested via API then via import → single `content_item`

### Group 4 — Token refresh
- Token with > 5 days remaining → no refresh
- Token with < 5 days remaining → refresh called
- Token refresh failure → logged, sync proceeds (will fail naturally)
- Missing `expires_at` in extra_config → no refresh attempted

### Group 5 — Full regression
- `python -m pytest tests/ -q --tb=no` → all existing tests still pass

## Out of scope

- OAuth flow / "Connect Instagram" button (Sprint 2)
- Instagram Stories / Reels insights endpoints (future enhancement)
- Other platform connectors (Facebook, YouTube, Google Maps)
- Frontend changes
- Scheduling changes
- Secret manager encryption hardening
