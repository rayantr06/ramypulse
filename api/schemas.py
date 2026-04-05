"""Modèles Pydantic pour l'API RamyPulse.

Définit les schemas de requête et réponse pour tous les routeurs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    message: str
    db_status: str


class ApiStatusResponse(BaseModel):
    api_status: str
    db_status: str
    latency_ms: int


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    health_score: int
    health_trend: str
    nss_progress_pts: float
    summary_text: str
    total_mentions: int = 0
    period: str = "sur la periode chargee"
    regional_distribution: list["RegionalDistributionItem"] = Field(default_factory=list)
    product_performance: list["ProductPerformanceItem"] = Field(default_factory=list)


class RegionalDistributionItem(BaseModel):
    wilaya: str
    pct: int


class ProductPerformanceItem(BaseModel):
    product: str
    trend_pct: float
    relative_volume: int


class AlertSummary(BaseModel):
    alert_id: str
    severity: str
    title: str
    description: str
    created_at: str


class ActionRecommendation(BaseModel):
    recommendation_id: str
    title: str
    priority: str
    target_platform: str
    description: str = ""
    confidence_score: float | None = None
    cta_label: str = "VOIR DETAILS"
    icon: str = "auto_awesome"


class DashboardAlerts(BaseModel):
    critical_alerts: list[AlertSummary]


class DashboardActions(BaseModel):
    top_actions: list[ActionRecommendation]


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

class CampaignCreate(BaseModel):
    campaign_name: str
    campaign_type: str | None = None
    platform: str | None = None
    description: str | None = None
    influencer_handle: str | None = None
    influencer_tier: str | None = None
    target_segment: str | None = None
    target_aspects: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    budget_dza: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    pre_window_days: int = 14
    post_window_days: int = 14
    revenue_dza: int | None = None


class CampaignStatusUpdate(BaseModel):
    status: str = Field(description="planned | active | completed | cancelled")


class PhaseMetrics(BaseModel):
    nss: float | None = None
    volume: int = 0
    aspect_breakdown: dict[str, float] = Field(default_factory=dict)
    sentiment_breakdown: dict[str, int] = Field(default_factory=dict)


class CampaignImpact(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    phases: dict[str, PhaseMetrics]
    uplift_nss: float | None = None
    uplift_volume_pct: float | None = None
    is_reliable: bool = False
    reliability_note: str = ""


class CampaignResponse(BaseModel):
    campaign_id: str
    client_id: str | None = None
    campaign_name: str
    campaign_type: str | None = None
    platform: str | None = None
    description: str | None = None
    influencer_handle: str | None = None
    influencer_tier: str | None = None
    target_segment: str | None = None
    target_aspects: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    budget_dza: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    pre_window_days: int | None = None
    post_window_days: int | None = None
    revenue_dza: int | None = None
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CampaignStats(BaseModel):
    quarterly_budget_committed: int = 0
    quarterly_budget_allocation: int = 0
    quarter_label: str


class CampaignOverviewTopPerformer(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    influencer_handle: str | None = None
    platform: str | None = None
    status: str | None = None
    budget_dza: int | None = None
    roi_pct: float | None = None
    engagement_rate: float | None = None
    signal_count: int = 0
    sentiment_breakdown: dict[str, int] = Field(default_factory=dict)
    negative_aspects: list[str] = Field(default_factory=list)
    selection_basis: str | None = None


class CampaignOverview(BaseModel):
    quarterly_budget_committed: int = 0
    quarterly_budget_allocation: int = 0
    quarter_label: str
    active_campaigns_count: int = 0
    top_performer: CampaignOverviewTopPerformer | None = None


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class RecommendationGenerate(BaseModel):
    trigger_type: str = "manual"
    trigger_id: str | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(description="active | archived | dismissed")


class ProviderModel(BaseModel):
    id: str
    label: str
    recommended: bool = False


class ProviderCatalog(BaseModel):
    providers: dict[str, list[ProviderModel]]


class RecommendationResponse(BaseModel):
    recommendation_id: str
    client_id: str | None = None
    trigger_type: str | None = None
    trigger_id: str | None = None
    analysis_summary: str | None = None
    recommendations: list = Field(default_factory=list)
    watchlist_priorities: list = Field(default_factory=list)
    confidence_score: float | None = None
    data_quality_note: str | None = None
    provider_used: str | None = None
    model_used: str | None = None
    context_tokens: int | None = None
    generation_ms: int | None = None
    status: str | None = None
    created_at: str | None = None


class ContextPreview(BaseModel):
    estimated_tokens: int = 0
    estimated_cost_usd: float | None = None
    nss_global: float | None = None
    volume_total: int = 0
    active_alerts_count: int = 0
    active_watchlists_count: int = 0
    recent_campaigns_count: int = 0
    provider_used: str | None = None
    model_used: str | None = None
    pricing_basis: str | None = None
    trigger: str | None = None


# ---------------------------------------------------------------------------
# Explorer
# ---------------------------------------------------------------------------

class VerbatimItem(BaseModel):
    text: str = ""
    sentiment_label: str = ""
    confidence: float = 0.0
    channel: str = ""
    aspect: str = ""
    wilaya: str = ""
    timestamp: str = ""
    source_url: str = ""


class VerbatimResponse(BaseModel):
    results: list[VerbatimItem]
    total: int
    page: int
    page_size: int


class SearchResult(BaseModel):
    text: str = ""
    score: float = 0.0
    sentiment_label: str = ""
    aspect: str = ""
    channel: str = ""
    source_url: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ---------------------------------------------------------------------------
# Admin (Ingestion & Sources)
# ---------------------------------------------------------------------------

class SourceCreate(BaseModel):
    source_id: str | None = None
    client_id: str | None = None
    source_name: str
    platform: str
    source_type: str
    owner_type: str
    auth_mode: str | None = None
    config_json: dict = Field(default_factory=dict)
    is_active: bool = True
    sync_frequency_minutes: int = 60
    freshness_sla_hours: int = 24
    source_purpose: str | None = None
    source_priority: int | None = None
    coverage_key: str | None = None
    credential_id: str | None = None


class SourceUpdate(BaseModel):
    client_id: str | None = None
    source_name: str | None = None
    is_active: bool | None = None
    config_json: dict | None = None
    sync_frequency_minutes: int | None = None
    freshness_sla_hours: int | None = None
    source_purpose: str | None = None
    source_priority: int | None = None
    coverage_key: str | None = None
    credential_id: str | None = None


class SourceSyncTrigger(BaseModel):
    client_id: str | None = None
    run_mode: str = "manual"
    manual_file_path: str | None = None
    credentials: dict | None = None
    column_mapping: dict[str, str] | None = None


class NormalizationTrigger(BaseModel):
    client_id: str | None = None
    batch_size: int = 200


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    scope_type: str = "product"
    filters: dict = Field(default_factory=dict)


class WatchlistUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    scope_type: str | None = None
    filters: dict | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Social Metrics
# ---------------------------------------------------------------------------

class CredentialCreate(BaseModel):
    entity_type: str
    entity_name: str
    platform: str
    account_id: str | None = None
    access_token: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    extra_config: dict = Field(default_factory=dict)


class CredentialResponse(BaseModel):
    credential_id: str
    entity_type: str
    entity_name: str
    platform: str
    account_id: str | None = None
    app_id: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class CampaignPostAdd(BaseModel):
    platform: str
    post_platform_id: str
    post_url: str | None = None
    entity_type: str = "brand"
    entity_name: str | None = None
    credential_id: str | None = None


class ManualMetricsInput(BaseModel):
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    reach: int = 0
    impressions: int = 0
    saves: int = 0


class CampaignRevenuePatch(BaseModel):
    revenue_dza: int = Field(ge=0)
