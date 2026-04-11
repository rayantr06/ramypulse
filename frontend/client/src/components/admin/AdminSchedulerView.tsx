import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import type { SchedulerTickResult, Source } from "@shared/schema";
import { buildSchedulerGroups } from "@/lib/adminSourcesViewModel";
import { mapAdminSource, mapSchedulerTickResult } from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";
import { toast } from "@/hooks/use-toast";

export function AdminSchedulerView() {
  const [lastTickResult, setLastTickResult] = useState<SchedulerTickResult | null>(null);

  const { data: sourceRows } = useQuery<Source[]>({
    queryKey: ["/api/admin/sources"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/sources");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapAdminSource);
    },
  });

  const allSourceRows = sourceRows ?? [];

  const schedulerGroups = useMemo(
    () => buildSchedulerGroups(allSourceRows, new Date()),
    [allSourceRows],
  );

  const schedulerMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/admin/scheduler/tick");
      return mapSchedulerTickResult(await res.json());
    },
    onSuccess: (result) => {
      setLastTickResult(result);
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  return (
    <div className="grid grid-cols-12 gap-8 items-start">
      <div className="col-span-12 lg:col-span-7 bg-surface-container rounded-xl border border-white/5 overflow-hidden">
        <div className="p-6 border-b border-white/5">
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Scheduler</p>
          <h2 className="text-xl font-headline font-bold mt-1">Coverage groups & priorité effective</h2>
        </div>
        <div className="divide-y divide-white/[0.03]">
          {schedulerGroups.length === 0 ? (
            <div className="p-6 text-on-surface-variant">Aucun groupe de couverture disponible.</div>
          ) : (
            schedulerGroups.map((group) => (
              <div key={group.coverageKey} className="p-6">
                <div className="font-semibold">{group.coverageKey}</div>
                <div className="mt-4 space-y-3">
                  {group.sources.map((source) => (
                    <div key={source.sourceId} className="bg-surface-container-high rounded-lg p-4 flex items-center justify-between">
                      <div>
                        <div className="font-semibold">{source.sourceName}</div>
                        <div className="text-xs text-on-surface-variant mt-1">Priorité {source.sourcePriority ?? "n/a"} · {source.platform}</div>
                      </div>
                      <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-bold ${source.isDue ? "bg-primary/15 text-primary" : "bg-surface-container-highest text-on-surface-variant"}`}>
                        <span className={`w-2 h-2 rounded-full ${source.isDue ? "bg-primary" : "bg-on-surface-variant/60"}`}></span>
                        {source.isDue ? "Due" : "Not due"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="col-span-12 lg:col-span-5 bg-surface-container p-6 rounded-xl border border-white/5 space-y-4">
        <div>
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Run orchestration</p>
          <h3 className="text-xl font-headline font-bold mt-1">Run due syncs</h3>
        </div>
        <button onClick={() => schedulerMutation.mutate()} disabled={schedulerMutation.isPending} className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
          {schedulerMutation.isPending ? "Exécution..." : "Run due syncs"}
        </button>
        {!lastTickResult ? (
          <div className="text-sm text-on-surface-variant">Aucun tick exécuté dans cette session.</div>
        ) : (
          <div className="space-y-4">
            <div className="bg-surface-container-high rounded-lg p-4 text-sm">
              {lastTickResult.groups_processed} groupe(s) traités · {lastTickResult.sources_scheduled} source(s) exécutées
            </div>
            {lastTickResult.groups.map((group) => (
              <div key={group.coverage_key} className="bg-surface-container-high rounded-lg p-4">
                <div className="font-semibold">{group.coverage_key}</div>
                <div className="text-xs text-on-surface-variant mt-1">Winner: {group.winner_source_id || "aucun"} · {group.winner_status || "n/a"}</div>
                <div className="mt-3 space-y-2">
                  {group.attempts.map((attempt) => (
                    <div key={`${group.coverage_key}-${attempt.source_id}`} className="text-xs">
                      {attempt.source_id} · p{attempt.source_priority ?? "n/a"} · {attempt.status}
                      {attempt.error ? ` · ${attempt.error}` : ""}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
