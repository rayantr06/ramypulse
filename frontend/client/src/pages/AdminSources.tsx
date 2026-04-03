import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  mapAdminHealthSnapshot,
  mapAdminSource,
  mapAdminSyncRun,
} from "@/lib/apiMappings";
import { Link } from "wouter";

interface SourceView {
  id: string;
  name: string;
  platform: string;
  platformValue: string;
  ownerType: string;
  ownerTypeValue: string;
  sourceType: string;
  authMode: string;
  healthPct: number;
  isActive: boolean;
  lastSync: string;
  configText: string;
  frequencyMin: number;
  slaHours: number;
  rawCount: number;
  normalizedCount: number;
  enrichedCount: number;
  lastSyncStatus: string;
  latestHealthComputedAt: string;
}

interface SyncRunView {
  id: string;
  sourceId: string;
  mode: string;
  status: string;
  fetched: number;
  inserted: number;
  errors: number;
  startedAt: string;
}

interface HealthSnapshotView {
  id: string;
  sourceId: string;
  level: "EXCELLENT" | "WARNING" | "ERROR";
  message: string;
  timestamp: string;
}

interface PipelineTraceView {
  source_count: number;
  raw_count: number;
  normalized_count: number;
  enriched_count: number;
}

interface SourceFormState {
  source_name: string;
  platform: string;
  owner_type: string;
  config_text: string;
  sync_frequency_minutes: number;
  freshness_sla_hours: number;
  is_active: boolean;
}

const PLATFORM_OPTIONS = [
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "google_maps", label: "Google Maps" },
  { value: "youtube", label: "YouTube" },
  { value: "import", label: "Import" },
];

const OWNER_OPTIONS = [
  { value: "owned", label: "Owned" },
  { value: "market", label: "Market" },
  { value: "competitor", label: "Competitor" },
];

function defaultSourceType(platform: string): string {
  if (platform === "google_maps") return "public_reviews";
  if (platform === "import") return "batch_import";
  if (platform === "instagram") return "instagram_profile";
  return `${platform}_feed`;
}

function labelFromOptions(value: string, options: Array<{ value: string; label: string }>): string {
  return options.find((option) => option.value === value)?.label || value;
}

function buildLastSync(status: string | null | undefined, timestamp: string | null | undefined): string {
  if (!timestamp) return "Jamais synchronisé";
  if (status === "failed" || status === "failed_downstream") return `Échec ${timestamp}`;
  if (status === "running") return `En cours ${timestamp}`;
  return timestamp;
}

function stringifyConfig(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseConfigText(value: string): Record<string, unknown> {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("config_json doit etre un objet JSON");
  }
  return parsed as Record<string, unknown>;
}

function mapSourceView(value: unknown): SourceView {
  const source = mapAdminSource(value);
  return {
    id: source.source_id,
    name: source.source_name,
    platform: labelFromOptions(source.platform, PLATFORM_OPTIONS),
    platformValue: source.platform,
    ownerType: labelFromOptions(source.owner_type, OWNER_OPTIONS),
    ownerTypeValue: source.owner_type,
    sourceType: source.source_type,
    authMode: source.auth_mode || "file_snapshot",
    healthPct: Number(source.latest_health_score ?? 0),
    isActive: Boolean(source.is_active),
    lastSync: buildLastSync(source.last_sync_status, source.last_sync_started_at || source.last_sync_at),
    configText: stringifyConfig(source.config_json),
    frequencyMin: source.sync_frequency_minutes,
    slaHours: source.freshness_sla_hours,
    rawCount: Number(source.raw_document_count ?? 0),
    normalizedCount: Number(source.normalized_count ?? 0),
    enrichedCount: Number(source.enriched_count ?? 0),
    lastSyncStatus: source.last_sync_status || "unknown",
    latestHealthComputedAt: source.latest_health_computed_at || "",
  };
}

function mapRunView(value: unknown): SyncRunView {
  const run = mapAdminSyncRun(value);
  return {
    id: run.sync_run_id,
    sourceId: run.source_id,
    mode: run.run_mode,
    status: run.status,
    fetched: run.records_fetched,
    inserted: run.records_inserted,
    errors: run.records_failed,
    startedAt: run.started_at,
  };
}

function snapshotLevel(score: number): "EXCELLENT" | "WARNING" | "ERROR" {
  if (score >= 80) return "EXCELLENT";
  if (score >= 50) return "WARNING";
  return "ERROR";
}

function mapSnapshotView(value: unknown): HealthSnapshotView {
  const snapshot = mapAdminHealthSnapshot(value);
  const level = snapshotLevel(snapshot.health_score);
  const parts = [
    `Score: ${snapshot.health_score}%`,
    snapshot.success_rate_pct != null ? `Succès: ${snapshot.success_rate_pct}%` : null,
    snapshot.freshness_hours != null ? `Freshness: ${snapshot.freshness_hours}h` : null,
    snapshot.records_fetched_avg != null ? `Moy. fetched: ${snapshot.records_fetched_avg}` : null,
  ].filter(Boolean);

  return {
    id: snapshot.snapshot_id,
    sourceId: snapshot.source_id,
    level,
    message: parts.join(" | "),
    timestamp: snapshot.computed_at,
  };
}

function formFromSource(source: SourceView): SourceFormState {
  return {
    source_name: source.name,
    platform: source.platformValue,
    owner_type: source.ownerTypeValue,
    config_text: source.configText,
    sync_frequency_minutes: source.frequencyMin,
    freshness_sla_hours: source.slaHours,
    is_active: source.isActive,
  };
}

function blankForm(): SourceFormState {
  return {
    source_name: "",
    platform: "facebook",
    owner_type: "owned",
    config_text: "{\n  \"fetch_mode\": \"snapshot\"\n}",
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    is_active: true,
  };
}

function HealthBar({ pct }: { pct: number }) {
  const color =
    pct >= 80
      ? "bg-tertiary shadow-[0_0_8px_rgba(76,214,255,0.4)]"
      : pct >= 50
        ? "bg-primary"
        : "bg-error shadow-[0_0_8px_rgba(255,180,171,0.4)]";
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
    <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${map[type] ?? ""}`}>
      {type}
    </span>
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

function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background text-on-surface font-body selection:bg-primary-container selection:text-on-primary-container min-h-screen">
      <nav className="bg-[#121315] text-[#ffb693] font-headline tracking-tight font-bold text-lg flex justify-between items-center w-full px-6 py-3 h-16 fixed top-0 z-50">
        <div className="text-xl font-black text-[#ffb693] tracking-tighter">RamyPulse Admin</div>
        <div className="hidden md:flex items-center gap-8">
          <Link href="/">
            <a className="text-gray-400 font-medium hover:text-white transition-colors duration-200 active:scale-95">
              Dashboard
            </a>
          </Link>
          <a className="text-[#ffb693] border-b-2 border-[#ffb693] pb-1 hover:text-white transition-colors duration-200 active:scale-95">
            Ingestion
          </a>
          <a className="text-gray-400 font-medium hover:text-white transition-colors duration-200 active:scale-95">
            Pipelines
          </a>
          <a className="text-gray-400 font-medium hover:text-white transition-colors duration-200 active:scale-95">
            Logs
          </a>
        </div>
        <div className="flex items-center gap-4">
          <span className="material-symbols-outlined hover:text-white transition-colors cursor-pointer">
            notifications
          </span>
          <span className="material-symbols-outlined hover:text-white transition-colors cursor-pointer">
            settings
          </span>
          <div className="w-8 h-8 rounded-full border-2 border-primary/20 bg-surface-container-high flex items-center justify-center">
            <span className="material-symbols-outlined text-sm text-gray-400">person</span>
          </div>
        </div>
      </nav>

      <div className="flex min-h-screen pt-16">
        <aside className="bg-[#121315] font-body text-sm font-semibold tracking-wide flex flex-col h-[calc(100vh-4rem)] border-r border-white/5 p-4 gap-2 w-64 shrink-0 fixed top-16 left-0">
          <div className="mb-6 px-2">
            <p className="text-xs text-on-surface-variant/50 uppercase tracking-widest font-bold mb-1">
              COMMAND CENTER
            </p>
            <h2 className="text-on-surface text-base">Ramy Juice Intelligence</h2>
          </div>
          <nav className="flex-1 space-y-1">
            {[
              { label: "Sources", icon: "database", active: true },
              { label: "Connectors", icon: "alt_route" },
              { label: "Health", icon: "analytics" },
              { label: "Validation", icon: "fact_check" },
              { label: "Archive", icon: "inventory_2" },
            ].map((item) => (
              <a
                key={item.label}
                className={`flex items-center gap-3 px-3 py-2 rounded-sm transition-all duration-200 ease-out ${
                  item.active
                    ? "text-[#ffb693] bg-[#1c1e21]"
                    : "text-gray-500 hover:bg-[#1c1e21] hover:text-white"
                }`}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </a>
            ))}
          </nav>
          <button className="mt-4 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed px-4 py-3 rounded-lg flex items-center justify-center gap-2 font-bold shadow-lg hover:brightness-110 active:scale-95 transition-all">
            <span className="material-symbols-outlined">add</span>
            New Pipeline
          </button>
          <div className="mt-auto pt-4 space-y-1 border-t border-white/5">
            <a className="flex items-center gap-3 px-3 py-2 text-gray-500 hover:text-white transition-all">
              <span className="material-symbols-outlined">help</span>
              <span>Support</span>
            </a>
            <a className="flex items-center gap-3 px-3 py-2 text-gray-500 hover:text-white transition-all">
              <span className="material-symbols-outlined">description</span>
              <span>Documentation</span>
            </a>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto bg-surface-container-lowest ml-64">
          {children}
        </main>
      </div>

      <div className="fixed top-0 left-0 w-full h-full pointer-events-none z-[-1] opacity-20">
        <div className="absolute top-[10%] left-[20%] w-96 h-96 bg-primary/20 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[20%] right-[10%] w-[500px] h-[500px] bg-tertiary/10 blur-[160px] rounded-full"></div>
      </div>
    </div>
  );
}

export default function AdminSources() {
  const queryClientHook = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [editForm, setEditForm] = useState<SourceFormState>(blankForm());
  const [formError, setFormError] = useState<string | null>(null);

  const { data: sources, isLoading: sourcesLoading } = useQuery<SourceView[]>({
    queryKey: ["/api/admin/sources"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/sources");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapSourceView);
    },
  });

  const allSources = sources ?? [];

  useEffect(() => {
    if (!allSources.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId && !isCreateMode) {
      setSelectedId(allSources[0].id);
    }
  }, [allSources, selectedId, isCreateMode]);

  const selectedSource = useMemo(() => {
    return allSources.find((source) => source.id === selectedId) ?? null;
  }, [allSources, selectedId]);

  useEffect(() => {
    if (selectedSource && !isCreateMode) {
      setEditForm(formFromSource(selectedSource));
      setFormError(null);
    }
  }, [selectedSource, isCreateMode]);

  const { data: runs, isLoading: runsLoading } = useQuery<SyncRunView[]>({
    queryKey: ["/api/admin/sources", selectedSource?.id, "runs"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/admin/sources/${selectedSource?.id}/runs`);
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapRunView);
    },
    enabled: Boolean(selectedSource?.id),
  });

  const { data: snapshots, isLoading: snapshotsLoading } = useQuery<HealthSnapshotView[]>({
    queryKey: ["/api/admin/sources", selectedSource?.id, "snapshots"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/admin/sources/${selectedSource?.id}/snapshots`);
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapSnapshotView);
    },
    enabled: Boolean(selectedSource?.id),
  });

  const pipelineData = useMemo<PipelineTraceView>(() => {
    return allSources.reduce(
      (accumulator, source) => ({
        source_count: accumulator.source_count + Math.max(source.rawCount, 0),
        raw_count: accumulator.raw_count + source.rawCount,
        normalized_count: accumulator.normalized_count + source.normalizedCount,
        enriched_count: accumulator.enriched_count + source.enrichedCount,
      }),
      {
        source_count: 0,
        raw_count: 0,
        normalized_count: 0,
        enriched_count: 0,
      },
    );
  }, [allSources]);

  const createMutation = useMutation({
    mutationFn: async (form: SourceFormState) => {
      const configJson = parseConfigText(form.config_text);
      const res = await apiRequest("POST", "/api/admin/sources", {
        source_name: form.source_name,
        platform: form.platform,
        source_type: defaultSourceType(form.platform),
        owner_type: form.owner_type,
        auth_mode: "file_snapshot",
        config_json: configJson,
        is_active: form.is_active,
        sync_frequency_minutes: form.sync_frequency_minutes,
        freshness_sla_hours: form.freshness_sla_hours,
      });
      return mapSourceView(await res.json());
    },
    onSuccess: (createdSource) => {
      setIsCreateMode(false);
      setSelectedId(createdSource.id);
      setEditForm(formFromSource(createdSource));
      setFormError(null);
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: { id: string; form: SourceFormState }) => {
      const configJson = parseConfigText(payload.form.config_text);
      const res = await apiRequest("PUT", `/api/admin/sources/${payload.id}`, {
        source_name: payload.form.source_name,
        is_active: payload.form.is_active,
        config_json: configJson,
        sync_frequency_minutes: payload.form.sync_frequency_minutes,
        freshness_sla_hours: payload.form.freshness_sla_hours,
      });
      return mapSourceView(await res.json());
    },
    onSuccess: (updatedSource) => {
      setSelectedId(updatedSource.id);
      setEditForm(formFromSource(updatedSource));
      setFormError(null);
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/sync`, {
        run_mode: "manual",
      });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
      if (selectedSource?.id) {
        queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources", selectedSource.id, "runs"] });
      }
    },
  });

  const healthCheckMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/health`, {});
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
      if (selectedSource?.id) {
        queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources", selectedSource.id, "snapshots"] });
      }
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    try {
      parseConfigText(editForm.config_text);
      if (isCreateMode) {
        createMutation.mutate(editForm);
      } else if (selectedSource) {
        updateMutation.mutate({ id: selectedSource.id, form: editForm });
      }
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "config_json invalide");
    }
  };

  const runsData = runs ?? [];
  const snapshotsData = snapshots ?? [];

  return (
    <AdminShell>
      <div className="p-8">
        <div className="grid grid-cols-12 gap-8 items-start">
          <div className="col-span-12 lg:col-span-8 space-y-6">
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
                  <span className={`material-symbols-outlined text-lg ${syncMutation.isPending ? "animate-spin" : ""}`}>
                    sync
                  </span>
                  Sync maintenant
                </button>
                <button
                  onClick={() => {
                    setIsCreateMode(true);
                    setSelectedId(null);
                    setEditForm(blankForm());
                    setFormError(null);
                  }}
                  className="bg-primary-container text-on-primary-fixed px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:brightness-110 shadow-lg transition-all text-sm"
                  data-testid="btn-new-source"
                >
                  <span className="material-symbols-outlined text-lg">add_circle</span>
                  Nouvelle source
                </button>
              </div>
            </div>

            <div className="bg-surface-container rounded-xl overflow-hidden border border-white/5">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-high">
                    {["Nom", "Plateforme", "Owner", "Santé", "Actif", "Dernier Sync", "Actions"].map((heading, index) => (
                      <th
                        key={heading}
                        className={`px-6 py-4 text-xs font-bold text-on-surface-variant/70 uppercase tracking-widest ${index === 6 ? "text-right" : index === 4 ? "text-center" : ""}`}
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {sourcesLoading ? (
                    Array.from({ length: 3 }).map((_, index) => (
                      <tr key={index}>
                        <td colSpan={7} className="px-6 py-4">
                          <div className="h-10 bg-surface-container-high rounded animate-pulse"></div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    allSources.map((source) => (
                      <tr
                        key={source.id}
                        onClick={() => {
                          setSelectedId(source.id);
                          setIsCreateMode(false);
                        }}
                        className={`hover:bg-surface-container-high/50 transition-colors group cursor-pointer ${selectedSource?.id === source.id && !isCreateMode ? "bg-surface-container-high/30" : ""}`}
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
                          <OwnerBadge type={source.ownerType} />
                        </td>
                        <td className="px-6 py-4">
                          <HealthBar pct={source.healthPct} />
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              updateMutation.mutate({
                                id: source.id,
                                form: { ...formFromSource(source), is_active: !source.isActive },
                              });
                            }}
                            className={`w-10 h-5 rounded-full relative p-0.5 cursor-pointer transition-colors ${source.isActive ? "bg-primary/20" : "bg-surface-container-highest"} ml-auto mr-auto block`}
                            data-testid={`toggle-active-${source.id}`}
                          >
                            <div
                              className={`w-4 h-4 rounded-full absolute top-0.5 transition-all ${source.isActive ? "right-0.5 bg-primary" : "left-0.5 bg-on-secondary-container"}`}
                            ></div>
                          </button>
                        </td>
                        <td className={`px-6 py-4 text-sm ${source.lastSync.startsWith("Échec") ? "text-error font-medium" : "text-on-surface-variant"}`}>
                          {source.lastSync}
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

            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-6">
                    PIPELINE TRACE & DÉBIT
              </p>
              <div className="flex items-center justify-between gap-4">
                {[
                  { icon: "input", color: "text-primary", borderColor: "border-primary", label: "Source Data", value: pipelineData.source_count },
                  { icon: "description", color: "text-tertiary", borderColor: "border-tertiary", label: "Raw Docs", value: pipelineData.raw_count },
                  { icon: "rule", color: "text-primary", borderColor: "border-primary", label: "Normalized", value: pipelineData.normalized_count },
                  { icon: "auto_awesome", color: "text-tertiary", borderColor: "border-tertiary", label: "Enriched", value: pipelineData.enriched_count },
                ].map(({ icon, color, borderColor, label, value }, index, items) => (
                  <div key={label} className="flex items-center gap-4 flex-1">
                    <div className={`flex-1 bg-surface-container-high p-4 rounded-lg flex flex-col items-center gap-2 text-center border-l-2 ${borderColor}`}>
                      <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                      <span className="text-xl font-headline font-bold">
                        {value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value}
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-tighter opacity-60">{label}</span>
                    </div>
                    {index < items.length - 1 ? (
                      <span className="material-symbols-outlined text-on-surface-variant/30 text-sm shrink-0">
                        arrow_forward
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>

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
                    {["Run ID", "Mode", "Status", "Records (F/I/E)", "Started at"].map((heading) => (
                      <th key={heading} className="px-6 py-3 font-bold opacity-70 text-xs">
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {runsLoading ? (
                    Array.from({ length: 2 }).map((_, index) => (
                      <tr key={index}>
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
                          {run.status === "success" ? (
                            <span className="inline-flex items-center gap-1.5 text-tertiary font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
                                  Succès
                            </span>
                          ) : run.status === "running" ? (
                            <span className="inline-flex items-center gap-1.5 text-primary font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                              En cours
                            </span>
                          ) : run.status === "failed_downstream" ? (
                            <span className="inline-flex items-center gap-1.5 text-primary font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                              Aval KO
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-error font-bold text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                                  Échec
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs font-medium">{run.fetched} / {run.inserted} / {run.errors}</td>
                        <td className="px-6 py-4 text-sm text-on-surface-variant">{run.startedAt}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4 space-y-6 sticky top-20">
            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">
                    {isCreateMode ? "CRÉATION DE SOURCE" : "ÉDITION DE SOURCE"}
              </p>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <div>
                  <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Nom de la source</label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    type="text"
                    value={editForm.source_name}
                    onChange={(event) => setEditForm({ ...editForm, source_name: event.target.value })}
                    data-testid="input-source-name"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Plateforme</label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={editForm.platform}
                      disabled={!isCreateMode}
                      onChange={(event) => setEditForm({ ...editForm, platform: event.target.value })}
                    >
                      {PLATFORM_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Owner Type</label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={editForm.owner_type}
                      disabled={!isCreateMode}
                      onChange={(event) => setEditForm({ ...editForm, owner_type: event.target.value })}
                    >
                      {OWNER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Config JSON</label>
                  <textarea
                    className="w-full bg-[#0d0e10] p-3 rounded-lg font-mono text-[11px] text-primary/80 h-28 overflow-y-auto border border-white/5 focus:outline-none focus:ring-1 focus:ring-primary/40"
                    value={editForm.config_text}
                    onChange={(event) => setEditForm({ ...editForm, config_text: event.target.value })}
                  />
                  {formError ? <p className="text-xs text-error mt-2">{formError}</p> : null}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                        <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Fréquence (min)</label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:outline-none"
                      type="number"
                      value={editForm.sync_frequency_minutes}
                      onChange={(event) => setEditForm({ ...editForm, sync_frequency_minutes: Number(event.target.value || 0) })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">SLA Fresh (h)</label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-lg text-sm py-2 px-3 focus:outline-none"
                      type="number"
                      value={editForm.freshness_sla_hours}
                      onChange={(event) => setEditForm({ ...editForm, freshness_sla_hours: Number(event.target.value || 0) })}
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg mt-2 shadow-xl shadow-primary/10 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50 text-sm"
                  data-testid="btn-save-source"
                >
                  {createMutation.isPending || updateMutation.isPending ? "Enregistrement..." : "Enregistrer les modifications"}
                </button>
                {!isCreateMode && selectedSource ? (
                  <button
                    type="button"
                    onClick={() => healthCheckMutation.mutate(selectedSource.id)}
                    disabled={healthCheckMutation.isPending}
                    className="w-full py-2 bg-surface-container-high text-on-surface-variant font-bold rounded-lg text-xs hover:bg-surface-bright transition-all disabled:opacity-50"
                  >
                        {healthCheckMutation.isPending ? "Vérification..." : "Vérifier la santé"}
                  </button>
                ) : null}
              </form>
            </div>

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
                  {[1, 2, 3].map((item) => (
                    <div key={item} className="h-16 bg-surface-container-high rounded animate-pulse"></div>
                  ))}
                </div>
              ) : snapshotsData.length === 0 ? (
                <div className="text-sm text-on-surface-variant">
                      Aucun snapshot de santé disponible pour cette source.
                </div>
              ) : (
                <div className="space-y-6 relative before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
                  {snapshotsData.map((snapshot) => (
                    <div key={snapshot.id} className="relative pl-8">
                      <SnapshotLevelDot level={snapshot.level} />
                      <div className="flex justify-between items-start">
                        <h4 className="text-sm font-bold">{snapshot.level}</h4>
                        <span className="text-[10px] font-mono opacity-50">{snapshot.timestamp}</span>
                      </div>
                      <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">{snapshot.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
