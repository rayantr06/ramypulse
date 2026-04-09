"""Routeur FastAPI pour les watchlists RamyPulse.

Délègue au core.watchlists.watchlist_manager pour le CRUD principal.
Les métriques (snapshots) utilisent un accès SQL direct car aucun
manager dédié n'existe encore pour cette table.
"""

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

import config
from api.deps.tenant import resolve_client_id
from api.schemas import WatchlistCreate, WatchlistUpdate
from core.watchlists.watchlist_manager import (
    create_watchlist as _core_create_watchlist,
    deactivate_watchlist as _core_deactivate_watchlist,
    get_watchlist as _core_get_watchlist,
    list_watchlists as _core_list_watchlists,
    update_watchlist as _core_update_watchlist,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


def _get_db_connection() -> sqlite3.Connection:
    """Connexion SQLite pour les requêtes snapshot (pas de manager core dédié)."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.post("", status_code=201)
def create_watchlist(
    data: WatchlistCreate,
    client_id: str = Depends(resolve_client_id),
):
    """Crée une nouvelle watchlist."""
    try:
        payload = data.model_dump()
        watchlist_id = _core_create_watchlist(
            name=payload["name"],
            description=payload["description"],
            scope_type=payload["scope_type"],
            filters=payload["filters"],
            client_id=client_id,
        )
        return {"watchlist_id": watchlist_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Erreur create_watchlist: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("")
def list_watchlists(
    is_active: bool = True,
    client_id: str = Depends(resolve_client_id),
):
    """Récupère la liste des watchlists via le manager core."""
    try:
        return [
            watchlist
            for watchlist in _core_list_watchlists(is_active=is_active)
            if watchlist.get("client_id") == client_id
        ]
    except Exception as e:
        logger.error("Erreur list_watchlists: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{watchlist_id}")
def get_watchlist(
    watchlist_id: str,
    client_id: str = Depends(resolve_client_id),
):
    """Récupère le détail d'une watchlist."""
    try:
        wl = _core_get_watchlist(watchlist_id)
        if not wl or wl.get("client_id") != client_id:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return wl
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur get_watchlist: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.put("/{watchlist_id}")
def update_watchlist(watchlist_id: str, data: WatchlistUpdate):
    """Met à jour les champs d'une watchlist existante."""
    try:
        updates = {
            k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None
        }
        if "name" in updates:
            updates["watchlist_name"] = updates.pop("name")
        updated = _core_update_watchlist(watchlist_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return {"watchlist_id": watchlist_id, "status": "updated"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Erreur update_watchlist: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.delete("/{watchlist_id}", status_code=204)
def deactivate_watchlist(watchlist_id: str):
    """Désactive une watchlist (suppression logique)."""
    try:
        deactivated = _core_deactivate_watchlist(watchlist_id)
        if not deactivated:
            raise HTTPException(status_code=404, detail="Watchlist not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur deactivate_watchlist: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{watchlist_id}/metrics")
def get_watchlist_metrics(
    watchlist_id: str,
    client_id: str = Depends(resolve_client_id),
):
    """Récupère les métriques courantes (snapshot le plus récent) d'une watchlist."""
    try:
        watchlist = _core_get_watchlist(watchlist_id)
        if not watchlist or watchlist.get("client_id") != client_id:
            raise HTTPException(status_code=404, detail="Watchlist not found")
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
