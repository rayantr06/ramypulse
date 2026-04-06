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

test("AppShell marks shell-only controls as explicitly non-interactive", () => {
  const source = readComponent("AppShell.tsx");
  assert.ok(source.includes('demoDisabledProps("language")'));
  assert.ok(source.includes('demoDisabledProps("grid_view")'));
  assert.ok(source.includes('demoDisabledProps("notifications")'));
  assert.ok(source.includes('demoDisabledProps("sensors")'));
});

test("Explorer keeps decorative controls explicitly tagged and source links real", () => {
  const source = readPage("Explorateur.tsx");
  assert.ok(source.includes('demoDisabledProps("explorer-filter")'));
  assert.ok(source.includes('demoDisabledProps("explorer-export")'));
  assert.ok(source.includes("Voir la source"));
  assert.ok(source.includes('target="_blank"'));
  assert.ok(source.includes("result.source_url"));
});

test("Recommendations no longer exposes a decorative card menu and routes the AI shortcut", () => {
  const source = readPage("Recommandations.tsx");
  assert.ok(!source.includes("more_vert"), "Recommandations still renders a decorative kebab menu");
  assert.ok(source.includes('href="/explorateur"'));
});

test("Campaigns exposes a real create path and tags export as shell-only", () => {
  const source = readPage("Campagnes.tsx");
  assert.ok(source.includes("scrollIntoView"));
  assert.ok(source.includes('demoDisabledProps("campaign-export")'));
});

test("Admin shell tags every non-operational control instead of leaving naked links", () => {
  const source = readPage("AdminSources.tsx");
  assert.ok(source.includes('demoDisabledProps("admin-top-pipelines")'));
  assert.ok(source.includes('demoDisabledProps("admin-top-logs")'));
  assert.ok(source.includes('demoDisabledProps("admin-new-pipeline")'));
  assert.ok(source.includes('demoDisabledProps("admin-support")'));
  assert.ok(source.includes('demoDisabledProps("admin-docs")'));
});
