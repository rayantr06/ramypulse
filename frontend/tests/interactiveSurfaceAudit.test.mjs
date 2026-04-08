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

test("AppShell keeps the shared search surface wired through props", () => {
  const source = readComponent("AppShell.tsx");
  assert.ok(source.includes("headerSearchPlaceholder"));
  assert.ok(source.includes("onSearch"));
  assert.ok(source.includes("onChange"));
  assert.ok(source.includes('data-testid="header-search"'));
});

test("Explorer exposes consultable source links without demo-only helpers", () => {
  const source = readPage("Explorateur.tsx");
  assert.ok(!source.includes("demoDisabledProps"));
  assert.ok(source.includes("Voir la source"));
  assert.ok(source.includes('target="_blank"'));
  assert.ok(source.includes("result.source_url"));
});

test("Recommendations routes the AI shortcut to Explorer without decorative card menus", () => {
  const source = readPage("Recommandations.tsx");
  assert.ok(!source.includes("more_vert"), "Recommandations still renders a decorative kebab menu");
  assert.ok(source.includes('href="/explorateur"'));
  assert.ok(source.includes('data-testid="recommendations-ai-shortcut"'));
});

test("Campaigns exposes create and impact flows without demo-only export flags", () => {
  const source = readPage("Campagnes.tsx");
  assert.ok(!source.includes("demoDisabledProps"));
  assert.ok(source.includes("Lancer la Campagne"));
  assert.ok(source.includes("/impact"));
});

test("Admin Sources mounts the real ops console without demo-only markers", () => {
  const source = readPage("AdminSources.tsx");
  assert.ok(!source.includes("demoDisabledProps"));
  assert.ok(source.includes("AdminSourcesOps"));
});
