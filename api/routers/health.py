import os
import sqlite3
import time

from fastapi import APIRouter

import config
from api.schemas import ApiStatusResponse, HealthResponse

router = APIRouter()


def _check_database() -> tuple[str, int]:
    db_status = "unreachable"
    started_at = time.perf_counter()

    try:
        if os.path.exists(config.SQLITE_DB_PATH):
            with sqlite3.connect(config.SQLITE_DB_PATH) as conn:
                conn.execute("SELECT 1")
            db_status = "connected"
        else:
            db_status = "missing"
    except Exception:
        db_status = "error"

    latency_ms = int(round((time.perf_counter() - started_at) * 1000))
    return db_status, latency_ms


def _api_status_label(db_status: str) -> str:
    if db_status == "connected":
        return "Normal"
    if db_status == "missing":
        return "Dégradé"
    return "Erreur"


@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health():
    """Verifier l'etat de sante de l'API et de la base SQLite."""
    db_status, _latency_ms = _check_database()
    status = "ok" if db_status == "connected" else "degraded"
    return HealthResponse(
        status=status,
        message="RamyPulse API Status",
        db_status=db_status,
    )


@router.get("/status", response_model=ApiStatusResponse, tags=["System"])
def get_status():
    """Expose un statut API simple avec une latence mesuree au runtime."""
    db_status, latency_ms = _check_database()
    return ApiStatusResponse(
        api_status=_api_status_label(db_status),
        db_status=db_status,
        latency_ms=latency_ms,
    )
