import { expect, test, type Page } from "@playwright/test";

const explorerAnnotationV04 = {
  schema_version: "0.4.0",
  is_exploitable: true,
  non_exploitable_reason: null,
  business_relevance: "directe",
  author_role: "consommateur",
  requires_parent_context: false,
  language: { dominant: "francais", detected: ["francais"], code_switching: false, scripts: ["latin"] },
  entities: [{ id: "ent_1", type: "produit", name: "YaghurtPlus", mention: null, source: "contexte" }],
  sentiment: {
    label: "negatif",
    intensity: "forte",
    emotion: "deception",
    sarcasm: false,
    target_entity_ids: ["ent_1"],
    evidence: [{ text: "goût est mauvais", start: 3, end: 19 }],
  },
  intents: ["plainte", "partage_experience"],
  aspects: [{
    family: "produit_service",
    attribute: "gout",
    target_entity_id: "ent_1",
    sentiment: "negatif",
    intensity: "forte",
    implicit: false,
    evidence: [{ text: "goût est mauvais", start: 3, end: 19 }],
  }],
  alerts: [],
  actionability: { actionable: true, queue: "produit", priority: "moyenne" },
};

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
      annotation: explorerAnnotationV04,
      model_version: "lidal-slm-search-s1",
      compiler_version: "compiler-v0.4",
      validation_status: "valid",
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
      annotation: explorerAnnotationV04,
      model_version: "lidal-slm-0.8b-s1",
      validation_status: "valid",
    },
  ],
  total: 1,
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
  suggested_sources: [
    {
      type: "public_page",
      label: "Page Ramy",
      url: "https://example.test/ramy",
      channel: "public_url_seed",
      confidence: 0.9,
      status: "ready",
      reason: "Page publique pertinente.",
    },
  ],
  required_credentials: [],
  recommended_channels: [
    { channel: "web_search", enabled_by_default: true, reason: "Couverture web." },
    { channel: "public_url_seed", enabled_by_default: true, reason: "Page indiquée." },
    { channel: "google_maps", enabled_by_default: true, reason: "Avis locaux." },
  ],
  suggested_watchlists: [
    {
      name: "NSS Oran",
      description: "Surveille le goût à Oran.",
      scope_type: "watch_seed",
      role: "seed",
      filters: {
        keywords: ["ramy citron", "avis ramy"],
        excluded_keywords: ["emploi"],
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

const recommendationProviders = [
  {
    provider: "google_gemini",
    models: ["gemini-2.5-flash"],
    default_model: "gemini-2.5-flash",
  },
];

const recommendationPreview = {
  provider: "google_gemini",
  model: "gemini-2.5-flash",
  estimated_cost_usd: 0.0003,
  context_summary: "Résumé de contexte pour la recommandation.",
  data_quality_note: "Données démo.",
};

const recommendationList = [
  {
    recommendation_id: "rec_1",
    trigger_type: "manual",
    analysis_summary: "La baisse du goût à Oran nécessite une action corrective.",
    recommendations: ["Renforcer le contrôle qualité", "Lancer une campagne ciblée"],
    provider_used: "google_gemini",
    model_used: "gemini-2.5-flash",
    created_at: "2026-04-04T10:30:00Z",
    status: "active",
  },
];

async function seedReadyTenant(page: Page, clientId = "tenant-ready") {
  await page.addInitScript((tenant) => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", tenant);
  }, clientId);

  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({
      json: {
        nss_global: 24,
        total_mentions: 41,
        positive_mentions: 20,
        neutral_mentions: 10,
        negative_mentions: 11,
        active_alerts: 2,
        active_watchlists: 3,
        recommendation_count: 1,
        top_aspect: "gout",
        top_channel: "facebook",
      },
    });
  });
}

async function mockExplorerApi(page: Page) {
  await page.route("**/api/explorer/search**", async (route) => {
    await route.fulfill({ json: explorerSearchPayload });
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
    await route.fulfill({ json: [] });
  });
  await page.route("**/api/watchlists/watch_active_1/metrics", async (route) => {
    await route.fulfill({ json: watchlistMetrics });
  });
}

async function mockRecommendationsApi(page: Page) {
  await page.route("**/api/recommendations/providers", async (route) => {
    await route.fulfill({ json: recommendationProviders });
  });
  await page.route("**/api/recommendations/context-preview**", async (route) => {
    await route.fulfill({ json: recommendationPreview });
  });
  await page.route("**/api/recommendations?limit=50", async (route) => {
    await route.fulfill({ json: recommendationList });
  });
}

test("Explorer search shows consultable cited sources", async ({ page }) => {
  await seedReadyTenant(page);
  await mockExplorerApi(page);
  await page.goto("/#/explorateur");
  await page.getByTestId("search-input").fill("Que pensent les clients du goût ?");
  await page.getByTestId("btn-search").click();

  await expect(page.getByTestId("explorer-ai-insight")).toBeVisible();
  await expect(page.getByText("Voir la source").first()).toHaveAttribute(
    "href",
    "https://facebook.com/posts/1",
  );
  await expect(page.getByTestId("search-result-facebook-0-0.01639344")).toBeVisible();
  await page.getByRole("button", { name: "Ouvrir le dossier" }).first().click();
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("SLM 0.4.0");
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("Plainte");
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("lidal-slm-search-s1");
});

test("Watchlists create flow submits backend-aligned filters", async ({ page }) => {
  let postedPayload: unknown = null;
  let postedRunPayload: unknown = null;

  await seedReadyTenant(page);
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
      seed_urls: ["https://example.test/ramy"],
      competitors: [],
      channels: ["web_search", "public_url_seed", "google_maps"],
      languages: ["fr", "ar"],
      hashtags: [],
      subject_type: "keyword",
      excluded_keywords: ["emploi"],
      regions: ["Oran"],
      period_days: 7,
      min_volume: 10,
    },
  });
  await expect.poll(() => postedRunPayload).not.toBeNull();
  expect(postedRunPayload).toEqual({
    watchlist_id: "watch_new_1",
    requested_channels: ["web_search", "public_url_seed", "google_maps"],
  });
});

test("Recommendations AI shortcut routes to Explorer", async ({ page }) => {
  await seedReadyTenant(page);
  await mockRecommendationsApi(page);
  await page.goto("/#/recommandations");
  await page.getByTestId("recommendations-ai-shortcut").click();
  await expect(page).toHaveURL(/#\/explorateur$/);
});
