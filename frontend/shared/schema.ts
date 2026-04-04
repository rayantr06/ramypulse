// RamyPulse frontend shared types aligned to the FastAPI contracts.

// System
export interface ApiStatus {
  api_status: string;
  db_status: string;
  latency_ms: number;
}

// Dashboard
export interface DashboardSummary {
  health_score: number;
  health_trend: "up" | "down" | "flat";
  nss_progress_pts: number;
  summary_text: string;
  total_mentions: number;
  period: string;
  regional_distribution: Array<{ wilaya: string; pct: number }>;
  product_performance: Array<{ product: string; trend_pct: number; relative_volume: number }>;
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
  description?: string;
  confidence_score?: number | null;
  cta_label?: string;
  icon?: string;
}

// Campaigns
export interface PhaseMetrics {
  nss: number | null;
  volume: number;
  aspect_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
}

export interface Campaign {
  campaign_id: string;
  client_id?: string | null;
  campaign_name: string;
  campaign_type?: string | null;
  platform?: string | null;
  description?: string | null;
  influencer_handle?: string | null;
  influencer_tier?: string | null;
  target_segment?: string | null;
  target_aspects: string[];
  target_regions: string[];
  keywords: string[];
  budget_dza?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  pre_window_days?: number | null;
  post_window_days?: number | null;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CampaignImpact {
  campaign_id: string;
  campaign_name?: string | null;
  phases: Record<string, PhaseMetrics>;
  uplift_nss?: number | null;
  uplift_volume_pct?: number | null;
  is_reliable: boolean;
  reliability_note: string;
}

export interface CampaignStats {
  quarterly_budget_committed: number;
  quarterly_budget_allocation: number;
  quarter_label: string;
}

// Alerts
export interface Alert {
  alert_id: string;
  client_id?: string | null;
  watchlist_id?: string | null;
  alert_rule_id?: string | null;
  title: string;
  description?: string | null;
  severity: string;
  status: string;
  detected_at?: string | null;
  resolved_at?: string | null;
  alert_payload?: Record<string, unknown>;
  dedup_key?: string | null;
  navigation_url?: string | null;
}

// Watchlists
export interface Watchlist {
  watchlist_id: string;
  client_id?: string | null;
  watchlist_name: string;
  description?: string | null;
  scope_type?: string | null;
  filters: Record<string, unknown>;
  is_active: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WatchlistMetrics {
  watchlist_id?: string | null;
  nss_current?: number | null;
  delta_nss?: number | null;
  volume_total?: number | null;
  volume_current?: number | null;
  volume_previous?: number | null;
  volume_delta?: number | null;
  aspect_breakdown: Record<string, number>;
  quick_insight?: string | null;
  computed_at?: string | null;
}

// Recommendations
export interface RecommendationItem {
  title: string;
  priority?: string | null;
  description?: string | null;
  target_platform?: string | null;
  kpi_impact?: string | null;
  timing?: string | null;
}

export interface Recommendation {
  recommendation_id: string;
  client_id?: string | null;
  trigger_type?: string | null;
  trigger_id?: string | null;
  analysis_summary?: string | null;
  recommendations: RecommendationItem[];
  watchlist_priorities: string[];
  confidence_score?: number | null;
  data_quality_note?: string | null;
  provider_used?: string | null;
  model_used?: string | null;
  context_tokens?: number | null;
  generation_ms?: number | null;
  status?: string | null;
  created_at?: string | null;
}

export interface ContextPreview {
  estimated_tokens: number;
  nss_global?: number | null;
  volume_total: number;
  active_alerts_count: number;
  active_watchlists_count: number;
  recent_campaigns_count: number;
  trigger?: string | null;
}

export interface ProviderOption {
  provider_id: string;
  model_id: string;
  label: string;
  recommended: boolean;
}

// Explorer
export interface SearchResult {
  text: string;
  score: number;
  sentiment_label: string;
  aspect: string;
  channel: string;
  source_url: string;
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
  total_pages: number;
}

// Admin sources
export interface Source {
  source_id: string;
  client_id?: string | null;
  source_name: string;
  platform: string;
  source_type: string;
  owner_type: string;
  auth_mode?: string | null;
  config_json: Record<string, unknown>;
  is_active: number;
  sync_frequency_minutes: number;
  freshness_sla_hours: number;
  last_sync_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_sync_status?: string | null;
  last_sync_started_at?: string | null;
  last_records_fetched?: number | null;
  last_records_inserted?: number | null;
  last_records_failed?: number | null;
  latest_health_score?: number | null;
  latest_success_rate_pct?: number | null;
  latest_health_computed_at?: string | null;
  raw_document_count?: number | null;
  normalized_count?: number | null;
  enriched_count?: number | null;
}

export interface SyncRun {
  sync_run_id: string;
  source_id: string;
  run_mode: string;
  status: string;
  records_fetched: number;
  records_inserted: number;
  records_failed: number;
  error_message?: string | null;
  started_at: string;
  ended_at?: string | null;
  created_at?: string | null;
  client_id?: string | null;
  source_name?: string | null;
  platform?: string | null;
}

export interface HealthSnapshot {
  snapshot_id: string;
  source_id: string;
  health_score: number;
  success_rate_pct?: number | null;
  freshness_hours?: number | null;
  records_fetched_avg?: number | null;
  computed_at: string;
  client_id?: string | null;
  source_name?: string | null;
  platform?: string | null;
}
