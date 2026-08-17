import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagesDir = path.resolve(__dirname, "../client/src/pages");
const componentsDir = path.resolve(__dirname, "../client/src/components");
const adminComponentsDir = path.resolve(__dirname, "../client/src/components/admin");

function readPage(name) {
  return readFileSync(path.join(pagesDir, name), "utf8");
}

function readComponent(name) {
  return readFileSync(path.join(componentsDir, name), "utf8");
}

function readAdminComponent(name) {
  return readFileSync(path.join(adminComponentsDir, name), "utf8");
}

function contains(source, text) {
  assert.ok(source.includes(text), `Expected source to contain: ${text}`);
}

function lacks(source, text) {
  assert.ok(!source.includes(text), `Expected source not to contain: ${text}`);
}

test("Dashboard exposes a plain-language alert-to-action flow", () => {
  const source = readPage("Dashboard.tsx");
  contains(source, 'title="Situation du jour"');
  contains(source, "Du signal à la décision");
  contains(source, "1 · Signal détecté");
  contains(source, "2 · Ce que cela signifie");
  contains(source, "3 · Décision proposée");
  contains(source, "File de traitement");
  contains(source, "Performance par produit");
  contains(source, "Répartition par wilaya");
  contains(source, "Vérifier les sources de données");
  lacks(source, "/api/status");
  lacks(source, "API Status:");
  lacks(source, "Latency:");
});

test("Recommandations keeps professional form labels and stats copy", () => {
  const source = readPage("Recommandations.tsx");
  contains(source, 'eyebrow="Agir"');
  contains(source, 'title="Actions recommandées"');
  contains(source, "Type de Déclencheur");
  contains(source, "Nom du Modèle / Endpoint");
  contains(source, "Coût est.");
  contains(source, "Historique des runs");
  lacks(source, "Generer");
  lacks(source, "Type de Declencheur");
  lacks(source, "Provider actif");
});

test("Recommandations keeps active analysis cards and actions", () => {
  const source = readPage("Recommandations.tsx");
  contains(source, "Volume mentions");
  contains(source, "Dernière run");
  contains(source, "Tout Archiver");
  contains(source, "Actions recommandées");
});

test("Watchlists keeps surveillance CTA copy", () => {
  const source = readPage("Watchlists.tsx");
  contains(source, "Créer une surveillance");
  contains(source, "SÉLECTION");
  contains(source, "Répartition par Aspect");
  contains(source, "Voir les détails analytiques");
  lacks(source, "Création via back-office");
});

test("Alertes names evidence in plain language", () => {
  const source = readPage("Alertes.tsx");
  contains(source, "Avis à l’origine de l’alerte");
  contains(source, "Extraits consultables pour vérifier l’interprétation");
  lacks(source, "Extraits Sociaux (Temps Réel)");
});

test("Alertes keeps explicit labels and actions", () => {
  const source = readPage("Alertes.tsx");
  contains(source, "alertes actives");
  contains(source, 'title="Alertes à traiter"');
  contains(source, "Sévérité");
  contains(source, "Ce qui a été détecté");
  contains(source, "Impact Estimé");
  contains(source, "Marquer comme prise en charge");
  contains(source, "Marquer comme résolue");
});

test("Campagnes keeps professional capitalization and accents", () => {
  const source = readPage("Campagnes.tsx");
  contains(source, 'eyebrow="Comprendre"');
  contains(source, 'title="Impact des campagnes"');
  contains(source, "Créer une campagne");
  contains(source, "Début");
  contains(source, "Mots-clés");
  lacks(source, "Gestion Operationnelle");
  lacks(source, "Creer une campagne");
});

test("Campagnes keeps Stitch structure while dropping fake performance numbers", () => {
  const source = readPage("Campagnes.tsx");
  contains(source, "Top Performeur (Mois)");
  contains(source, "Budget Total Engagé");
  contains(source, "Campagne / Influenceur");
  contains(source, "Impact NSS");
  contains(source, "Page ${safeCurrentPage} de ${totalPages}");
  contains(source, "LIDAL Pulse Pro");
  contains(source, "Influenceur Algerien");
  contains(source, "allocation trimestrielle");
  contains(source, "/api/campaigns/overview");
  lacks(source, "6_320_000");
  lacks(source, "ROI 4.2x");
  lacks(source, "+18% Engagement");
});

test("Explorateur keeps evidence-oriented search copy", () => {
  const source = readPage("Explorateur.tsx");
  contains(source, 'title="Explorer les avis clients"');
  contains(source, "consultez les verbatims, leurs sources");
  contains(source, "Que pensent les clients du goût à Alger ?");
  contains(source, "Base de données complète des interactions clients");
});

test("Explorateur keeps Stitch relative date and sentiment labels", () => {
  const source = readPage("Explorateur.tsx");
  contains(source, "Aujourd'hui");
  contains(source, "Hier");
  contains(source, "Très Positif");
  contains(source, "Négatif");
});

test("AdminSources uses the shared product shell and keeps operations labels", () => {
  const page = readPage("AdminSources.tsx");
  const ops = readAdminComponent("AdminSourcesOps.tsx");
  const sources = readAdminComponent("AdminSourcesView.tsx");
  const scheduler = readAdminComponent("AdminSchedulerView.tsx");
  const campaignOps = readAdminComponent("AdminCampaignOpsView.tsx");
  contains(page, "import { AppShell }");
  contains(page, "STITCH_AVATARS.admin.alt");
  contains(page, 'data-testid="admin-shell-canvas"');
  contains(page, "sidebarFooterSubtitle");
  contains(sources, "Gouvernance source");
  contains(ops, "Credentials");
  contains(ops, "Campaign Ops");
  contains(ops, "Scheduler");
  contains(ops, "Centre de contrôle des sources");
  contains(ops, "Opérations & qualité des données");
  contains(sources, "SOURCES DE DONNÉES");
  contains(sources, "PIPELINE TRACE & DÉBIT");
  contains(scheduler, "Run due syncs");
  contains(campaignOps, "Retirer le post");
  lacks(sources, "SOURCES DE DONNEES");
  lacks(sources, "PIPELINE TRACE & DEBIT");
});

test("AdminSources page no longer carries legacy admin logic", () => {
  const page = readPage("AdminSources.tsx");
  lacks(page, "function LegacyAdminSources");
  lacks(page, "interface SourceFormState");
  lacks(page, "function mapSourceView");
  lacks(page, "function buildLastSync");
  contains(page, "<AdminSourcesOps />");
});

test("Shared product shell exposes clear navigation and a persistent create action", () => {
  const appShell = readComponent("AppShell.tsx");
  const sidebar = readComponent("Sidebar.tsx");
  const navigation = readFileSync(
    path.resolve(__dirname, "../client/src/lib/productNavigation.ts"),
    "utf8",
  );
  lacks(appShell, "PRODUCT_STAGES");
  contains(appShell, 'data-testid="header-new-watch"');
  contains(appShell, "MobileNavigation");
  contains(sidebar, "BrandMark");
  contains(sidebar, "PRODUCT_NAV_GROUPS");
  contains(navigation, "Surveiller");
  contains(navigation, "Comprendre");
  contains(navigation, "Agir");
  contains(navigation, "Sources de données");
});

test("Core product pages use the shared shell and surveillance uses a focused drawer", () => {
  contains(readPage("Watchlists.tsx"), "<AppShell");
  contains(readPage("Watchlists.tsx"), "<SheetContent");
  contains(readPage("Explorateur.tsx"), "<AppShell");
  contains(readPage("Recommandations.tsx"), "<AppShell");
  contains(readPage("Alertes.tsx"), "<AppShell");
  contains(readPage("Campagnes.tsx"), "<AppShell");
  contains(readPage("AdminSources.tsx"), "<AppShell");
});

test("Recommandations keeps hook declarations before any early empty-state return", () => {
  const source = readPage("Recommandations.tsx");
  assert.ok(
    source.indexOf("const runHistory = useMemo") <
      source.indexOf("if (!recoLoading && (recommendations ?? []).length === 0)"),
    "Recommandations declares hooks after an early return and can blank the route",
  );
});
