"""Routeur FastAPI pour le dashboard RamyPulse.

Agrege des donnees cross-tables (watchlist_metric_snapshots, alerts,
recommendations) et enrichit le resume avec les signaux disponibles
dans `annotated.parquet` quand ils existent.
"""

import json
import logging
import sqlite3
from collections import Counter

from fastapi import APIRouter, Depends

import config
from api.data_loader import load_annotated
from api.deps.tenant import resolve_client_id
from api.schemas import (
    ActionRecommendation,
    AlertSummary,
    DashboardActions,
    DashboardAlerts,
    DashboardSummary,
    ProductPerformanceItem,
    RegionalDistributionItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _get_db_connection() -> sqlite3.Connection:
    """Connexion SQLite en lecture pour les agrégations dashboard."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _coerce_percent(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round((part / total) * 100))


def _compute_regional_distribution(df) -> list[RegionalDistributionItem]:
    if df.empty or "wilaya" not in df.columns:
        return []

    values = [str(value).strip() for value in df["wilaya"].dropna().tolist() if str(value).strip()]
    if not values:
        return []

    counts = Counter(values)
    total = sum(counts.values())
    top_items = counts.most_common(4)
    regional_distribution = [
        RegionalDistributionItem(wilaya=wilaya, pct=_coerce_percent(count, total))
        for wilaya, count in top_items
    ]

    other_count = total - sum(count for _, count in top_items)
    if other_count > 0:
        regional_distribution.append(
            RegionalDistributionItem(wilaya="Autres", pct=_coerce_percent(other_count, total))
        )
    return regional_distribution


def _resolve_product_column(df) -> str | None:
    for candidate in ("product", "product_line", "brand", "sku"):
        if candidate in df.columns and df[candidate].dropna().astype(str).str.strip().any():
            return candidate
    return None


def _sentiment_score(values) -> float:
    if len(values) == 0:
        return 0.0

    positive = {"tres_positif", "très_positif", "positif"}
    negative = {"tres_negatif", "très_négatif", "tres_négatif", "très_negatif", "negatif", "négatif"}

    pos = 0
    neg = 0
    for value in values:
        normalized = str(value).strip().lower()
        if normalized in positive:
            pos += 1
        elif normalized in negative:
            neg += 1
    return round(((pos - neg) / len(values)) * 100, 1)


def _compute_product_performance(df) -> list[ProductPerformanceItem]:
    product_column = _resolve_product_column(df)
    if df.empty or product_column is None:
        return []

    grouped = []
    max_volume = 0
    for product, subset in df.groupby(product_column):
        product_name = str(product).strip()
        if not product_name:
            continue
        volume = int(len(subset))
        max_volume = max(max_volume, volume)
        grouped.append(
            {
                "product": product_name,
                "volume": volume,
                "trend_pct": _sentiment_score(subset.get("sentiment_label", [])),
            }
        )

    grouped.sort(key=lambda item: item["volume"], reverse=True)
    return [
        ProductPerformanceItem(
            product=item["product"],
            trend_pct=item["trend_pct"],
            relative_volume=_coerce_percent(item["volume"], max_volume),
        )
        for item in grouped[:3]
    ]


def _compute_period_label(df) -> str:
    if df.empty or "timestamp" not in df.columns:
        return "sur la periode chargee"

    timestamps = df["timestamp"].dropna()
    if timestamps.empty:
        return "sur la periode chargee"

    try:
        parsed = timestamps.astype("datetime64[ns]")
    except Exception:
        return "sur la periode chargee"

    if parsed.empty:
        return "sur la periode chargee"

    start = parsed.min()
    end = parsed.max()
    if start.date() == end.date():
        return f"le {start.strftime('%Y-%m-%d')}"
    return f"du {start.strftime('%Y-%m-%d')} au {end.strftime('%Y-%m-%d')}"


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(client_id: str = Depends(resolve_client_id)):
    """Retourne le score santé de la marque et les tendances générales.

    Si la base est vierge, renvoie un fallback métier élégant.
    """
    health_score = 0
    delta = 0.0
    text = "Pas de données suffisantes pour établir un diagnostic."

    total_mentions = 0
    period = "sur la periode chargee"
    regional_distribution: list[RegionalDistributionItem] = []
    product_performance: list[ProductPerformanceItem] = []

    try:
        with _get_db_connection() as conn:
            row = conn.execute(
                "SELECT wms.nss_current, wms.delta_nss "
                "FROM watchlist_metric_snapshots wms "
                "INNER JOIN watchlists w ON w.watchlist_id = wms.watchlist_id "
                "WHERE w.client_id = ? "
                "ORDER BY wms.computed_at DESC LIMIT 1",
                (client_id,),
            ).fetchone()

            if row and row["nss_current"] is not None:
                raw_nss = float(row["nss_current"])
                health_score = int((raw_nss + 100) / 2.0)
                delta = float(row["delta_nss"]) if row["delta_nss"] else 0.0

                if health_score > 70:
                    text = (
                        f"Votre marque est en bonne santé. Le NSS a évolué de "
                        f"{delta:+.1f} pts, tiré par des signaux récents positifs."
                    )
                elif health_score > 40:
                    text = (
                        f"Votre marque est sous surveillance. Le NSS stagne "
                        f"avec un delta de {delta:+.1f} pts."
                    )
                else:
                    text = (
                        f"Alerte sur la santé de la marque. Dégradation détectée "
                        f"de {delta:+.1f} pts, action requise."
                    )
    except Exception as e:
        logger.error("Erreur get_dashboard_summary: %s", e)

    try:
        df = load_annotated(client_id=client_id)
        if not df.empty:
            total_mentions = int(len(df))
            period = _compute_period_label(df)
            regional_distribution = _compute_regional_distribution(df)
            product_performance = _compute_product_performance(df)
    except Exception as e:
        logger.warning("Impossible d'enrichir le dashboard depuis annotated.parquet: %s", e)

    trend = "up" if delta > 0 else "down" if delta < 0 else "flat"

    return DashboardSummary(
        health_score=health_score,
        health_trend=trend,
        nss_progress_pts=round(delta, 1),
        summary_text=text,
        total_mentions=total_mentions,
        period=period,
        regional_distribution=regional_distribution,
        product_performance=product_performance,
    )


@router.get("/alerts-critical", response_model=DashboardAlerts)
def get_critical_alerts(client_id: str = Depends(resolve_client_id)):
    """Retourne les 3 alertes critiques les plus récentes."""
    alerts = []
    try:
        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT alert_id, severity, title, description, detected_at "
                "FROM alerts "
                "WHERE client_id = ? AND severity = 'critical' AND status != 'resolved' "
                "ORDER BY detected_at DESC LIMIT 3",
                (client_id,),
            ).fetchall()

            for row in rows:
                alerts.append(
                    AlertSummary(
                        alert_id=str(row["alert_id"]),
                        severity=row["severity"],
                        title=row["title"],
                        description=row["description"] or "",
                        created_at=row["detected_at"] or "",
                    )
                )
    except Exception as e:
        logger.error("Erreur get_critical_alerts: %s", e)

    return DashboardAlerts(critical_alerts=alerts)


@router.get("/top-actions", response_model=DashboardActions)
def get_top_actions(client_id: str = Depends(resolve_client_id)):
    """Retourne les 3 recommandations / actions prioritaires."""
    actions = []
    try:
        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT recommendation_id, analysis_summary, recommendations, confidence_score "
                "FROM recommendations "
                "WHERE client_id = ? AND status = 'active' "
                "ORDER BY created_at DESC LIMIT 3",
                (client_id,),
            ).fetchall()

            for row in rows:
                title = row["analysis_summary"] or "Action suggeree"
                recos_json = row["recommendations"]
                priority = "medium"
                description = row["analysis_summary"] or ""
                target_platform = "Toutes"
                icon = "auto_awesome"
                cta_label = "VOIR DETAILS"

                try:
                    if recos_json:
                        recos_list = json.loads(recos_json)
                        if isinstance(recos_list, list) and len(recos_list) > 0:
                            first_item = recos_list[0]
                            title = first_item.get("title", title)
                            description = first_item.get("description") or description
                            priority = first_item.get("priority", priority)
                            target_platform = first_item.get("target_platform") or target_platform
                            if target_platform and target_platform != "Toutes":
                                icon = "rocket_launch"
                            cta_label = "EXECUTER L'ACTION"
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

                actions.append(
                    ActionRecommendation(
                        recommendation_id=str(row["recommendation_id"]),
                        title=title,
                        priority=priority,
                        target_platform=target_platform,
                        description=description,
                        confidence_score=row["confidence_score"],
                        cta_label=cta_label,
                        icon=icon,
                    )
                )
    except Exception as e:
        logger.error("Erreur get_top_actions: %s", e)

    return DashboardActions(top_actions=actions)
