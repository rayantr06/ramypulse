"""Agrégateur de métriques d'engagement et de sentiment par campagne."""

from __future__ import annotations

import sqlite3

import config


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _empty_signal_summary() -> dict:
    return {
        "signal_count": 0,
        "sentiment_breakdown": {},
        "negative_aspects": [],
    }


def _merge_signal_summaries(base: dict, extra: dict) -> dict:
    merged = {
        "signal_count": int(base.get("signal_count", 0)) + int(extra.get("signal_count", 0)),
        "sentiment_breakdown": dict(base.get("sentiment_breakdown", {})),
        "negative_aspects": list(base.get("negative_aspects", [])),
    }
    for label, count in extra.get("sentiment_breakdown", {}).items():
        merged["sentiment_breakdown"][label] = merged["sentiment_breakdown"].get(label, 0) + count
    for aspect in extra.get("negative_aspects", []):
        if aspect not in merged["negative_aspects"]:
            merged["negative_aspects"].append(aspect)
    return merged


def _is_negative_sentiment(label: str | None) -> bool:
    normalized = str(label or "").strip().lower()
    return normalized in {"negatif", "négatif", "tres_negatif", "très_négatif", "très_negatif", "tres_négatif"}


def _load_post_signal_summary(connection: sqlite3.Connection, post: sqlite3.Row) -> dict:
    rows = connection.execute(
        """
        SELECT DISTINCT es.signal_id, es.sentiment_label, es.aspect
        FROM content_items ci
        INNER JOIN raw_documents rd ON rd.content_item_id = ci.content_item_id
        INNER JOIN normalized_records nr ON nr.raw_document_id = rd.raw_document_id
        INNER JOIN enriched_signals es ON es.normalized_record_id = nr.normalized_record_id
        WHERE ci.platform = ?
          AND (
                ci.external_content_id = ?
                OR (? IS NOT NULL AND ? != '' AND ci.canonical_url = ?)
          )
        """,
        (
            post["platform"],
            post["post_platform_id"],
            post["post_url"],
            post["post_url"],
            post["post_url"],
        ),
    ).fetchall()

    if not rows:
        return _empty_signal_summary()

    sentiment_breakdown: dict[str, int] = {}
    negative_aspects: list[str] = []
    seen_signal_ids: set[str] = set()
    for row in rows:
        signal_id = str(row["signal_id"])
        if signal_id in seen_signal_ids:
            continue
        seen_signal_ids.add(signal_id)

        label = str(row["sentiment_label"] or "")
        sentiment_breakdown[label] = sentiment_breakdown.get(label, 0) + 1
        aspect = str(row["aspect"] or "").strip()
        if aspect and _is_negative_sentiment(label) and aspect not in negative_aspects:
            negative_aspects.append(aspect)

    return {
        "signal_count": len(seen_signal_ids),
        "sentiment_breakdown": sentiment_breakdown,
        "negative_aspects": negative_aspects,
    }


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
        aggregated_signals = _empty_signal_summary()
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
            signal_summary = _load_post_signal_summary(conn, post)
            aggregated_signals = _merge_signal_summaries(aggregated_signals, signal_summary)

            post_payload = {
                "post_id": post_id,
                "platform": post["platform"],
                "post_url": post["post_url"],
                "entity_type": post["entity_type"],
                "entity_name": post["entity_name"],
                **{key: metrics.get(key, 0) for key in totals},
                "collected_at": metrics.get("collected_at"),
                **signal_summary,
            }
            posts_detail.append(post_payload)

            if engagement > best_engagement:
                best_engagement = engagement
                best_post = {
                    "post_id": post_id,
                    "platform": post["platform"],
                    "post_url": post["post_url"],
                    "entity_name": post["entity_name"],
                    "engagement": engagement,
                    "reach": metrics.get("reach", 0),
                    **signal_summary,
                }

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
        **aggregated_signals,
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
        **_empty_signal_summary(),
    }
