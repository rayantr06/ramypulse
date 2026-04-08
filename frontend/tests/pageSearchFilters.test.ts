import assert from "node:assert/strict";
import test from "node:test";

import {
  filterAlertViews,
  filterCampaignViews,
  filterRecommendationViews,
  filterWatchlistViews,
} from "../client/src/lib/pageSearchFilters";

test("filterWatchlistViews matches by name, description, and scope", () => {
  const items = [
    {
      id: "watch-1",
      name: "NSS Oran",
      description: "Surveille Oran",
      scope: "REGION",
    },
    {
      id: "watch-2",
      name: "Prix Alger",
      description: "Veille prix",
      scope: "CHANNEL",
    },
  ];

  assert.deepEqual(
    filterWatchlistViews(items, "oran").map((item) => item.id),
    ["watch-1"],
  );
  assert.deepEqual(
    filterWatchlistViews(items, "channel").map((item) => item.id),
    ["watch-2"],
  );
});

test("filterAlertViews matches by title, description, location, and excerpt text", () => {
  const items = [
    {
      id: "alert-1",
      title: "Baisse NSS Oran",
      description: "Le goût se dégrade",
      location: "Oran",
      social_excerpts: [{ text: "Le goût est mauvais" }],
    },
    {
      id: "alert-2",
      title: "Prix Alger",
      description: "Hausse tarifaire",
      location: "Alger",
      social_excerpts: [],
    },
  ];

  assert.deepEqual(
    filterAlertViews(items, "mauvais").map((item) => item.id),
    ["alert-1"],
  );
  assert.deepEqual(
    filterAlertViews(items, "alger").map((item) => item.id),
    ["alert-2"],
  );
});

test("filterRecommendationViews matches by title, rationale, provider, and trigger", () => {
  const items = [
    {
      id: "rec-1",
      title: "Contrôle qualité",
      rationale: "Le goût à Oran se dégrade",
      provider: "google_gemini",
      model: "gemini-2.5-flash",
      trigger: "Depuis une alerte",
      summary: "Résumé 1",
      target: "Instagram",
    },
    {
      id: "rec-2",
      title: "Campagne prix",
      rationale: "Renforcer la promo Alger",
      provider: "openai",
      model: "gpt-4o",
      trigger: "Manuel",
      summary: "Résumé 2",
      target: "Facebook",
    },
  ];

  assert.deepEqual(
    filterRecommendationViews(items, "gemini").map((item) => item.id),
    ["rec-1"],
  );
  assert.deepEqual(
    filterRecommendationViews(items, "promo").map((item) => item.id),
    ["rec-2"],
  );
});

test("filterCampaignViews matches by campaign, influencer, platform, and keywords", () => {
  const items = [
    {
      id: "camp-1",
      name: "Ramy Été",
      influencer: "@rifka",
      platform: "instagram",
      keywords: ["#ramy", "#citron"],
      status: "ACTIVE",
    },
    {
      id: "camp-2",
      name: "Promo Prix",
      influencer: "@amine",
      platform: "facebook",
      keywords: ["#promo", "#alger"],
      status: "PLANIFIEE",
    },
  ];

  assert.deepEqual(
    filterCampaignViews(items, "rifka").map((item) => item.id),
    ["camp-1"],
  );
  assert.deepEqual(
    filterCampaignViews(items, "promo").map((item) => item.id),
    ["camp-2"],
  );
});
