import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from core.alerts.alert_manager import get_alert, update_alert_status
import sqlite3
import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])

def _get_connection():
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("")
def list_alerts(status: str = None, severity: str = None, limit: int = 50):
    """Récupère la liste des alertes."""
    try:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
            
        query += " ORDER BY detected_at DESC LIMIT ?"
        params.append(limit)
        
        with _get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erreur list_alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal DB error")

@router.get("/{alert_id}")
def get_alert_detail(alert_id: str):
    """Récupère le détail d'une alerte spécifique par l'API."""
    try:
        alert = get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
    except Exception as e:
        logger.error(f"Erreur get_alert: {e}")
        raise HTTPException(status_code=500, detail="Internal DB error")

@router.put("/{alert_id}/status")
def update_status(alert_id: str, payload: dict):
    """Met à jour le statut (ex: resolved, acknowledged) d'une alerte."""
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing 'status' in body")
        
    try:
        success = update_alert_status(alert_id, new_status)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"result": "success", "alert_id": alert_id, "status": new_status}
    except Exception as e:
        logger.error(f"Erreur update_status: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
