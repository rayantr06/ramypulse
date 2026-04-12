"""API routes for smart onboarding."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.onboarding.onboarding_service import analyze_brand, confirm_onboarding


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class OnboardingAnalyzeRequest(BaseModel):
    brand_name: str
    product_name: str | None = None
    country: str = "dz"


class TenantSetupInput(BaseModel):
    client_name: str
    client_slug: str | None = None
    country: str = "DZ"


class SelectedSourceInput(BaseModel):
    type: str
    label: str
    url: str
    channel: str


class SelectedWatchlistInput(BaseModel):
    name: str
    description: str = ""
    scope_type: str
    role: str
    filters: dict[str, Any] = Field(default_factory=dict)


class SelectedAlertProfileInput(BaseModel):
    watchlist_ref: str
    profile_name: str
    enabled_by_default: bool = True
    rules: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""


class DeferredAgentConfigInput(BaseModel):
    key: str
    value: Any = None
    reason: str = ""


class OnboardingConfirmRequest(BaseModel):
    review_confirmed: bool
    tenant_setup: TenantSetupInput
    brand_name: str
    industry: str | None = None
    selected_sources: list[SelectedSourceInput] = Field(default_factory=list)
    selected_channels: list[str] = Field(default_factory=list)
    selected_watchlists: list[SelectedWatchlistInput] = Field(default_factory=list)
    selected_alert_profiles: list[SelectedAlertProfileInput] = Field(default_factory=list)
    deferred_agent_config: list[DeferredAgentConfigInput] = Field(default_factory=list)


@router.post("/analyze")
def analyze_onboarding_route(payload: OnboardingAnalyzeRequest) -> dict[str, Any]:
    try:
        return analyze_brand(
            brand_name=payload.brand_name,
            product_name=payload.product_name,
            country=payload.country,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Erreur analyze_onboarding_route: %s", exc)
        raise HTTPException(status_code=500, detail="Smart onboarding analyze failed")


@router.post("/confirm", status_code=201)
def confirm_onboarding_route(payload: OnboardingConfirmRequest) -> dict[str, Any]:
    try:
        return confirm_onboarding(
            review_confirmed=payload.review_confirmed,
            tenant_setup=payload.tenant_setup.model_dump(),
            brand_name=payload.brand_name,
            industry=payload.industry,
            selected_sources=[item.model_dump() for item in payload.selected_sources],
            selected_channels=payload.selected_channels,
            selected_watchlists=[item.model_dump() for item in payload.selected_watchlists],
            selected_alert_profiles=[item.model_dump() for item in payload.selected_alert_profiles],
            deferred_agent_config=[item.model_dump() for item in payload.deferred_agent_config],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Erreur confirm_onboarding_route: %s", exc)
        raise HTTPException(status_code=500, detail="Smart onboarding confirm failed")
