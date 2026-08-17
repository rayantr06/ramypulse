import { expect, test, type Page } from "@playwright/test";

const explorerSearchPayload = {
  query: "Que pensent les clients du goût ?",
  total: 2,
  results: [
    {
      text: "Le goût est mauvais",
      channel: "facebook",
      source_url: "https://facebook.com/posts/1",
      timestamp: "2026-04-04T09:00:00Z",
      aspect: "gout",
      sentiment_label: "negatif",
      score: 0.01639344,
    },
    {
      text: "Le goût manque de fraîcheur",
      channel: "facebook",
      source_url: "https://facebook.com/posts/2",
      timestamp: "2026-04-04T08:00:00Z",
      aspect: "gout",
      sentiment_label: "negatif",
      score: 0.01612903,
    },
  ],
};

const explorerRagPayload = {
  query: "Que pensent les clients du goût ?",
  answer: "Les signaux cités indiquent une perception négative du goût et de la fraîcheur.",
  confidence: "high",
  chunks: explorerSearchPayload.results.map((result) => ({
    text: result.text,
    channel: result.channel,
    source_url: result.source_url,
    url: result.source_url,
    sentiment_label: result.sentiment_label,
    aspect: result.aspect,
    score: result.score,
  })),
};

const explorerVerbatimsPayload = {
  results: [
    {
      text: "Le goût est mauvais",
      channel: "facebook",
      source_url: "https://facebook.com/posts/1",
      timestamp: "2026-04-04T09:00:00Z",
      aspect: "gout",
      sentiment_label: "negatif",
      wilaya: "alger",
    },
    {
      text: "Le prix est trop élevé",
      channel: "google_maps",
      source_url: "https://maps.google.com/review/1",
      timestamp: "2026-04-04T07:00:00Z",
      aspect: "prix",
      sentiment_label: "negatif",
      wilaya: "oran",
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  total_pages: 1,
};

const activeWatchlists = [
  {
    watchlist_id: "watch_active_1",
    watchlist_name: "NSS Oran",
    description: "Surveille Oran",
    scope_type: "region",
    filters: {
      channel: "google_maps",
      wilaya: "oran",
      product: "ramy_citron",
      aspect: "gout",
      sentiment: null,
      period_days: 7,
      min_volume: 10,
    },
    is_active: true,
    created_at: "2026-04-04T09:00:00Z",
  },
];

const inactiveWatchlists = [
  {
    watchlist_id: "watch_inactive_1",
    watchlist_name: "Archive Alger",
    description: "Archive",
    scope_type: "region",
    filters: {
      channel: "facebook",
      wilaya: "alger",
      product: null,
      aspect: "prix",
      sentiment: null,
      period_days: 30,
      min_volume: 5,
    },
    is_active: false,
    created_at: "2026-03-01T09:00:00Z",
  },
];

const watchlistMetrics = {
  watchlist_id: "watch_active_1",
  computed_at: "2026-04-04T10:00:00Z",
  nss_current: -18,
  delta_nss: -6,
  volume_total: 41,
  volume_delta: 5,
  aspect_breakdown: {
    gout: -62,
    disponibilite: -24,
  },
  quick_insight: "La baisse est concentrée sur le goût à Oran.",
};

const smartWatchAnalysis = {
  tenant_setup: { client_name: "Tenant Ready", client_slug: "tenant-ready", country: "DZ" },
  suggested_sources: [],
  required_credentials: [],
  recommended_channels: [
    { channel: "web_search", enabled_by_default: true, reason: "Couverture web." },
    { channel: "public_url_seed", enabled_by_default: true, reason: "Pages publiques." },
    { channel: "google_maps", enabled_by_default: true, reason: "Avis locaux." },
  ],
  suggested_watchlists: [
    {
      name: "NSS Oran",
      description: "Surveille Oran.",
      scope_type: "watch_seed",
      role: "seed",
      filters: {
        keywords: ["ramy citron", "avis ramy"],
        languages: ["fr", "ar"],
        regions: ["Oran"],
        period_days: 7,
        min_volume: 10,
      },
      enabled_by_default: true,
      reason: "Périmètre principal.",
    },
  ],
  suggested_alert_profiles: [],
  deferred_agent_config: [],
  warnings: [],
  fallback_used: false,
};

async function mockExplorerApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", "tenant-ready");
  });
  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({
      json: {
        nss_global: 24,
        total_mentions: 41,
        active_alerts: 2,
        active_watchlists: 3,
      },
    });
  });
  await page.route("**/api/explorer/search**", async (route) => {
    await route.fulfill({ json: explorerSearchPayload });
  });
  await page.route("**/api/explorer/rag**", async (route) => {
    await route.fulfill({ json: explorerRagPayload });
  });
  await page.route("**/api/explorer/verbatims**", async (route) => {
    await route.fulfill({ json: explorerVerbatimsPayload });
  });
}

async function mockWatchlistsApi(page: Page) {
  await page.route("**/api/watchlists?is_active=true", async (route) => {
    await route.fulfill({ json: activeWatchlists });
  });
  await page.route("**/api/watchlists?is_active=false", async (route) => {
    await route.fulfill({ json: inactiveWatchlists });
  });
  await page.route("**/api/watchlists/watch_active_1/metrics", async (route) => {
    await route.fulfill({ json: watchlistMetrics });
  });
}

test("explorer golden path shows consultable RAG evidence and real source links", async ({ page }) => {
  await mockExplorerApi(page);
  await page.goto("/#/explorateur");
  await page.fill('[data-testid="search-input"]', "Que pensent les clients du goût ?");
  await page.click('[data-testid="btn-search"]');

  await expect(page.getByTestId("explorer-ai-insight")).toBeVisible();
  await expect(page.getByText("Voir la source").first()).toHaveAttribute(
    "href",
    "https://facebook.com/posts/1",
  );
  await expect(page.getByRole("button", { name: "Filtrer" })).toBeVisible();
  await expect(page.getByTestId("search-result-facebook-0-0.01639344")).toBeVisible();
  await expect(page.getByTestId("verbatim-row-facebook-0-2026-04-04T09:00:00Z")).toBeVisible();
});

test("watchlists golden path submits backend-aligned filters", async ({ page }) => {
  let postedPayload: unknown = null;
  let postedRunPayload: unknown = null;
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", "tenant-ready");
  });
  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({
      json: {
        nss_global: 24,
        total_mentions: 41,
        active_alerts: 2,
        active_watchlists: 3,
      },
    });
  });
  await mockWatchlistsApi(page);
  await page.route("**/api/onboarding/analyze", async (route) => {
    await route.fulfill({ json: smartWatchAnalysis });
  });
  await page.route("**/api/watchlists", async (route) => {
    if (route.request().method() === "POST") {
      postedPayload = route.request().postDataJSON();
      await route.fulfill({ json: { watchlist_id: "watch_new_1" } });
      return;
    }
    await route.fulfill({ json: [] });
  });
  await page.route("**/api/watchlists/watch_new_1/metrics", async (route) => {
    await route.fulfill({ json: watchlistMetrics });
  });
  await page.route("**/api/watch-runs", async (route) => {
    postedRunPayload = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: { run_id: "run_new_1" } });
  });

  await page.goto("/#/watchlists");
  await page.getByTestId("btn-create-watchlist").click();
  await page
    .getByTestId("watch-intent-input")
    .fill("Surveiller les avis sur le goût de Ramy à Oran");
  await page.getByTestId("btn-prepare-watch").click();
  await expect(page.getByTestId("smart-watch-review")).toBeVisible();
  await page.getByTestId("btn-submit-watchlist").click();

  await expect.poll(() => postedPayload).not.toBeNull();
  expect(postedPayload).toEqual({
    name: "NSS Oran",
    description: "Surveiller les avis sur le goût de Ramy à Oran",
    scope_type: "watch_seed",
    filters: {
      brand_name: "Tenant Ready",
      product_name: "Surveiller les avis sur le goût de Ramy à Oran",
      keywords: ["ramy citron", "avis ramy"],
      seed_urls: [],
      competitors: [],
      channels: ["web_search", "public_url_seed", "google_maps"],
      languages: ["fr", "ar"],
      hashtags: [],
      subject_type: "keyword",
      excluded_keywords: [],
      regions: ["Oran"],
      period_days: 7,
      min_volume: 10,
    },
  });
  await expect.poll(() => postedRunPayload).not.toBeNull();
});
