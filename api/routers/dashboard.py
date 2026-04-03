"""Routeur FastAPI pour le dashboard RamyPulse.

Agrège des données cross-tables (watchlist_metric_snapshots, alerts,
recommendations) en lecture seule. SQL direct justifié car il s'agit
de vues d'agrégation sans manager core dédié.
"""

import json
import logging
import sqlite3

from fastapi import APIRouter

import config
from api.schemas import (
    ActionRecommendation,
    AlertSummary,
    DashboardActions,
    DashboardAlerts,
    DashboardSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _get_db_connection() -> sqlite3.Connection:
    """Connexion SQLite en lecture pour les agrégations dashboard."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    """Retourne le score santé de la marque et les tendances générales.

    Si la base est vierge, renvoie un fallback métier élégant.
    """
    health_score = 0
    delta = 0.0
    text = "Pas de données suffisantes pour établir un diagnostic."

    try:
        with _get_db_connection() as conn:
            row = conn.execute(
                "SELECT nss_current, delta_nss "
                "FROM watchlist_metric_snapshots "
                "ORDER BY computed_at DESC LIMIT 1"
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

    trend = "up" if delta > 0 else "down" if delta < 0 else "flat"

    return DashboardSummary(
        health_score=health_score,
        health_trend=trend,
        nss_progress_pts=round(delta, 1),
        summary_text=text,
    )


@router.get("/alerts-critical", response_model=DashboardAlerts)
def get_critical_alerts():
    """Retourne les 3 alertes critiques les plus récentes."""
    alerts = []
    try:
        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT alert_id, severity, title, description, detected_at "
                "FROM alerts "
                "WHERE severity = 'critical' AND status != 'resolved' "
                "ORDER BY detected_at DESC LIMIT 3"
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
def get_top_actions():
    """Retourne les 3 recommandations / actions prioritaires."""
    actions = []
    try:
        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT recommendation_id, analysis_summary, recommendations "
                "FROM recommendations "
                "WHERE status = 'active' "
                "ORDER BY created_at DESC LIMIT 3"
            ).fetchall()

            for row in rows:
                title = row["analysis_summary"] or "Action suggérée"
                recos_json = row["recommendations"]
                priority = "medium"

                try:
                    if recos_json:
                        recos_list = json.loads(recos_json)
                        if isinstance(recos_list, list) and len(recos_list) > 0:
                            title = recos_list[0].get("title", title)
                            priority = "high"
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

                actions.append(
                    ActionRecommendation(
                        recommendation_id=str(row["recommendation_id"]),
                        title=title,
                        priority=priority,
                        target_platform="Toutes",
                    )
                )
    except Exception as e:
        logger.error("Erreur get_top_actions: %s", e)

    return DashboardActions(top_actions=actions)
