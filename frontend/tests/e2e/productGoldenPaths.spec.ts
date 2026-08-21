import { expect, test, type Page } from "@playwright/test";

const explorerAnnotationV04 = {
  schema_version: "0.4.0",
  is_exploitable: true,
  non_exploitable_reason: null,
  business_relevance: "directe",
  author_role: "consommateur",
  requires_parent_context: false,
  language: { dominant: "francais", detected: ["francais"], code_switching: false, scripts: ["latin"] },
  entities: [{ id: "ent_1", type: "produit", name: "YaghurtPlus", mention: null, source: "contexte" }],
  sentiment: {
    label: "negatif",
    intensity: "forte",
    emotion: "deception",
    sarcasm: false,
    target_entity_ids: ["ent_1"],
    evidence: [{ text: "goût est mauvais", start: 3, end: 19 }],
  },
  intents: ["plainte", "partage_experience"],
  aspects: [{
    family: "produit_service",
    attribute: "gout",
    target_entity_id: "ent_1",
    sentiment: "negatif",
    intensity: "forte",
    implicit: false,
    evidence: [{ text: "goût est mauvais", start: 3, end: 19 }],
  }],
  alerts: [],
  actionability: { actionable: true, queue: "produit", priority: "moyenne" },
};

async function seedReadyTenant(page: Page, clientId = "tenant-ready", resetStorageOnNavigation = true) {
  await page.addInitScript(({ tenant, resetStorage }) => {
    if (resetStorage) localStorage.clear();
    localStorage.setItem("ramypulse.activeTenantId", tenant);
  }, { tenant: clientId, resetStorage: resetStorageOnNavigation });

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
        recommendation_count: 1,
        top_aspect: "gout",
        top_channel: "facebook",
      },
    });
  });
}

async function mockExplorerApi(page: Page) {
  await page.route("**/api/explorer/search**", async (route) => {
    await route.fulfill({
      json: {
        query: "Que pensent les clients du goût ?",
        total: 1,
        results: [{
          text: "Le goût est mauvais",
          channel: "facebook",
          source_url: "https://facebook.com/posts/1",
          timestamp: "2026-04-04T09:00:00Z",
          aspect: "gout",
          sentiment_label: "negatif",
          score: 0.01639344,
          annotation: explorerAnnotationV04,
          model_version: "lidal-slm-search-s1",
          compiler_version: "compiler-v0.4",
          validation_status: "valid",
        }],
      },
    });
  });
  await page.route("**/api/explorer/verbatims**", async (route) => {
    await route.fulfill({ json: { results: [], total: 0, page: 1, page_size: 50, total_pages: 0 } });
  });
}

test("Explorer search shows consultable cited sources", async ({ page }) => {
  await seedReadyTenant(page);
  await mockExplorerApi(page);
  await page.goto("/#/explorateur");
  await page.getByTestId("search-input").fill("Que pensent les clients du goût ?");
  await page.getByTestId("btn-search").click();

  await expect(page.getByTestId("explorer-ai-insight")).toBeVisible();
  await expect(page.getByText("Voir la source").first()).toHaveAttribute(
    "href",
    "https://facebook.com/posts/1",
  );
  await page.getByRole("button", { name: "Ouvrir le dossier" }).first().click();
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("SLM 0.4.0");
  await expect(page.getByTestId("signal-analysis-panel")).toContainText("Plainte");
});

test("Assisted monitor creation asks for three decisions then confirms the scope", async ({ page }) => {
  await seedReadyTenant(page);
  await page.goto("/#/watchlists");
  await page.getByRole("button", { name: "Créer une surveillance" }).click();

  await page.getByLabel("1. Cible").fill("Algérie Télécom");
  await page
    .getByLabel("Résultat recherché")
    .fill("Détecter les problèmes récurrents de connexion et de service client");
  await page.getByRole("button", { name: "Préparer le périmètre" }).click();

  await expect(page.getByText("Périmètre préparé")).toBeVisible();
  await expect(page.getByText("Facebook · YouTube · Google Maps")).toBeVisible();
  await page.getByRole("button", { name: "Confirmer et lancer" }).click();
  await expect(page).toHaveURL(/#\/watchlists$/);
  await expect(page.getByRole("heading", { name: "Algérie Télécom" })).toBeVisible();
});

test("A signal exposes its evidence and can be converted into a case", async ({ page }) => {
  await seedReadyTenant(page);
  await page.goto("/#/signals");

  await expect(page.getByRole("heading", { name: "Pourquoi ce signal existe" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Preuves reliées" })).toBeVisible();
  await expect(page.getByText("Ma l9itch le produit fi Oran", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Ouvrir un dossier" }).click();
  await page.getByLabel("Responsable").fill("Nadia B.");
  await page.getByRole("button", { name: "Confirmer le dossier" }).click();
  await expect(page.getByText("Dossier créé", { exact: true })).toBeVisible();
});

test("Agent LIDAL only produces a cited draft", async ({ page }) => {
  await seedReadyTenant(page);
  await page.goto("/#/actions");

  await expect(page.getByText("Analyse et brouillons uniquement")).toBeVisible();
  await page.getByRole("button", { name: "Préparer un plan" }).click();
  await expect(page.getByText("Brouillon · validation requise")).toBeVisible();
  await expect(page.getByText("Ce brouillon ne déclenche aucune action externe.", { exact: false })).toBeVisible();
});

test("Legacy recommendations route redirects to the V3 action workspace", async ({ page }) => {
  await seedReadyTenant(page);
  await page.goto("/#/recommandations");
  await expect(page).toHaveURL(/#\/actions$/);
  await expect(page.getByRole("heading", { name: "Actions" })).toBeVisible();
});

test("public QR feedback returns to the point as pending", async ({ context, page }) => {
  await seedReadyTenant(page, "demo-expo-2026", false);
  await page.goto("/#/listening-points");
  const popupPromise = context.waitForEvent("page");
  await page.getByRole("link", { name: "Tester le formulaire" }).click();
  const feedback = await popupPromise;
  await feedback.getByRole("radio", { name: "2 étoiles" }).click();
  await feedback.getByLabel("Votre message").fill("Ma l9itch le produit fi Oran.");
  await feedback.getByRole("checkbox").check();
  await feedback.getByRole("button", { name: "Envoyer mon retour" }).click();
  await expect(feedback.getByText("En attente d’analyse")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("pending-submission")).toContainText("Ma l9itch le produit fi Oran.");
});

test("a created listening point hides its disabled public channel", async ({ context, page }) => {
  await seedReadyTenant(page, "demo-expo-2026", false);
  await page.goto("/#/listening-points/new");
  await expect(page.getByRole("heading", { name: "Créer un point d’écoute" })).toBeVisible();
  await expect(page.getByText("Note", { exact: true })).toHaveCount(0);
  await page.getByLabel("Nom de la cible").fill("Rayon boissons Oran");
  await page.getByLabel("Nom interne").fill("QR texte uniquement");
  await page.getByLabel("Personne responsable").fill("Nadia B.");
  await page.getByText("Audio", { exact: true }).click();
  await page.getByRole("button", { name: "Créer le QR" }).click();

  await page.getByRole("button", { name: /QR texte uniquement/ }).click();
  const popupPromise = context.waitForEvent("page");
  await page.getByRole("link", { name: "Tester le formulaire" }).click();
  const feedback = await popupPromise;

  await expect(feedback.getByRole("radio", { name: "5 étoiles" })).toBeVisible();
  await expect(feedback.getByLabel("Votre message")).toBeVisible();
  await expect(feedback.getByText("Durée audio locale")).toHaveCount(0);
  await feedback.getByLabel("Votre message").fill("Message avec note obligatoire.");
  await feedback.getByRole("checkbox").check();
  await feedback.getByRole("button", { name: "Envoyer mon retour" }).click();
  await expect(feedback.getByText("Choisissez une note.")).toBeVisible();
});
