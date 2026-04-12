import { expect, test } from "@playwright/test";

const smartAnalysis = {
  tenant_setup: {
    client_name: "Yaghurt Plus",
    client_slug: "yaghurt-plus",
    country: "DZ",
  },
  suggested_sources: [
    {
      type: "website",
      label: "Site officiel",
      url: "https://yaghurt.example",
      channel: "public_url_seed",
      confidence: 0.98,
      status: "suggested_only",
      reason: "Site officiel detecte",
    },
    {
      type: "facebook_page",
      label: "Yaghurt Plus DZ",
      url: "https://facebook.com/yaghurtplus",
      channel: "facebook",
      confidence: 0.92,
      status: "requires_credentials",
      reason: "Page officielle detectee",
    },
  ],
  required_credentials: [
    {
      platform: "facebook",
      credential_type: "oauth_access_token",
      required: true,
      reason: "Credential requis pour la collecte admin",
    },
  ],
  recommended_channels: [
    { channel: "public_url_seed", enabled_by_default: true, reason: "Base seed" },
    { channel: "web_search", enabled_by_default: true, reason: "Decouverte web" },
    { channel: "facebook", enabled_by_default: true, reason: "Page officielle detectee" },
  ],
  suggested_watchlists: [
    {
      name: "Yaghurt Plus watch seed",
      description: "Seed watchlist",
      scope_type: "watch_seed",
      role: "seed",
      filters: {
        brand_name: "Yaghurt Plus",
        keywords: ["yaghurt plus"],
        seed_urls: ["https://yaghurt.example"],
      },
      enabled_by_default: true,
      reason: "Collecte de depart",
    },
    {
      name: "Yaghurt Plus produit",
      description: "Product watchlist",
      scope_type: "product",
      role: "analysis",
      filters: { product: "yaourt", period_days: 7, min_volume: 10 },
      enabled_by_default: true,
      reason: "Suivi produit",
    },
    {
      name: "Yaghurt Plus facebook",
      description: "Channel watchlist",
      scope_type: "channel",
      role: "analysis",
      filters: { channel: "facebook", period_days: 7, min_volume: 10 },
      enabled_by_default: true,
      reason: "Suivi canal",
    },
  ],
  suggested_alert_profiles: [
    {
      watchlist_ref: "yaghurt-plus-facebook",
      profile_name: "Veille Facebook",
      enabled_by_default: true,
      rules: [
        {
          rule_id: "negative_volume_surge",
          threshold_value: 60,
          comparator: "gt",
          lookback_window: "7d",
          severity_level: "high",
          reason: "Pic negatif",
        },
      ],
      reason: "Surveiller les pics negatifs",
    },
  ],
  deferred_agent_config: [
    {
      key: "weekly_digest",
      value: true,
      reason: "A activer apres validation humaine",
    },
  ],
  warnings: [],
  fallback_used: false,
};

test("smart onboarding enforces review before confirm and hands off to the first run", async ({
  page,
}) => {
  let confirmPayload: Record<string, unknown> | null = null;

  await page.addInitScript(() => localStorage.clear());

  await page.route("**/api/onboarding/analyze", async (route) => {
    await route.fulfill({ json: smartAnalysis });
  });

  await page.route("**/api/onboarding/confirm", async (route) => {
    confirmPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      json: {
        client_id: "yaghurt-plus",
        watch_seed_watchlist_id: "watch-seed-001",
        watchlist_ids: ["watch-seed-001", "watch-product-001", "watch-channel-001"],
        source_ids: ["src-facebook-001"],
        pending_credentials: smartAnalysis.required_credentials,
        pending_alert_profiles: smartAnalysis.suggested_alert_profiles,
        deferred_agent_config: smartAnalysis.deferred_agent_config,
        run_id: "run-001",
        watchlist_id: "watch-seed-001",
      },
    });
  });

  await page.route("**/api/watch-runs/run-001", async (route) => {
    await route.fulfill({
      json: {
        run_id: "run-001",
        client_id: "yaghurt-plus",
        watchlist_id: "watch-seed-001",
        requested_channels: ["public_url_seed", "web_search", "facebook"],
        stage: "collecting",
        status: "running",
        records_collected: 4,
        steps: {
          "collect:public_url_seed": {
            step_key: "collect:public_url_seed",
            stage: "collecting",
            collector_key: "public_url_seed",
            status: "success",
            records_seen: 2,
            error_message: null,
          },
          "collect:web_search": {
            step_key: "collect:web_search",
            stage: "collecting",
            collector_key: "web_search",
            status: "running",
            records_seen: 2,
            error_message: null,
          },
        },
      },
    });
  });

  await page.goto("/#/nouveau-client");

  await page.getByTestId("input-brand-name").fill("Yaghurt Plus");
  await page.getByTestId("input-product-name").fill("Yaourt");
  await page.getByTestId("btn-smart-analyze").click();

  await expect(page.getByTestId("smart-review-screen")).toBeVisible();
  await expect(page.getByText("Veille Facebook")).toBeVisible();
  expect(confirmPayload).toBeNull();

  await page.getByTestId("btn-confirm-smart-onboarding").click();

  await expect(page.getByTestId("watch-run-stage-collecting")).toBeVisible();
  expect(confirmPayload?.review_confirmed).toBe(true);
  expect(Array.isArray(confirmPayload?.selected_watchlists)).toBe(true);
});

test("smart onboarding offers a manual fallback when providers are unavailable", async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.clear());

  await page.route("**/api/onboarding/analyze", async (route) => {
    await route.fulfill({
      json: {
        ...smartAnalysis,
        fallback_used: true,
        warnings: [
          {
            code: "provider_unavailable",
            message: "Analyse heuristique uniquement",
            severity: "warning",
          },
        ],
      },
    });
  });

  await page.goto("/#/nouveau-client");

  await page.getByTestId("input-brand-name").fill("Yaghurt Plus");
  await page.getByTestId("btn-smart-analyze").click();

  await expect(page.getByTestId("btn-switch-manual-onboarding")).toBeVisible();
});
