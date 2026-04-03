"""Routeur FastAPI pour les alertes RamyPulse.

Délègue au core.alerts.alert_manager pour la logique métier et la
désérialisation JSON automatique des payloads.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.alerts.alert_manager import get_alert, list_alerts as _core_list_alerts, update_alert_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertStatusUpdate(BaseModel):
    """Schema pour la mise à jour du statut d'une alerte."""
    status: str


@router.get("")
def list_alerts(status: str = None, severity: str = None, limit: int = 50):
    """Récupère la liste des alertes via le manager core."""
    try:
        return _core_list_alerts(status=status, severity=severity, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erreur list_alerts: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str):
    """Récupère le détail d'une alerte spécifique."""
    try:
        alert = get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur get_alert: %s", e)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.put("/{alert_id}/status")
def update_status(alert_id: str, payload: AlertStatusUpdate):
    """Met à jour le statut (ex: resolved, acknowledged) d'une alerte."""
    try:
        success = update_alert_status(alert_id, payload.status)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"result": "success", "alert_id": alert_id, "status": payload.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur update_status: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")
