import { expect, test, type Page } from "@playwright/test";

const FIXTURE_NOW = "2026-04-04T12:00:00Z";

const sources = [
  {
    source_id: "src_owned_api",
    client_id: "ramy_client_001",
    source_name: "Instagram Ramy API",
    platform: "instagram",
    source_type: "managed_page",
    owner_type: "owned",
    auth_mode: "api",
    config_json: { fetch_mode: "snapshot", account: "ramy_official" },
    is_active: 1,
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    source_purpose: "owned_content",
    source_priority: 1,
    coverage_key: "owned:instagram:ramy-official",
    credential_id: "cred_brand_1",
    last_sync_at: "2026-04-04T10:58:00Z",
    created_at: "2026-04-02T08:00:00Z",
    updated_at: "2026-04-04T10:58:00Z",
    last_sync_status: "success",
    last_sync_started_at: "2026-04-04T10:55:00Z",
    last_records_fetched: 28,
    last_records_inserted: 28,
    last_records_failed: 0,
    latest_health_score: 91,
    latest_success_rate_pct: 100,
    latest_health_computed_at: "2026-04-04T11:00:00Z",
    raw_document_count: 248,
    normalized_count: 241,
    enriched_count: 232,
  },
  {
    source_id: "src_market_scraper",
    client_id: "ramy_client_001",
    source_name: "Market Beverage Scraper",
    platform: "facebook",
    source_type: "market_monitor",
    owner_type: "market",
    auth_mode: "scraper",
    config_json: { keywords: ["ramy", "hamoud", "citron"] },
    is_active: 1,
    sync_frequency_minutes: 180,
    freshness_sla_hours: 48,
    source_purpose: "market_monitoring",
    source_priority: 2,
    coverage_key: "market:beverage-dz:facebook",
    credential_id: null,
    last_sync_at: "2026-04-04T06:00:00Z",
    created_at: "2026-04-01T08:00:00Z",
    updated_at: "2026-04-04T06:10:00Z",
    last_sync_status: "failed_downstream",
    last_sync_started_at: "2026-04-04T06:00:00Z",
    last_records_fetched: 46,
    last_records_inserted: 46,
    last_records_failed: 0,
    latest_health_score: 64,
    latest_success_rate_pct: 82,
    latest_health_computed_at: "2026-04-04T06:15:00Z",
    raw_document_count: 684,
    normalized_count: 660,
    enriched_count: 655,
  },
];

const sourceRunsById: Record<string, unknown[]> = {
  src_owned_api: [
    {
      sync_run_id: "run_src_owned_api_1",
      source_id: "src_owned_api",
      run_mode: "scheduled",
      status: "success",
      records_fetched: 28,
      records_inserted: 28,
      records_failed: 0,
      started_at: "2026-04-04T10:55:00Z",
      ended_at: "2026-04-04T10:57:10Z",
    },
    {
      sync_run_id: "run_src_owned_api_0",
      source_id: "src_owned_api",
      run_mode: "manual",
      status: "success",
      records_fetched: 26,
      records_inserted: 26,
      records_failed: 0,
      started_at: "2026-04-03T12:00:00Z",
      ended_at: "2026-04-03T12:02:00Z",
    },
  ],
  src_market_scraper: [
    {
      sync_run_id: "run_src_market_scraper_1",
      source_id: "src_market_scraper",
      run_mode: "scheduled",
      status: "failed_downstream",
      records_fetched: 46,
      records_inserted: 46,
      records_failed: 0,
      started_at: "2026-04-04T06:00:00Z",
      ended_at: "2026-04-04T06:05:00Z",
    },
  ],
};

const sourceSnapshotsById: Record<string, unknown[]> = {
  src_owned_api: [
    {
      snapshot_id: "snap_src_owned_api_1",
      source_id: "src_owned_api",
      health_score: 91,
      success_rate_pct: 100,
      freshness_hours: 1,
      records_fetched_avg: 27,
      computed_at: "2026-04-04T11:00:00Z",
    },
  ],
  src_market_scraper: [
    {
      snapshot_id: "snap_src_market_scraper_1",
      source_id: "src_market_scraper",
      health_score: 64,
      success_rate_pct: 82,
      freshness_hours: 6,
      records_fetched_avg: 43,
      computed_at: "2026-04-04T06:15:00Z",
    },
  ],
};

const credentials = [
  {
    credential_id: "cred_brand_1",
    entity_type: "brand",
    entity_name: "Ramy Official",
    platform: "instagram",
    account_id: "1789",
    app_id: "ramy-instagram-app",
    is_active: 1,
    created_at: "2026-04-03T09:00:00Z",
    updated_at: "2026-04-04T08:00:00Z",
  },
  {
    credential_id: "cred_influencer_1",
    entity_type: "influencer",
    entity_name: "Rifka BJM",
    platform: "instagram",
    account_id: "if-882",
    app_id: "rifka-app",
    is_active: 1,
    created_at: "2026-04-02T10:00:00Z",
    updated_at: "2026-04-04T08:30:00Z",
  },
];

const campaigns = [
  {
    campaign_id: "camp_rifka",
    client_id: "ramy_client_001",
    campaign_name: "Rifka Summer Push",
    campaign_type: "influencer",
    platform: "instagram",
    influencer_handle: "@rifka.bjm",
    target_aspects: ["gout", "disponibilite"],
    target_regions: ["Alger", "Oran"],
    keywords: ["ramy", "citron"],
    budget_dza: 1250000,
    revenue_dza: 1680000,
    start_date: "2026-04-01",
    end_date: "2026-04-30",
    status: "active",
  },
];

const campaignPostsById: Record<string, unknown[]> = {
  camp_rifka: [
    {
      post_id: "post_rifka_1",
      campaign_id: "camp_rifka",
      platform: "instagram",
      post_platform_id: "IG-44551",
      post_url: "https://instagram.com/p/IG-44551",
      entity_type: "influencer",
      entity_name: "Rifka BJM",
      credential_id: "cred_influencer_1",
      added_at: "2026-04-04T09:15:00Z",
    },
    {
      post_id: "post_ramy_1",
      campaign_id: "camp_rifka",
      platform: "instagram",
      post_platform_id: "IG-44552",
      post_url: "https://instagram.com/p/IG-44552",
      entity_type: "brand",
      entity_name: "Ramy Official",
      credential_id: "cred_brand_1",
      added_at: "2026-04-04T09:35:00Z",
    },
  ],
};

const campaignSummaryById: Record<string, unknown> = {
  camp_rifka: {
    campaign_id: "camp_rifka",
    post_count: 2,
    metrics_collected_count: 2,
    totals: {
      likes: 1240,
      comments: 146,
      shares: 57,
      views: 38400,
      reach: 21100,
      impressions: 24500,
      saves: 98,
    },
    engagement_rate: 6.84,
    engagement_rate_note: "Basé sur portée réelle collectée via API",
    roi_pct: 34.4,
    roi_note: "Basé sur revenue_dza saisi manuellement",
    budget_dza: 1250000,
    revenue_dza: 1680000,
    signal_count: 14,
    sentiment_breakdown: {
      positive: 9,
      neutral: 3,
      negative: 2,
    },
    negative_aspects: ["disponibilite", "prix"],
    top_performer: {
      post_id: "post_rifka_1",
      platform: "instagram",
      post_url: "https://instagram.com/p/IG-44551",
      entity_name: "Rifka BJM",
      engagement: 932,
      reach: 12450,
      signal_count: 8,
      sentiment_breakdown: {
        positive: 5,
        neutral: 2,
        negative: 1,
      },
      negative_aspects: ["disponibilite"],
    },
    posts: [
      {
        post_id: "post_rifka_1",
        platform: "instagram",
        post_url: "https://instagram.com/p/IG-44551",
        entity_type: "influencer",
        entity_name: "Rifka BJM",
        likes: 830,
        comments: 74,
        shares: 28,
        views: 22500,
        reach: 12450,
        impressions: 14600,
        saves: 64,
        signal_count: 8,
        sentiment_breakdown: { positive: 5, neutral: 2, negative: 1 },
        negative_aspects: ["disponibilite"],
        collected_at: "2026-04-04T10:10:00Z",
      },
      {
        post_id: "post_ramy_1",
        platform: "instagram",
        post_url: "https://instagram.com/p/IG-44552",
        entity_type: "brand",
        entity_name: "Ramy Official",
        likes: 410,
        comments: 72,
        shares: 29,
        views: 15900,
        reach: 8650,
        impressions: 9900,
        saves: 34,
        signal_count: 6,
        sentiment_breakdown: { positive: 4, neutral: 1, negative: 1 },
        negative_aspects: ["prix"],
        collected_at: "2026-04-04T10:20:00Z",
      },
    ],
  },
};

async function mockAdminApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const method = request.method();

    if (method === "GET" && pathname === "/api/admin/sources") {
      await route.fulfill({ json: sources });
      return;
    }

    const runMatch = pathname.match(/^\/api\/admin\/sources\/([^/]+)\/runs$/);
    if (method === "GET" && runMatch) {
      await route.fulfill({ json: sourceRunsById[runMatch[1]] ?? [] });
      return;
    }

    const snapshotMatch = pathname.match(/^\/api\/admin\/sources\/([^/]+)\/snapshots$/);
    if (method === "GET" && snapshotMatch) {
      await route.fulfill({ json: sourceSnapshotsById[snapshotMatch[1]] ?? [] });
      return;
    }

    if (method === "GET" && pathname === "/api/social-metrics/credentials") {
      await route.fulfill({ json: credentials });
      return;
    }

    if (method === "GET" && pathname === "/api/campaigns") {
      await route.fulfill({ json: campaigns });
      return;
    }

    const postsMatch = pathname.match(/^\/api\/social-metrics\/campaigns\/([^/]+)\/posts$/);
    if (method === "GET" && postsMatch) {
      await route.fulfill({ json: campaignPostsById[postsMatch[1]] ?? [] });
      return;
    }

    const summaryMatch = pathname.match(/^\/api\/social-metrics\/campaigns\/([^/]+)$/);
    if (method === "GET" && summaryMatch) {
      await route.fulfill({ json: campaignSummaryById[summaryMatch[1]] ?? {} });
      return;
    }

    if (method === "POST" && pathname === "/api/admin/scheduler/tick") {
      await route.fulfill({
        json: {
          tick_at: FIXTURE_NOW,
          groups_processed: 2,
          sources_scheduled: 2,
          groups: [
            {
              coverage_key: "owned:instagram:ramy-official",
              winner_source_id: "src_owned_api",
              winner_status: "success",
              attempts: [
                {
                  source_id: "src_owned_api",
                  source_priority: 1,
                  status: "success",
                  records_fetched: 28,
                  records_inserted: 28,
                  records_failed: 0,
                },
              ],
            },
            {
              coverage_key: "market:beverage-dz:facebook",
              winner_source_id: "src_market_scraper",
              winner_status: "failed_downstream",
              attempts: [
                {
                  source_id: "src_market_scraper",
                  source_priority: 2,
                  status: "failed_downstream",
                  records_fetched: 46,
                  records_inserted: 46,
                  records_failed: 0,
                  error: "Normalizer timeout",
                },
              ],
            },
          ],
        },
      });
      return;
    }

    await route.fulfill({ status: 200, json: {} });
  });
}

async function openAdminView(page: Page, view: string) {
  await mockAdminApi(page);
  await page.goto(`/#/admin-sources?view=${view}`);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.evaluate(async () => {
    if ("fonts" in document) {
      await document.fonts.ready;
    }
  });
  await expect(page.getByTestId("admin-ops-canvas")).toHaveAttribute("data-view", view);
  await expect(page.getByTestId("admin-shell-canvas")).toBeVisible();
}

test("admin sources view keeps Stitch shell", async ({ page }) => {
  await openAdminView(page, "sources");
  await expect(page).toHaveScreenshot("admin-sources-view.png");
});

test("admin credentials view keeps Stitch shell", async ({ page }) => {
  await openAdminView(page, "credentials");
  await expect(page).toHaveScreenshot("admin-credentials-view.png");
});

test("admin campaign ops view keeps Stitch shell", async ({ page }) => {
  await openAdminView(page, "campaign-ops");
  await expect(page).toHaveScreenshot("admin-campaign-ops-view.png");
});

test("admin scheduler view keeps Stitch shell", async ({ page }) => {
  await openAdminView(page, "scheduler");
  await expect(page).toHaveScreenshot("admin-scheduler-view.png");
});
