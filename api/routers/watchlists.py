import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sqlite3
import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])

def _get_connection():
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("")
def list_watchlists(is_active: bool = True):
    """Récupère la liste des watchlists existantes."""
    try:
        query = "SELECT * FROM watchlists WHERE is_active = ?"
        with _get_connection() as conn:
            rows = conn.execute(query, [1 if is_active else 0]).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erreur list_watchlists: {e}")
        raise HTTPException(status_code=500, detail="Internal DB error")

@router.get("/{watchlist_id}/metrics")
def get_watchlist_metrics(watchlist_id: str):
    """Récupère les métriques courantes (snapshot le plus récent) d'une watchlist."""
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM watchlist_metric_snapshots "
                "WHERE watchlist_id = ? ORDER BY computed_at DESC LIMIT 1",
                [watchlist_id]
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No metrics found for this watchlist")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_watchlist_metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal DB error")
