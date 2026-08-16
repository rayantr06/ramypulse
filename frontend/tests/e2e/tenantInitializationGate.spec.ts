import { expect, test, type Page } from "@playwright/test";

async function seedRunInProgress(page: Page) {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", "tenant-yaghurt");
    localStorage.setItem(
      "ramypulse.activeOnboardingRun",
      JSON.stringify({
        clientId: "tenant-yaghurt",
        runId: "run-001",
        watchlistId: "watch-001",
        source: "smart",
      }),
    );
  });

  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({
      json: {
        nss_global: null,
        total_mentions: 0,
        positive_mentions: 0,
        neutral_mentions: 0,
        negative_mentions: 0,
        active_alerts: 0,
        active_watchlists: 0,
        recommendation_count: 0,
        top_aspect: null,
        top_channel: null,
      },
    });
  });

  await page.route("**/api/watch-runs/run-001", async (route) => {
    await route.fulfill({
      json: {
        run_id: "run-001",
        client_id: "tenant-yaghurt",
        watchlist_id: "watch-001",
        stage: "collecting",
        status: "running",
        records_collected: 7,
        steps: {
          "collect:web_search": {
            step_key: "collect:web_search",
            stage: "collecting",
            collector_key: "web_search",
            status: "running",
            records_seen: 7,
            error_message: null,
          },
        },
      },
    });
  });
}

async function seedReadyTenant(page: Page) {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", "tenant-ready");
  });

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
        recommendation_count: 0,
        top_aspect: "gout",
        top_channel: "facebook",
      },
    });
  });
}

test("product routes resume the visible onboarding pipeline while the first run is still active", async ({
  page,
}) => {
  await seedRunInProgress(page);

  await page.goto("/#/recommandations");

  await expect(page).toHaveURL(/#\/nouveau-client$/);
  await expect(page.getByText("Pipeline d'initialisation")).toBeVisible();
  await expect(page.getByTestId("watch-run-stage-collecting")).toBeVisible();
});

test("recommendations keeps a visible empty state instead of a blank screen when the tenant has no generated recos", async ({
  page,
}) => {
  await seedReadyTenant(page);

  await page.route("**/api/recommendations/providers", async (route) => {
    await route.fulfill({
      json: [
        {
          provider: "google_gemini",
          models: ["gemini-2.5-flash"],
          default_model: "gemini-2.5-flash",
        },
      ],
    });
  });

  await page.route("**/api/recommendations/context-preview**", async (route) => {
    await route.fulfill({
      json: {
        provider: "google_gemini",
        model: "gemini-2.5-flash",
        estimated_cost_usd: 0.0003,
        context_summary: "Resume de contexte pour la recommandation.",
        data_quality_note: "Donnees reelles disponibles, mais aucune reco generee.",
      },
    });
  });

  await page.route("**/api/recommendations?limit=50", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto("/#/recommandations");

  await expect(page.getByText("Les recommandations attendent un premier corpus")).toBeVisible();
  await expect(page.getByText("Le module IA devient utile")).toBeVisible();
});
