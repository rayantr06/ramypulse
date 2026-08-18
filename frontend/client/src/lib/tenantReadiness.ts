import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { mapDashboardSummary } from "./apiMappings";
import { getStoredTenantId, useTenantId } from "./tenantContext";
import {
  patchStoredOnboardingRun,
  setStoredOnboardingRun,
  type ActiveOnboardingRun,
  useStoredOnboardingRun,
} from "./onboardingRunState";
import { apiRequest } from "./queryClient";
import { isDemoMode } from "./demoMode";

export type TenantReadinessState =
  | "checking"
  | "missing_tenant"
  | "needs_onboarding"
  | "run_in_progress"
  | "run_failed"
  | "run_completed_no_data"
  | "ready";

export interface WatchRunStepState {
  status: string;
  stage?: string | null;
  error_message?: string | null;
}

export interface WatchRunState {
  run_id: string;
  client_id: string;
  stage: string;
  status: string;
  records_collected: number;
  steps?: Record<string, WatchRunStepState>;
}

interface DashboardSignalSummary {
  total_mentions: number;
}

interface TenantReadinessInput {
  tenantId: string | null;
  activeRun: ActiveOnboardingRun | null;
  run: WatchRunState | null;
  summary: DashboardSignalSummary | null;
  runLookupFailed?: boolean;
}

function hasRunError(run: WatchRunState | null): boolean {
  if (!run) {
    return false;
  }

  if (run.status === "error") {
    return true;
  }

  return Object.values(run.steps || {}).some((step) => step.status === "error");
}

function hasUsableDashboardData(summary: DashboardSignalSummary | null): boolean {
  return Boolean(summary && summary.total_mentions > 0);
}

function isTerminalSuccessRun(run: WatchRunState | null): boolean {
  if (!run || hasRunError(run)) {
    return false;
  }

  if (["ready", "partial_success", "finished", "success"].includes(run.status)) {
    return true;
  }

  return run.stage === "finished" && run.status !== "running" && run.status !== "queued";
}

export function resolveTenantReadiness({
  tenantId,
  activeRun,
  run,
  summary,
  runLookupFailed = false,
}: TenantReadinessInput): TenantReadinessState {
  if (!tenantId) {
    return "missing_tenant";
  }

  if (activeRun && runLookupFailed) {
    return hasUsableDashboardData(summary) ? "ready" : "needs_onboarding";
  }

  if (activeRun && hasRunError(run)) {
    return "run_failed";
  }

  if (activeRun && isTerminalSuccessRun(run)) {
    return hasUsableDashboardData(summary) ? "ready" : "run_completed_no_data";
  }

  if (activeRun) {
    return "run_in_progress";
  }

  if (hasUsableDashboardData(summary)) {
    return "ready";
  }

  return "needs_onboarding";
}

export function useTenantReadiness() {
  const tenantId = useTenantId();
  const demoMode = isDemoMode();
  const storedRun = useStoredOnboardingRun();
  const activeRun = storedRun && storedRun.clientId === tenantId ? storedRun : null;

  const runQuery = useQuery<WatchRunState>({
    queryKey: ["/api/watch-runs", tenantId, activeRun?.runId, "tenant-readiness"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/watch-runs/${activeRun?.runId}`);
      return (await res.json()) as WatchRunState;
    },
    enabled: Boolean(!demoMode && tenantId && activeRun?.runId && getStoredTenantId()),
    retry: false,
  });

  const summaryQuery = useQuery<DashboardSignalSummary>({
    queryKey: ["/api/dashboard/summary", tenantId, "tenant-readiness"],
    queryFn: async () => {
      if (demoMode) {
        return { total_mentions: 200 };
      }
      const res = await apiRequest("GET", "/api/dashboard/summary");
      const summary = mapDashboardSummary(await res.json());
      return { total_mentions: summary.total_mentions };
    },
    enabled: Boolean(tenantId),
    retry: false,
  });

  useEffect(() => {
    if (!activeRun || !runQuery.data) {
      return;
    }

    patchStoredOnboardingRun({
      lastKnownStatus: runQuery.data.status || null,
      lastKnownStage: runQuery.data.stage || null,
    });
  }, [activeRun, runQuery.data?.stage, runQuery.data?.status]);

  useEffect(() => {
    if (activeRun && runQuery.isError) {
      setStoredOnboardingRun(null);
    }
  }, [activeRun, runQuery.isError]);

  useEffect(() => {
    if (activeRun && tenantId && resolveTenantReadiness({
      tenantId,
      activeRun,
      run: runQuery.data ?? null,
      summary: summaryQuery.data ?? null,
      runLookupFailed: runQuery.isError,
    }) === "ready") {
      setStoredOnboardingRun(null);
    }
  }, [activeRun, runQuery.data, runQuery.isError, summaryQuery.data, tenantId]);

  const isCheckingReadyTenant = Boolean(
    tenantId && !activeRun && summaryQuery.isLoading && !summaryQuery.data,
  );

  const resolvedState = resolveTenantReadiness({
    tenantId,
    activeRun,
    run: runQuery.data ?? null,
    summary: summaryQuery.data ?? null,
    runLookupFailed: runQuery.isError,
  });

  const state = isCheckingReadyTenant ? "checking" : resolvedState;

  return {
    state,
    tenantId,
    activeRun,
    run: runQuery.data ?? null,
    summary: summaryQuery.data ?? null,
    isLoading:
      Boolean(tenantId) &&
      ((Boolean(activeRun?.runId) && runQuery.isLoading) || summaryQuery.isLoading),
  };
}
