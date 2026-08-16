import assert from "node:assert/strict";
import test from "node:test";

import {
  buildWatchWizardPayload,
  parseDelimitedWatchValues,
  suggestBrandKeywords,
  suggestWatchKeywords,
} from "../client/src/lib/watchWizard";

test("suggestBrandKeywords splits a brand seed into prioritized search variants", () => {
  assert.deepEqual(suggestBrandKeywords("Cevital Elio"), [
    "cevital elio",
    "cevital",
    "elio",
  ]);
});

test("suggestWatchKeywords keeps brand and product phrases independently useful", () => {
  assert.deepEqual(suggestWatchKeywords("Cevital Elio", "Huile Elio"), [
    "cevital elio",
    "cevital",
    "elio",
    "huile elio",
    "huile",
  ]);
});

test("parseDelimitedWatchValues accepts commas, semicolons and line breaks", () => {
  assert.deepEqual(
    parseDelimitedWatchValues(" elio, huile elio;\ncevital\nelio "),
    ["elio", "huile elio", "cevital"],
  );
});

test("buildWatchWizardPayload builds the watch-first watch_seed payload shape", () => {
  assert.deepEqual(
    buildWatchWizardPayload({
      name: "  Veille Elio  ",
      description: "  Surveiller la marque  ",
      brand_name: " Cevital Elio ",
      product_name: " Huile Elio ",
      seed_urls: [" https://example.test/brand ", "", "https://example.test/product "],
      competitors: [" Ifri ", "Hamoud", ""],
      channels: [" facebook ", "instagram", ""],
      languages: [" fr ", "ar", ""],
      hashtags: [" #elio ", "#cevital", ""],
    }),
    {
      name: "Veille Elio",
      description: "Surveiller la marque",
      scope_type: "watch_seed",
      filters: {
        brand_name: "Cevital Elio",
        product_name: "Huile Elio",
        keywords: ["cevital elio", "cevital", "elio", "huile elio", "huile"],
        seed_urls: ["https://example.test/brand", "https://example.test/product"],
        competitors: ["Ifri", "Hamoud"],
        channels: ["facebook", "instagram"],
        languages: ["fr", "ar"],
        hashtags: ["#elio", "#cevital"],
      },
    },
  );
});

test("buildWatchWizardPayload preserves the editable monitoring scope", () => {
  assert.deepEqual(
    buildWatchWizardPayload({
      name: "Veille reputation",
      description: "Surveillance multi-source",
      subject_type: "campaign",
      brand_name: "Ramy",
      product_name: "Ramy Orange",
      keywords: [" Ramy Orange ", "RAMY", "ramy"],
      excluded_keywords: ["emploi", " stage "],
      seed_urls: ["https://example.test/post"],
      competitors: ["Concurrent A"],
      channels: ["WEB_SEARCH", "facebook"],
      languages: ["FR", "ar"],
      regions: ["Alger", " Oran "],
      period_days: 30.9,
      min_volume: -2,
    }),
    {
      name: "Veille reputation",
      description: "Surveillance multi-source",
      scope_type: "watch_seed",
      filters: {
        brand_name: "Ramy",
        product_name: "Ramy Orange",
        keywords: ["ramy orange", "ramy"],
        seed_urls: ["https://example.test/post"],
        competitors: ["Concurrent A"],
        channels: ["web_search", "facebook"],
        languages: ["fr", "ar"],
        hashtags: [],
        subject_type: "campaign",
        excluded_keywords: ["emploi", "stage"],
        regions: ["Alger", "Oran"],
        period_days: 30,
        min_volume: 0,
      },
    },
  );
});
