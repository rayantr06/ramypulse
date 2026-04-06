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

test("Watchlists create form exposes real backend filters, not an empty filter payload", () => {
  const source = readPage("Watchlists.tsx");
  assert.ok(!source.includes("filters: {}"), "Watchlists form still posts empty filters");
  assert.ok(source.includes("period_days"), "Watchlists form is missing period_days");
  assert.ok(source.includes("min_volume"), "Watchlists form is missing min_volume");
});

test("Explorer exposes consultable source links for cited and ranked results", () => {
  const source = readPage("Explorateur.tsx");
  assert.ok(source.includes("Voir la source"));
  assert.ok(source.includes("result.source_url"));
  assert.ok(source.includes('target="_blank"'));
});

test("Campaigns main CTA points to a real create flow", () => {
  const source = readPage("Campagnes.tsx");
  assert.ok(source.includes("scrollIntoView"));
});

test("Admin Sources explicitly marks decorative shell controls as non-interactive", () => {
  const source = readPage("AdminSources.tsx");
  assert.ok(source.includes("demoDisabledProps"));
});
