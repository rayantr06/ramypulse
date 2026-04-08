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
});

test("Watchlists create flow submits backend-aligned filters", async ({ page }) => {
  let postedPayload: unknown = null;

  await mockWatchlistsApi(page);
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

  await page.goto("/#/watchlists");
  await page.getByTestId("btn-create-watchlist").click();
  await page.getByTestId("input-watchlist-name").fill("NSS Oran");
  await page.getByPlaceholder("Description (optionnel)").fill("Surveille Oran");
  await page.locator("select").nth(0).selectOption("region");
  await page.getByPlaceholder("Produit").fill("ramy_citron");
  await page.getByPlaceholder("Wilaya").fill("oran");
  await page.getByPlaceholder("Canal").fill("google_maps");
  await page.getByPlaceholder("Aspect").fill("gout");
  await page.getByPlaceholder("Jours").fill("7");
  await page.getByPlaceholder("Volume min.").fill("10");
  await page.getByTestId("btn-submit-watchlist").click();

  await expect.poll(() => postedPayload).not.toBeNull();
  expect(postedPayload).toEqual({
    name: "NSS Oran",
    description: "Surveille Oran",
    scope_type: "region",
    filters: {
      channel: "google_maps",
      aspect: "gout",
      wilaya: "oran",
      product: "ramy_citron",
      sentiment: null,
      period_days: 7,
      min_volume: 10,
    },
  });
});

test("Recommendations AI shortcut routes to Explorer", async ({ page }) => {
  await mockRecommendationsApi(page);
  await page.goto("/#/recommandations");
  await page.getByTestId("recommendations-ai-shortcut").click();
  await expect(page).toHaveURL(/#\/explorateur$/);
});
