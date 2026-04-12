import type {
  OnboardingAnalysis,
  WatchSeedFilters,
  WatchlistCreatePayload,
} from "./apiMappings";

export interface WatchWizardInput {
  name: string;
  description?: string;
  brand_name: string;
  product_name?: string;
  seed_urls?: string[];
  competitors?: string[];
  channels?: string[];
  languages?: string[];
  hashtags?: string[];
}

export interface SmartOnboardingConfirmInput {
  analysis: OnboardingAnalysis;
  brand_name: string;
  industry?: string;
  selected_source_urls: string[];
  selected_channels: string[];
  selected_watchlist_names: string[];
  selected_alert_profile_names: string[];
}

function normalizeText(value: string | null | undefined): string | null {
  const text = value?.trim() ?? "";
  return text === "" ? null : text;
}

function normalizeStringList(
  values: readonly string[] | null | undefined,
  { lowercase = false }: { lowercase?: boolean } = {},
): string[] {
  if (!values?.length) {
    return [];
  }

  const normalized: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const text = normalizeText(value);
    if (!text) {
      continue;
    }

    const candidate = lowercase ? text.toLowerCase() : text;
    if (seen.has(candidate)) {
      continue;
    }

    seen.add(candidate);
    normalized.push(candidate);
  }

  return normalized;
}

export function suggestBrandKeywords(raw: string): string[] {
  const brand = normalizeText(raw)?.toLowerCase() ?? "";
  if (brand === "") {
    return [];
  }

  const parts = brand
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  const keywords = [brand, ...parts];
  return Array.from(new Set(keywords));
}

export function buildWatchWizardPayload(input: WatchWizardInput): WatchlistCreatePayload {
  const brandName = normalizeText(input.brand_name);
  const filters: WatchSeedFilters = {
    brand_name: brandName,
    product_name: normalizeText(input.product_name),
    keywords: suggestBrandKeywords(brandName ?? ""),
    seed_urls: normalizeStringList(input.seed_urls),
    competitors: normalizeStringList(input.competitors),
    channels: normalizeStringList(input.channels, { lowercase: true }),
    languages: normalizeStringList(input.languages, { lowercase: true }),
    hashtags: normalizeStringList(input.hashtags, { lowercase: true }),
  };

  return {
    name: input.name.trim(),
    description: input.description?.trim() ?? "",
    scope_type: "watch_seed",
    filters,
  };
}

export function buildSmartOnboardingConfirmPayload(
  input: SmartOnboardingConfirmInput,
): Record<string, unknown> {
  const selectedSourceUrls = new Set(normalizeStringList(input.selected_source_urls));
  const selectedWatchlistNames = new Set(normalizeStringList(input.selected_watchlist_names));
  const selectedAlertProfileNames = new Set(normalizeStringList(input.selected_alert_profile_names));
  const normalizedIndustry = normalizeText(input.industry);

  return {
    review_confirmed: true,
    tenant_setup: input.analysis.tenant_setup,
    brand_name: normalizeText(input.brand_name) ?? input.analysis.tenant_setup.client_name,
    ...(normalizedIndustry ? { industry: normalizedIndustry } : {}),
    selected_sources: input.analysis.suggested_sources.filter((source) =>
      selectedSourceUrls.has(source.url),
    ),
    selected_channels: normalizeStringList(input.selected_channels),
    selected_watchlists: input.analysis.suggested_watchlists.filter((watchlist) =>
      selectedWatchlistNames.has(watchlist.name),
    ),
    selected_alert_profiles: input.analysis.suggested_alert_profiles.filter((profile) =>
      selectedAlertProfileNames.has(profile.profile_name),
    ),
    deferred_agent_config: input.analysis.deferred_agent_config,
  };
}
