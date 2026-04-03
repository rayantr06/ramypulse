import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { Source, SyncRun, HealthSnapshot, PipelineTrace } from "@shared/schema";

const MOCK_SOURCES: Source[] = [
  {
    id: "1",
    name: "Facebook Ramy Officiel",
    platform: "Facebook",
    owner_type: "Owned",
    health_pct: 98,
    is_active: true,
    last_sync: "Il y a 12 min",
    config_json: JSON.stringify({ api_version: "v14.0", fields: ["insights", "comments"], auth: "OAuth2", rate_limit: 1000 }, null, 2),
    frequency_min: 15,
    sla_hours: 1,
  },
  {
    id: "2",
    name: "Google Maps - Alger",
    platform: "G-Maps",
    owner_type: "Market",
    health_pct: 82,
    is_active: true,
    last_sync: "Il y a 4h",
    config_json: JSON.stringify({ api_version: "v3", place_ids: ["ChIJXXXX"], fields: ["reviews", "rating"] }, null, 2),
    frequency_min: 60,
    sla_hours: 4,
  },
  {
    id: "3",
    name: "YouTube - Reviews",
    platform: "YouTube",
    owner_type: "Competitor",
    health_pct: 45,
    is_active: false,
    last_sync: "Échec hier",
    config_json: JSON.stringify({ api_version: "v3", channel_ids: ["UCxxxx"], quota_units: 10000 }, null, 2),
    frequency_min: 120,
    sla_hours: 8,
  },
];

const MOCK_RUNS: SyncRun[] = [
  { id: "RUN-8812", source_id: "1", mode: "Incremental", status: "SUCCESS", fetched: 842, inserted: 840, errors: 0, started_at: "12:05:33" },
  { id: "RUN-8811", source_id: "1", mode: "Full Reset", status: "FAILURE", fetched: 120, inserted: 0, errors: 120, started_at: "08:12:10" },
];

const MOCK_SNAPSHOTS: HealthSnapshot[] = [
  { id: "1", source_id: "1", level: "EXCELLENT", message: "Latency: 240ms. Validation schema passed for 1,200 entities.", timestamp: "Maintenant" },
  { id: "2", source_id: "1", level: "WARNING", message: "Facebook API returned 429 (Rate Limit). Retrying in 15min.", timestamp: "12:15 AM" },
  { id: "3", source_id: "1", level: "ERROR", message: "Token for 'YouTube Reviews' needs manual refresh in settings.", timestamp: "Hier" },
];

const MOCK_PIPELINE: PipelineTrace = {
  source_count: 12400,
  raw_count: 11800,
  normalized_count: 11200,
  enriched_count: 10900,
};

// Map API source response to Source schema
function mapSourceFromApi(s: Record<string, unknown>): Source {
  return {
    id: String(s.id ?? s.source_id ?? ""),
    name: String(s.name ?? ""),
    platform: String(s.platform ?? ""),
    owner_type: (s.owner_type as Source["owner_type"]) ?? "Owned",
    health_pct: Number(s.health_pct ?? s.health ?? 0),
    is_active: Boolean(s.is_active ?? true),
    last_sync: String(s.last_sync ?? s.last_synced_at ?? ""),
    config_json: typeof s.config_json === "string" ? s.config_json : JSON.stringify(s.config_json ?? {}, null, 2),
    frequency_min: Number(s.frequency_min ?? 60),
    sla_hours: Number(s.sla_hours ?? 4),
  };
}

// Map API sync run response to SyncRun schema
function mapRunFromApi(r: Record<string, unknown>): SyncRun {
  return {
    id: String(r.id ?? r.run_id ?? ""),
    source_id: String(r.source_id ?? ""),
    mode: String(r.mode ?? "Incremental"),
    status: (r.status as SyncRun["status"]) ?? "SUCCESS",
    fetched: Number(r.fetched ?? r.fetched_count ?? 0),
    inserted: Number(r.inserted ?? r.inserted_count ?? 0),
    errors: Number(r.errors ?? r.error_count ?? 0),
    started_at: String(r.started_at ?? r.created_at ?? ""),
  };
}

// Map API health snapshot to HealthSnapshot schema
function mapSnapshotFromApi(s: Record<string, unknown>): HealthSnapshot {
  return {
    id: String(s.id ?? ""),
    source_id: String(s.source_id ?? ""),
    level: (s.level as HealthSnapshot["level"]) ?? "WARNING",
    message: String(s.message ?? ""),
    timestamp: String(s.timestamp ?? s.created_at ?? ""),
  };
}

function HealthBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-tertiary shadow-[0_0_8px_rgba(76,214,255,0.4)]" : pct >= 50 ? "bg-primary" : "bg-error shadow-[0_0_8px_rgba(255,180,171,0.4)]";
  const textColor = pct >= 80 ? "text-tertiary" : pct >= 50 ? "text-primary" : "text-error";
  return (
    <div className="flex items-center gap-3">
      <div className="w-12 h-1 bg-surface-container-highest rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }}></div>
      </div>
      <span className={`text-xs font-bold ${textColor}`}>{pct}%</span>
    </div>
  );
}

function OwnerBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    Owned: "bg-primary/10 text-primary",
    Market: "bg-tertiary/10 text-tertiary",
    Competitor: "bg-on-surface-variant/10 text-on-surface-variant",
  };
  return (
    <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${map[type] ?? ""}`}>{type}</span>
  );
}

function SnapshotLevelDot({ level }: { level: string }) {
  const map: Record<string, { bg: string; ring: string }> = {
    EXCELLENT: { bg: "bg-tertiary/20", ring: "bg-tertiary" },
    WARNING: { bg: "bg-primary/20", ring: "bg-primary" },
    ERROR: { bg: "bg-error/20", ring: "bg-error" },
  };
  const style = map[level] ?? map.WARNING;
  return (
    <div className={`absolute left-0 top-1.5 w-[22px] h-[22px] ${style.bg} rounded-full flex items-center justify-center`}>
      <div className={`w-2 h-2 ${style.ring} rounded-full`}></div>
    </div>
  );
}

export default function AdminSources() {
  const [selectedSource, setSelectedSource] = useState<Source | null>(MOCK_SOURCES[0]);
  const [editForm, setEditForm] = useState<Source>(MOCK_SOURCES[0]);

  const queryClientHook = useQueryClient();

  const { data: sources, isLoading: sourcesLoading } = useQuery<Source[]>({
    queryKey: ["/api/admin/sources"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/admin/sources");
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.sources ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapSourceFromApi);
        return mapped.length > 0 ? mapped : MOCK_SOURCES;
      } catch {
        return MOCK_SOURCES;
      }
    },
  });

  const { data: runs, isLoading: runsLoading } = useQuery<SyncRun[]>({
    queryKey: ["/api/admin/sources", selectedSource?.id, "runs"],
    queryFn: async () => {
      if (!selectedSource) return MOCK_RUNS;
      try {
        const res = await apiRequest("GET", `/api/admin/sources/${selectedSource.id}/runs`);
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.runs ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapRunFromApi);
        return mapped.length > 0 ? mapped : MOCK_RUNS;
      } catch {
        return MOCK_RUNS;
      }
    },
    enabled: !!selectedSource,
  });

  const { data: snapshots, isLoading: snapshotsLoading } = useQuery<HealthSnapshot[]>({
    queryKey: ["/api/admin/sources", selectedSource?.id, "snapshots"],
    queryFn: async () => {
      if (!selectedSource) return MOCK_SNAPSHOTS;
      try {
        const res = await apiRequest("GET", `/api/admin/sources/${selectedSource.id}/snapshots`);
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.snapshots ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapSnapshotFromApi);
        return mapped.length > 0 ? mapped : MOCK_SNAPSHOTS;
      } catch {
        return MOCK_SNAPSHOTS;
      }
    },
    enabled: !!selectedSource,
  });

  const { data: pipeline, isLoading: pipelineLoading } = useQuery<PipelineTrace>({
    queryKey: ["/api/admin/pipeline"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/admin/pipeline");
        const apiData = await res.json();
        return {
          source_count: Number(apiData.source_count ?? MOCK_PIPELINE.source_count),
          raw_count: Number(apiData.raw_count ?? MOCK_PIPELINE.raw_count),
          normalized_count: Number(apiData.normalized_count ?? MOCK_PIPELINE.normalized_count),
          enriched_count: Number(apiData.enriched_count ?? MOCK_PIPELINE.enriched_count),
        };
      } catch {
        return MOCK_PIPELINE;
      }
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: Partial<Source> & { id: string }) => {
      const res = await apiRequest("PUT", `/api/admin/sources/${data.id}`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/sync`, {});
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
  });

  const healthCheckMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/health`, {});
      return res.json();
    },
    onSuccess: () => {
      if (selectedSource) {
        queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources", selectedSource.id, "snapshots"] });
      }
    },
  });

  const allSources = sources ?? MOCK_SOURCES;
  const runsData = runs ?? MOCK_RUNS;
  const snapshotsData = snapshots ?? MOCK_SNAPSHOTS;
  const pipelineData = pipeline ?? MOCK_PIPELINE;

  const selectSource = (source: Source) => {
    setSelectedSource(source);
    setEditForm(source);
  };

  return (
    <AppShell>
      <div className="p-8">
        <div className="grid grid-cols-12 gap-8 items-start">
          {/* Left: Main Content */}
          <div className="col-span-12 lg:col-span-8 space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between">
              <div>
                <p className="text-on-surface-variant font-bold tracking-[0.15em] mb-1 uppercase text-[10px]">
                  SOURCES DE DONNÉES
                </p>
                <h1 className="text-3xl font-headline font-extrabold tracking-tight">
                  Ramy Intelligence Dashboard
                </h1>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => selectedSource && syncMutation.mutate(selectedSource.id)}
                  disabled={!selectedSource || syncMutation.isPending}
                  className="bg-surface-container-high text-on-surface px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-surface-bright transition-all text-sm disabled:opacity-50"
                >
                  <span className={`material-symbols-outlined text-lg ${syncMutation.isPending ? "animate-spin" : ""}`}>sync</span>
                  Sync maintenant
                </button>
                <button
                  className="bg-primary-container text-on-primary-fixed px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:brightness-110 shadow-lg transition-all text-sm"
                  data-testid="btn-new-source"
                >
                  <span className="material-symbols-outlined text-lg">add_circle</span>
                  Nouvelle source
                </button>
              </div>
            </div>

            {/* Sources Table */}
            <div className="bg-surface-container rounded-xl overflow-hidden border border-white/5">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-high">
                    {["Nom", "Plateforme", "Owner", "Santé", "Actif", "Dernier Sync", "Actions"].map((h, i) => (
                      <th
                        key={h}
                        className={`px-6 py-4 text-xs font-bold text-on-surface-variant/70 uppercase tracking-widest ${i === 6 ? "text-right" : i === 4 ? "text-center" : ""}`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {sourcesLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan={7} className="px-6 py-4">
                          <div className="h-10 bg-surface-container-high rounded animate-pulse"></div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    allSources.map((source) => (
                      <tr
                        key={source.id}
                        onClick={() => selectSource(source)}
                        className={`hover:bg-surface-container-high/50 transition-colors group cursor-pointer ${selectedSource?.id === source.id ? "bg-surface-container-high/30" : ""}`}
                        data-testid={`source-row-${source.id}`}
                      >
                        <td className="px-6 py-4 font-semibold text-on-surface">{source.name}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-tertiary text-lg">public</span>
                            <span className="text-sm">{source.platform}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <OwnerBadge type={source.owner_type} />
                        </td>
                        <td className="px-6 py-4">
                          <HealthBar pct={source.health_pct} />
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              updateMutation.mutate({ id: source.id, is_active: !source.is_active });
                            }}
                            className={`w-10 h-5 rounded-full relative p-0.5 cursor-pointer transition-colors ${source.is_active ? "bg-primary/20" : "bg-surface-container-highest"} ml-auto mr-auto block`}
                            data-testid={`toggle-active-${source.id}`}
                          >
                            <div className={`w-4 h-4 rounded-full absolute top-0.5 transition-all ${source.is_active ? "right-0.5 bg-primary" : "left-0.5 bg-on-secondary-container"}`}></div>
                          </button>
                        </td>
                        <td className={`px-6 py-4 text-sm ${source.last_sync.startsWith("Échec") ? "text-error font-medium" : "text-on-surface-variant"}`}>
                          {source.last_sync}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button className="text-on-surface-variant hover:text-primary transition-colors">
                            <span className="material-symbols-outlined text-xl">edit</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pipeline Trace */}
            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-6">
                PIPELINE TRACE & DÉBIT
              </p>
              {pipelineLoading ? (
                <div className="flex items-center justify-between gap-4">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="flex-1 h-24 bg-surface-container-high rounded-lg animate-pulse"></div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-between gap-4">
                  {[
                    { icon: "input", color: "text-primary", borderColor: "border-primary", label: "Source Data", value: pipelineData.source_count },
                    { icon: "description", color: "text-tertiary", borderColor: "border-tertiary", label: "Raw Docs", value: pipelineData.raw_count },
                    { icon: "rule", color: "text-primary", borderColor: "border-primary", label: "Normalized", value: pipelineData.normalized_count },
                    { icon: "auto_awesome", color: "text-tertiary", borderColor: "border-tertiary", label: "Enriched", value: pipelineData.enriched_count },
                  ].map(({ icon, color, borderColor, label, value }, i, arr) => (
                    <div key={label} className="flex items-center gap-4 flex-1">
                      <div className={`flex-1 bg-surface-container-high p-4 rounded-lg flex flex-col items-center gap-2 text-center border-l-2 ${borderColor}`}>
                        <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                        <span className="text-xl font-headline font-bold">
                          {value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value}
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-tighter opacity-60">{label}</span>
                      </div>
                      {i < arr.length - 1 && (
                        <span className="material-symbols-outlined text-on-surface-variant/30 text-sm shrink-0">
                          arrow_forward
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Sync Runs Table */}
            <div className="bg-surface-container rounded-xl border border-white/5">
              <div className="p-6 border-b border-white/5 flex justify-between items-center">
                <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface-variant">
                  Historique Sync Runs
                </h3>
                <span className="text-xs text-primary font-medium cursor-pointer hover:underline">
                  Voir tout l'historique
                </span>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-container-high/30">
                  <tr>
                    {["Run ID", "Mode", "Status", "Records (F/I/E)", "Started at"].map((h) => (
                      <th key={h} className="px-6 py-3 font-bold opacity-70 text-xs">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {runsLoading ? (
                    Array.from({ length: 2 }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan={5} className="px-6 py-4">
                          <div className="h-6 bg-surface-container-high rounded animate-pulse"></div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    runsData.map((run) => (
                      <tr key={run.id} data-testid={`run-row-${run.id}`}>
                        <td className="px-6 py-4 font-mono text-xs">#{run.id}</td>
                        <td className="px-6 py-4 text-sm">{run.mode}</td>
                        <td className="px-6 py-4">
                          {run.status === "SUCCESS" ? (
                            <span className="inline-flex items-center gap-1.5 text-tertiary font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
                              Succès
                            </span>
                          ) : run.status === "RUNNING" ? (
                            <span className="inline-flex items-center gap-1.5 text-primary font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                              En cours
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-error font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                              Échec
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs font-medium">
                          {run.fetched} / {run.inserted} / {run.errors}
                        </td>
                        <td className="px-6 py-4 text-sm text-on-surface-variant">{run.started_at}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right: Edit + Health Snapshots */}
          <div className="col-span-12 lg:col-span-4 space-y-6 sticky top-20">
            {/* Edit form */}
            {editForm && (
              <div className="bg-surface-container p-6 rounded-xl border border-white/5">
                <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">
                  ÉDITION DE SOURCE
                </p>
                <form
                  className="space-y-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    updateMutation.mutate(editForm);
                  }}
                >
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Nom de la source</label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      data-testid="input-source-name"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Plateforme</label>
                      <select
                        className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                        value={editForm.platform}
                        onChange={(e) => setEditForm({ ...editForm, platform: e.target.value })}
                      >
                        <option>Facebook</option>
                        <option>Instagram</option>
                        <option>Google Maps</option>
                        <option>YouTube</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Owner Type</label>
                      <select
                        className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                        value={editForm.owner_type}
                        onChange={(e) => setEditForm({ ...editForm, owner_type: e.target.value as Source["owner_type"] })}
                      >
                        <option>Owned</option>
                        <option>Market</option>
                        <option>Competitor</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Config JSON</label>
                    <div className="bg-[#0d0e10] p-3 rounded-lg font-mono text-[11px] text-primary/80 h-28 overflow-y-auto border border-white/5">
                      <pre className="whitespace-pre-wrap break-all">{editForm.config_json}</pre>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Fréquence (min)</label>
                      <input
                        className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:outline-none"
                        type="number"
                        value={editForm.frequency_min}
                        onChange={(e) => setEditForm({ ...editForm, frequency_min: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">SLA Fresh (h)</label>
                      <input
                        className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:outline-none"
                        type="number"
                        value={editForm.sla_hours}
                        onChange={(e) => setEditForm({ ...editForm, sla_hours: parseInt(e.target.value) })}
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={updateMutation.isPending}
                    className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg mt-2 shadow-xl shadow-primary/10 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50 text-sm"
                    data-testid="btn-save-source"
                  >
                    {updateMutation.isPending ? "Enregistrement..." : "Enregistrer les modifications"}
                  </button>
                  {selectedSource && (
                    <button
                      type="button"
                      onClick={() => healthCheckMutation.mutate(selectedSource.id)}
                      disabled={healthCheckMutation.isPending}
                      className="w-full py-2 bg-surface-container-high text-on-surface-variant font-bold rounded-lg text-xs hover:bg-surface-bright transition-all disabled:opacity-50"
                    >
                      {healthCheckMutation.isPending ? "Vérification..." : "Vérifier la santé"}
                    </button>
                  )}
                </form>
              </div>
            )}

            {/* Health Snapshots */}
            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <div className="flex justify-between items-center mb-6">
                <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Health Snapshots</p>
                <span
                  className="material-symbols-outlined text-tertiary cursor-pointer hover:opacity-70 transition-opacity"
                  onClick={() => selectedSource && healthCheckMutation.mutate(selectedSource.id)}
                >
                  refresh
                </span>
              </div>
              {snapshotsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-surface-container-high rounded animate-pulse"></div>
                  ))}
                </div>
              ) : (
                <div className="space-y-6 relative before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
                  {snapshotsData.map((snap) => (
                    <div key={snap.id} className="relative pl-8">
                      <SnapshotLevelDot level={snap.level} />
                      <div className="flex justify-between items-start">
                        <h4 className="text-sm font-bold">{snap.level}</h4>
                        <span className="text-[10px] font-mono opacity-50">{snap.timestamp}</span>
                      </div>
                      <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">{snap.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
