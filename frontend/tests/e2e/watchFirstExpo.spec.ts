import { expect, test } from "@playwright/test";

test("watch-first expo flow creates a tenant, starts a run, and offers a value switch", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());

  await page.route("**/api/clients", async (route) => {
    await route.fulfill({
      json: {
        client_id: "tenant-cevital-elio",
        client_name: "Cevital Elio",
      },
    });
  });
  await page.route("**/api/clients/active", async (route) => {
    await route.fulfill({
      json: {
        client_id: "tenant-cevital-elio",
        client_name: "Cevital Elio",
      },
    });
  });
  await page.route("**/api/watchlists", async (route) => {
    await route.fulfill({ json: { watchlist_id: "watch-001", status: "created" } });
  });
  await page.route("**/api/watch-runs", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          run_id: "run-001",
          client_id: "tenant-cevital-elio",
          watchlist_id: "watch-001",
          stage: "queued",
          status: "queued",
          records_collected: 0,
          steps: {},
        },
      });
      return;
    }

    await route.fulfill({
      json: {
        run_id: "run-001",
        client_id: "tenant-cevital-elio",
        watchlist_id: "watch-001",
        stage: "collecting",
        status: "running",
        records_collected: 12,
        steps: {
          "collect:public_url_seed": {
            step_key: "collect:public_url_seed",
            stage: "collecting",
            collector_key: "public_url_seed",
            status: "success",
            records_seen: 4,
            error_message: null,
          },
          "collect:web_search": {
            step_key: "collect:web_search",
            stage: "collecting",
            collector_key: "web_search",
            status: "running",
            records_seen: 8,
            error_message: null,
          },
        },
      },
    });
  });

  await page.goto("/#/nouveau-client");

  await page.getByTestId("input-brand-name").fill("Cevital Elio");
  await page.getByTestId("input-product-name").fill("Elio");
  await page.getByTestId("btn-next-watch-step").click();

  await page.getByTestId("input-seed-url").fill("https://example.com/brand");
  await page.getByTestId("checkbox-channel-public_url_seed").check();
  await page.getByTestId("checkbox-channel-web_search").check();
  await page.getByTestId("btn-launch-watch-run").click();

  await expect(page.getByTestId("watch-run-stage-collecting")).toBeVisible();
  await expect(page.getByTestId("btn-switch-to-demo-tenant")).toBeVisible();
});
