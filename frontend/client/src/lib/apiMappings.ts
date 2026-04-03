import type {
  Alert,
  Campaign,
  CampaignImpact,
  ContextPreview,
  DashboardAction,
  DashboardAlert,
  DashboardSummary,
  HealthSnapshot,
  ProviderOption,
  Recommendation,
  RecommendationItem,
  SearchResult,
  Source,
  SyncRun,
  VerbatimsResponse,
  VerbatimItem,
  Watchlist,
  WatchlistMetrics,
} from "@shared/schema";

type UnknownRecord = Record<string, unknown>;

export interface CampaignFormInput {
  campaign_name: string;
  campaign_type?: string;
  platform?: string;
  description?: string;
  influencer_handle?: string;
  target_aspects?: string[];
  target_regions?: string[];
  keywords?: string[];
  budget_dza?: string;
  start_date?: string;
  end_date?: string;
}

function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))
      ? Number(value)
      : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => asString(item)).filter((item) => item !== "")
    : [];
}

function asObjectArray(value: unknown): UnknownRecord[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function asNumberRecord(value: unknown): Record<string, number> {
  const record = asRecord(value);
  return Object.fromEntries(
    Object.entries(record).map(([key, rawValue]) => [key, asNumber(rawValue)]),
  );
}

export function mapDashboardSummary(value: unknown): DashboardSummary {
  const record = asRecord(value);
  return {
    health_score: asNumber(record.health_score),
    health_trend: (asString(record.health_trend, "flat") as DashboardSummary["health_trend"]),
    nss_progress_pts: asNumber(record.nss_progress_pts),
    summary_text: asString(record.summary_text),
    total_mentions: asNumber(record.total_mentions),
    period: asString(record.period, "sur la periode chargee"),
    regional_distribution: asObjectArray(record.regional_distribution).map((item) => ({
      wilaya: asString(item.wilaya),
      pct: asNumber(item.pct),
    })),
    product_performance: asObjectArray(record.product_performance).map((item) => ({
      product: asString(item.product),
      trend_pct: asNumber(item.trend_pct),
      relative_volume: asNumber(item.relative_volume),
    })),
  };
}

export function mapDashboardAlerts(value: unknown): DashboardAlert[] {
  const record = asRecord(value);
  return asObjectArray(record.critical_alerts).map((item) => ({
    alert_id: asString(item.alert_id),
    severity: asString(item.severity),
    title: asString(item.title),
    description: asString(item.description),
    created_at: asString(item.created_at),
  }));
}

export function mapDashboardActions(value: unknown): DashboardAction[] {
  const record = asRecord(value);
  return asObjectArray(record.top_actions).map((item) => ({
    recommendation_id: asString(item.recommendation_id),
    title: asString(item.title),
    priority: asString(item.priority),
    target_platform: asString(item.target_platform),
    description: asString(item.description) || undefined,
    confidence_score:
      item.confidence_score == null ? undefined : asNumber(item.confidence_score),
    cta_label: asString(item.cta_label) || undefined,
    icon: asString(item.icon) || undefined,
  }));
}

export function mapCampaign(value: unknown): Campaign {
  const record = asRecord(value);
  return {
    campaign_id: asString(record.campaign_id),
    client_id: asString(record.client_id) || null,
    campaign_name: asString(record.campaign_name),
    campaign_type: asString(record.campaign_type) || null,
    platform: asString(record.platform) || null,
    description: asString(record.description) || null,
    influencer_handle: asString(record.influencer_handle) || null,
    influencer_tier: asString(record.influencer_tier) || null,
    target_segment: asString(record.target_segment) || null,
    target_aspects: asStringArray(record.target_aspects),
    target_regions: asStringArray(record.target_regions),
    keywords: asStringArray(record.keywords),
    budget_dza: record.budget_dza == null ? null : asNumber(record.budget_dza),
    start_date: asString(record.start_date) || null,
    end_date: asString(record.end_date) || null,
    pre_window_days: record.pre_window_days == null ? null : asNumber(record.pre_window_days),
    post_window_days: record.post_window_days == null ? null : asNumber(record.post_window_days),
    status: asString(record.status) || null,
    created_at: asString(record.created_at) || null,
    updated_at: asString(record.updated_at) || null,
  };
}

export function buildCampaignCreatePayload(input: CampaignFormInput): UnknownRecord {
  const payload: UnknownRecord = {
    campaign_name: input.campaign_name,
  };

  if (input.campaign_type) payload.campaign_type = input.campaign_type;
  if (input.platform) payload.platform = input.platform;
  if (input.description) payload.description = input.description;
  if (input.influencer_handle) payload.influencer_handle = input.influencer_handle;
  if (input.target_aspects?.length) payload.target_aspects = input.target_aspects;
  if (input.target_regions?.length) payload.target_regions = input.target_regions;
  if (input.keywords?.length) payload.keywords = input.keywords;
  if (input.budget_dza && input.budget_dza.trim() !== "") {
    payload.budget_dza = asNumber(input.budget_dza);
  }
  if (input.start_date) payload.start_date = input.start_date;
  if (input.end_date) payload.end_date = input.end_date;

  return payload;
}

export function mapCampaignImpact(value: unknown): CampaignImpact {
  const record = asRecord(value);
  const phases = asRecord(record.phases);
  return {
    campaign_id: asString(record.campaign_id),
    campaign_name: asString(record.campaign_name) || null,
    phases: Object.fromEntries(
      Object.entries(phases).map(([phase, rawMetrics]) => {
        const metrics = asRecord(rawMetrics);
        return [
          phase,
          {
            nss: metrics.nss == null ? null : asNumber(metrics.nss),
            volume: asNumber(metrics.volume),
            aspect_breakdown: asNumberRecord(metrics.aspect_breakdown),
            sentiment_breakdown: asNumberRecord(metrics.sentiment_breakdown),
          },
        ];
      }),
    ),
    uplift_nss: record.uplift_nss == null ? null : asNumber(record.uplift_nss),
    uplift_volume_pct:
      record.uplift_volume_pct == null ? null : asNumber(record.uplift_volume_pct),
    is_reliable: Boolean(record.is_reliable),
    reliability_note: asString(record.reliability_note),
  };
}

export function mapAlert(value: unknown): Alert {
  const record = asRecord(value);
  const payload = asRecord(record.alert_payload);
  return {
    alert_id: asString(record.alert_id),
    client_id: asString(record.client_id) || null,
    watchlist_id: asString(record.watchlist_id) || null,
    alert_rule_id: asString(record.alert_rule_id) || null,
    title: asString(record.title),
    description: asString(record.description) || null,
    severity: asString(record.severity),
    status: asString(record.status),
    detected_at: asString(record.detected_at) || null,
    resolved_at: asString(record.resolved_at) || null,
    alert_payload: Object.keys(payload).length ? payload : undefined,
    dedup_key: asString(record.dedup_key) || null,
    navigation_url: asString(record.navigation_url) || null,
  };
}

export function mapWatchlist(value: unknown): Watchlist {
  const record = asRecord(value);
  return {
    watchlist_id: asString(record.watchlist_id),
    client_id: asString(record.client_id) || null,
    watchlist_name: asString(record.watchlist_name),
    description: asString(record.description) || null,
    scope_type: asString(record.scope_type) || null,
    filters: asRecord(record.filters),
    is_active: asNumber(record.is_active),
    created_at: asString(record.created_at) || null,
    updated_at: asString(record.updated_at) || null,
  };
}

export function mapWatchlistMetrics(value: unknown): WatchlistMetrics {
  const record = asRecord(value);
  const volumeCurrent = record.volume_current == null ? null : asNumber(record.volume_current);
  const volumePrevious = record.volume_previous == null ? null : asNumber(record.volume_previous);
  const explicitDelta = record.volume_delta == null ? null : asNumber(record.volume_delta);
  return {
    watchlist_id: asString(record.watchlist_id) || null,
    nss_current: record.nss_current == null ? null : asNumber(record.nss_current),
    delta_nss: record.delta_nss == null ? null : asNumber(record.delta_nss),
    volume_total: record.volume_total == null ? null : asNumber(record.volume_total),
    volume_current: volumeCurrent,
    volume_previous: volumePrevious,
    volume_delta:
      explicitDelta ??
      (volumeCurrent != null && volumePrevious != null ? volumeCurrent - volumePrevious : null),
    aspect_breakdown: asNumberRecord(record.aspect_breakdown),
    quick_insight: asString(record.quick_insight) || null,
    computed_at: asString(record.computed_at) || null,
  };
}

export function flattenProviderCatalog(value: unknown): ProviderOption[] {
  const record = asRecord(value);
  const providers = asRecord(record.providers);
  return Object.entries(providers).flatMap(([providerId, models]) =>
    asObjectArray(models).map((model) => ({
      provider_id: providerId,
      model_id: asString(model.id),
      label: asString(model.label),
      recommended: Boolean(model.recommended),
    })),
  );
}

export function mapContextPreview(value: unknown): ContextPreview {
  const record = asRecord(value);
  return {
    estimated_tokens: asNumber(record.estimated_tokens),
    nss_global: record.nss_global == null ? null : asNumber(record.nss_global),
    volume_total: asNumber(record.volume_total),
    active_alerts_count: asNumber(record.active_alerts_count),
    active_watchlists_count: asNumber(record.active_watchlists_count),
    recent_campaigns_count: asNumber(record.recent_campaigns_count),
    trigger: asString(record.trigger) || null,
  };
}

function mapRecommendationItem(value: unknown): RecommendationItem {
  const record = asRecord(value);
  return {
    title: asString(record.title),
    priority: asString(record.priority) || null,
    description: asString(record.description) || null,
    target_platform: asString(record.target_platform) || null,
    kpi_impact: asString(record.kpi_impact) || null,
    timing: asString(record.timing) || null,
  };
}

export function mapRecommendation(value: unknown): Recommendation {
  const record = asRecord(value);
  return {
    recommendation_id: asString(record.recommendation_id),
    client_id: asString(record.client_id) || null,
    trigger_type: asString(record.trigger_type) || null,
    trigger_id: asString(record.trigger_id) || null,
    analysis_summary: asString(record.analysis_summary) || null,
    recommendations: asObjectArray(record.recommendations).map(mapRecommendationItem),
    watchlist_priorities: asStringArray(record.watchlist_priorities),
    confidence_score:
      record.confidence_score == null ? null : asNumber(record.confidence_score),
    data_quality_note: asString(record.data_quality_note) || null,
    provider_used: asString(record.provider_used) || null,
    model_used: asString(record.model_used) || null,
    context_tokens: record.context_tokens == null ? null : asNumber(record.context_tokens),
    generation_ms: record.generation_ms == null ? null : asNumber(record.generation_ms),
    status: asString(record.status) || null,
    created_at: asString(record.created_at) || null,
  };
}

export function getPrimaryRecommendation(
  recommendation: Recommendation,
): RecommendationItem | undefined {
  return recommendation.recommendations[0];
}

export function mapExplorerSearchResults(value: unknown): SearchResult[] {
  const record = asRecord(value);
  return asObjectArray(record.results).map((item) => ({
    text: asString(item.text),
    score: asNumber(item.score),
    sentiment_label: asString(item.sentiment_label),
    aspect: asString(item.aspect),
    channel: asString(item.channel),
    source_url: asString(item.source_url),
  }));
}

function mapVerbatimItem(value: unknown): VerbatimItem {
  const record = asRecord(value);
  return {
    text: asString(record.text),
    sentiment_label: asString(record.sentiment_label),
    confidence: asNumber(record.confidence),
    channel: asString(record.channel),
    aspect: asString(record.aspect),
    wilaya: asString(record.wilaya),
    timestamp: asString(record.timestamp),
    source_url: asString(record.source_url),
  };
}

export function mapExplorerVerbatims(value: unknown): VerbatimsResponse {
  const record = asRecord(value);
  return {
    results: asObjectArray(record.results).map(mapVerbatimItem),
    total: asNumber(record.total),
    page: asNumber(record.page, 1),
    page_size: asNumber(record.page_size, 50),
    total_pages: asNumber(record.total_pages),
  };
}

export function mapAdminSource(value: unknown): Source {
  const record = asRecord(value);
  return {
    source_id: asString(record.source_id),
    client_id: asString(record.client_id) || null,
    source_name: asString(record.source_name),
    platform: asString(record.platform),
    source_type: asString(record.source_type),
    owner_type: asString(record.owner_type),
    auth_mode: asString(record.auth_mode) || null,
    config_json: asRecord(record.config_json),
    is_active: asNumber(record.is_active),
    sync_frequency_minutes: asNumber(record.sync_frequency_minutes),
    freshness_sla_hours: asNumber(record.freshness_sla_hours),
    last_sync_at: asString(record.last_sync_at) || null,
    created_at: asString(record.created_at) || null,
    updated_at: asString(record.updated_at) || null,
    last_sync_status: asString(record.last_sync_status) || null,
    last_sync_started_at: asString(record.last_sync_started_at) || null,
    last_records_fetched:
      record.last_records_fetched == null ? null : asNumber(record.last_records_fetched),
    last_records_inserted:
      record.last_records_inserted == null ? null : asNumber(record.last_records_inserted),
    last_records_failed:
      record.last_records_failed == null ? null : asNumber(record.last_records_failed),
    latest_health_score:
      record.latest_health_score == null ? null : asNumber(record.latest_health_score),
    latest_success_rate_pct:
      record.latest_success_rate_pct == null
        ? null
        : asNumber(record.latest_success_rate_pct),
    latest_health_computed_at: asString(record.latest_health_computed_at) || null,
    raw_document_count:
      record.raw_document_count == null ? null : asNumber(record.raw_document_count),
    normalized_count: record.normalized_count == null ? null : asNumber(record.normalized_count),
    enriched_count: record.enriched_count == null ? null : asNumber(record.enriched_count),
  };
}

export function mapAdminSyncRun(value: unknown): SyncRun {
  const record = asRecord(value);
  return {
    sync_run_id: asString(record.sync_run_id),
    source_id: asString(record.source_id),
    run_mode: asString(record.run_mode),
    status: asString(record.status),
    records_fetched: asNumber(record.records_fetched),
    records_inserted: asNumber(record.records_inserted),
    records_failed: asNumber(record.records_failed),
    error_message: asString(record.error_message) || null,
    started_at: asString(record.started_at),
    ended_at: asString(record.ended_at) || null,
    created_at: asString(record.created_at) || null,
    client_id: asString(record.client_id) || null,
    source_name: asString(record.source_name) || null,
    platform: asString(record.platform) || null,
  };
}

export function mapAdminHealthSnapshot(value: unknown): HealthSnapshot {
  const record = asRecord(value);
  return {
    snapshot_id: asString(record.snapshot_id),
    source_id: asString(record.source_id),
    health_score: asNumber(record.health_score),
    success_rate_pct:
      record.success_rate_pct == null ? null : asNumber(record.success_rate_pct),
    freshness_hours:
      record.freshness_hours == null ? null : asNumber(record.freshness_hours),
    records_fetched_avg:
      record.records_fetched_avg == null ? null : asNumber(record.records_fetched_avg),
    computed_at: asString(record.computed_at),
    client_id: asString(record.client_id) || null,
    source_name: asString(record.source_name) || null,
    platform: asString(record.platform) || null,
  };
}
