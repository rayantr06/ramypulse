import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", "demo-expo-2026");
  });
  await page.route("**/api/dashboard/summary", async (route) => {
    await route.fulfill({ json: { total_mentions: 8 } });
  });
});

test("recording path explains source to decision without overclaiming", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/#/");

  const sourceFlow = page.getByTestId("demo-source-flow");
  await expect(sourceFlow).toContainText("Facebook");
  await expect(sourceFlow).toContainText("Google Maps");
  await expect(sourceFlow).toContainText("YouTube");
  await expect(sourceFlow).toContainText("Audio autorisé");
  await expect(sourceFlow).toContainText("QR");
  await expect(sourceFlow).toContainText("décision validée par l’équipe");
  await expect(sourceFlow.getByTestId("demo-source-channel")).toHaveText([
    "Facebook",
    "Google Maps",
    "YouTube",
    "Audio autorisé",
    "QR",
  ]);
  await expect(page.getByTestId("card-health-score")).toBeVisible();

  const flowBox = await sourceFlow.boundingBox();
  const kpiBox = await page.getByTestId("card-health-score").boundingBox();
  expect(flowBox).not.toBeNull();
  expect(kpiBox).not.toBeNull();
  expect(flowBox!.y + flowBox!.height).toBeLessThanOrEqual(kpiBox!.y);
  expect(kpiBox!.y + kpiBox!.height).toBeLessThanOrEqual(1080);

  await page.goto("/#/explorateur");
  await expect(page.getByTestId("demo-slm-provenance")).toContainText(
    "Analyse du SLM — exemple de démonstration",
  );
  await expect(page.getByTestId("demo-slm-provenance")).toContainText(
    "Le modèle spécialisé est en cours de validation. Cette sortie préparée montre le contrat produit visé.",
  );
  await expect(page.getByTestId("demo-structured-output")).toContainText("Disponibilité");
  await expect(page.getByTestId("demo-structured-output")).toContainText("Confiance du signal");
  await expect(page.getByTestId("demo-structured-output")).toContainText("91 %");
  await expect(page.getByTestId("signal-analysis-panel")).toContainText(
    "Ma l9itch le produit fi Oran",
  );
  await expect(page.getByTestId("signal-analysis-panel")).not.toContainText(/\d+\s*ms/);
});
