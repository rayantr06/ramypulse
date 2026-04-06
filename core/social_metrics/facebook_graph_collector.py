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
    """Retourne une connexion à la base de données principale."""
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
        raise ValueError(
            f"Aucune métrique collectée pour le post Facebook {post_id} "
            "(vérifier les logs pour l'erreur API sous-jacente)"
        )

    metric_id = save_metrics(post_id, metrics, collection_mode="api")
    return {"metric_id": metric_id, **metrics}
