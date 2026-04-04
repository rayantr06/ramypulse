import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pagesDir = path.resolve(__dirname, "../client/src/pages");
const componentsDir = path.resolve(__dirname, "../client/src/components");

function readPage(name) {
  return readFileSync(path.join(pagesDir, name), "utf8");
}

function readComponent(name) {
  return readFileSync(path.join(componentsDir, name), "utf8");
}

function contains(source, text) {
  assert.ok(source.includes(text), `Expected source to contain: ${text}`);
}

function lacks(source, text) {
  assert.ok(!source.includes(text), `Expected source not to contain: ${text}`);
}

test("Dashboard keeps Stitch headline copy", () => {
  const source = readPage("Dashboard.tsx");
  contains(source, "Direct Temps Réel");
  contains(source, "Algérie (Toutes régions)");
  contains(source, "ACTIONS RECOMMANDÉES PAR L'IA");
  contains(source, "VENTES PAR PRODUIT (7 JOURS)");
  contains(source, "DISTRIBUTION RÉGIONALE");
  lacks(source, "Direct Temps Reel");
  lacks(source, "Algerie (Toutes regions)");
});

test("Recommandations keeps Stitch form labels and stats copy", () => {
  const source = readPage("Recommandations.tsx");
  contains(source, "Générer des recommandations");
  contains(source, "Type de Déclencheur");
  contains(source, "Nom du Modèle / Endpoint");
  contains(source, "Coût est.");
  contains(source, "Historique des runs");
  lacks(source, "Generer des recommandations");
  lacks(source, "Type de Declencheur");
  lacks(source, "Provider actif");
});

test("Recommandations keeps Stitch active analysis cards and actions", () => {
  const source = readPage("Recommandations.tsx");
  contains(source, "Volume (m³)");
  contains(source, "Dernière run");
  contains(source, "Tout Archiver");
  contains(source, "Actions recommandées");
});

test("Watchlists keeps Stitch CTA copy", () => {
  const source = readPage("Watchlists.tsx");
  contains(source, "Créer une watchlist");
  contains(source, "SÉLECTION");
  contains(source, "Répartition par Aspect");
  contains(source, "Voir les détails analytiques");
  lacks(source, "Création via back-office");
});

test("Alertes keeps Stitch real-time excerpt label", () => {
  const source = readPage("Alertes.tsx");
  contains(source, "Extraits Sociaux (Temps Réel)");
  lacks(source, "Extraits Sociaux (Temps Reel)");
});

test("Alertes keeps Stitch console labels and actions", () => {
  const source = readPage("Alertes.tsx");
  contains(source, "Système en ligne");
  contains(source, "Sévérité");
  contains(source, "Détails de l'Alerte");
  contains(source, "Impact Estimé");
  contains(source, "Reconnaître");
  contains(source, "Résoudre");
});

test("Campagnes keeps Stitch capitalization and accents", () => {
  const source = readPage("Campagnes.tsx");
  contains(source, "Gestion Opérationnelle");
  contains(source, "CRÉER UNE CAMPAGNE");
  contains(source, "Début");
  contains(source, "Mots-clés");
  lacks(source, "Gestion Operationnelle");
  lacks(source, "CREER UNE CAMPAGNE");
});

test("Campagnes keeps Stitch structure for table and performance cards", () => {
  const source = readPage("Campagnes.tsx");
  contains(source, "Top Performeur (Mois)");
  contains(source, "Budget Total Engagé");
  contains(source, "Campagne / Influenceur");
  contains(source, "Impact NSS");
  contains(source, "Page ${safeCurrentPage} de ${totalPages}");
  contains(source, "Ramy Pulse Pro");
  contains(source, "Influenceur Algerien");
  contains(source, "allocation trimestrielle");
});

test("Explorateur keeps Stitch search copy", () => {
  const source = readPage("Explorateur.tsx");
  contains(source, "Recherche sémantique et verbatims à travers l'écosystème digital");
  contains(source, "Que pensent les clients du goût à Alger ?");
  contains(source, "Base de données complète des interactions clients");
});

test("AdminSources keeps Stitch labels and dedicated admin shell", () => {
  const source = readPage("AdminSources.tsx");
  contains(source, "function AdminShell");
  contains(source, "RamyPulse Admin");
  contains(source, "STITCH_AVATARS.admin.alt");
  contains(source, "COMMAND CENTER");
  contains(source, "New Pipeline");
  contains(source, "SOURCES DE DONNÉES");
  contains(source, "PIPELINE TRACE & DÉBIT");
  lacks(source, "import { AppShell }");
  lacks(source, "SOURCES DE DONNEES");
  lacks(source, "PIPELINE TRACE & DEBIT");
});

test("Shared product shell keeps Stitch branding and avatar", () => {
  const appShell = readComponent("AppShell.tsx");
  const sidebar = readComponent("Sidebar.tsx");
  contains(appShell, "avatarSrc = STITCH_AVATARS.dashboard.src");
  contains(appShell, "avatarAlt = STITCH_AVATARS.dashboard.alt");
  contains(sidebar, "Marketing Intelligence");
  contains(sidebar, "Ammar, Brand Manager");
});

test("Pages wire Stitch-specific header avatars", () => {
  contains(readPage("Watchlists.tsx"), "STITCH_AVATARS.watchlists.src");
  contains(readPage("Explorateur.tsx"), "STITCH_AVATARS.explorateur.src");
  contains(readPage("Recommandations.tsx"), "STITCH_AVATARS.recommandations.src");
  contains(readPage("Alertes.tsx"), "STITCH_AVATARS.alertes.src");
  contains(readPage("Campagnes.tsx"), "STITCH_AVATARS.campagnes.src");
  contains(readPage("AdminSources.tsx"), "STITCH_AVATARS.admin.src");
});
