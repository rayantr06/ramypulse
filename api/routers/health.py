from fastapi import APIRouter
from pydantic import BaseModel

import sqlite3
import os
import config

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    message: str
    db_status: str

@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health():
    """Vérifier l'état de santé de l'API et des dépendances critiques."""
    db_status = "unreachable"
    try:
        if os.path.exists(config.SQLITE_DB_PATH):
            with sqlite3.connect(config.SQLITE_DB_PATH) as conn:
                conn.execute("SELECT 1")
            db_status = "connected"
        else:
            db_status = "missing"
    except Exception:
        db_status = "error"
        
    status = "ok" if db_status == "connected" else "degraded"
    return HealthResponse(
        status=status,
        message="RamyPulse API Status",
        db_status=db_status
    )
