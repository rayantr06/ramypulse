import { expect, test } from "@playwright/test";

const tenantId = process.env.VITE_SAFE_EXPO_CLIENT_ID || "ramy-demo";

test.beforeEach(async ({ page }) => {
  await page.addInitScript((value) => {
    window.localStorage.setItem("ramypulse.activeTenantId", value);
  }, tenantId);
});

test("Ramy demo live smoke covers the main expo surfaces", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByRole("heading", { name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByTestId("card-health-score")).toBeVisible();
  await expect(page.getByTestId("nss-score")).toBeVisible();

  await page.getByTestId("nav-watchlists").click();
  await expect(page).toHaveURL(/#\/watchlists$/);
  await expect(page.getByRole("heading", { name: "Watchlists" })).toBeVisible();
  await expect(page.getByText("Ramy Pulse Global")).toBeVisible();

  await page.getByTestId("nav-alertes").click();
  await expect(page).toHaveURL(/#\/alertes$/);
  await expect(page.getByText("Console d'Alertes")).toBeVisible();
  await expect(page.locator('[data-testid^="alert-item-"]').first()).toBeVisible();
  await expect(
    page
      .getByRole("button", { name: /Ouvrir dans l'explorateur/i })
      .or(page.getByRole("link", { name: /Ouvrir la source/i }))
      .first(),
  ).toBeVisible();

  await page.getByTestId("nav-recommandations").click();
  await expect(page).toHaveURL(/#\/recommandations$/);
  await expect(page.getByText("Recommandations actives")).toBeVisible();
  await expect(page.locator('[data-testid^="reco-card-"]').first()).toBeVisible();

  await page.getByTestId("nav-campagnes").click();
  await expect(page).toHaveURL(/#\/campagnes$/);
  await expect(page.getByText("Campagnes Marketing")).toBeVisible();
  await expect(page.locator('[data-testid^="campaign-row-"]').first()).toBeVisible();

  await page.getByTestId("nav-admin-sources").click();
  await expect(page).toHaveURL(/#\/admin-sources$/);
  await expect(page.getByTestId("admin-ops-canvas")).toBeVisible();
  await expect(page.getByText("Ramy Facebook Corpus")).toBeVisible();

  await page.goto("/#/explorateur");
  await expect(page).toHaveURL(/#\/explorateur$/);
  await expect(page.getByRole("heading", { name: "Explorateur" })).toBeVisible();
  await expect(page.locator('[data-testid^="verbatim-row-"]').first()).toBeVisible();
  await expect(page.locator('a[href^="https://www.facebook.com/"]').first()).toBeVisible();
});
