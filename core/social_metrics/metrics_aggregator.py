"""Agrégateur de métriques d'engagement par campagne."""

from __future__ import annotations

import sqlite3

import config


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_campaign_engagement(campaign_id: str) -> dict:
    """Retourne les métriques d'engagement agrégées pour une campagne."""
    with _get_conn() as conn:
        campaign_row = conn.execute(
            "SELECT budget_dza, revenue_dza FROM campaigns WHERE campaign_id = ?",
            [campaign_id],
        ).fetchone()
        if not campaign_row:
            return {"campaign_id": campaign_id, "error": "Campaign not found"}

        budget_dza = campaign_row["budget_dza"]
        revenue_dza = campaign_row["revenue_dza"]

        posts = conn.execute(
            """
            SELECT p.post_id, p.platform, p.post_url, p.post_platform_id,
                   p.entity_type, p.entity_name
            FROM campaign_posts p
            WHERE p.campaign_id = ?
            ORDER BY p.added_at DESC
            """,
            [campaign_id],
        ).fetchall()

        post_ids = [post["post_id"] for post in posts]
        if not post_ids:
            return _empty_engagement(campaign_id, budget_dza, revenue_dza)

        placeholders = ",".join("?" * len(post_ids))
        metrics_rows = conn.execute(
            f"""
            SELECT m.*
            FROM post_engagement_metrics m
            INNER JOIN (
                SELECT post_id, MAX(collected_at) AS latest
                FROM post_engagement_metrics
                WHERE post_id IN ({placeholders})
                GROUP BY post_id
            ) latest_m ON m.post_id = latest_m.post_id AND m.collected_at = latest_m.latest
            """,
            post_ids,
        ).fetchall()

    metrics_by_post = {row["post_id"]: dict(row) for row in metrics_rows}
    totals = {
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "views": 0,
        "reach": 0,
        "impressions": 0,
        "saves": 0,
    }
    best_post = None
    best_engagement = -1
    posts_detail: list[dict] = []

    for post in posts:
        post_id = post["post_id"]
        metrics = metrics_by_post.get(post_id, {})
        for key in totals:
            totals[key] += metrics.get(key, 0)

        engagement = (
            metrics.get("likes", 0)
            + metrics.get("comments", 0)
            + metrics.get("shares", 0)
        )
        if engagement > best_engagement:
            best_engagement = engagement
            best_post = {
                "post_id": post_id,
                "platform": post["platform"],
                "post_url": post["post_url"],
                "entity_name": post["entity_name"],
                "engagement": engagement,
                "reach": metrics.get("reach", 0),
            }

        posts_detail.append(
            {
                "post_id": post_id,
                "platform": post["platform"],
                "post_url": post["post_url"],
                "entity_type": post["entity_type"],
                "entity_name": post["entity_name"],
                **{key: metrics.get(key, 0) for key in totals},
                "collected_at": metrics.get("collected_at"),
            }
        )

    total_interactions = totals["likes"] + totals["comments"] + totals["shares"]
    engagement_rate = None
    if totals["reach"] > 0:
        engagement_rate = round(total_interactions / totals["reach"] * 100, 2)

    roi_pct = None
    if budget_dza and budget_dza > 0 and revenue_dza and revenue_dza > 0:
        roi_pct = round((revenue_dza - budget_dza) / budget_dza * 100, 1)

    return {
        "campaign_id": campaign_id,
        "post_count": len(posts),
        "metrics_collected_count": len(metrics_by_post),
        "totals": totals,
        "engagement_rate": engagement_rate,
        "engagement_rate_note": (
            "Basé sur portée réelle collectée via API"
            if engagement_rate is not None
            else "Non disponible — portée non collectée"
        ),
        "roi_pct": roi_pct,
        "roi_note": (
            "Basé sur revenue_dza saisi manuellement"
            if roi_pct is not None
            else "Non calculable — revenue_dza non renseigné sur la campagne"
        ),
        "budget_dza": budget_dza,
        "revenue_dza": revenue_dza,
        "top_performer": best_post,
        "posts": posts_detail,
    }


def _empty_engagement(campaign_id: str, budget_dza, revenue_dza) -> dict:
    """Retourne une structure vide mais cohérente quand aucun post n'est lié."""
    roi_pct = None
    roi_note = "Aucun post lié à cette campagne"
    if budget_dza and budget_dza > 0 and revenue_dza and revenue_dza > 0:
        roi_pct = round((revenue_dza - budget_dza) / budget_dza * 100, 1)
        roi_note = "Basé sur revenue_dza saisi manuellement"

    return {
        "campaign_id": campaign_id,
        "post_count": 0,
        "metrics_collected_count": 0,
        "totals": {
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "views": 0,
            "reach": 0,
            "impressions": 0,
            "saves": 0,
        },
        "engagement_rate": None,
        "engagement_rate_note": "Aucun post lié à cette campagne",
        "roi_pct": roi_pct,
        "roi_note": roi_note,
        "budget_dza": budget_dza,
        "revenue_dza": revenue_dza,
        "top_performer": None,
        "posts": [],
    }
