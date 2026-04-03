"""Routeur FastAPI pour les watchlists RamyPulse.

Délègue au core.watchlists.watchlist_manager pour le CRUD principal.
Les métriques (snapshots) utilisent un accès SQL direct car aucun
manager dédié n'existe encore pour cette table.
"""

import logging
import sqlite3

from fastapi import APIRouter, HTTPException

import config
from core.watchlists.watchlist_manager import (
    list_watchlists as _core_list_watchlists,
    get_watchlist as _core_get_watchlist,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


def _get_db_connection() -> sqlite3.Connection:
    """Connexion SQLite pour les requêtes snapshot (pas de manager core dédié)."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def list_watchlists(is_active: bool = True):
    """Récupère la liste des watchlists via le manager core."""
    try:
        return _core_list_watchlists(is_active=is_active)
    except Exception as e:
        logger.error("Erreur list_watchlists: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{watchlist_id}")
def get_watchlist(watchlist_id: str):
    """Récupère le détail d'une watchlist."""
    try:
        wl = _core_get_watchlist(watchlist_id)
        if not wl:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return wl
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur get_watchlist: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{watchlist_id}/metrics")
def get_watchlist_metrics(watchlist_id: str):
    """Récupère les métriques courantes (snapshot le plus récent) d'une watchlist."""
    try:
        with _get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM watchlist_metric_snapshots "
                "WHERE watchlist_id = ? ORDER BY computed_at DESC LIMIT 1",
                [watchlist_id],
            ).fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No metrics found for this watchlist",
                )
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur get_watchlist_metrics: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")
