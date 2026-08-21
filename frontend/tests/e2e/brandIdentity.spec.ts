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

test("Leticia recording path loads the configured body and heading fonts", async ({ page }) => {
  await page.goto("/#/", { waitUntil: "networkidle" });

  const fontEvidence = await page.evaluate(async () => {
    const [interFaces, urbanistFaces] = await Promise.all([
      document.fonts.load('400 16px "Inter"', "RamyPulse"),
      document.fonts.load('700 48px "Urbanist"', "Aujourd’hui"),
    ]);
    const resources = performance
      .getEntriesByType("resource")
      .map((entry) => new URL(entry.name));

    return {
      bodyFamily: getComputedStyle(document.body).fontFamily,
      headingFamily: getComputedStyle(document.querySelector("h1")!).fontFamily,
      interFaceCount: interFaces.length,
      urbanistFaceCount: urbanistFaces.length,
      interLoaded: document.fonts.check('400 16px "Inter"', "RamyPulse"),
      urbanistLoaded: document.fonts.check('700 48px "Urbanist"', "Aujourd’hui"),
      interLocalResource: resources.some(
        (url) => url.hostname === "127.0.0.1" && /\/assets\/inter-latin-400-normal-.*\.woff2$/.test(url.pathname),
      ),
      urbanistLocalResource: resources.some(
        (url) => url.hostname === "127.0.0.1" && /\/assets\/urbanist-latin-700-normal-.*\.woff2$/.test(url.pathname),
      ),
    };
  });

  expect(fontEvidence.bodyFamily).toMatch(/^Inter\b/);
  expect(fontEvidence.headingFamily).toMatch(/^Urbanist\b/);
  expect(fontEvidence.interFaceCount).toBeGreaterThan(0);
  expect(fontEvidence.urbanistFaceCount).toBeGreaterThan(0);
  expect(fontEvidence.interLoaded).toBe(true);
  expect(fontEvidence.urbanistLoaded).toBe(true);
  expect(fontEvidence.interLocalResource).toBe(true);
  expect(fontEvidence.urbanistLocalResource).toBe(true);
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
