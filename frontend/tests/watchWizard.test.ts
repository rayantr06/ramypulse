import assert from "node:assert/strict";
import test from "node:test";

import {
  buildWatchWizardPayload,
  suggestBrandKeywords,
} from "../client/src/lib/watchWizard";

test("suggestBrandKeywords splits a brand seed into prioritized search variants", () => {
  assert.deepEqual(suggestBrandKeywords("Cevital Elio"), [
    "cevital elio",
    "cevital",
    "elio",
  ]);
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
        keywords: ["cevital elio", "cevital", "elio"],
        seed_urls: ["https://example.test/brand", "https://example.test/product"],
        competitors: ["Ifri", "Hamoud"],
        channels: ["facebook", "instagram"],
        languages: ["fr", "ar"],
        hashtags: ["#elio", "#cevital"],
      },
    },
  );
});
