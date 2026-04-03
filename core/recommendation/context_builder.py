"""Assembleur de contexte pour l'agent de recommandations.

Construit un payload contextualise a partir du DataFrame annote, des alertes,
des watchlists, des campagnes et du RAG local. Le focus produit de l'etape A
est de rendre le contexte plus declencheur-driven sans casser le contrat
public de Wave 5.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import pandas as pd

import config
from config import ASPECT_LIST, FAISS_INDEX_PATH

logger = logging.getLogger(__name__)

try:
    from core.campaigns.campaign_manager import list_campaigns as _list_campaigns

    _HAS_CAMPAIGNS = True
except ImportError:
    _HAS_CAMPAIGNS = False
    logger.debug("core.campaigns indisponible")

try:
    from core.alerts.alert_manager import list_alerts as _list_alerts

    _HAS_ALERTS = True
except ImportError:
    _HAS_ALERTS = False
    logger.debug("core.alerts indisponible")

try:
    from core.watchlists.watchlist_manager import list_watchlists as _list_watchlists

    _HAS_WATCHLISTS = True
except ImportError:
    _HAS_WATCHLISTS = False
    logger.debug("core.watchlists indisponible")


_POSITIVE_LABELS = {"très_positif", "positif"}
_NEGATIVE_LABELS = {"négatif", "très_négatif"}


def _compute_nss(df: pd.DataFrame) -> float | None:
    """Calcule le NSS sur un DataFrame de signaux."""
    if df.empty or "sentiment_label" not in df.columns:
        return None
    total = len(df)
    positives = int(df["sentiment_label"].isin(_POSITIVE_LABELS).sum())
    negatives = int(df["sentiment_label"].isin(_NEGATIVE_LABELS).sum())
    return round((positives - negatives) / total * 100.0, 2)


def _compute_nss_by_aspect(df: pd.DataFrame) -> dict:
    """Calcule le NSS par aspect."""
    if "aspect" not in df.columns:
        return {aspect: None for aspect in ASPECT_LIST}
    result: dict[str, float | None] = {}
    for aspect in ASPECT_LIST:
        result[aspect] = _compute_nss(df[df["aspect"] == aspect])
    return result


def _compute_nss_by_channel(df: pd.DataFrame) -> dict:
    """Calcule le NSS par canal."""
    if "channel" not in df.columns:
        return {}
    result: dict[str, float | None] = {}
    for channel in df["channel"].dropna().astype(str).unique():
        result[str(channel)] = _compute_nss(df[df["channel"] == channel])
    return result


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite courte duree pour les enrichissements contexte."""
    connection = sqlite3.connect(str(config.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _latest_watchlist_metrics_map() -> dict[str, dict]:
    """Retourne le dernier snapshot connu par watchlist."""
    try:
        with _get_connection() as connection:
            rows = connection.execute(
                """
                SELECT w1.*
                FROM watchlist_metric_snapshots w1
                JOIN (
                    SELECT watchlist_id, MAX(computed_at) AS max_computed_at
                    FROM watchlist_metric_snapshots
                    GROUP BY watchlist_id
                ) latest
                  ON latest.watchlist_id = w1.watchlist_id
                 AND latest.max_computed_at = w1.computed_at
                """
            ).fetchall()
    except sqlite3.Error:
        return {}

    payload: dict[str, dict] = {}
    for row in rows:
        item = dict(row)
        try:
            item["aspect_breakdown"] = json.loads(item.get("aspect_breakdown") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            item["aspect_breakdown"] = {}
        payload[str(item["watchlist_id"])] = item
    return payload


def _latest_campaign_snapshot_map() -> dict[str, dict]:
    """Retourne le dernier snapshot campagne utile pour l'uplift recent."""
    try:
        with _get_connection() as connection:
            rows = connection.execute(
                """
                SELECT c1.*
                FROM campaign_metrics_snapshots c1
                JOIN (
                    SELECT campaign_id, MAX(computed_at) AS max_computed_at
                    FROM campaign_metrics_snapshots
                    GROUP BY campaign_id
                ) latest
                  ON latest.campaign_id = c1.campaign_id
                 AND latest.max_computed_at = c1.computed_at
                ORDER BY c1.computed_at DESC
                """
            ).fetchall()
    except sqlite3.Error:
        return {}

    payload: dict[str, dict] = {}
    for row in rows:
        item = dict(row)
        try:
            item["aspect_breakdown"] = json.loads(item.get("aspect_breakdown") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            item["aspect_breakdown"] = {}
        payload[str(item["campaign_id"])] = item
    return payload


def _top_negative_aspects(df: pd.DataFrame, n: int = 3) -> list[str]:
    """Retourne les n aspects avec le NSS le plus faible."""
    scored = [
        (aspect, nss)
        for aspect, nss in _compute_nss_by_aspect(df).items()
        if nss is not None
    ]
    scored.sort(key=lambda item: item[1])
    return [aspect for aspect, _ in scored[:n]]


def _load_retriever() -> Any | None:
    """Charge le retriever hybride si l'index local est disponible."""
    try:
        from core.rag.embedder import Embedder
        from core.rag.retriever import Retriever
        from core.rag.vector_store import VectorStore

        vector_store = VectorStore()
        vector_store.load(str(FAISS_INDEX_PATH))
        if not vector_store.metadata:
            return None
        return Retriever(vector_store, Embedder())
    except Exception as exc:  # pragma: no cover - degrade gracieusement
        logger.debug("RAG indisponible: %s", exc)
        return None


def _estimate_tokens(context: dict) -> int:
    """Estime le nombre de tokens du contexte JSON."""
    try:
        serialized = json.dumps(context, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return 0
    return max(1, len(serialized) // 4)


def _build_rag_query(trigger_type: str, trigger_id: str | None, metrics: dict) -> str:
    """Construit la requete RAG a partir du declencheur et des metriques."""
    top_negative = metrics.get("top_negative_aspects", [])
    base = "recommandations marketing Ramy"
    if top_negative:
        base += " " + " ".join(top_negative[:2]) + " problemes clients"
    if trigger_type == "alert_triggered" and trigger_id:
        base += " alerte critique"
    return base


def _enrich_active_alerts(alerts: list[dict], trigger_id: str | None) -> list[dict]:
    """Trie les alertes actives en mettant l'alerte declencheuse en tete si connue."""
    if not trigger_id:
        return alerts
    triggering = [alert for alert in alerts if alert.get("alert_id") == trigger_id]
    others = [alert for alert in alerts if alert.get("alert_id") != trigger_id]
    return triggering + others


def _enrich_watchlists(watchlists: list[dict]) -> list[dict]:
    """Ajoute les dernieres metriques persistées aux watchlists actives."""
    latest_metrics = _latest_watchlist_metrics_map()
    enriched: list[dict] = []
    for watchlist in watchlists:
        item = dict(watchlist)
        item["latest_metrics"] = latest_metrics.get(str(watchlist.get("watchlist_id")), {})
        enriched.append(item)
    return enriched


def _build_trigger_focus(
    trigger_type: str,
    trigger_id: str | None,
    active_alerts: list[dict],
) -> dict:
    """Derive un focus metier a partir du declencheur courant."""
    focus = {
        "trigger_type": trigger_type,
        "trigger_id": trigger_id,
        "watchlist_id": None,
        "campaign_ids": [],
    }
    if trigger_type != "alert_triggered" or not trigger_id:
        return focus

    alert = next((item for item in active_alerts if item.get("alert_id") == trigger_id), None)
    if not alert:
        return focus

    focus["watchlist_id"] = alert.get("watchlist_id")
    payload = alert.get("alert_payload") or {}
    for campaign in payload.get("active_campaigns", []):
        campaign_id = str(campaign.get("campaign_id") or "").strip()
        if campaign_id:
            focus["campaign_ids"].append(campaign_id)
    return focus


def _prioritize_watchlists(watchlists: list[dict], trigger_focus: dict) -> list[dict]:
    """Priorise la watchlist liee au declencheur puis les plus en derive."""
    target_watchlist_id = trigger_focus.get("watchlist_id")

    def _sort_key(item: dict) -> tuple:
        latest_metrics = item.get("latest_metrics") or {}
        delta_nss = latest_metrics.get("delta_nss")
        try:
            delta_value = float(delta_nss)
        except (TypeError, ValueError):
            delta_value = 0.0
        return (
            0 if item.get("watchlist_id") == target_watchlist_id else 1,
            delta_value,
            str(item.get("watchlist_name") or ""),
        )

    return sorted(watchlists, key=_sort_key)


def _enrich_campaigns(campaigns: list[dict]) -> list[dict]:
    """Ajoute l'uplift recent et le dernier snapshot aux campagnes recentes."""
    latest_snapshots = _latest_campaign_snapshot_map()
    enriched: list[dict] = []
    for campaign in campaigns:
        item = dict(campaign)
        latest_snapshot = latest_snapshots.get(str(campaign.get("campaign_id")), {})
        item["latest_snapshot"] = latest_snapshot
        item["latest_uplift_nss"] = latest_snapshot.get("nss_uplift")
        item["latest_volume_lift_pct"] = latest_snapshot.get("volume_lift_pct")
        enriched.append(item)
    return enriched


def _prioritize_campaigns(campaigns: list[dict], trigger_focus: dict) -> list[dict]:
    """Priorise les campagnes explicitement liees au declencheur."""
    target_campaign_ids = {str(item) for item in trigger_focus.get("campaign_ids", []) if item}

    def _sort_key(item: dict) -> tuple:
        uplift = item.get("latest_uplift_nss")
        try:
            uplift_value = float(uplift)
        except (TypeError, ValueError):
            uplift_value = 0.0
        return (
            0 if str(item.get("campaign_id")) in target_campaign_ids else 1,
            uplift_value,
            str(item.get("campaign_name") or ""),
        )

    return sorted(campaigns, key=_sort_key)


def _build_data_quality(df_annotated: pd.DataFrame, rag_chunks: list[dict]) -> dict:
    """Assemble un resume simple de la qualite des donnees disponibles."""
    volume_total = int(len(df_annotated))
    channel_count = int(df_annotated["channel"].nunique()) if "channel" in df_annotated.columns else 0
    sparse_dataset = volume_total < 50
    mono_channel_dataset = channel_count <= 1
    return {
        "volume_total": volume_total,
        "channel_count": channel_count,
        "rag_chunk_count": len(rag_chunks),
        "sparse_dataset": sparse_dataset,
        "mono_channel_dataset": mono_channel_dataset,
    }


def build_recommendation_context(
    trigger_type: str,
    trigger_id: str | None,
    df_annotated: pd.DataFrame,
    max_rag_chunks: int = 8,
) -> dict:
    """Assemble le contexte complet pour l'agent de recommandations."""
    context: dict[str, Any] = {}

    context["client_profile"] = {
        "client_name": "Ramy",
        "industry": "Agroalimentaire algerien",
        "main_products": ["Ramy Citron", "Ramy Orange", "Ramy Fraise", "Ramy Multivitamines"],
        "active_regions": ["alger", "oran", "constantine", "annaba", "tlemcen", "setif"],
    }
    context["trigger"] = {"type": trigger_type, "id": trigger_id}

    nss_global = _compute_nss(df_annotated)
    nss_by_aspect = _compute_nss_by_aspect(df_annotated)
    nss_by_channel = _compute_nss_by_channel(df_annotated)
    top_negative = _top_negative_aspects(df_annotated) if not df_annotated.empty else []
    context["current_metrics"] = {
        "nss_global": nss_global,
        "nss_by_aspect": nss_by_aspect,
        "nss_by_channel": nss_by_channel,
        "volume_total": len(df_annotated),
        "top_negative_aspects": top_negative,
    }

    active_alerts: list[dict] = []
    if _HAS_ALERTS:
        try:
            all_alerts = _list_alerts(limit=100)
            active = [
                item
                for item in all_alerts
                if item.get("status") in ("new", "acknowledged", "investigating")
            ]
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            active.sort(key=lambda item: severity_order.get(item.get("severity", "low"), 4))
            active_alerts = _enrich_active_alerts(active, trigger_id)[:5]
        except Exception as exc:  # pragma: no cover - degrade gracieusement
            logger.warning("Erreur chargement alertes: %s", exc)
    context["active_alerts"] = active_alerts

    trigger_focus = _build_trigger_focus(trigger_type, trigger_id, active_alerts)
    context["trigger_focus"] = trigger_focus

    active_watchlists: list[dict] = []
    if _HAS_WATCHLISTS:
        try:
            watchlists = _enrich_watchlists(_list_watchlists(is_active=True))
            active_watchlists = _prioritize_watchlists(watchlists, trigger_focus)[:5]
        except Exception as exc:  # pragma: no cover - degrade gracieusement
            logger.warning("Erreur chargement watchlists: %s", exc)
    context["active_watchlists"] = active_watchlists

    recent_campaigns: list[dict] = []
    if _HAS_CAMPAIGNS:
        try:
            campaigns = _enrich_campaigns(_list_campaigns(limit=20))
            recent_campaigns = _prioritize_campaigns(campaigns, trigger_focus)[:5]
        except Exception as exc:  # pragma: no cover - degrade gracieusement
            logger.warning("Erreur chargement campagnes: %s", exc)
    context["recent_campaigns"] = recent_campaigns

    rag_chunks: list[dict] = []
    retriever = _load_retriever()
    if retriever is not None:
        try:
            query = _build_rag_query(trigger_type, trigger_id, context["current_metrics"])
            raw_chunks = retriever.search(query, top_k=max_rag_chunks)
            rag_chunks = [
                {
                    "text": chunk["text"],
                    "channel": chunk["channel"],
                    "timestamp": chunk["timestamp"],
                }
                for chunk in raw_chunks
            ]
        except Exception as exc:  # pragma: no cover - degrade gracieusement
            logger.warning("Erreur recuperation RAG: %s", exc)
    context["rag_chunks"] = rag_chunks

    context["data_quality"] = _build_data_quality(df_annotated, rag_chunks)
    context["estimated_tokens"] = _estimate_tokens(context)

    logger.info(
        "Contexte assemble - trigger=%s alertes=%d watchlists=%d campagnes=%d chunks=%d tokens~%d",
        trigger_type,
        len(active_alerts),
        len(active_watchlists),
        len(recent_campaigns),
        len(rag_chunks),
        context["estimated_tokens"],
    )
    return context
