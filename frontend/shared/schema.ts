/**
 * RamyPulse frontend types — aligned with api/schemas.py Pydantic models
 * and core manager return shapes.
 */

// ---------------------------------------------------------------------------
// Dashboard (matches api/routers/dashboard.py responses)
// ---------------------------------------------------------------------------

export interface DashboardSummary {
  health_score: number;
  health_trend: "up" | "down" | "flat";
  nss_progress_pts: number;
  summary_text: string;
}

export interface DashboardAlert {
  alert_id: string;
  severity: string;
  title: string;
  description: string;
  created_at: string;
}

export interface DashboardAction {
  recommendation_id: string;
  title: string;
  priority: string;
  target_platform: string;
}

// ---------------------------------------------------------------------------
// Campaigns (matches CampaignResponse, CampaignImpact in schemas.py)
// ---------------------------------------------------------------------------

export interface Campaign {
  campaign_id: string;
  client_id?: string;
  campaign_name: string;
  campaign_type?: string;
  platform?: string;
  description?: string;
  influencer_handle?: string;
  influencer_tier?: string;
  target_segment?: string;
  target_aspects: string[];
  target_regions: string[];
  keywords: string[];
  budget_dza?: number;
  start_date?: string;
  end_date?: string;
  pre_window_days?: number;
  post_window_days?: number;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PhaseMetrics {
  nss: number | null;
  volume: number;
  aspect_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
}

export interface CampaignImpact {
  campaign_id: string;
  campaign_name?: string;
  phases: {
    pre: PhaseMetrics;
    active: PhaseMetrics;
    post: PhaseMetrics;
  };
  uplift_nss: number | null;
  uplift_volume_pct: number | null;
  is_reliable: boolean;
  reliability_note: string;
}

export interface CreateCampaignPayload {
  campaign_name: string;
  campaign_type?: string;
  platform?: string;
  description?: string;
  influencer_handle?: string;
  target_aspects?: string[];
  target_regions?: string[];
  keywords?: string[];
  budget_dza?: number;
  start_date?: string;
  end_date?: string;
}

// ---------------------------------------------------------------------------
// Alerts (matches core/alerts/alert_manager.py _row_to_alert dict)
// ---------------------------------------------------------------------------

export interface Alert {
  alert_id: string;
  client_id?: string;
  watchlist_id?: string;
  alert_rule_id?: string;
  title: string;
  description?: string;
  severity: string;
  status: string;
  detected_at?: string;
  resolved_at?: string;
  alert_payload?: Record<string, unknown>;
  dedup_key?: string;
  navigation_url?: string;
}

// ---------------------------------------------------------------------------
// Watchlists (matches core/watchlists/watchlist_manager.py dict)
// ---------------------------------------------------------------------------

export interface Watchlist {
  watchlist_id: string;
  client_id?: string;
  watchlist_name: string;
  description?: string;
  scope_type?: string;
  filters?: Record<string, unknown>;
  is_active: number;
  created_at?: string;
  updated_at?: string;
}

export interface WatchlistMetrics {
  watchlist_id: string;
  nss_current?: number;
  delta_nss?: number;
  volume_total?: number;
  volume_delta?: number;
  computed_at?: string;
}

// ---------------------------------------------------------------------------
// Recommendations (matches RecommendationResponse in schemas.py)
// ---------------------------------------------------------------------------

export interface RecommendationContext {
  estimated_tokens: number;
  nss_global: number | null;
  volume_total: number;
  active_alerts_count: number;
  active_watchlists_count: number;
  recent_campaigns_count: number;
}

export interface RecommendationItem {
  title: string;
  priority: string;
  description?: string;
  target_platform?: string;
  kpi_impact?: string;
  timing?: string;
}

export interface Recommendation {
  recommendation_id: string;
  client_id?: string;
  trigger_type?: string;
  trigger_id?: string;
  analysis_summary?: string;
  recommendations: RecommendationItem[];
  watchlist_priorities: unknown[];
  confidence_score?: number;
  data_quality_note?: string;
  provider_used?: string;
  model_used?: string;
  context_tokens?: number;
  generation_ms?: number;
  status?: string;
  created_at?: string;
}

export interface GenerateRecommendationsPayload {
  trigger_type: string;
  provider: string;
  model: string;
  api_key?: string;
}

// ---------------------------------------------------------------------------
// Explorer (matches SearchResponse, VerbatimResponse in schemas.py)
// ---------------------------------------------------------------------------

export interface SearchResult {
  text: string;
  score: number;
  sentiment_label: string;
  aspect: string;
  channel: string;
  source_url: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface VerbatimItem {
  text: string;
  sentiment_label: string;
  confidence: number;
  channel: string;
  aspect: string;
  wilaya: string;
  timestamp: string;
  source_url: string;
}

export interface VerbatimsResponse {
  results: VerbatimItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

// ---------------------------------------------------------------------------
// Admin Sources
// ---------------------------------------------------------------------------

export interface Source {
  source_id: string;
  client_id?: string;
  source_name: string;
  platform: string;
  source_type: string;
  owner_type: string;
  is_active: boolean;
  config_json?: Record<string, unknown>;
  sync_frequency_minutes?: number;
  freshness_sla_hours?: number;
}

export interface SyncRun {
  run_id: string;
  source_id: string;
  run_mode: string;
  status: string;
  records_fetched: number;
  records_inserted: number;
  errors_count: number;
  started_at: string;
  finished_at?: string;
}

export interface HealthSnapshot {
  snapshot_id: string;
  source_id: string;
  health_level: string;
  message: string;
  computed_at: string;
}
