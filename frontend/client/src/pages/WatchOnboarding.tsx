import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import { RunProgressPanel } from "@/components/watch/RunProgressPanel";
import { WatchOnboardingWizard } from "@/components/watch/WatchOnboardingWizard";

export default function WatchOnboarding() {
  const [runState, setRunState] = useState<{
    run_id: string;
    client_id: string;
    watchlist_id: string;
  } | null>(null);

  const runQuery = useQuery({
    queryKey: ["/api/watch-runs", runState?.run_id],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/watch-runs/${runState?.run_id}`);
      return res.json();
    },
    enabled: Boolean(runState?.run_id),
    refetchInterval: runState?.run_id ? 1000 : false,
  });

  return (
    <AppShell sidebarFooterSubtitle="Nouveau client">
      <div className="min-h-[calc(100vh-4rem)] p-8">
        {!runState ? (
          <WatchOnboardingWizard onRunCreated={setRunState} />
        ) : (
          <RunProgressPanel run={runQuery.data} isLoading={runQuery.isLoading} />
        )}
      </div>
    </AppShell>
  );
}
