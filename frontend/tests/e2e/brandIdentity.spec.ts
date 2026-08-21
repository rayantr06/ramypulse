import { expect, test } from "@playwright/test";

test("Leticia demo uses the official local LIDAL mark", async ({ page }) => {
  await page.goto("/#/");
  const logo = page.getByRole("img", { name: "LIDAL Pulse" }).first();
  await expect(logo).toHaveAttribute("src", /\/brand\/lidal-mark-dark\.png$/);
  const response = await page.request.get("/brand/lidal-mark-dark.png");
  expect(response.ok()).toBeTruthy();
});
