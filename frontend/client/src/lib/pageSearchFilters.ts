interface SearchableExcerpt {
  text?: string | null;
}

interface SearchableWatchlist {
  name?: string | null;
  description?: string | null;
  scope?: string | null;
  owners?: string[] | null;
}

interface SearchableAlert {
  title?: string | null;
  description?: string | null;
  location?: string | null;
  estimated_impact?: string | null;
  social_excerpts?: SearchableExcerpt[] | null;
}

interface SearchableRecommendation {
  title?: string | null;
  rationale?: string | null;
  provider?: string | null;
  model?: string | null;
  trigger?: string | null;
  summary?: string | null;
  target?: string | null;
}

interface SearchableCampaign {
  name?: string | null;
  influencer?: string | null;
  platform?: string | null;
  keywords?: string[] | null;
  status?: string | null;
  type?: string | null;
}

function normalizeSearchValue(value: string | null | undefined): string {
  return (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function matchesQuery(parts: Array<string | null | undefined>, query: string): boolean {
  const normalizedQuery = normalizeSearchValue(query);
  if (!normalizedQuery) {
    return true;
  }

  return parts.some((part) => normalizeSearchValue(part).includes(normalizedQuery));
}

export function filterWatchlistViews<T extends SearchableWatchlist>(
  items: T[],
  query: string,
): T[] {
  return items.filter((item) =>
    matchesQuery(
      [
        item.name,
        item.description,
        item.scope,
        ...(item.owners ?? []),
      ],
      query,
    ),
  );
}

export function filterAlertViews<T extends SearchableAlert>(items: T[], query: string): T[] {
  return items.filter((item) =>
    matchesQuery(
      [
        item.title,
        item.description,
        item.location,
        item.estimated_impact,
        ...(item.social_excerpts ?? []).map((excerpt) => excerpt.text),
      ],
      query,
    ),
  );
}

export function filterRecommendationViews<T extends SearchableRecommendation>(
  items: T[],
  query: string,
): T[] {
  return items.filter((item) =>
    matchesQuery(
      [
        item.title,
        item.rationale,
        item.provider,
        item.model,
        item.trigger,
        item.summary,
        item.target,
      ],
      query,
    ),
  );
}

export function filterCampaignViews<T extends SearchableCampaign>(items: T[], query: string): T[] {
  return items.filter((item) =>
    matchesQuery(
      [
        item.name,
        item.influencer,
        item.platform,
        item.status,
        item.type,
        ...(item.keywords ?? []),
      ],
      query,
    ),
  );
}
