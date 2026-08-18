import type {
  V3ActionItem,
  V3AgentDraft,
  V3AnalyticsOverview,
  V3Case,
  V3MentionEvidence,
  V3Monitor,
  V3Notification,
  V3Observation,
  V3Report,
  V3Signal,
} from "@shared/v3";

import { apiRequest } from "@/lib/queryClient";

function toCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

function camelize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelize);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, nested]) => [
      toCamelKey(key),
      camelize(nested),
    ]),
  );
}

async function v3Request<T>(
  method: string,
  path: string,
  organizationId: string,
  body?: Record<string, unknown>,
  idempotent = false,
): Promise<T> {
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  const baseUrl = env?.VITE_LIDAL_V3_API_BASE_URL?.replace(/\/$/, "") ?? "";
  const response = await apiRequest(`${baseUrl}${path}`, {
    method,
    headers: {
      "X-Organization-Id": organizationId,
      ...(idempotent ? { "Idempotency-Key": crypto.randomUUID() } : {}),
    },
    body,
  });
  // La validation stricte appartient au service Pydantic. Cette conversion est
  // l'unique frontiere snake_case -> camelCase du client V3.
  return camelize(await response.json()) as T;
}

export const v3Api = {
  monitors: (organizationId: string) =>
    v3Request<V3Monitor[]>("GET", "/api/v3/monitors", organizationId),
  createMonitor: (
    organizationId: string,
    payload: Record<string, unknown>,
  ) => v3Request<V3Monitor>("POST", "/api/v3/monitors", organizationId, payload, true),
  mentions: (organizationId: string) =>
    v3Request<V3MentionEvidence[]>("GET", "/api/v3/mentions", organizationId),
  observations: (organizationId: string) =>
    v3Request<V3Observation[]>("GET", "/api/v3/observations", organizationId),
  signals: (organizationId: string) =>
    v3Request<V3Signal[]>("GET", "/api/v3/signals", organizationId),
  cases: (organizationId: string) =>
    v3Request<V3Case[]>("GET", "/api/v3/cases", organizationId),
  actions: (organizationId: string) =>
    v3Request<V3ActionItem[]>("GET", "/api/v3/actions", organizationId),
  reports: (organizationId: string) =>
    v3Request<V3Report[]>("GET", "/api/v3/reports", organizationId),
  createReport: (
    organizationId: string,
    payload: { title: string; report_type: V3Report["reportType"]; period_start: string; period_end: string },
  ) => v3Request<V3Report>("POST", "/api/v3/reports", organizationId, payload, true),
  notifications: (organizationId: string) =>
    v3Request<V3Notification[]>("GET", "/api/v3/notifications", organizationId),
  overview: (organizationId: string) =>
    v3Request<V3AnalyticsOverview>("GET", "/api/v3/analytics/overview", organizationId),
  transitionSignal: (
    organizationId: string,
    signalId: string,
    status: V3Signal["status"],
    reason: string,
  ) => v3Request<V3Signal>("PATCH", `/api/v3/signals/${signalId}`, organizationId, { status, reason }, true),
  createCase: (
    organizationId: string,
    payload: {
      signal_id: string;
      title: string;
      priority: V3Signal["severity"];
      owner_id?: string;
      owner_name?: string;
      due_at?: string;
      expected_outcome?: string;
    },
  ) => v3Request<V3Case>("POST", "/api/v3/cases", organizationId, payload, true),
  transitionAction: (
    organizationId: string,
    actionId: string,
    status: V3ActionItem["status"],
    comment: string,
    resultValue?: number,
  ) => v3Request<V3ActionItem>("PATCH", `/api/v3/actions/${actionId}`, organizationId, { status, comment, ...(resultValue == null ? {} : { result_value: resultValue }) }, true),
  agentDraft: (
    organizationId: string,
    payload: { draft_type: V3AgentDraft["draftType"]; references: V3AgentDraft["citations"]; instruction: string },
  ) => v3Request<V3AgentDraft>("POST", "/api/v3/agent/drafts", organizationId, payload, true),
};
