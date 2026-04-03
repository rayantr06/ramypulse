// RamyPulse shared types — frontend only (no DB needed, API is FastAPI backend)

// Dashboard
export interface DashboardSummary {
  nss_score: number;
  nss_trend: number;
  total_mentions: number;
  period: string;
  regional_distribution: Array<{ wilaya: string; pct: number }>;
  product_performance: Array<{ product: string; trend_pct: number; relative_volume: number }>;
}

export interface DashboardAlert {
  id: string;
  title: string;
  description: string;
  severity: "URGENT" | "ANALYSE" | "SYSTÈME";
  timestamp: string;
  icon: string;
}

export interface DashboardAction {
  id: string;
  title: string;
  description: string;
  confidence: number;
  icon: string;
  cta_label: string;
}

// Explorer
export interface SearchResult {
  id: string;
  source: string;
  content: string;
  relevance_score: number;
  sentiment: string;
  wilaya: string;
  created_at: string;
}

export interface Verbatim {
  id: string;
  date: string;
  time: string;
  source: string;
  aspect: string;
  sentiment: string;
  wilaya: string;
  text: string;
}

export interface VerbatimsResponse {
  items: Verbatim[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Campaigns
export interface Campaign {
  id: string;
  name: string;
  type: string;
  platform: string;
  influencer: string;
  budget_dza: number;
  start_date: string;
  end_date: string;
  keywords: string[];
  status: "ACTIVE" | "PLANIFIÉE" | "TERMINÉE" | "ANNULÉE";
  impact_nss?: number;
}

export interface CampaignImpact {
  pre_campaign_nss: number;
  during_campaign_nss: number;
  post_campaign_nss: number;
  uplift_pct: number;
  retention_pct: number;
  ai_insight: string;
}

export interface CreateCampaignPayload {
  name: string;
  type: string;
  platform: string;
  influencer: string;
  budget_dza: number;
  start_date: string;
  end_date: string;
  keywords: string[];
}

// Alerts
export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: "CRITIQUE" | "HAUTE" | "MOYENNE" | "BASSE";
  status: "NOUVEAU" | "RECONNU" | "EN_COURS" | "RÉSOLU";
  location: string;
  estimated_impact: string;
  detected_at: string;
  social_excerpts: Array<{ author: string; platform: string; text: string }>;
}

// Watchlists
export interface Watchlist {
  id: string;
  name: string;
  description: string;
  scope: "RÉGION" | "CANAL" | "PRODUIT";
  is_active: boolean;
  owners: string[];
}

export interface WatchlistMetrics {
  nss_score: number;
  nss_delta: number;
  volume: number;
  volume_delta: number;
  aspects: Array<{ name: string; score: number; is_negative?: boolean }>;
  quick_insight: string;
  last_updated: string;
}

// Recommendations
export interface RecommendationContext {
  nss_global: number;
  volume: number;
  active_alerts: number;
  last_run: string;
}

export interface Recommendation {
  id: string;
  run_id: string;
  priority: "URGENT" | "MOYEN" | "BAS";
  title: string;
  rationale: string;
  target: string;
  timing: string;
  kpi_impact: string;
  status: "ACTIVE" | "ARCHIVED" | "APPLIED";
  created_at: string;
  confidence: number;
  provider: string;
  model: string;
  summary: string;
}

export interface GenerateRecommendationsPayload {
  trigger_type: string;
  provider: string;
  model: string;
}

// Admin Sources
export interface Source {
  id: string;
  name: string;
  platform: string;
  owner_type: "Owned" | "Market" | "Competitor";
  health_pct: number;
  is_active: boolean;
  last_sync: string;
  config_json: string;
  frequency_min: number;
  sla_hours: number;
}

export interface SyncRun {
  id: string;
  source_id: string;
  mode: string;
  status: "SUCCESS" | "FAILURE" | "RUNNING";
  fetched: number;
  inserted: number;
  errors: number;
  started_at: string;
}

export interface HealthSnapshot {
  id: string;
  source_id: string;
  level: "EXCELLENT" | "WARNING" | "ERROR";
  message: string;
  timestamp: string;
}

export interface PipelineTrace {
  source_count: number;
  raw_count: number;
  normalized_count: number;
  enriched_count: number;
}
