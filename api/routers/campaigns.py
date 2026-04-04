import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from api.data_loader import load_annotated
from api.schemas import CampaignCreate, CampaignStats, CampaignStatusUpdate
from core.campaigns import campaign_manager
from core.campaigns.impact_calculator import compute_campaign_impact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _parse_campaign_date(value: str | None) -> date | None:
    if not value:
        return None

    candidate = str(value).strip()
    if not candidate:
        return None

    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(candidate[:10])
        except ValueError:
            return None


def _quarter_bounds(today: date | None = None) -> tuple[date, date, str]:
    current = today or date.today()
    quarter_start_month = ((current.month - 1) // 3) * 3 + 1
    quarter_end_month = quarter_start_month + 2
    start = date(current.year, quarter_start_month, 1)
    end = date(current.year, quarter_end_month, monthrange(current.year, quarter_end_month)[1])
    quarter_index = ((quarter_start_month - 1) // 3) + 1
    return start, end, f"T{quarter_index} {current.year}"


def _campaign_reference_date(campaign: dict[str, Any]) -> date | None:
    return _parse_campaign_date(campaign.get("start_date"))


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
def list_campaigns(status: str = None, platform: str = None):
    """Lister les campagnes existantes."""
    try:
        return campaign_manager.list_campaigns(status=status, platform=platform)
    except Exception as exc:
        logger.error("Erreur list_campaigns: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/stats", response_model=CampaignStats)
def get_campaign_stats():
    """Expose les stats budget reelles du trimestre courant."""
    try:
        campaigns = campaign_manager.list_campaigns(limit=1000)
        quarter_start, quarter_end, quarter_label = _quarter_bounds()

        quarter_campaigns = []
        for campaign in campaigns:
            reference_date = _campaign_reference_date(campaign)
            if reference_date is None:
                continue
            if not (quarter_start <= reference_date <= quarter_end):
                continue
            if campaign.get("status") == "cancelled":
                continue
            budget = campaign.get("budget_dza")
            if budget in (None, ""):
                continue
            quarter_campaigns.append(campaign)

        quarterly_budget_allocation = sum(
            int(campaign.get("budget_dza") or 0) for campaign in quarter_campaigns
        )
        quarterly_budget_committed = sum(
            int(campaign.get("budget_dza") or 0)
            for campaign in quarter_campaigns
            if campaign.get("status") in {"active", "completed"}
        )

        return CampaignStats(
            quarterly_budget_committed=quarterly_budget_committed,
            quarterly_budget_allocation=quarterly_budget_allocation,
            quarter_label=quarter_label,
        )
    except Exception as exc:
        logger.error("Erreur get_campaign_stats: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.get("/{campaign_id}")
def get_campaign_detail(campaign_id: str):
    """Detail d'une campagne precise."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id)
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
def get_campaign_impact(campaign_id: str):
    """Calcule l'impact NSS de la campagne depuis le Parquet annote."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        df = load_annotated()
        if df.empty:
            raise HTTPException(status_code=400, detail="Data source unavailable or empty")

        return compute_campaign_impact(campaign_id, df)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_campaign_impact: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
