"""Idempotent seed pipeline for the Ramy expo tenant."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import pandas as pd

import config
from api.data_loader import invalidate_cache, load_annotated_from_sqlite
from core.alerts.alert_detector import run_alert_detection
from core.analysis.aspect_extractor import extract_aspects
from core.campaigns.impact_calculator import compute_campaign_impact
from core.database import DatabaseManager
from core.ingestion.content_identity import resolve_or_create_content_item
from core.ingestion.health_checker import compute_source_health
from core.ingestion.normalizer import normalize
from core.recommendation.recommendation_manager import save_recommendation, update_client_agent_config
from core.security.auth import create_api_key, deactivate_api_key, list_api_keys
from core.tenancy.artifact_refresh import refresh_tenant_artifacts
from core.tenancy.client_manager import get_or_create_client, set_active_client
from core.tenancy.tenant_paths import get_tenant_paths

REQUIRED_COLUMNS = {
    "text",
    "sentiment",
    "confidence",
    "prob_positive",
    "prob_negative",
    "prob_neutral",
    "prob_mixed",
    "brand",
    "platform",
    "date",
    "likes",
    "author",
    "post_url",
    "is_reply",
}

WILAYAS = ["Alger", "Oran", "Constantine", "Annaba", "Setif", "Tlemcen"]
PRODUCTS = [
    ("Ramy Orange", "Orange"),
    ("Ramy Citron", "Citron"),
    ("Ramy Tropical", "Tropical"),
    ("Ramy Pomme", "Pomme"),
]
DATASET_RELATIVE_PATH = Path("data") / "scrapimauelle" / "dataset_ramy_sentiment.csv"
RAMY_FACEBOOK_PAGE_URL = "https://www.facebook.com/ramy.jus/"
RAMY_INSTAGRAM_PROFILE_URL = "https://www.instagram.com/ramy_officiel/"

_QUALITY_KEYWORDS = {
    "زيقو",
    "الصرف",
    "صرف",
    "مريض",
    "مرض",
    "pollution",
    "contamination",
    "sante",
    "santé",
    "mauvais",
    "frais",
    "périmé",
}
_PRICE_KEYWORDS = {"ghali", "rkhis", "prix", "cher", "سعر", "promo"}
_AVAILABILITY_KEYWORDS = {"disponible", "rupture", "متوفر", "stock", "ma kaynch", "kayen"}
_TASTE_KEYWORDS = {"bnin", "goût", "taste", "mlih", "ذوق", "طعم", "gout"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _db_path(db_path: str | Path | None = None) -> str:
    return str(db_path or config.SQLITE_DB_PATH)


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _stable_int(*parts: object) -> int:
    raw = "|".join(str(part or "") for part in parts)
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _stable_pick(options: list[str] | list[tuple[str, str]], *parts: object):
    if not options:
        raise ValueError("options must not be empty")
    return options[_stable_int(*parts) % len(options)]


def _sentiment_label(raw_label: object, confidence: object) -> str:
    normalized = str(raw_label or "").strip().lower()
    try:
        score = float(confidence or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    if normalized == "positive":
        return "très_positif" if score >= 0.92 else "positif"
    if normalized == "negative":
        return "très_négatif" if score >= 0.92 else "négatif"
    return "neutre"


def _clean_bool(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes"}


def _infer_aspects(text: str) -> list[str]:
    extracted: list[str] = []
    try:
        mentions = extract_aspects(text)
    except Exception:
        mentions = []
    for mention in mentions or []:
        if not isinstance(mention, dict):
            continue
        aspect = str(mention.get("aspect") or "").strip()
        if aspect and aspect not in extracted:
            extracted.append(aspect)
    if extracted:
        return extracted

    lowered = text.lower()
    if any(keyword in lowered for keyword in _PRICE_KEYWORDS):
        return ["prix"]
    if any(keyword in lowered for keyword in _AVAILABILITY_KEYWORDS):
        return ["disponibilité"]
    if any(keyword in lowered for keyword in _TASTE_KEYWORDS):
        return ["goût"]
    if any(keyword in lowered for keyword in _QUALITY_KEYWORDS):
        return ["fraîcheur"]
    return ["fraîcheur"]


def _derive_wilaya(post_url: str, author: str) -> str:
    return _stable_pick(WILAYAS, post_url, author)


def _derive_product(post_url: str) -> tuple[str, str]:
    return _stable_pick(PRODUCTS, post_url)


def _checksum(text: str, author: str, timestamp: str, post_url: str) -> str:
    raw = "|".join((text, author, timestamp, post_url))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _timestamp_iso(value: object) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    return timestamp.isoformat()


def resolve_ramy_seed_dataset_path(csv_path: str | Path | None = None) -> Path:
    """Resolve the manual Ramy dataset from the worktree or the parent repo root."""
    if csv_path is not None:
        candidate = Path(csv_path)
        if candidate.exists():
            return candidate

    base_dir = Path(getattr(config, "BASE_DIR", Path.cwd()))
    for candidate_root in (base_dir, *base_dir.parents):
        candidate = candidate_root / DATASET_RELATIVE_PATH
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Unable to locate {DATASET_RELATIVE_PATH}")


def issue_demo_api_key(
    *,
    client_id: str,
    label: str = "ramy_demo_frontend",
    rotate_existing: bool = True,
) -> dict[str, str]:
    """Create a fresh raw API key for the Ramy demo runtime."""
    if rotate_existing:
        for api_key in list_api_keys(client_id):
            if api_key.get("label") == label and api_key.get("is_active"):
                deactivate_api_key(str(api_key["key_id"]))

    key_id, raw_key = create_api_key(client_id=client_id, label=label)
    return {
        "key_id": key_id,
        "api_key": raw_key,
        "label": label,
    }


def write_frontend_env_file(
    *,
    api_key: str,
    client_id: str,
    env_path: str | Path,
) -> Path:
    """Persist the demo frontend auth context in a Vite env file."""
    target = Path(env_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    preserved_lines: list[str] = []
    if target.exists():
        for raw_line in target.read_text(encoding="utf-8").splitlines():
            if raw_line.startswith("VITE_RAMYPULSE_API_KEY="):
                continue
            if raw_line.startswith("VITE_SAFE_EXPO_CLIENT_ID="):
                continue
            preserved_lines.append(raw_line)

    preserved_lines.extend(
        [
            f"VITE_RAMYPULSE_API_KEY={api_key}",
            f"VITE_SAFE_EXPO_CLIENT_ID={client_id}",
        ]
    )
    target.write_text("\n".join(preserved_lines).strip() + "\n", encoding="utf-8")
    return target


def load_ramy_seed_dataset(csv_path: str | Path, brand_name: str = "Ramy") -> pd.DataFrame:
    """Load and normalize the Ramy seed dataset."""
    dataframe = pd.read_csv(csv_path)
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns in seed dataset: {missing}")

    filtered = dataframe[
        dataframe["brand"].fillna("").astype(str).str.strip().str.lower() == brand_name.strip().lower()
    ].copy()
    filtered["timestamp"] = pd.to_datetime(filtered["date"], errors="coerce", utc=True)
    filtered = filtered[filtered["timestamp"].notna()].copy()
    filtered["text"] = filtered["text"].fillna("").astype(str).str.strip()
    filtered = filtered[filtered["text"] != ""].copy()
    filtered["post_url"] = filtered["post_url"].fillna("").astype(str).str.strip()
    filtered["author"] = filtered["author"].fillna("").astype(str).str.strip()
    filtered["likes"] = pd.to_numeric(filtered["likes"], errors="coerce").fillna(0).astype(int)
    filtered["confidence"] = pd.to_numeric(filtered["confidence"], errors="coerce").fillna(0.0).astype(float)
    filtered["is_reply"] = filtered["is_reply"].apply(_clean_bool)
    filtered.sort_values(["timestamp", "post_url", "author"], inplace=True)
    filtered.reset_index(drop=True, inplace=True)
    return filtered


def _source_definitions(client_id: str, csv_path: str | Path) -> list[dict[str, object]]:
    return [
        {
            "source_id": f"src-{client_id}-facebook-corpus",
            "source_name": "Ramy Facebook Corpus",
            "platform": "facebook",
            "source_type": "facebook_feed",
            "owner_type": "market",
            "auth_mode": "none",
            "config_json": {
                "fetch_mode": "seed_dataset",
                "dataset_path": str(csv_path),
                "page_url": RAMY_FACEBOOK_PAGE_URL,
            },
            "source_purpose": "bulk_import",
            "source_priority": 1,
            "coverage_key": f"{client_id}:facebook:corpus",
        },
        {
            "source_id": f"src-{client_id}-facebook-live",
            "source_name": "Ramy Facebook Live Watch",
            "platform": "facebook",
            "source_type": "facebook_feed",
            "owner_type": "owned",
            "auth_mode": "apify",
            "config_json": {
                "fetch_mode": "collector",
                "page_url": RAMY_FACEBOOK_PAGE_URL,
                "max_posts": 2,
                "max_comments_per_post": 20,
            },
            "source_purpose": "market_monitoring",
            "source_priority": 2,
            "coverage_key": f"{client_id}:facebook:live",
        },
        {
            "source_id": f"src-{client_id}-instagram-live",
            "source_name": "Ramy Instagram Live Watch",
            "platform": "instagram",
            "source_type": "instagram_profile",
            "owner_type": "owned",
            "auth_mode": "apify",
            "config_json": {
                "fetch_mode": "collector",
                "profile_url": RAMY_INSTAGRAM_PROFILE_URL,
                "max_posts": 2,
                "max_comments_per_post": 20,
            },
            "source_purpose": "market_monitoring",
            "source_priority": 2,
            "coverage_key": f"{client_id}:instagram:live",
        },
    ]


def _registry_definitions(client_id: str) -> list[dict[str, object]]:
    return [
        {
            "source_id": f"registry-{client_id}-facebook",
            "platform": "facebook",
            "source_type": "facebook_page",
            "display_name": "Ramy Facebook",
            "external_id": client_id,
            "url": RAMY_FACEBOOK_PAGE_URL,
            "owner_type": "owned",
            "auth_mode": "apify",
            "brand": "Ramy",
            "is_active": 1,
            "sync_frequency": "hourly",
            "last_sync_at": _now(),
            "updated_at": _now(),
        },
        {
            "source_id": f"registry-{client_id}-instagram",
            "platform": "instagram",
            "source_type": "instagram_profile",
            "display_name": "Ramy Instagram",
            "external_id": client_id,
            "url": RAMY_INSTAGRAM_PROFILE_URL,
            "owner_type": "owned",
            "auth_mode": "apify",
            "brand": "Ramy",
            "is_active": 1,
            "sync_frequency": "hourly",
            "last_sync_at": _now(),
            "updated_at": _now(),
        },
    ]


def _watchlist_definitions(client_id: str) -> list[dict[str, object]]:
    return [
        {
            "watchlist_id": f"watch-{client_id}-global",
            "client_id": client_id,
            "watchlist_name": "Ramy Pulse Global",
            "description": "Barometre global Ramy sur le corpus expo et les futures collectes live.",
            "scope_type": "watch_seed",
            "filters": {
                "channel": "facebook",
                "period_days": 30,
                "min_volume": 20,
                "keywords": ["ramy", "jus ramy"],
                "channels": ["facebook", "instagram", "web_search", "youtube", "google_maps"],
                "seed_urls": [RAMY_FACEBOOK_PAGE_URL, RAMY_INSTAGRAM_PROFILE_URL],
            },
        },
        {
            "watchlist_id": f"watch-{client_id}-quality",
            "client_id": client_id,
            "watchlist_name": "Ramy Qualite & Securite",
            "description": "Focus sur les signaux qualite, fraicheur et securite sanitaire.",
            "scope_type": "analysis",
            "filters": {
                "channel": "facebook",
                "aspect": "fraîcheur",
                "period_days": 30,
                "min_volume": 10,
            },
        },
        {
            "watchlist_id": f"watch-{client_id}-price",
            "client_id": client_id,
            "watchlist_name": "Ramy Prix & Accessibilite",
            "description": "Suivi des tensions prix et disponibilite.",
            "scope_type": "analysis",
            "filters": {
                "channel": "facebook",
                "aspect": "prix",
                "period_days": 30,
                "min_volume": 3,
            },
        },
    ]


def _campaign_definitions(client_id: str) -> list[dict[str, object]]:
    return [
        {
            "campaign_id": f"camp-{client_id}-response",
            "client_id": client_id,
            "campaign_name": "Ramy Reponse Qualite Mars 2026",
            "campaign_type": "crisis_response",
            "platform": "facebook",
            "description": "Campagne de re-assurance suite a la crise reputaionnelle.",
            "influencer_handle": "@ramy_officiel",
            "target_segment": "grand_public",
            "target_aspects": json.dumps(["fraîcheur"]),
            "target_regions": json.dumps(["Alger", "Oran"]),
            "keywords": json.dumps(["ramy", "qualité", "santé"]),
            "budget_dza": 250000,
            "revenue_dza": 420000,
            "start_date": "2026-03-10",
            "end_date": "2026-03-25",
            "pre_window_days": 10,
            "post_window_days": 10,
            "status": "completed",
            "created_at": _now(),
            "updated_at": _now(),
        },
        {
            "campaign_id": f"camp-{client_id}-recovery",
            "client_id": client_id,
            "campaign_name": "Ramy Recovery Social Avril 2026",
            "campaign_type": "brand_recovery",
            "platform": "facebook",
            "description": "Reprise de la conversation et contenus positifs post-crise.",
            "influencer_handle": "@ramy_community",
            "target_segment": "familles",
            "target_aspects": json.dumps(["fraîcheur", "prix"]),
            "target_regions": json.dumps(["Constantine", "Annaba", "Setif"]),
            "keywords": json.dumps(["ramy", "jus", "orange"]),
            "budget_dza": 180000,
            "revenue_dza": 315000,
            "start_date": "2026-03-26",
            "end_date": "2026-04-06",
            "pre_window_days": 7,
            "post_window_days": 7,
            "status": "active",
            "created_at": _now(),
            "updated_at": _now(),
        },
    ]


def _clear_client_data(connection: sqlite3.Connection, client_id: str) -> None:
    source_ids = [row["source_id"] for row in connection.execute("SELECT source_id FROM sources WHERE client_id = ?", (client_id,))]
    watchlist_ids = [row["watchlist_id"] for row in connection.execute("SELECT watchlist_id FROM watchlists WHERE client_id = ?", (client_id,))]
    campaign_ids = [row["campaign_id"] for row in connection.execute("SELECT campaign_id FROM campaigns WHERE client_id = ?", (client_id,))]
    if campaign_ids:
        placeholders = ",".join("?" for _ in campaign_ids)
        post_ids = [
            row["post_id"]
            for row in connection.execute(
                f"SELECT post_id FROM campaign_posts WHERE campaign_id IN ({placeholders})",
                tuple(campaign_ids),
            )
        ]
        connection.execute(f"DELETE FROM campaign_posts WHERE campaign_id IN ({placeholders})", tuple(campaign_ids))
        connection.execute(f"DELETE FROM campaign_metrics_snapshots WHERE campaign_id IN ({placeholders})", tuple(campaign_ids))
        connection.execute(f"DELETE FROM campaign_signal_links WHERE campaign_id IN ({placeholders})", tuple(campaign_ids))
        if post_ids:
            post_placeholders = ",".join("?" for _ in post_ids)
            connection.execute(
                f"DELETE FROM post_engagement_metrics WHERE post_id IN ({post_placeholders})",
                tuple(post_ids),
            )
    if watchlist_ids:
        placeholders = ",".join("?" for _ in watchlist_ids)
        connection.execute(f"DELETE FROM watchlist_metric_snapshots WHERE watchlist_id IN ({placeholders})", tuple(watchlist_ids))
    if source_ids:
        placeholders = ",".join("?" for _ in source_ids)
        connection.execute(f"DELETE FROM source_sync_runs WHERE source_id IN ({placeholders})", tuple(source_ids))
        connection.execute(f"DELETE FROM source_health_snapshots WHERE source_id IN ({placeholders})", tuple(source_ids))

    connection.execute("DELETE FROM source_registry WHERE source_id LIKE ?", (f"registry-{client_id}-%",))
    connection.execute("DELETE FROM alerts WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM recommendations WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM watch_run_steps WHERE run_id IN (SELECT run_id FROM watch_runs WHERE client_id = ?)", (client_id,))
    connection.execute("DELETE FROM watch_runs WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM watchlists WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM sources WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM campaigns WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM content_items WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM raw_documents WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM normalized_records WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM enriched_signals WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM api_keys WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM client_agent_config WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM alert_rules WHERE client_id = ?", (client_id,))
    connection.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))


def _clear_tenant_directory(client_id: str) -> None:
    tenant_root = get_tenant_paths(client_id).tenant_root
    if tenant_root.exists():
        shutil.rmtree(tenant_root)


def _upsert_sources(connection: sqlite3.Connection, client_id: str, csv_path: str | Path) -> list[dict[str, object]]:
    created: list[dict[str, object]] = []
    now = _now()
    for source in _source_definitions(client_id, csv_path):
        connection.execute(
            """
            INSERT OR REPLACE INTO sources (
                source_id, client_id, source_name, platform, source_type, owner_type,
                auth_mode, config_json, is_active, sync_frequency_minutes,
                freshness_sla_hours, source_purpose, source_priority, coverage_key,
                credential_id, last_sync_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["source_id"],
                client_id,
                source["source_name"],
                source["platform"],
                source["source_type"],
                source["owner_type"],
                source["auth_mode"],
                json.dumps(source["config_json"], ensure_ascii=False),
                1,
                60,
                24,
                source["source_purpose"],
                source["source_priority"],
                source["coverage_key"],
                None,
                now,
                now,
                now,
            ),
        )
        created.append(source)

    for source in _registry_definitions(client_id):
        columns = list(source.keys()) + ["created_at"]
        values = [source[key] for key in source.keys()] + [now]
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(
            f"INSERT OR REPLACE INTO source_registry ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )

    return created


def _upsert_watchlists(connection: sqlite3.Connection, client_id: str) -> list[dict[str, object]]:
    rows = []
    now = _now()
    for watchlist in _watchlist_definitions(client_id):
        connection.execute(
            """
            INSERT OR REPLACE INTO watchlists (
                watchlist_id, client_id, watchlist_name, description,
                scope_type, filters, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                watchlist["watchlist_id"],
                watchlist["client_id"],
                watchlist["watchlist_name"],
                watchlist["description"],
                watchlist["scope_type"],
                json.dumps(watchlist["filters"], ensure_ascii=False),
                1,
                now,
                now,
            ),
        )
        rows.append(watchlist)
    return rows


def _upsert_campaigns(connection: sqlite3.Connection, client_id: str) -> list[dict[str, object]]:
    rows = []
    for campaign in _campaign_definitions(client_id):
        connection.execute(
            """
            INSERT OR REPLACE INTO campaigns (
                campaign_id, client_id, campaign_name, campaign_type, platform,
                description, influencer_handle, influencer_tier, target_segment,
                target_aspects, target_regions, keywords, budget_dza, revenue_dza,
                start_date, end_date, pre_window_days, post_window_days,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign["campaign_id"],
                campaign["client_id"],
                campaign["campaign_name"],
                campaign["campaign_type"],
                campaign["platform"],
                campaign["description"],
                campaign["influencer_handle"],
                None,
                campaign["target_segment"],
                campaign["target_aspects"],
                campaign["target_regions"],
                campaign["keywords"],
                campaign["budget_dza"],
                campaign["revenue_dza"],
                campaign["start_date"],
                campaign["end_date"],
                campaign["pre_window_days"],
                campaign["post_window_days"],
                campaign["status"],
                campaign["created_at"],
                campaign["updated_at"],
            ),
        )
        rows.append(campaign)
    return rows


def _seed_documents(
    connection: sqlite3.Connection,
    *,
    dataframe: pd.DataFrame,
    client_id: str,
    source_id: str,
    coverage_key: str,
) -> int:
    inserted = 0
    for row in dataframe.to_dict(orient="records"):
        raw_text = str(row["text"]).strip()
        timestamp = _timestamp_iso(row["timestamp"])
        author = str(row.get("author") or "").strip()
        post_url = str(row.get("post_url") or "").strip()
        checksum = _checksum(raw_text, author, timestamp, post_url)
        raw_document_id = f"raw-{uuid.uuid4()}"
        external_document_id = f"comment-{checksum[:16]}"
        normalized_record_id = f"norm-{uuid.uuid4()}"
        signal_id = f"sig-{uuid.uuid4()}"
        normalized = normalize(raw_text)
        sentiment_label = _sentiment_label(row.get("sentiment"), row.get("confidence"))
        aspects = _infer_aspects(raw_text)
        primary_aspect = aspects[0] if aspects else ""
        wilaya = _derive_wilaya(post_url, author)
        product, product_line = _derive_product(post_url)
        content_item_id, canonical_key, canonical_url = resolve_or_create_content_item(
            connection,
            client_id=client_id,
            platform="facebook",
            external_content_id=external_document_id,
            canonical_url=post_url,
            owner_type="market",
            coverage_key=coverage_key,
            checksum_sha256=checksum,
            fallback_id=raw_document_id,
        )
        raw_metadata = {
            "channel": "facebook",
            "post_url": post_url,
            "source_url": post_url,
            "author": author,
            "date": str(row.get("date") or ""),
            "likes": int(row.get("likes") or 0),
            "is_reply": bool(row.get("is_reply")),
        }
        aspect_sentiments = [
            {
                "aspect": aspect,
                "label": sentiment_label,
                "confidence": float(row.get("confidence") or 0.0),
            }
            for aspect in aspects
        ]

        connection.execute(
            """
            INSERT INTO raw_documents (
                raw_document_id, client_id, source_id, sync_run_id, external_document_id,
                raw_payload, raw_text, raw_metadata, checksum_sha256, content_item_id,
                platform, canonical_url, canonical_key, collected_at, is_normalized,
                normalizer_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_document_id,
                client_id,
                source_id,
                f"source-sync-{client_id}-facebook-corpus",
                external_document_id,
                json.dumps({"dataset_row": row}, ensure_ascii=False, default=str),
                raw_text,
                json.dumps(raw_metadata, ensure_ascii=False),
                checksum,
                content_item_id,
                "facebook",
                canonical_url,
                canonical_key,
                timestamp,
                1,
                "expo-seed-v1",
                _now(),
            ),
        )
        connection.execute(
            """
            INSERT INTO normalized_records (
                normalized_record_id, client_id, source_id, raw_document_id, text,
                text_original, channel, source_url, published_at, language,
                script_detected, normalized_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_record_id,
                client_id,
                source_id,
                raw_document_id,
                normalized.get("normalized") or raw_text,
                raw_text,
                "facebook",
                post_url,
                timestamp,
                normalized.get("language"),
                normalized.get("script_detected"),
                json.dumps(normalized, ensure_ascii=False),
                _now(),
            ),
        )
        connection.execute(
            """
            INSERT INTO enriched_signals (
                signal_id, client_id, normalized_record_id, source_id, sentiment_label,
                confidence, aspect, aspects, aspect_sentiments, brand, competitor,
                product, product_line, sku, wilaya, source_url, channel,
                event_timestamp, normalizer_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                client_id,
                normalized_record_id,
                source_id,
                sentiment_label,
                float(row.get("confidence") or 0.0),
                primary_aspect,
                json.dumps(aspects, ensure_ascii=False),
                json.dumps(aspect_sentiments, ensure_ascii=False),
                "Ramy",
                None,
                product,
                product_line,
                None,
                wilaya,
                post_url,
                "facebook",
                timestamp,
                "expo-seed-v1",
                _now(),
            ),
        )
        inserted += 1
    return inserted


def _seed_source_runs(connection: sqlite3.Connection, *, sources: list[dict[str, object]], imported_count: int) -> None:
    now = _now()
    for source in sources:
        if str(source["source_id"]).endswith("facebook-corpus"):
            fetched = imported_count
            inserted = imported_count
        else:
            fetched = 2
            inserted = 0
        connection.execute(
            """
            INSERT OR REPLACE INTO source_sync_runs (
                sync_run_id, source_id, run_mode, status, records_fetched,
                records_inserted, records_failed, error_message, started_at,
                ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"source-sync-{source['source_id']}",
                source["source_id"],
                "manual",
                "success",
                fetched,
                inserted,
                0,
                None,
                now,
                now,
                now,
            ),
        )


def _seed_watch_run(connection: sqlite3.Connection, *, client_id: str, watchlist_id: str, imported_count: int) -> None:
    now = _now()
    run_id = f"watch-run-{client_id}"
    connection.execute(
        """
        INSERT OR REPLACE INTO watch_runs (
            run_id, client_id, watchlist_id, requested_channels, stage, status,
            records_collected, error_message, created_at, updated_at, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            client_id,
            watchlist_id,
            json.dumps(["facebook", "instagram", "web_search"], ensure_ascii=False),
            "indexing",
            "ready",
            imported_count,
            None,
            now,
            now,
            now,
            now,
        ),
    )
    for step_key, stage, records_seen in (
        ("collect:facebook", "collecting", imported_count),
        ("normalize", "normalizing", imported_count),
        ("index", "indexing", imported_count),
    ):
        connection.execute(
            """
            INSERT OR REPLACE INTO watch_run_steps (
                step_id, run_id, step_key, stage, collector_key, status, records_seen,
                error_message, created_at, updated_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{run_id}:{step_key}",
                run_id,
                step_key,
                stage,
                "facebook" if step_key.startswith("collect:") else None,
                "success",
                records_seen,
                None,
                now,
                now,
                now,
                now,
            ),
        )


def _seed_campaign_posts(
    connection: sqlite3.Connection,
    *,
    campaigns: list[dict[str, object]],
    dataframe: pd.DataFrame,
) -> None:
    top_posts = (
        dataframe.groupby("post_url", as_index=False)
        .agg(comment_count=("text", "size"), likes_sum=("likes", "sum"))
        .sort_values(["comment_count", "likes_sum"], ascending=[False, False])
        .head(max(2, len(campaigns)))
    )

    for index, campaign in enumerate(campaigns):
        if index >= len(top_posts):
            break
        row = top_posts.iloc[index]
        post_url = str(row["post_url"])
        post_id = f"post-{campaign['campaign_id']}"
        post_platform_id = post_url.rstrip("/").split("/")[-1] or f"ramy-{index + 1}"
        comments = int(row["comment_count"])
        likes = int(row["likes_sum"])
        shares = max(3, comments // 5)
        views = max(250, comments * 18)
        reach = max(400, comments * 24)
        impressions = max(reach, reach + comments * 6)
        saves = max(1, comments // 8)

        connection.execute(
            """
            INSERT OR REPLACE INTO campaign_posts (
                post_id, campaign_id, platform, post_platform_id, post_url,
                entity_type, entity_name, credential_id, added_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                campaign["campaign_id"],
                "facebook",
                post_platform_id,
                post_url,
                "brand",
                "Ramy",
                None,
                _now(),
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO post_engagement_metrics (
                metric_id, post_id, collected_at, likes, comments, shares,
                views, reach, impressions, saves, collection_mode, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"metric-{post_id}",
                post_id,
                _now(),
                likes,
                comments,
                shares,
                views,
                reach,
                impressions,
                saves,
                "seed",
                json.dumps(
                    {"post_url": post_url, "comment_count": comments, "likes_sum": likes},
                    ensure_ascii=False,
                ),
            ),
        )


def _top_negative_aspects(dataframe: pd.DataFrame) -> list[str]:
    aspect_scores = (
        dataframe.groupby("aspect")["sentiment_label"]
        .apply(
            lambda series: (
                series.isin(["positif", "très_positif"]).sum()
                - series.isin(["négatif", "très_négatif"]).sum()
            )
        )
        .sort_values()
    )
    return [str(index) for index in aspect_scores.index.tolist()[:3] if str(index).strip()]


def _seed_recommendations(
    client_id: str,
    dataframe: pd.DataFrame,
    alerts_created: list[str],
    db_path: str | Path | None = None,
) -> int:
    positives = int(dataframe["sentiment_label"].isin(["positif", "très_positif"]).sum()) if not dataframe.empty else 0
    negatives = int(dataframe["sentiment_label"].isin(["négatif", "très_négatif"]).sum()) if not dataframe.empty else 0
    nss = round(((positives - negatives) / len(dataframe)) * 100.0, 2) if len(dataframe) else 0.0
    top_aspects = _top_negative_aspects(dataframe)
    result_payloads = [
        {
            "analysis_summary": (
                f"Corpus Ramy seedé avec {len(dataframe)} signaux Facebook réels. "
                f"NSS global actuel {nss:.1f}. Aspects les plus exposés: {', '.join(top_aspects or ['fraîcheur'])}."
            ),
            "recommendations": [
                {
                    "title": "Activer une cellule de reponse qualite",
                    "priority": "high",
                    "description": "Répondre rapidement aux commentaires négatifs les plus visibles avec un message qualité unifié et un lien source.",
                    "target_platform": "facebook",
                    "kpi_impact": "Réduire la part des signaux négatifs sur 7 jours",
                    "timing": "Immédiat",
                }
            ],
            "watchlist_priorities": ["Ramy Pulse Global", "Ramy Qualite & Securite"],
            "confidence_score": 0.86,
            "data_quality_note": "Basé sur le corpus seedé expo + contexte live activable via watchlists.",
            "provider_used": "expo_seed",
            "model_used": "ramy-demo-v1",
            "generation_ms": 0,
            "context_tokens": 0,
        },
        {
            "analysis_summary": "Le volet prix et accessibilité doit être suivi séparément pour éviter que la crise qualité masque les irritants d’achat.",
            "recommendations": [
                {
                    "title": "Monitorer prix et disponibilité par wilaya",
                    "priority": "medium",
                    "description": "Créer une routine de suivi dédiée pour Alger, Oran et Constantine avec relance terrain sur les signaux prix.",
                    "target_platform": "watchlists",
                    "kpi_impact": "Améliorer le NSS prix/disponibilité",
                    "timing": "Sous 72h",
                }
            ],
            "watchlist_priorities": ["Ramy Prix & Accessibilite"],
            "confidence_score": 0.79,
            "data_quality_note": "Les signaux prix restent plus clairsemés que les signaux qualité.",
            "provider_used": "expo_seed",
            "model_used": "ramy-demo-v1",
            "generation_ms": 0,
            "context_tokens": 0,
        },
    ]
    created = 0
    for index, payload in enumerate(result_payloads):
        save_recommendation(
            result=payload,
            trigger_type="alert_triggered" if alerts_created else "manual",
            trigger_id=alerts_created[index] if index < len(alerts_created) else None,
            client_id=client_id,
            db_path=_db_path(db_path),
        )
        created += 1
    return created


def seed_ramy_demo(
    *,
    csv_path: str | Path,
    client_id: str | None = None,
    client_name: str = "Ramy Demo",
    reset: bool = False,
    db_path: str | Path | None = None,
    refresh_artifacts_fn: Callable[..., dict[str, object]] | None = None,
) -> dict[str, object]:
    """Seed the Ramy demo tenant from the manual annotated dataset."""
    resolved_client_id = str(client_id or config.SAFE_EXPO_CLIENT_ID).strip()
    resolved_csv_path = resolve_ramy_seed_dataset_path(csv_path)
    dataframe = load_ramy_seed_dataset(resolved_csv_path)
    database = DatabaseManager(_db_path(db_path))
    database.create_tables()
    database.close()

    if reset:
        with _connect(db_path) as connection:
            _clear_client_data(connection, resolved_client_id)
            connection.commit()
        _clear_tenant_directory(resolved_client_id)

    get_or_create_client(client_id=resolved_client_id, client_name=client_name, industry="agroalimentaire")
    set_active_client(resolved_client_id)
    update_client_agent_config(
        {
            "provider": config.DEFAULT_AGENT_PROVIDER,
            "model": config.DEFAULT_AGENT_MODEL,
            "auto_trigger_on_alert": False,
        },
        client_id=resolved_client_id,
        db_path=_db_path(db_path),
    )

    with _connect(db_path) as connection:
        sources = _upsert_sources(connection, resolved_client_id, resolved_csv_path)
        watchlists = _upsert_watchlists(connection, resolved_client_id)
        campaigns = _upsert_campaigns(connection, resolved_client_id)
        imported_count = _seed_documents(
            connection,
            dataframe=dataframe,
            client_id=resolved_client_id,
            source_id=f"src-{resolved_client_id}-facebook-corpus",
            coverage_key=f"{resolved_client_id}:facebook:corpus",
        )
        _seed_source_runs(connection, sources=sources, imported_count=imported_count)
        _seed_watch_run(connection, client_id=resolved_client_id, watchlist_id=watchlists[0]["watchlist_id"], imported_count=imported_count)
        _seed_campaign_posts(connection, campaigns=campaigns, dataframe=dataframe)
        connection.commit()

    for source in _source_definitions(resolved_client_id, csv_path):
        compute_source_health(source["source_id"], db_path=_db_path(db_path), client_id=resolved_client_id)

    invalidate_cache(resolved_client_id)
    annotated = load_annotated_from_sqlite(resolved_client_id)
    alerts_created = run_alert_detection(annotated, client_id=resolved_client_id)
    for campaign in _campaign_definitions(resolved_client_id):
        compute_campaign_impact(campaign["campaign_id"], annotated)
    recommendations_created = _seed_recommendations(
        resolved_client_id,
        annotated,
        alerts_created,
        db_path=db_path,
    )
    refresh = (refresh_artifacts_fn or refresh_tenant_artifacts)(client_id=resolved_client_id, force=True)

    with _connect(db_path) as connection:
        sources_count = connection.execute("SELECT COUNT(*) FROM sources WHERE client_id = ?", (resolved_client_id,)).fetchone()[0]
        watchlists_count = connection.execute("SELECT COUNT(*) FROM watchlists WHERE client_id = ?", (resolved_client_id,)).fetchone()[0]
        campaigns_count = connection.execute("SELECT COUNT(*) FROM campaigns WHERE client_id = ?", (resolved_client_id,)).fetchone()[0]

    return {
        "client_id": resolved_client_id,
        "documents_seeded": imported_count,
        "sources_count": int(sources_count),
        "watchlists_count": int(watchlists_count),
        "campaigns_count": int(campaigns_count),
        "alerts_created": len(alerts_created),
        "recommendations_created": recommendations_created,
        "artifacts": refresh,
    }
