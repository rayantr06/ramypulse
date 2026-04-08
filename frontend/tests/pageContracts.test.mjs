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

test("Watchlists page exposes a create flow plus live metrics lookup", () => {
  const source = readPage("Watchlists.tsx");
  assert.ok(source.includes('"/api/watchlists"'));
  assert.ok(source.includes('/api/watchlists/${selectedWatchlist?.id}/metrics'));
  assert.ok(source.includes("scope_type"));
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
  assert.ok(source.includes("Lancer la Campagne"));
  assert.ok(source.includes("/impact"));
});

test("Admin Sources composes the real operations surface", () => {
  const source = readPage("AdminSources.tsx");
  assert.ok(source.includes("AdminSourcesOps"));
  assert.ok(source.includes("RamyPulse Admin"));
});
