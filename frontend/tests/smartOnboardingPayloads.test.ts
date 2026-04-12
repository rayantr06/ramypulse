import assert from "node:assert/strict";
import test from "node:test";

import type { OnboardingAnalysis } from "../client/src/lib/apiMappings";
import { buildSmartOnboardingConfirmPayload } from "../client/src/lib/watchWizard";

const analysis: OnboardingAnalysis = {
  tenant_setup: {
    client_name: "Yaghurt Plus",
    client_slug: "yaghurt-plus",
    country: "DZ",
  },
  suggested_sources: [
    {
      type: "website",
      label: "Site officiel",
      url: "https://yaghurt.example",
      channel: "public_url_seed",
      confidence: 0.98,
      status: "suggested_only",
      reason: "Site detecte",
    },
    {
      type: "facebook_page",
      label: "Yaghurt Plus DZ",
      url: "https://facebook.com/yaghurtplus",
      channel: "facebook",
      confidence: 0.91,
      status: "requires_credentials",
      reason: "Page officielle",
    },
  ],
  required_credentials: [],
  recommended_channels: [
    { channel: "public_url_seed", enabled_by_default: true, reason: "Seed" },
    { channel: "web_search", enabled_by_default: true, reason: "Discovery" },
    { channel: "facebook", enabled_by_default: true, reason: "Page" },
  ],
  suggested_watchlists: [
    {
      name: "Yaghurt Plus watch seed",
      description: "Seed watchlist",
      scope_type: "watch_seed",
      role: "seed",
      filters: { brand_name: "Yaghurt Plus", keywords: ["yaghurt plus"], seed_urls: [] },
      enabled_by_default: true,
      reason: "Seed",
    },
    {
      name: "Yaghurt Plus produit",
      description: "Produit",
      scope_type: "product",
      role: "analysis",
      filters: { product: "yaourt", period_days: 7, min_volume: 10 },
      enabled_by_default: true,
      reason: "Produit",
    },
    {
      name: "Yaghurt Plus canal",
      description: "Canal",
      scope_type: "channel",
      role: "analysis",
      filters: { channel: "facebook", period_days: 7, min_volume: 10 },
      enabled_by_default: true,
      reason: "Canal",
    },
  ],
  suggested_alert_profiles: [
    {
      watchlist_ref: "yaghurt-plus-canal",
      profile_name: "Veille Facebook",
      enabled_by_default: true,
      rules: [
        {
          rule_id: "negative_volume_surge",
          threshold_value: 60,
          comparator: "gt",
          lookback_window: "7d",
          severity_level: "high",
          reason: "Pic negatif",
        },
      ],
      reason: "Profile",
    },
  ],
  deferred_agent_config: [
    {
      key: "weekly_digest",
      value: true,
      reason: "Differe",
    },
  ],
  warnings: [],
  fallback_used: false,
};

test("buildSmartOnboardingConfirmPayload preserves the reviewed snake_case contract", () => {
  const payload = buildSmartOnboardingConfirmPayload({
    analysis,
    brand_name: "Yaghurt Plus",
    selected_source_urls: ["https://yaghurt.example", "https://facebook.com/yaghurtplus"],
    selected_channels: ["public_url_seed", "web_search", "facebook"],
    selected_watchlist_names: ["Yaghurt Plus watch seed", "Yaghurt Plus produit", "Yaghurt Plus canal"],
    selected_alert_profile_names: ["Veille Facebook"],
  });

  assert.deepEqual(payload, {
    review_confirmed: true,
    tenant_setup: analysis.tenant_setup,
    brand_name: "Yaghurt Plus",
    selected_sources: analysis.suggested_sources,
    selected_channels: ["public_url_seed", "web_search", "facebook"],
    selected_watchlists: analysis.suggested_watchlists,
    selected_alert_profiles: analysis.suggested_alert_profiles,
    deferred_agent_config: analysis.deferred_agent_config,
  });
});
