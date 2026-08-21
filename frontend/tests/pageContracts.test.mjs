import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagesDir = path.resolve(__dirname, "../client/src/pages");

function readPage(name) {
  return readFileSync(path.join(pagesDir, name), "utf8");
}

test("Surveillances exposes the V3 assisted composer and tenant-scoped monitor cache", () => {
  const source = readPage("Watchlists.tsx");
  const composer = readFileSync(
    path.resolve(__dirname, "../client/src/components/watch/V3MonitorComposer.tsx"),
    "utf8",
  );
  assert.ok(source.includes('"/api/v3/monitors"'));
  assert.ok(source.includes("useV3Monitors"));
  assert.ok(composer.includes("target_type"));
  assert.ok(composer.includes("max_monthly_documents"));
  assert.ok(composer.includes("Préparer le périmètre"));
});

test("V3 operational pages preserve the signal to action chain", () => {
  const signals = readPage("Signals.tsx");
  const actions = readPage("Actions.tsx");
  const dashboard = readPage("Dashboard.tsx");
  assert.ok(signals.includes("Pourquoi ce signal existe"));
  assert.ok(signals.includes("Preuves reliées"));
  assert.ok(signals.includes("Ouvrir un dossier"));
  assert.ok(actions.includes("Agent LIDAL"));
  assert.ok(actions.includes("Analyse et brouillons uniquement"));
  assert.ok(dashboard.includes("Mentions qualifiées"));
  assert.ok(dashboard.includes("Couverture analytique"));
});

test("Explorer exposes consultable source links for cited and ranked results", () => {
  const source = readPage("Explorateur.tsx");
  assert.ok(source.includes("Voir la source"));
  assert.ok(source.includes("result.source_url"));
  assert.ok(source.includes('target="_blank"'));
});

test("Campaigns page exposes create and impact flows", () => {
  const source = readPage("Campagnes.tsx");
  assert.ok(source.includes('"/api/campaigns"'));
  assert.ok(source.includes("Créer la campagne"));
  assert.ok(source.includes("/impact"));
});

test("Admin Sources composes the real operations surface", () => {
  const source = readPage("AdminSources.tsx");
  assert.ok(source.includes("AdminSourcesOps"));
  assert.ok(source.includes("AppShell"));
  assert.ok(source.includes('data-testid="admin-shell-canvas"'));
});

test("Watch onboarding exposes the watch-first wizard and progress handoff", () => {
  const source = readPage("WatchOnboarding.tsx");
  assert.ok(source.includes("WatchOnboardingWizard"));
  assert.ok(source.includes("RunProgressPanel"));
  assert.ok(source.includes("getStoredOnboardingRun"));
});

test("Campaigns page keeps a visible beta badge", () => {
  const source = readPage("Campagnes.tsx");
  assert.ok(source.includes("Beta"));
});

test("Product routing uses an initialization gate instead of tenant id only", () => {
  const productHome = readPage("ProductHome.tsx");
  const appSource = readFileSync(path.resolve(__dirname, "../client/src/App.tsx"), "utf8");
  assert.ok(productHome.includes("TenantInitializationGate"));
  assert.ok(appSource.includes("useTenantReadiness"));
});

test("Run progress panel exposes operator failure controls", () => {
  const source = readFileSync(
    path.resolve(__dirname, "../client/src/components/watch/RunProgressPanel.tsx"),
    "utf8",
  );
  assert.ok(source.includes("Une etape a echoue"));
  assert.ok(source.includes("Relancer l'initialisation"));
});

test("QR listening pages expose the reliable recording path", () => {
  const points = readPage("ListeningPoints.tsx");
  const feedback = readPage("PublicFeedback.tsx");
  const reset = readPage("DemoReset.tsx");
  assert.ok(points.includes('data-testid="listening-point-qr"'));
  assert.ok(points.includes("Tester le formulaire"));
  assert.ok(feedback.includes('data-testid="public-feedback-form"'));
  assert.ok(feedback.includes("En attente d’analyse"));
  assert.ok(reset.includes("resetLeticiaDemoState"));
});
