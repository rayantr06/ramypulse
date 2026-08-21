import { expect, test } from "@playwright/test";

test("Leticia demo uses the official local LIDAL mark", async ({ page }) => {
  await page.goto("/#/");
  const logo = page.getByRole("img", { name: "LIDAL Pulse" }).first();
  await expect(logo).toHaveAttribute("src", /\/brand\/lidal-mark-dark\.png$/);
  const response = await page.request.get("/brand/lidal-mark-dark.png");
  expect(response.ok()).toBeTruthy();
});

test("Leticia recording path does not request non-local assets", async ({ page }) => {
  const nonLocalHosts = new Set<string>();
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      ["http:", "https:", "ws:", "wss:"].includes(url.protocol)
      && !["127.0.0.1", "localhost", "::1"].includes(url.hostname)
    ) {
      nonLocalHosts.add(url.hostname);
    }
  });

  await page.goto("/#/", { waitUntil: "networkidle" });

  expect([...nonLocalHosts]).toEqual([]);
});

test("Leticia recording path renders local Material Symbols as glyphs", async ({ page }) => {
  await page.goto("/#/explorateur");
  const sourceIcon = page.locator(".material-symbols-outlined", { hasText: "social_leaderboard" });
  await expect(sourceIcon).toBeVisible();
  await page.evaluate(async () => {
    await document.fonts.load('24px "Material Symbols Outlined Variable"', "social_leaderboard");
    await document.fonts.ready;
  });

  const iconRendering = await sourceIcon.evaluate((element) => ({
    fontFamily: getComputedStyle(element).fontFamily,
    width: element.getBoundingClientRect().width,
  }));

  expect(iconRendering.fontFamily).toContain("Material Symbols Outlined Variable");
  expect(iconRendering.width).toBeLessThanOrEqual(32);
});
