"""Collecte de métriques d'engagement via l'Instagram Graph API."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

import config

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
_FIELD_MAP = {
    "like_count": "likes",
    "likes": "likes",
    "comments_count": "comments",
    "shares": "shares",
    "video_views": "views",
    "plays": "views",
    "reach": "reach",
    "impressions": "impressions",
    "saved": "saves",
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _http_get(url: str, params: dict[str, str]) -> dict[str, Any]:
    """Exécute une requête GET simple vers Meta Graph."""
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "RamyPulse/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_post_metrics(
    post_id: str,
    *,
    access_token: str,
    ig_media_id: str,
) -> dict[str, int]:
    """Collecte les métriques d'un post Instagram et les normalise."""
    del post_id
    fields = "like_count,comments_count,shares,video_views,reach,impressions,saved,media_type"
    try:
        data = _http_get(
            f"{_GRAPH_API_BASE}/{ig_media_id}",
            {"fields": fields, "access_token": access_token},
        )
    except Exception:
        logger.exception("Erreur de collecte Graph API pour %s", ig_media_id)
        return {}

    metrics: dict[str, int] = {}
    for api_field, db_field in _FIELD_MAP.items():
        value = data.get(api_field)
        if value is None:
            continue
        try:
            metrics[db_field] = int(value)
        except (TypeError, ValueError):
            continue

    if data.get("media_type") in {"VIDEO", "REEL"} and "views" not in metrics:
        try:
            insights = _http_get(
                f"{_GRAPH_API_BASE}/{ig_media_id}/insights",
                {"metric": "plays,reach,impressions", "access_token": access_token},
            )
            for item in insights.get("data", []):
                name = item.get("name")
                value = item.get("values", [{}])[0].get("value", 0)
                if name == "plays":
                    metrics["views"] = int(value)
                elif name == "reach":
                    metrics["reach"] = int(value)
                elif name == "impressions":
                    metrics["impressions"] = int(value)
        except Exception:
            logger.exception("Erreur insights Graph API pour %s", ig_media_id)

    return metrics


def save_metrics(
    post_id: str,
    metrics: dict[str, int],
    *,
    collection_mode: str = "api",
    raw_response: dict | None = None,
) -> str:
    """Persiste un snapshot de métriques pour un post."""
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
    ig_media_id: str,
) -> dict[str, Any]:
    """Collecte les métriques d'un post puis les persiste."""
    metrics = collect_post_metrics(
        post_id,
        access_token=access_token,
        ig_media_id=ig_media_id,
    )
    if not metrics:
        raise ValueError(f"Aucune métrique collectée pour le post {ig_media_id}")

    metric_id = save_metrics(post_id, metrics, collection_mode="api")
    return {"metric_id": metric_id, **metrics}
