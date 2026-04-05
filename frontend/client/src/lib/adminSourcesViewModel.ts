import type { Source } from "@shared/schema";

export type AdminSourcesView =
  | "sources"
  | "credentials"
  | "campaign-ops"
  | "scheduler";

export interface SchedulerSourceView {
  sourceId: string;
  sourceName: string;
  platform: string;
  sourcePurpose: string | null;
  sourcePriority: number | null;
  credentialId: string | null;
  lastSyncAt: string | null;
  isDue: boolean;
}

export interface SchedulerCoverageGroupView {
  coverageKey: string;
  sources: SchedulerSourceView[];
}

const VALID_VIEWS: AdminSourcesView[] = [
  "sources",
  "credentials",
  "campaign-ops",
  "scheduler",
];

function parseHashQuery(hash: string): URLSearchParams {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  const queryIndex = normalized.indexOf("?");
  return new URLSearchParams(queryIndex >= 0 ? normalized.slice(queryIndex + 1) : "");
}

function parseIsoDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isSourceDue(source: Source, now: Date): boolean {
  const lastSyncAt = parseIsoDate(source.last_sync_at);
  if (!lastSyncAt) {
    return true;
  }
  const frequencyMs = Math.max(source.sync_frequency_minutes || 0, 0) * 60_000;
  return lastSyncAt.getTime() + frequencyMs <= now.getTime();
}

export function readAdminSourcesView(hash: string): AdminSourcesView {
  const view = parseHashQuery(hash).get("view");
  return VALID_VIEWS.includes(view as AdminSourcesView)
    ? (view as AdminSourcesView)
    : "sources";
}

export function buildSchedulerGroups(
  sources: Source[],
  now: Date = new Date(),
): SchedulerCoverageGroupView[] {
  const groups = new Map<string, Source[]>();

  for (const source of sources) {
    const coverageKey = source.coverage_key || source.source_id;
    const current = groups.get(coverageKey) ?? [];
    current.push(source);
    groups.set(coverageKey, current);
  }

  return Array.from(groups.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([coverageKey, groupedSources]) => ({
      coverageKey,
      sources: [...groupedSources]
        .sort((left, right) => {
          const leftPriority = left.source_priority ?? Number.MAX_SAFE_INTEGER;
          const rightPriority = right.source_priority ?? Number.MAX_SAFE_INTEGER;
          return leftPriority - rightPriority || left.source_name.localeCompare(right.source_name);
        })
        .map((source) => ({
          sourceId: source.source_id,
          sourceName: source.source_name,
          platform: source.platform,
          sourcePurpose: source.source_purpose ?? null,
          sourcePriority: source.source_priority ?? null,
          credentialId: source.credential_id ?? null,
          lastSyncAt: source.last_sync_at ?? null,
          isDue: isSourceDue(source, now),
        })),
    }));
}
