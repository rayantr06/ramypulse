import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from api.schemas import CampaignCreate, CampaignResponse, CampaignImpact, CampaignStatusUpdate
from core.campaigns import campaign_manager
from api.data_loader import load_annotated
import sqlite3
import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.post("", response_model=Dict[str, Any])
def create_campaign(data: CampaignCreate):
    """Création d'une nouvelle campagne marketing."""
    try:
        campaign_dict = data.model_dump(exclude_unset=True)
        # Handle lists directly, campaign_manager takes lists via _serialize_list internally if needed, but it expects them as Python lists!
        campaign_id = campaign_manager.create_campaign(campaign_dict)
        return {"campaign_id": campaign_id, "status": "created"}
    except Exception as e:
        logger.error(f"Erreur create_campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def list_campaigns(status: str = None, platform: str = None):
    """Lister les campagnes existantes."""
    try:
        return campaign_manager.list_campaigns(status=status, platform=platform)
    except Exception as e:
        logger.error(f"Erreur list_campaigns: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@router.get("/{campaign_id}")
def get_campaign_detail(campaign_id: str):
    """Détail d'une campagne précise."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_campaign_detail: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@router.delete("/{campaign_id}")
def archive_campaign(campaign_id: str):
    """Supprimer la campagne."""
    try:
        success = campaign_manager.delete_campaign(campaign_id)
        if not success:
             raise HTTPException(status_code=404, detail="Campaign not found")
        return {"result": "success", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"Erreur archive_campaign: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@router.put("/{campaign_id}/status")
def update_campaign(campaign_id: str, update: CampaignStatusUpdate):
    """Mettre à jour le statut d'une campagne."""
    try:
        success = campaign_manager.update_campaign_status(campaign_id, update.status)
        if not success:
             raise HTTPException(status_code=404, detail="Campaign not found")
        return {"result": "success", "campaign_id": campaign_id, "status": update.status}
    except Exception as e:
        logger.error(f"Erreur update_campaign: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")

@router.get("/{campaign_id}/impact")
def get_campaign_impact(campaign_id: str):
    """Calcule l'impact NSS de la campagne (Pre/Active/Post) à la volée depuis le Parquet."""
    from core.campaigns.impact_calculator import CampaignImpactCalculator
    
    try:
        campaign = campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
            
        df = load_annotated()
        if df.empty:
            raise HTTPException(status_code=400, detail="Data source unavailable or empty")
            
        calculator = CampaignImpactCalculator(config.SQLITE_DB_PATH)
        impact = calculator.evaluate_campaign_impact(campaign_id, df)
        return impact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_campaign_impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))
