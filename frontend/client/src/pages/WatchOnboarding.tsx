import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/AppShell";
import { mapDashboardSummary } from "@/lib/apiMappings";
import {
  getStoredOnboardingRun,
  patchStoredOnboardingRun,
  useStoredOnboardingRun,
} from "@/lib/onboardingRunState";
import { apiRequest } from "@/lib/queryClient";
import { RunProgressPanel } from "@/components/watch/RunProgressPanel";
import { WatchOnboardingWizard } from "@/components/watch/WatchOnboardingWizard";

interface ActiveRunView {
  run_id: string;
  client_id: string;
  watchlist_id: string;
}

function mapStoredRunToView() {
  const persistedRun = getStoredOnboardingRun();
  if (!persistedRun) {
    return null;
  }

  return {
    run_id: persistedRun.runId,
    client_id: persistedRun.clientId,
    watchlist_id: persistedRun.watchlistId,
  };
}

export default function WatchOnboarding() {
  const storedRun = useStoredOnboardingRun();
  const [runState, setRunState] = useState<ActiveRunView | null>(() => mapStoredRunToView());

  useEffect(() => {
    if (!storedRun) {
      setRunState(null);
      return;
    }

    setRunState({
      run_id: storedRun.runId,
      client_id: storedRun.clientId,
      watchlist_id: storedRun.watchlistId,
    });
  }, [storedRun]);

  const activeRunState = useMemo(() => runState, [runState]);

  const runQuery = useQuery({
    queryKey: ["/api/watch-runs", activeRunState?.run_id],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/watch-runs/${activeRunState?.run_id}`);
      return res.json();
    },
    enabled: Boolean(activeRunState?.run_id),
    retry: false,
    refetchInterval: (query) => {
      if (!activeRunState?.run_id) return false;

      const data = query.state.data as
        | {
            status?: string;
            steps?: Record<string, { status?: string }>;
          }
        | undefined;

      const hasStepError = Object.values(data?.steps || {}).some((step) => step.status === "error");
      const terminalStatuses = ["ready", "finished", "error", "partial_success", "success"];
      return data?.status && (terminalStatuses.includes(data.status) || hasStepError) ? false : 1000;
    },
  });

  useEffect(() => {
    if (!runQuery.data || !activeRunState?.run_id) {
      return;
    }

    patchStoredOnboardingRun({
      lastKnownStatus: String(runQuery.data.status || ""),
      lastKnownStage: String(runQuery.data.stage || ""),
    });
  }, [activeRunState?.run_id, runQuery.data]);

  const summaryQuery = useQuery({
    queryKey: ["/api/dashboard/summary", activeRunState?.client_id, "watch-onboarding"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/summary");
      return mapDashboardSummary(await res.json());
    },
    enabled: Boolean(
      activeRunState?.run_id &&
        runQuery.data?.status &&
        ["ready", "partial_success", "finished", "success"].includes(runQuery.data.status),
    ),
    retry: false,
  });

  return (
    <AppShell sidebarFooterSubtitle="Configuration de l’espace">
      <div className="min-h-[calc(100vh-4rem)] px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
        {!activeRunState ? (
          <WatchOnboardingWizard onRunCreated={setRunState} />
        ) : (
          <RunProgressPanel
            run={runQuery.data}
            isLoading={runQuery.isLoading}
            showNoDataState={Boolean(
              runQuery.data?.status &&
                ["ready", "partial_success", "finished", "success"].includes(runQuery.data.status) &&
                (summaryQuery.data?.total_mentions ?? 0) === 0,
            )}
          />
        )}
      </div>
    </AppShell>
  );
}
