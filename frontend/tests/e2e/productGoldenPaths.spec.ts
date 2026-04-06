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
  {
    watchlist_id: "watch_active_2",
    watchlist_name: "Prix Alger",
    description: "Surveille la pression prix a Alger",
    scope_type: "channel",
    filters: {
      channel: "facebook",
      wilaya: "alger",
      product: "ramy_orange",
      aspect: "prix",
      sentiment: null,
      period_days: 14,
      min_volume: 4,
    },
    is_active: true,
    created_at: "2026-04-04T09:30:00Z",
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
    confidence_score: 86,
  },
  {
    recommendation_id: "rec_2",
    trigger_type: "alert",
    analysis_summary: "Lancer une promo prix a Alger pour contenir la hausse percue.",
    recommendations: ["Activer une offre prix a Alger"],
    provider_used: "openai",
    model_used: "gpt-4o",
    created_at: "2026-04-04T11:00:00Z",
    status: "active",
    confidence_score: 73,
  },
];

const campaignList = [
  {
    campaign_id: "camp_1",
    campaign_name: "Ramy Ete",
    campaign_type: "Influenceur",
    platform: "instagram",
    influencer_handle: "@rifka",
    keywords: ["#ramy", "#citron"],
    budget_dza: 120000,
    start_date: "2026-04-01",
    end_date: "2026-04-15",
    status: "active",
  },
  {
    campaign_id: "camp_2",
    campaign_name: "Promo Prix Alger",
    campaign_type: "Social Media",
    platform: "facebook",
    influencer_handle: "@amine",
    keywords: ["#promo", "#alger"],
    budget_dza: 70000,
    start_date: "2026-04-10",
    end_date: "2026-04-22",
    status: "planned",
  },
];

const campaignOverview = {
  quarterly_budget_committed: 190000,
  quarterly_budget_allocation: 300000,
  quarter_label: "T2 2026",
  active_campaigns_count: 1,
  top_performer: {
    campaign_id: "camp_1",
    campaign_name: "Ramy Ete",
    influencer_handle: "@rifka",
    platform: "instagram",
    status: "active",
    budget_dza: 120000,
    roi_pct: 18,
    engagement_rate: 7,
    signal_count: 12,
    sentiment_breakdown: { positif: 8, negatif: 2 },
    negative_aspects: ["gout"],
    selection_basis: "roi_pct",
  },
};

const campaignImpact = {
  campaign_id: "camp_1",
  campaign_name: "Ramy Ete",
  phases: {
    pre: { nss: -10, volume: 18, aspect_breakdown: {}, sentiment_breakdown: {} },
    active: { nss: 12, volume: 41, aspect_breakdown: {}, sentiment_breakdown: {} },
    post: { nss: 7, volume: 23, aspect_breakdown: {}, sentiment_breakdown: {} },
  },
  uplift_nss: 22,
  uplift_volume_pct: 40,
  is_reliable: true,
  reliability_note: "Le signal est robuste sur la campagne selectionnee.",
};

const alertList = [
  {
    alert_id: "alert_1",
    title: "Baisse NSS Oran",
    description: "Le gout se degrade rapidement sur Google Maps.",
    severity: "critical",
    status: "new",
    navigation_url: "/#/explorateur",
    detected_at: "2026-04-04T12:00:00Z",
    alert_payload: {
      wilaya: "Oran",
      value: -18,
      social_excerpts: [{ author: "Amina", platform: "google_maps", text: "Le gout est mauvais" }],
    },
  },
  {
    alert_id: "alert_2",
    title: "Prix Alger",
    description: "Hausse tarifaire percue sur Facebook.",
    severity: "medium",
    status: "acknowledged",
    navigation_url: null,
    detected_at: "2026-04-04T13:00:00Z",
    alert_payload: {
      wilaya: "Alger",
      value: 6,
      social_excerpts: [{ author: "Samir", platform: "facebook", text: "Le prix a augmente" }],
    },
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

async function mockCampaignsApi(page: Page) {
  await page.route("**/api/campaigns/overview", async (route) => {
    await route.fulfill({ json: campaignOverview });
  });
  await page.route("**/api/campaigns/camp_1/impact", async (route) => {
    await route.fulfill({ json: campaignImpact });
  });
  await page.route("**/api/campaigns/camp_2/impact", async (route) => {
    await route.fulfill({
      json: {
        ...campaignImpact,
        campaign_id: "camp_2",
        campaign_name: "Promo Prix Alger",
        uplift_nss: 8,
      },
    });
  });
  await page.route("**/api/campaigns*", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/api/campaigns")) {
      await route.fulfill({ json: campaignList });
      return;
    }
    await route.fallback();
  });
}

async function mockAlertsApi(page: Page) {
  await page.route("**/api/alerts?**", async (route) => {
    await route.fulfill({ json: alertList });
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

test("Watchlists header search narrows cards with business filters", async ({ page }) => {
  await mockWatchlistsApi(page);
  await page.goto("/#/watchlists");

  await page.getByTestId("header-search").fill("oran");

  await expect(page.getByText("NSS Oran").first()).toBeVisible();
  await expect(page.getByText("Prix Alger")).toHaveCount(0);
});

test("Recommendations AI shortcut routes to Explorer", async ({ page }) => {
  await mockRecommendationsApi(page);
  await page.goto("/#/recommandations");
  await page.getByTestId("recommendations-ai-shortcut").click();
  await expect(page).toHaveURL(/#\/explorateur$/);
});

test("Recommendations header search narrows active recommendation cards", async ({ page }) => {
  await mockRecommendationsApi(page);
  await page.goto("/#/recommandations");

  await page.getByTestId("header-search").fill("promo");

  await expect(page.getByTestId("reco-card-rec_2")).toBeVisible();
  await expect(page.getByTestId("reco-card-rec_1")).toHaveCount(0);
});

test("Campaigns header search narrows visible campaign rows", async ({ page }) => {
  await mockCampaignsApi(page);
  await page.goto("/#/campagnes");

  await page.getByTestId("header-search").fill("amine");

  await expect(page.getByTestId("campaign-row-camp_2")).toBeVisible();
  await expect(page.getByTestId("campaign-row-camp_1")).toHaveCount(0);
});

test("Alertes header search narrows alert triage list", async ({ page }) => {
  await mockAlertsApi(page);
  await page.goto("/#/alertes");

  await page.getByTestId("header-search").fill("oran");

  await expect(page.getByTestId("alert-item-alert_1")).toBeVisible();
  await expect(page.getByTestId("alert-item-alert_2")).toHaveCount(0);
});
