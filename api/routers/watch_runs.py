"""FastAPI router exposing tracked watch run orchestration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.deps.tenant import resolve_client_id
from api.schemas import WatchRunCreate, WatchRunResponse
from core.watch_runs.run_service import get_watch_run, start_watch_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watch-runs", tags=["Watch Runs"])


@router.post("", response_model=WatchRunResponse, status_code=202)
def create_watch_run_route(
    payload: WatchRunCreate,
    client_id: str = Depends(resolve_client_id),
):
    """Create a tracked watch run and launch it asynchronously for expo usage."""
    try:
        run = start_watch_run(
            client_id=client_id,
            watchlist_id=payload.watchlist_id,
            requested_channels=payload.requested_channels,
        )
        if run is None:
            raise HTTPException(status_code=500, detail="Watch run creation failed")
        return run
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur create_watch_run: %s", exc)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{run_id}", response_model=WatchRunResponse)
def get_watch_run_route(
    run_id: str,
    client_id: str = Depends(resolve_client_id),
):
    """Return a tenant-scoped watch run by identifier."""
    try:
        run = get_watch_run(run_id)
        if run is None or run.get("client_id") != client_id:
            raise HTTPException(status_code=404, detail="Watch run not found")
        return run
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_watch_run: %s", exc)
        raise HTTPException(status_code=500, detail="Internal DB error")
