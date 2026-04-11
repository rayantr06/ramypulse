import { expect, test, type Page } from "@playwright/test";

const TENANT_STORAGE_KEY = "ramypulse.activeTenantId";
const DEMO_TENANT_ID = "demo-expo-2026";

const dashboardSummaryPayload = {
  health_score: 72,
  health_trend: "up",
  nss_progress_pts: 4,
  summary_text: "Sentiment global en hausse sur la dernière semaine.",
  total_mentions: 1247,
  period: "7 derniers jours",
  regional_distribution: [
    { wilaya: "alger", pct: 42 },
    { wilaya: "oran", pct: 28 },
    { wilaya: "constantine", pct: 18 },
  ],
  product_performance: [
    { product: "ramy_citron", trend_pct: 8, relative_volume: 45 },
    { product: "ramy_orange", trend_pct: -3, relative_volume: 32 },
  ],
};

const dashboardAlertsPayload = {
  critical_alerts: [
    {
      alert_id: "alert_demo_1",
      severity: "critical",
      title: "Baisse critique du goût Oran",
      description: "NSS goût en chute de -18 pts sur 7 jours.",
      created_at: "2026-04-10T09:00:00Z",
    },
  ],
};

const dashboardActionsPayload = {
  top_actions: [
    {
      recommendation_id: "rec_demo_1",
      title: "Renforcer contrôle qualité Oran",
      priority: "high",
      target_platform: "production",
      description: "Action corrective recommandée suite à la baisse NSS.",
      confidence_score: 0.87,
      cta_label: "VOIR DÉTAILS",
      icon: "rocket_launch",
    },
  ],
};

const apiStatusPayload = {
  api_status: "healthy",
  db_status: "healthy",
  latency_ms: 42,
};

const alertsPayload = [
  {
    alert_id: "alert_e2e_1",
    client_id: DEMO_TENANT_ID,
    title: "Spike négatif goût Alger",
    description: "Volume critique de commentaires négatifs détecté.",
    severity: "critical",
    status: "new",
    detected_at: "2026-04-10T08:30:00Z",
    alert_payload: {
      value: -12,
      wilaya: "alger",
      social_excerpts: [
        {
          author: "user123",
          platform: "facebook",
          text: "Le goût a changé, c'est plus comme avant",
        },
      ],
    },
    navigation_url: null,
  },
  {
    alert_id: "alert_e2e_2",
    client_id: DEMO_TENANT_ID,
    title: "Rupture stock Constantine",
    description: "Signalements de rupture en hausse.",
    severity: "high",
    status: "acknowledged",
    detected_at: "2026-04-09T14:00:00Z",
    alert_payload: { metric: "DISPONIBILITÉ", region: "constantine" },
    navigation_url: null,
  },
];

const campaignsPayload = [
  {
    campaign_id: "camp_demo_1",
    client_id: DEMO_TENANT_ID,
    campaign_name: "Lancement Ramy Citron 2026",
    campaign_type: "product_launch",
    platform: "instagram",
    description: "Campagne de lancement du nouveau Ramy Citron.",
    influencer_handle: "@ramy.citron",
    target_aspects: ["gout"],
    target_regions: ["Alger", "Oran"],
    keywords: ["ramy", "citron"],
    budget_dza: 500000,
    revenue_dza: null,
    start_date: "2026-04-01",
    end_date: "2026-04-30",
    status: "active",
    created_at: "2026-03-28T10:00:00Z",
    updated_at: "2026-03-28T10:00:00Z",
  },
];

const campaignOverviewPayload = {
  quarterly_budget_committed: 500000,
  quarterly_budget_allocation: 1000000,
  quarter_label: "Q2 2026",
  active_campaigns_count: 1,
  top_performer: {
    campaign_id: "camp_demo_1",
    campaign_name: "Lancement Ramy Citron 2026",
    influencer_handle: "@ramy.citron",
    platform: "instagram",
    status: "active",
    budget_dza: 500000,
    roi_pct: 12.5,
    engagement_rate: 3.2,
    signal_count: 18,
    sentiment_breakdown: {
      positive: 12,
      neutral: 4,
      negative: 2,
    },
    negative_aspects: ["prix"],
    selection_basis: "roi_pct",
  },
};

const campaignImpactPayload = {
  campaign_id: "camp_demo_1",
  campaign_name: "Lancement Ramy Citron 2026",
  phases: {
    pre: {
      nss: 54,
      volume: 120,
      aspect_breakdown: { gout: 54 },
      sentiment_breakdown: { positif: 62, neutre: 25, negatif: 13 },
    },
    active: {
      nss: 68,
      volume: 180,
      aspect_breakdown: { gout: 68 },
      sentiment_breakdown: { positif: 71, neutre: 18, negatif: 11 },
    },
    post: {
      nss: 64,
      volume: 140,
      aspect_breakdown: { gout: 64 },
      sentiment_breakdown: { positif: 68, neutre: 20, negatif: 12 },
    },
  },
  uplift_nss: 14,
  uplift_volume_pct: 50,
  is_reliable: true,
  reliability_note: "Impact mesuré sur un corpus consolidé.",
};

const adminSourcesPayload = [
  {
    source_id: "src_e2e_1",
    client_id: DEMO_TENANT_ID,
    source_name: "FB Ramy Officiel",
    platform: "facebook",
    source_type: "managed_page",
    owner_type: "owned",
    auth_mode: "api",
    is_active: 1,
    latest_health_score: 85,
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    config_json: { fetch_mode: "snapshot" },
    source_purpose: "owned_content",
    source_priority: 1,
    coverage_key: "ramy_fb",
    credential_id: "cred_e2e_1",
    raw_document_count: 1200,
    normalized_count: 1180,
    enriched_count: 1100,
    last_sync_status: "completed",
    last_sync_at: "2026-04-10T12:00:00Z",
    last_sync_started_at: "2026-04-10T11:55:00Z",
    created_at: "2026-04-01T08:00:00Z",
    updated_at: "2026-04-10T12:00:00Z",
  },
];

const credentialsPayload = [
  {
    credential_id: "cred_e2e_1",
    entity_type: "brand",
    entity_name: "Ramy",
    platform: "facebook",
    account_id: "ramy_official",
    app_id: "ramy-facebook-app",
    is_active: 1,
    created_at: "2026-04-01T08:00:00Z",
    updated_at: "2026-04-10T08:00:00Z",
  },
];

const adminRunsPayload = [
  {
    sync_run_id: "run_e2e_1",
    source_id: "src_e2e_1",
    run_mode: "scheduled",
    status: "success",
    records_fetched: 120,
    records_inserted: 118,
    records_failed: 2,
    error_message: null,
    started_at: "2026-04-10T11:55:00Z",
    ended_at: "2026-04-10T12:00:00Z",
    created_at: "2026-04-10T11:55:00Z",
    client_id: DEMO_TENANT_ID,
    source_name: "FB Ramy Officiel",
    platform: "facebook",
  },
];

const adminSnapshotsPayload = [
  {
    snapshot_id: "snap_e2e_1",
    source_id: "src_e2e_1",
    health_score: 85,
    success_rate_pct: 98,
    freshness_hours: 1,
    records_fetched_avg: 120,
    computed_at: "2026-04-10T12:00:00Z",
    client_id: DEMO_TENANT_ID,
    source_name: "FB Ramy Officiel",
    platform: "facebook",
  },
];

const schedulerTickPayload = {
  tick_at: "2026-04-10T12:05:00Z",
  groups_processed: 0,
  sources_scheduled: 0,
  groups: [],
};

const recommendationProvidersPayload = {
  providers: {
    google: [
      {
        id: "gemini-2.5-flash",
        label: "Gemini 2.5 Flash",
        recommended: true,
      },
    ],
  },
};

const recommendationContextPayload = {
  estimated_tokens: 1200,
  estimated_cost_usd: 0.0003,
  nss_global: 72,
  volume_total: 1247,
  active_alerts_count: 1,
  active_watchlists_count: 2,
  recent_campaigns_count: 1,
  provider_used: "google",
  model_used: "gemini-2.5-flash",
  pricing_basis: "demo",
  trigger: "manual",
};

async function seedDemoTenant(page: Page) {
  await page.addInitScript(
    ({ key, value }) => {
      window.localStorage.clear();
      window.localStorage.setItem(key, value);
    },
    { key: TENANT_STORAGE_KEY, value: DEMO_TENANT_ID },
  );
}

async function mockDashboardApi(page: Page) {
  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({ json: dashboardSummaryPayload });
  });
  await page.route("**/api/dashboard/alerts-critical", async (route) => {
    await route.fulfill({ json: dashboardAlertsPayload });
  });
  await page.route("**/api/dashboard/top-actions", async (route) => {
    await route.fulfill({ json: dashboardActionsPayload });
  });
  await page.route("**/api/status", async (route) => {
    await route.fulfill({ json: apiStatusPayload });
  });
}

async function mockAlertesApi(page: Page): Promise<{ getAcknowledgeCount: () => number }> {
  let acknowledgeCount = 0;
  let currentAlerts = alertsPayload.map((alert) => ({
    ...alert,
    alert_payload: { ...alert.alert_payload },
  }));

  await page.route("**/api/alerts**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === "PUT") {
      const alertId = url.pathname.match(/^\/api\/alerts\/([^/]+)\/status$/)?.[1];
      const body = request.postDataJSON() as { status?: string };

      if (alertId && body.status) {
        if (body.status === "acknowledged") {
          acknowledgeCount += 1;
        }
        currentAlerts = currentAlerts.map((alert) =>
          alert.alert_id === alertId ? { ...alert, status: body.status ?? alert.status } : alert,
        );
      }

      await route.fulfill({ json: { status: body.status ?? "acknowledged" } });
      return;
    }

    const statusFilter = url.searchParams.get("status");
    const filteredAlerts = statusFilter
      ? currentAlerts.filter((alert) => alert.status === statusFilter)
      : currentAlerts;

    await route.fulfill({ json: filteredAlerts });
  });

  return {
    getAcknowledgeCount: () => acknowledgeCount,
  };
}

async function mockCampagnesApi(
  page: Page,
): Promise<{ getPostedCampaign: () => unknown | null }> {
  let postedCampaign: unknown | null = null;
  const currentCampaigns: Array<Record<string, unknown>> = [...campaignsPayload];

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (request.method() === "GET" && pathname === "/api/campaigns/overview") {
      await route.fulfill({ json: campaignOverviewPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/campaigns/camp_demo_1/impact") {
      await route.fulfill({ json: campaignImpactPayload });
      return;
    }

    if (request.method() === "POST" && pathname === "/api/campaigns") {
      postedCampaign = request.postDataJSON();
      currentCampaigns.push({
        campaign_id: "camp_new_1",
        client_id: DEMO_TENANT_ID,
        campaign_name: "E2E Test Campaign",
        campaign_type: "product_launch",
        platform: "instagram",
        description: "",
        influencer_handle: "",
        target_aspects: [],
        target_regions: [],
        keywords: [],
        budget_dza: null,
        revenue_dza: null,
        start_date: null,
        end_date: null,
        status: "active",
        created_at: "2026-04-10T12:30:00Z",
        updated_at: "2026-04-10T12:30:00Z",
      });
      await route.fulfill({
        json: { campaign_id: "camp_new_1", campaign_name: "E2E Test Campaign" },
      });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/campaigns") {
      await route.fulfill({ json: currentCampaigns });
      return;
    }

    await route.fallback();
  });

  return {
    getPostedCampaign: () => postedCampaign,
  };
}

async function mockAdminApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (request.method() === "GET" && pathname === "/api/admin/sources") {
      await route.fulfill({ json: adminSourcesPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/social-metrics/credentials") {
      await route.fulfill({ json: credentialsPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/campaigns") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/admin/sources/src_e2e_1/runs") {
      await route.fulfill({ json: adminRunsPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/admin/sources/src_e2e_1/snapshots") {
      await route.fulfill({ json: adminSnapshotsPayload });
      return;
    }

    if (request.method() === "POST" && pathname === "/api/admin/scheduler/tick") {
      await route.fulfill({ json: schedulerTickPayload });
      return;
    }

    await route.fulfill({ status: 200, json: [] });
  });
}

async function mockAllApis(page: Page) {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (request.method() === "GET" && pathname === "/api/dashboard/summary") {
      await route.fulfill({ json: dashboardSummaryPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/dashboard/alerts-critical") {
      await route.fulfill({ json: { critical_alerts: [] } });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/dashboard/top-actions") {
      await route.fulfill({ json: { top_actions: [] } });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/status") {
      await route.fulfill({
        json: { api_status: "healthy", db_status: "healthy", latency_ms: 10 },
      });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/alerts") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname.startsWith("/api/explorer/")) {
      await route.fulfill({
        json: { results: [], total: 0, page: 1, page_size: 50, total_pages: 0 },
      });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/campaigns/overview") {
      await route.fulfill({
        json: {
          quarterly_budget_committed: 0,
          quarterly_budget_allocation: 0,
          quarter_label: "Q2 2026",
          active_campaigns_count: 0,
          top_performer: null,
        },
      });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/campaigns") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/watchlists") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/recommendations/providers") {
      await route.fulfill({ json: recommendationProvidersPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/recommendations/context-preview") {
      await route.fulfill({ json: recommendationContextPayload });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/recommendations") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/admin/sources") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "GET" && pathname === "/api/social-metrics/credentials") {
      await route.fulfill({ json: [] });
      return;
    }

    if (request.method() === "POST" && pathname === "/api/admin/scheduler/tick") {
      await route.fulfill({ json: schedulerTickPayload });
      return;
    }

    await route.fulfill({ status: 200, json: [] });
  });
}

test("Dashboard displays health score and key data", async ({ page }) => {
  await seedDemoTenant(page);
  await mockDashboardApi(page);

  await page.goto("/");

  await expect(page.getByTestId("card-health-score")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("card-health-score")).toContainText("72");
  await expect(page.getByTestId("nss-score")).toBeVisible();
  await expect(page.getByTestId("alert-card-alert_demo_1")).toBeVisible();
  await expect(page.getByTestId("action-card-rec_demo_1")).toBeVisible();
});

test("Alertes filtering and acknowledge action", async ({ page }) => {
  await seedDemoTenant(page);
  const alertController = await mockAlertesApi(page);

  await page.goto("/#/alertes");

  await expect(page.getByTestId("alert-item-alert_e2e_1")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("alert-item-alert_e2e_2")).toBeVisible();

  await page.getByTestId("filter-status-nouveau").click();
  await page.getByTestId("alert-item-alert_e2e_1").click();
  await expect(page.getByTestId("btn-acknowledge")).toBeVisible();
  await page.getByTestId("btn-acknowledge").click();

  await expect.poll(() => alertController.getAcknowledgeCount()).toBe(1);
  await expect(page.getByTestId("alert-item-alert_e2e_1")).toHaveCount(0);
});

test("Campagnes creation flow", async ({ page }) => {
  await seedDemoTenant(page);
  const campaignController = await mockCampagnesApi(page);

  await page.goto("/#/campagnes");

  await expect(page.getByTestId("campaign-row-camp_demo_1")).toBeVisible({ timeout: 10000 });

  await page.getByTestId("btn-create-campaign").click();
  await page.getByTestId("input-campaign-name").fill("E2E Test Campaign");
  await page.getByTestId("btn-submit-campaign").click();

  await expect.poll(() => campaignController.getPostedCampaign()).not.toBeNull();
});

test("Admin tab navigation across all views", async ({ page }) => {
  await mockAdminApi(page);

  await page.goto("/#/admin-sources");

  await expect(page.getByTestId("admin-ops-canvas")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("admin-ops-canvas")).toHaveAttribute("data-view", "sources");

  await page.getByTestId("admin-view-credentials").click();
  await expect(page.getByTestId("admin-ops-canvas")).toHaveAttribute("data-view", "credentials");

  await page.getByTestId("admin-view-campaign-ops").click();
  await expect(page.getByTestId("admin-ops-canvas")).toHaveAttribute("data-view", "campaign-ops");

  await page.getByTestId("admin-view-scheduler").click();
  await expect(page.getByTestId("admin-ops-canvas")).toHaveAttribute("data-view", "scheduler");
});

test("Full navigation without console errors", async ({ page }) => {
  await seedDemoTenant(page);
  await mockAllApis(page);

  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });

  const routes = [
    "/",
    "/#/alertes",
    "/#/explorateur",
    "/#/campagnes",
    "/#/watchlists",
    "/#/recommandations",
    "/#/admin-sources",
  ];

  for (const route of routes) {
    await page.goto(route);
    await page.waitForTimeout(1500);
  }

  const critical = errors.filter(
    (error) =>
      !error.includes("favicon") &&
      !error.includes("ResizeObserver") &&
      !error.includes("net::ERR"),
  );

  expect(critical).toHaveLength(0);
});
