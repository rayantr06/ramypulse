import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.data_loader import load_annotated
from api.deps.tenant import resolve_client_id
from api.schemas import CampaignCreate, CampaignOverview, CampaignStats, CampaignStatusUpdate
from core.campaigns import campaign_manager, overview_service
from core.campaigns.impact_calculator import compute_campaign_impact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.post("", response_model=Dict[str, Any])
def create_campaign(data: CampaignCreate):
    """Creation d'une nouvelle campagne marketing."""
    try:
        campaign_dict = data.model_dump(exclude_unset=True)
        campaign_id = campaign_manager.create_campaign(campaign_dict)
        return {"campaign_id": campaign_id, "status": "created"}
    except Exception as exc:
        logger.error("Erreur create_campaign: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
def list_campaigns(
    status: str = None,
    platform: str = None,
    client_id: str = Depends(resolve_client_id),
):
    """Lister les campagnes existantes."""
    try:
        return campaign_manager.list_campaigns(status=status, platform=platform, client_id=client_id)
    except Exception as exc:
        logger.error("Erreur list_campaigns: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/stats", response_model=CampaignStats)
def get_campaign_stats(client_id: str = Depends(resolve_client_id)):
    """Expose les stats budget reelles du trimestre courant."""
    try:
        stats = overview_service.get_quarter_budget_stats(client_id=client_id)
        return CampaignStats(
            quarterly_budget_committed=stats["quarterly_budget_committed"],
            quarterly_budget_allocation=stats["quarterly_budget_allocation"],
            quarter_label=stats["quarter_label"],
        )
    except Exception as exc:
        logger.error("Erreur get_campaign_stats: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/overview", response_model=CampaignOverview)
def get_campaign_overview(client_id: str = Depends(resolve_client_id)):
    """Expose le bundle métier de la page Campagnes."""
    try:
        return CampaignOverview(**overview_service.get_campaigns_overview(client_id=client_id))
    except Exception as exc:
        logger.error("Erreur get_campaign_overview: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/{campaign_id}")
def get_campaign_detail(campaign_id: str, client_id: str = Depends(resolve_client_id)):
    """Detail d'une campagne precise."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id, client_id=client_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_campaign_detail: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.delete("/{campaign_id}")
def archive_campaign(campaign_id: str):
    """Supprimer la campagne."""
    try:
        success = campaign_manager.delete_campaign(campaign_id)
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"result": "success", "campaign_id": campaign_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur archive_campaign: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.put("/{campaign_id}/status")
def update_campaign(campaign_id: str, update: CampaignStatusUpdate):
    """Mettre a jour le statut d'une campagne."""
    try:
        success = campaign_manager.update_campaign_status(campaign_id, update.status)
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"result": "success", "campaign_id": campaign_id, "status": update.status}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur update_campaign: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/{campaign_id}/impact")
def get_campaign_impact(campaign_id: str, client_id: str = Depends(resolve_client_id)):
    """Calcule l'impact NSS de la campagne depuis le Parquet annote."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id, client_id=client_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        df = load_annotated(client_id=client_id)
        if df.empty:
            raise HTTPException(status_code=400, detail="Data source unavailable or empty")

        return compute_campaign_impact(campaign_id, df)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_campaign_impact: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
