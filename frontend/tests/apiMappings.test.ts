import assert from "node:assert/strict";
import test from "node:test";

import * as apiMappings from "../client/src/lib/apiMappings";
import {
  buildCampaignCreatePayload,
  flattenProviderCatalog,
  getPrimaryRecommendation,
  mapAdminHealthSnapshot,
  mapAdminSource,
  mapAdminSyncRun,
  mapAlert,
  mapCampaign,
  mapCampaignImpact,
  mapContextPreview,
  mapDashboardActions,
  mapDashboardAlerts,
  mapDashboardSummary,
  mapExplorerSearchResults,
  mapExplorerVerbatims,
  mapRecommendation,
  mapWatchlist,
  mapWatchlistMetrics,
} from "../client/src/lib/apiMappings";

const adminSourcesViewModel = await import("../client/src/lib/adminSourcesViewModel").catch(
  () => ({}) as Record<string, unknown>,
);

test("mapDashboardSummary keeps the real API contract fields", () => {
  const summary = mapDashboardSummary({
    health_score: 61,
    health_trend: "up",
    nss_progress_pts: 3.5,
    summary_text: "Le NSS remonte.",
    total_mentions: 42,
    period: "du 2026-04-01 au 2026-04-03",
    regional_distribution: [{ wilaya: "Alger", pct: 60 }],
    product_performance: [{ product: "Ramy Citron", trend_pct: 12.4, relative_volume: 78 }],
  });

  assert.deepEqual(summary, {
    health_score: 61,
    health_trend: "up",
    nss_progress_pts: 3.5,
    summary_text: "Le NSS remonte.",
    total_mentions: 42,
    period: "du 2026-04-01 au 2026-04-03",
    regional_distribution: [{ wilaya: "Alger", pct: 60 }],
    product_performance: [{ product: "Ramy Citron", trend_pct: 12.4, relative_volume: 78 }],
  });
});

test("mapDashboardAlerts and actions normalize list wrappers", () => {
  const alerts = mapDashboardAlerts({
    critical_alerts: [
      {
        alert_id: "alt_1",
        severity: "critical",
        title: "Alerte",
        description: "Description",
        created_at: "2026-04-03T10:00:00Z",
      },
    ],
  });
  const actions = mapDashboardActions({
    top_actions: [
      {
        recommendation_id: "rec_1",
        title: "Action IA",
        priority: "high",
        target_platform: "Toutes",
        description: "Description detaillee",
        confidence_score: 0.84,
        cta_label: "EXECUTER",
        icon: "rocket_launch",
      },
    ],
  });

  assert.equal(alerts[0]?.alert_id, "alt_1");
  assert.equal(actions[0]?.recommendation_id, "rec_1");
  assert.equal(actions[0]?.confidence_score, 0.84);
});

test("mapCampaign and buildCampaignCreatePayload use the FastAPI field names", () => {
  const campaign = mapCampaign({
    campaign_id: "camp_1",
    client_id: "ramy_client_001",
    campaign_name: "Summer Push",
    campaign_type: "influencer",
    platform: "instagram",
    influencer_handle: "@numidia",
    target_aspects: ["taste"],
    target_regions: ["Alger"],
    keywords: ["#ramy"],
    budget_dza: 500000,
    start_date: "2026-04-01",
    end_date: "2026-04-30",
    status: "active",
  });

  assert.equal(campaign.campaign_name, "Summer Push");
  assert.equal(campaign.influencer_handle, "@numidia");

  const payload = buildCampaignCreatePayload({
    campaign_name: "Summer Push",
    campaign_type: "influencer",
    platform: "instagram",
    influencer_handle: "@numidia",
    target_aspects: ["taste"],
    target_regions: ["Alger"],
    keywords: ["#ramy"],
    budget_dza: "500000",
    start_date: "2026-04-01",
    end_date: "2026-04-30",
  });

  assert.deepEqual(payload, {
    campaign_name: "Summer Push",
    campaign_type: "influencer",
    platform: "instagram",
    influencer_handle: "@numidia",
    target_aspects: ["taste"],
    target_regions: ["Alger"],
    keywords: ["#ramy"],
    budget_dza: 500000,
    start_date: "2026-04-01",
    end_date: "2026-04-30",
  });
});

test("mapCampaignImpact preserves the phased impact structure", () => {
  const impact = mapCampaignImpact({
    campaign_id: "camp_1",
    campaign_name: "Summer Push",
    phases: {
      pre: { nss: 12, volume: 10, aspect_breakdown: {}, sentiment_breakdown: {} },
      active: { nss: 24, volume: 20, aspect_breakdown: {}, sentiment_breakdown: {} },
      post: { nss: 18, volume: 15, aspect_breakdown: {}, sentiment_breakdown: {} },
    },
    uplift_nss: 12,
    uplift_volume_pct: 100,
    is_reliable: true,
    reliability_note: "",
  });

  assert.equal(impact.phases.active.nss, 24);
  assert.equal(impact.uplift_nss, 12);
});

test("mapAlert preserves real backend statuses and severities", () => {
  const alert = mapAlert({
    alert_id: "alt_1",
    client_id: "ramy_client_001",
    title: "Disponibilite",
    description: "Stock faible",
    severity: "high",
    status: "acknowledged",
    detected_at: "2026-04-03T11:00:00Z",
    alert_payload: { metric: "volume" },
    navigation_url: "/watchlists/w1",
  });

  assert.equal(alert.alert_id, "alt_1");
  assert.equal(alert.severity, "high");
  assert.equal(alert.status, "acknowledged");
  assert.deepEqual(alert.alert_payload, { metric: "volume" });
});

test("mapWatchlist and metrics preserve the manager/core shapes", () => {
  const watchlist = mapWatchlist({
    watchlist_id: "wl_1",
    watchlist_name: "Disponibilite Oran",
    description: "Surveillance",
    scope_type: "product",
    filters: { aspect: "availability" },
    is_active: 1,
  });

  const metrics = mapWatchlistMetrics({
    watchlist_id: "wl_1",
    nss_current: 14.5,
    delta_nss: 3.2,
    volume_total: 120,
    aspect_breakdown: { availability: 0.4 },
    computed_at: "2026-04-03T11:00:00Z",
  });

  assert.equal(watchlist.watchlist_name, "Disponibilite Oran");
  assert.equal(metrics.nss_current, 14.5);
  assert.deepEqual(metrics.aspect_breakdown, { availability: 0.4 });
});

test("provider catalog and context preview follow the recommendations API", () => {
  const providers = flattenProviderCatalog({
    providers: {
      ollama_local: [{ id: "qwen2.5:14b", label: "Qwen 14B", recommended: true }],
      google_gemini: [{ id: "gemini-2.5-flash", label: "Gemini Flash", recommended: false }],
    },
  });

  const context = mapContextPreview({
    estimated_tokens: 1200,
    nss_global: 22.5,
    volume_total: 340,
    active_alerts_count: 2,
    active_watchlists_count: 4,
    recent_campaigns_count: 1,
    trigger: "manual",
    estimated_cost_usd: 0.36,
  });

  assert.equal(providers.length, 2);
  assert.equal(providers[0]?.provider_id, "ollama_local");
  assert.equal(context.volume_total, 340);
  assert.equal(context.estimated_cost_usd, 0.36);
});

test("mapRecommendation preserves nested recommendation items and provider metadata", () => {
  const recommendation = mapRecommendation({
    recommendation_id: "rec_1",
    trigger_type: "manual",
    analysis_summary: "Prioriser la disponibilite a Oran",
    recommendations: [
      { title: "Redistribuer le stock", priority: "high", description: "Action terrain" },
      { title: "Alerter le retail", priority: "medium", description: "Escalade" },
    ],
    watchlist_priorities: ["Disponibilite Oran"],
    confidence_score: 0.87,
    provider_used: "ollama_local",
    model_used: "qwen2.5:14b",
    status: "active",
    created_at: "2026-04-03T10:00:00Z",
  });

  assert.equal(recommendation.recommendation_id, "rec_1");
  assert.equal(recommendation.recommendations.length, 2);
  assert.equal(getPrimaryRecommendation(recommendation)?.title, "Redistribuer le stock");
});

test("mapExplorerSearchResults and mapExplorerVerbatims use the real explorer contracts", () => {
  const results = mapExplorerSearchResults({
    query: "ramy",
    total: 1,
    results: [
      {
        text: "Le gout est bon",
        score: 0.91,
        sentiment_label: "positive",
        aspect: "taste",
        channel: "facebook",
        source_url: "https://example.test/post/1",
      },
    ],
  });
  const verbatims = mapExplorerVerbatims({
    total: 1,
    page: 1,
    page_size: 50,
    total_pages: 1,
    results: [
      {
        text: "Le gout est bon",
        sentiment_label: "positive",
        confidence: 0.88,
        channel: "facebook",
        aspect: "taste",
        wilaya: "Alger",
        timestamp: "2026-04-03T12:00:00Z",
        source_url: "https://example.test/post/1",
      },
    ],
  });

  assert.equal(results[0]?.text, "Le gout est bon");
  assert.equal(verbatims.results[0]?.wilaya, "Alger");
});

test("mapAdminSource, run and snapshot use platform service field names", () => {
  const source = mapAdminSource({
    source_id: "src_1",
    client_id: "ramy_client_001",
    source_name: "Facebook Ramy",
    platform: "facebook",
    source_type: "managed_page",
    owner_type: "owned",
    auth_mode: "api",
    config_json: { page_id: "123" },
    is_active: 1,
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    last_sync_status: "success",
    latest_health_score: 88,
    raw_document_count: 12,
    normalized_count: 11,
    enriched_count: 10,
  });

  const run = mapAdminSyncRun({
    sync_run_id: "run_1",
    source_id: "src_1",
    run_mode: "manual",
    status: "failed_downstream",
    records_fetched: 12,
    records_inserted: 12,
    records_failed: 0,
    error_message: "Normalizer error",
    started_at: "2026-04-03T11:00:00Z",
    ended_at: "2026-04-03T11:05:00Z",
  });

  const snapshot = mapAdminHealthSnapshot({
    snapshot_id: "snap_1",
    source_id: "src_1",
    health_score: 82,
    success_rate_pct: 90,
    freshness_hours: 2,
    records_fetched_avg: 14,
    computed_at: "2026-04-03T12:00:00Z",
  });

  assert.equal(source.source_name, "Facebook Ramy");
  assert.equal(run.sync_run_id, "run_1");
  assert.equal(snapshot.health_score, 82);
});

test("admin mappings expose governance and admin-ops contracts", () => {
  assert.equal(typeof apiMappings.mapCredentialSummary, "function");
  assert.equal(typeof apiMappings.mapCampaignPost, "function");
  assert.equal(typeof apiMappings.mapCampaignEngagementSummary, "function");
  assert.equal(typeof apiMappings.mapSchedulerTickResult, "function");

  const source = mapAdminSource({
    source_id: "src_governed",
    source_name: "Instagram Ramy",
    platform: "instagram",
    source_type: "managed_page",
    owner_type: "owned",
    config_json: {},
    is_active: 1,
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    source_purpose: "campaign_engagement",
    source_priority: 2,
    coverage_key: "campaign:instagram:ramy-official",
    credential_id: "cred_123",
  });

  assert.equal(source.source_purpose, "campaign_engagement");
  assert.equal(source.source_priority, 2);
  assert.equal(source.coverage_key, "campaign:instagram:ramy-official");
  assert.equal(source.credential_id, "cred_123");

  const credential = (apiMappings as any).mapCredentialSummary({
    credential_id: "cred_123",
    entity_type: "brand",
    entity_name: "Ramy Official",
    platform: "instagram",
    account_id: "acct_1",
    app_id: "app_1",
    is_active: 1,
    created_at: "2026-04-04T10:00:00Z",
    updated_at: "2026-04-04T11:00:00Z",
  });
  assert.equal(credential.entity_name, "Ramy Official");
  assert.equal(credential.is_active, true);

  const post = (apiMappings as any).mapCampaignPost({
    post_id: "post_1",
    campaign_id: "camp_1",
    platform: "instagram",
    post_platform_id: "ig-post-1",
    post_url: "https://instagram.com/p/ig-post-1",
    entity_type: "brand",
    entity_name: "Ramy Official",
    credential_id: "cred_123",
    added_at: "2026-04-04T12:00:00Z",
  });
  assert.equal(post.post_platform_id, "ig-post-1");
  assert.equal(post.credential_id, "cred_123");

  const engagement = (apiMappings as any).mapCampaignEngagementSummary({
    campaign_id: "camp_1",
    post_count: 1,
    metrics_collected_count: 1,
    totals: { likes: 10, comments: 4, shares: 2, views: 100, reach: 90, impressions: 120, saves: 3 },
    engagement_rate: 17.78,
    engagement_rate_note: "Basé sur portée réelle collectée via API",
    roi_pct: null,
    roi_note: "Non calculable",
    budget_dza: 100000,
    revenue_dza: null,
    signal_count: 1,
    sentiment_breakdown: { negatif: 1 },
    negative_aspects: ["gout"],
    top_performer: {
      post_id: "post_1",
      platform: "instagram",
      post_url: "https://instagram.com/p/ig-post-1",
      entity_name: "Ramy Official",
      engagement: 16,
      reach: 90,
      signal_count: 1,
      sentiment_breakdown: { negatif: 1 },
      negative_aspects: ["gout"],
    },
    posts: [],
  });
  assert.equal(engagement.signal_count, 1);
  assert.equal(engagement.top_performer?.negative_aspects[0], "gout");

  const tick = (apiMappings as any).mapSchedulerTickResult({
    tick_at: "2026-04-04T12:00:00Z",
    groups_processed: 1,
    sources_scheduled: 1,
    groups: [
      {
        coverage_key: "owned:instagram:ramy-official",
        winner_source_id: "src_1",
        winner_status: "success",
        attempts: [
          {
            source_id: "src_1",
            source_priority: 1,
            status: "success",
            records_fetched: 5,
            records_inserted: 5,
            records_failed: 0,
          },
        ],
      },
    ],
  });
  assert.equal(tick.groups[0]?.attempts[0]?.records_inserted, 5);
});

test("admin sources view model resolves view and groups scheduler sources", () => {
  assert.equal(typeof (adminSourcesViewModel as any).readAdminSourcesView, "function");
  assert.equal(typeof (adminSourcesViewModel as any).buildSchedulerGroups, "function");

  assert.equal(
    (adminSourcesViewModel as any).readAdminSourcesView("#/admin-sources?view=credentials"),
    "credentials",
  );
  assert.equal(
    (adminSourcesViewModel as any).readAdminSourcesView("#/admin-sources?view=unknown"),
    "sources",
  );

  const groups = (adminSourcesViewModel as any).buildSchedulerGroups(
    [
      {
        source_id: "src_b",
        source_name: "Secondary",
        platform: "instagram",
        source_type: "managed_page",
        owner_type: "owned",
        config_json: {},
        is_active: 1,
        sync_frequency_minutes: 60,
        freshness_sla_hours: 24,
        source_purpose: "owned_content",
        source_priority: 2,
        coverage_key: "owned:instagram:ramy",
        credential_id: null,
        last_sync_at: "2026-04-04T11:45:00Z",
      },
      {
        source_id: "src_a",
        source_name: "Primary",
        platform: "instagram",
        source_type: "managed_page",
        owner_type: "owned",
        config_json: {},
        is_active: 1,
        sync_frequency_minutes: 60,
        freshness_sla_hours: 24,
        source_purpose: "owned_content",
        source_priority: 1,
        coverage_key: "owned:instagram:ramy",
        credential_id: "cred_1",
        last_sync_at: "2026-04-04T10:00:00Z",
      },
    ],
    new Date("2026-04-04T12:00:00Z"),
  );

  assert.equal(groups.length, 1);
  assert.equal(groups[0]?.coverageKey, "owned:instagram:ramy");
  assert.equal(groups[0]?.sources[0]?.sourceId, "src_a");
  assert.equal(groups[0]?.sources[0]?.isDue, true);
  assert.equal(groups[0]?.sources[1]?.isDue, false);
});
