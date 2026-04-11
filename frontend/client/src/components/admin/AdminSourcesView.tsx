import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { CredentialSummary, Source } from "@shared/schema";
import {
  mapAdminHealthSnapshot,
  mapAdminSource,
  mapAdminSyncRun,
  mapCredentialSummary,
} from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";
import { toast } from "@/hooks/use-toast";

interface SourceView {
  id: string;
  name: string;
  platform: string;
  platformValue: string;
  ownerType: string;
  ownerTypeValue: string;
  healthPct: number;
  isActive: boolean;
  lastSync: string;
  configText: string;
  frequencyMin: number;
  slaHours: number;
  sourcePurpose: string;
  sourcePriority: number;
  coverageKey: string;
  credentialId: string;
  rawCount: number;
  normalizedCount: number;
  enrichedCount: number;
}

interface SyncRunView {
  id: string;
  mode: string;
  status: string;
  fetched: number;
  inserted: number;
  errors: number;
  startedAt: string;
}

interface HealthSnapshotView {
  id: string;
  level: "EXCELLENT" | "WARNING" | "ERROR";
  message: string;
  timestamp: string;
}

interface SourceFormState {
  source_name: string;
  platform: string;
  owner_type: string;
  config_text: string;
  sync_frequency_minutes: number;
  freshness_sla_hours: number;
  is_active: boolean;
  source_purpose: string;
  source_priority: number;
  coverage_key: string;
  credential_id: string;
}

const PLATFORM_OPTIONS = [
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "google_maps", label: "Google Maps" },
  { value: "youtube", label: "YouTube" },
  { value: "import", label: "Import" },
  { value: "tiktok", label: "TikTok" },
];

const OWNER_OPTIONS = [
  { value: "owned", label: "Owned" },
  { value: "market", label: "Market" },
  { value: "competitor", label: "Competitor" },
];

const SOURCE_PURPOSE_OPTIONS = [
  { value: "owned_content", label: "Owned Content" },
  { value: "campaign_engagement", label: "Campaign Engagement" },
  { value: "market_monitoring", label: "Market Monitoring" },
  { value: "competitor_monitoring", label: "Competitor Monitoring" },
  { value: "manual_evidence", label: "Manual Evidence" },
  { value: "bulk_import", label: "Bulk Import" },
];

function labelFromOptions(value: string, options: Array<{ value: string; label: string }>): string {
  return options.find((option) => option.value === value)?.label || value;
}

function defaultSourceType(platform: string): string {
  if (platform === "google_maps") return "public_reviews";
  if (platform === "import") return "batch_import";
  if (platform === "instagram") return "instagram_profile";
  return `${platform}_feed`;
}

function stringifyConfig(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseObjectJson(value: string, label: string): Record<string, unknown> {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} doit être un objet JSON`);
  }
  return parsed as Record<string, unknown>;
}

function buildLastSync(status: string | null | undefined, timestamp: string | null | undefined): string {
  if (!timestamp) return "Jamais synchronisé";
  if (status === "failed" || status === "failed_downstream") return `Échec ${timestamp}`;
  if (status === "running") return `En cours ${timestamp}`;
  return timestamp;
}

function mapSourceView(source: Source): SourceView {
  return {
    id: source.source_id,
    name: source.source_name,
    platform: labelFromOptions(source.platform, PLATFORM_OPTIONS),
    platformValue: source.platform,
    ownerType: labelFromOptions(source.owner_type, OWNER_OPTIONS),
    ownerTypeValue: source.owner_type,
    healthPct: Number(source.latest_health_score ?? 0),
    isActive: Boolean(source.is_active),
    lastSync: buildLastSync(source.last_sync_status, source.last_sync_started_at || source.last_sync_at),
    configText: stringifyConfig(source.config_json),
    frequencyMin: source.sync_frequency_minutes,
    slaHours: source.freshness_sla_hours,
    sourcePurpose: source.source_purpose || "owned_content",
    sourcePriority: Number(source.source_priority ?? 3),
    coverageKey: source.coverage_key || "",
    credentialId: source.credential_id || "",
    rawCount: Number(source.raw_document_count ?? 0),
    normalizedCount: Number(source.normalized_count ?? 0),
    enrichedCount: Number(source.enriched_count ?? 0),
  };
}

function mapRunView(value: unknown): SyncRunView {
  const run = mapAdminSyncRun(value);
  return {
    id: run.sync_run_id,
    mode: run.run_mode,
    status: run.status,
    fetched: run.records_fetched,
    inserted: run.records_inserted,
    errors: run.records_failed,
    startedAt: run.started_at,
  };
}

function mapSnapshotView(value: unknown): HealthSnapshotView {
  const snapshot = mapAdminHealthSnapshot(value);
  const level =
    snapshot.health_score >= 80
      ? "EXCELLENT"
      : snapshot.health_score >= 50
        ? "WARNING"
        : "ERROR";
  const parts = [
    `Score: ${snapshot.health_score}%`,
    snapshot.success_rate_pct != null ? `Succès: ${snapshot.success_rate_pct}%` : null,
    snapshot.freshness_hours != null ? `Freshness: ${snapshot.freshness_hours}h` : null,
    snapshot.records_fetched_avg != null ? `Moy. fetched: ${snapshot.records_fetched_avg}` : null,
  ].filter(Boolean);
  return {
    id: snapshot.snapshot_id,
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
    source_purpose: source.sourcePurpose,
    source_priority: source.sourcePriority,
    coverage_key: source.coverageKey,
    credential_id: source.credentialId,
  };
}

function blankSourceForm(): SourceFormState {
  return {
    source_name: "",
    platform: "facebook",
    owner_type: "owned",
    config_text: "{\n  \"fetch_mode\": \"snapshot\"\n}",
    sync_frequency_minutes: 60,
    freshness_sla_hours: 24,
    is_active: true,
    source_purpose: "owned_content",
    source_priority: 1,
    coverage_key: "",
    credential_id: "",
  };
}

function compactNumber(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : `${value}`;
}

function HealthBar({ pct }: { pct: number }) {
  const tone =
    pct >= 80 ? "bg-tertiary text-tertiary" : pct >= 50 ? "bg-primary text-primary" : "bg-error text-error";
  const [bar, text] = tone.split(" ");
  return (
    <div className="flex items-center gap-3">
      <div className="w-12 h-1 bg-surface-container-highest rounded-full overflow-hidden">
        <div className={`h-full ${bar}`} style={{ width: `${pct}%` }}></div>
      </div>
      <span className={`text-xs font-bold ${text}`}>{pct}%</span>
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

export function AdminSourcesView() {
  const queryClientHook = useQueryClient();
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [sourceForm, setSourceForm] = useState<SourceFormState>(blankSourceForm());
  const [sourceError, setSourceError] = useState<string | null>(null);

  const { data: sourceRows, isLoading: sourcesLoading } = useQuery<Source[]>({
    queryKey: ["/api/admin/sources"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/admin/sources");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapAdminSource);
    },
  });

  const { data: credentials } = useQuery<CredentialSummary[]>({
    queryKey: ["/api/social-metrics/credentials"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/social-metrics/credentials");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapCredentialSummary);
    },
  });

  const allSourceRows = sourceRows ?? [];
  const allSources = useMemo(() => allSourceRows.map(mapSourceView), [allSourceRows]);
  const credentialOptions = credentials ?? [];

  const selectedSource = useMemo(
    () => allSources.find((source) => source.id === selectedSourceId) ?? null,
    [allSources, selectedSourceId],
  );

  const pipelineData = useMemo(
    () =>
      allSources.reduce(
        (accumulator, source) => ({
          source_count: accumulator.source_count + 1,
          raw_count: accumulator.raw_count + source.rawCount,
          normalized_count: accumulator.normalized_count + source.normalizedCount,
          enriched_count: accumulator.enriched_count + source.enrichedCount,
        }),
        { source_count: 0, raw_count: 0, normalized_count: 0, enriched_count: 0 },
      ),
    [allSources],
  );

  useEffect(() => {
    if (!allSources.length) {
      setSelectedSourceId(null);
      return;
    }
    setSelectedSourceId((current) =>
      current && allSources.some((source) => source.id === current) ? current : allSources[0].id,
    );
  }, [allSources]);

  useEffect(() => {
    if (selectedSource && !isCreateMode) {
      setSourceForm(formFromSource(selectedSource));
      setSourceError(null);
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

  const invalidateSources = () => {
    queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    if (selectedSource?.id) {
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources", selectedSource.id, "runs"] });
      queryClientHook.invalidateQueries({
        queryKey: ["/api/admin/sources", selectedSource.id, "snapshots"],
      });
    }
  };

  const createSourceMutation = useMutation({
    mutationFn: async (form: SourceFormState) => {
      const res = await apiRequest("POST", "/api/admin/sources", {
        source_name: form.source_name,
        platform: form.platform,
        source_type: defaultSourceType(form.platform),
        owner_type: form.owner_type,
        auth_mode: "file_snapshot",
        config_json: parseObjectJson(form.config_text, "config_json"),
        is_active: form.is_active,
        sync_frequency_minutes: form.sync_frequency_minutes,
        freshness_sla_hours: form.freshness_sla_hours,
        source_purpose: form.source_purpose,
        source_priority: form.source_priority,
        coverage_key: form.coverage_key || undefined,
        credential_id: form.credential_id || undefined,
      });
      return mapSourceView(mapAdminSource(await res.json()));
    },
    onSuccess: (createdSource) => {
      setIsCreateMode(false);
      setSelectedSourceId(createdSource.id);
      setSourceForm(formFromSource(createdSource));
      invalidateSources();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const updateSourceMutation = useMutation({
    mutationFn: async (payload: { id: string; form: SourceFormState }) => {
      const res = await apiRequest("PUT", `/api/admin/sources/${payload.id}`, {
        source_name: payload.form.source_name,
        is_active: payload.form.is_active,
        config_json: parseObjectJson(payload.form.config_text, "config_json"),
        sync_frequency_minutes: payload.form.sync_frequency_minutes,
        freshness_sla_hours: payload.form.freshness_sla_hours,
        source_purpose: payload.form.source_purpose,
        source_priority: payload.form.source_priority,
        coverage_key: payload.form.coverage_key || undefined,
        credential_id: payload.form.credential_id || undefined,
      });
      return mapSourceView(mapAdminSource(await res.json()));
    },
    onSuccess: (updatedSource) => {
      setSelectedSourceId(updatedSource.id);
      setSourceForm(formFromSource(updatedSource));
      invalidateSources();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/sync`, {
        run_mode: "manual",
      });
      return res.json();
    },
    onSuccess: invalidateSources,
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const healthMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      const res = await apiRequest("POST", `/api/admin/sources/${sourceId}/health`, {});
      return res.json();
    },
    onSuccess: invalidateSources,
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const handleSourceSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSourceError(null);
    try {
      parseObjectJson(sourceForm.config_text, "config_json");
      if (isCreateMode || !selectedSource) {
        createSourceMutation.mutate(sourceForm);
      } else {
        updateSourceMutation.mutate({ id: selectedSource.id, form: sourceForm });
      }
    } catch (error) {
      setSourceError(error instanceof Error ? error.message : "config_json invalide");
    }
  };

  return (
    <div className="grid grid-cols-12 gap-8 items-start">
      <div className="col-span-12 lg:col-span-8 space-y-6">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-on-surface-variant font-bold tracking-[0.15em] mb-1 uppercase text-[10px]">
              SOURCES DE DONNÉES
            </p>
            <h2 className="text-2xl font-headline font-extrabold tracking-tight">Ingestion Operations</h2>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => selectedSource && syncMutation.mutate(selectedSource.id)}
              disabled={!selectedSource || syncMutation.isPending}
              className="bg-surface-container-high text-on-surface px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-surface-bright transition-all text-sm disabled:opacity-50"
            >
              Sync maintenant
            </button>
            <button
              onClick={() => {
                setIsCreateMode(true);
                setSelectedSourceId(null);
                setSourceForm(blankSourceForm());
                setSourceError(null);
              }}
              className="bg-primary-container text-on-primary-fixed px-4 py-2 rounded-lg font-bold text-sm"
            >
              Nouvelle source
            </button>
          </div>
        </div>

        <div className="bg-surface-container rounded-xl overflow-hidden border border-white/5">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-high">
                {["Nom", "Plateforme", "Owner", "Santé", "Actif", "Dernier Sync"].map((heading) => (
                  <th key={heading} className="px-6 py-4 text-xs font-bold text-on-surface-variant/70 uppercase tracking-widest">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {sourcesLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4">
                    <div className="h-10 bg-surface-container-high rounded animate-pulse"></div>
                  </td>
                </tr>
              ) : (
                allSources.map((source) => (
                  <tr
                    key={source.id}
                    onClick={() => {
                      setSelectedSourceId(source.id);
                      setIsCreateMode(false);
                    }}
                    className={`hover:bg-surface-container-high/50 transition-colors cursor-pointer ${selectedSource?.id === source.id && !isCreateMode ? "bg-surface-container-high/30" : ""}`}
                  >
                    <td className="px-6 py-4 font-semibold text-on-surface">{source.name}</td>
                    <td className="px-6 py-4">{source.platform}</td>
                    <td className="px-6 py-4">
                      <OwnerBadge type={source.ownerType} />
                    </td>
                    <td className="px-6 py-4">
                      <HealthBar pct={source.healthPct} />
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          updateSourceMutation.mutate({
                            id: source.id,
                            form: { ...formFromSource(source), is_active: !source.isActive },
                          });
                        }}
                        className={`w-10 h-5 rounded-full relative p-0.5 transition-colors ${source.isActive ? "bg-primary/20" : "bg-surface-container-highest"}`}
                      >
                        <div className={`w-4 h-4 rounded-full absolute top-0.5 transition-all ${source.isActive ? "right-0.5 bg-primary" : "left-0.5 bg-on-secondary-container"}`}></div>
                      </button>
                    </td>
                    <td className="px-6 py-4 text-sm text-on-surface-variant">{source.lastSync}</td>
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
            ].map(({ icon, color, borderColor, label, value }) => (
              <div key={label} className={`flex-1 bg-surface-container-high p-4 rounded-lg flex flex-col items-center gap-2 text-center border-l-2 ${borderColor}`}>
                <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                <span className="text-xl font-headline font-bold">{compactNumber(value)}</span>
                <span className="text-[10px] font-bold uppercase tracking-tighter opacity-60">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-container rounded-xl border border-white/5">
          <div className="p-6 border-b border-white/5 flex justify-between items-center">
            <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface-variant">
              Historique Sync Runs
            </h3>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-container-high/30">
              <tr>
                {["Run ID", "Mode", "Status", "Records (F/I/E)", "Started at"].map((heading) => (
                  <th key={heading} className="px-6 py-3 font-bold opacity-70 text-xs">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {runsLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4">
                    <div className="h-6 bg-surface-container-high rounded animate-pulse"></div>
                  </td>
                </tr>
              ) : (
                (runs ?? []).map((run) => (
                  <tr key={run.id}>
                    <td className="px-6 py-4 font-mono text-xs">#{run.id}</td>
                    <td className="px-6 py-4">{run.mode}</td>
                    <td className="px-6 py-4">{run.status}</td>
                    <td className="px-6 py-4">{run.fetched} / {run.inserted} / {run.errors}</td>
                    <td className="px-6 py-4 text-on-surface-variant">{run.startedAt}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-4 space-y-6">
        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">
            {isCreateMode || !selectedSource ? "CRÉATION DE SOURCE" : "ÉDITION DE SOURCE"}
          </p>
          <form className="space-y-4" onSubmit={handleSourceSubmit}>
            <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" value={sourceForm.source_name} onChange={(event) => setSourceForm({ ...sourceForm, source_name: event.target.value })} />
            <div className="grid grid-cols-2 gap-4">
              <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={sourceForm.platform} disabled={!isCreateMode} onChange={(event) => setSourceForm({ ...sourceForm, platform: event.target.value })}>
                {PLATFORM_OPTIONS.filter((option) => option.value !== "tiktok").map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={sourceForm.owner_type} disabled={!isCreateMode} onChange={(event) => setSourceForm({ ...sourceForm, owner_type: event.target.value })}>
                {OWNER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
            <textarea className="w-full bg-[#0d0e10] p-3 rounded-lg font-mono text-[11px] text-primary/80 h-28 overflow-y-auto border border-white/5" value={sourceForm.config_text} onChange={(event) => setSourceForm({ ...sourceForm, config_text: event.target.value })} />
            <div className="grid grid-cols-2 gap-4">
              <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="number" value={sourceForm.sync_frequency_minutes} onChange={(event) => setSourceForm({ ...sourceForm, sync_frequency_minutes: Number(event.target.value || 0) })} />
              <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="number" value={sourceForm.freshness_sla_hours} onChange={(event) => setSourceForm({ ...sourceForm, freshness_sla_hours: Number(event.target.value || 0) })} />
            </div>
            <details className="bg-surface-container-high rounded-lg p-4">
              <summary className="cursor-pointer text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                Gouvernance source
              </summary>
              <div className="grid grid-cols-1 gap-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={sourceForm.source_purpose} onChange={(event) => setSourceForm({ ...sourceForm, source_purpose: event.target.value })}>
                    {SOURCE_PURPOSE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                  <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="number" value={sourceForm.source_priority} onChange={(event) => setSourceForm({ ...sourceForm, source_priority: Number(event.target.value || 0) })} />
                </div>
                <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" value={sourceForm.coverage_key} onChange={(event) => setSourceForm({ ...sourceForm, coverage_key: event.target.value })} placeholder="coverage_key" />
                <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={sourceForm.credential_id} onChange={(event) => setSourceForm({ ...sourceForm, credential_id: event.target.value })}>
                  <option value="">Aucun credential</option>
                  {credentialOptions.map((credential) => (
                    <option key={credential.credential_id} value={credential.credential_id}>
                      {credential.entity_name} · {credential.platform}
                    </option>
                  ))}
                </select>
              </div>
            </details>
            {sourceError ? <p className="text-xs text-error">{sourceError}</p> : null}
            <button type="submit" disabled={createSourceMutation.isPending || updateSourceMutation.isPending} className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
              {createSourceMutation.isPending || updateSourceMutation.isPending ? "Enregistrement..." : "Enregistrer les modifications"}
            </button>
            {!isCreateMode && selectedSource ? (
              <button type="button" onClick={() => healthMutation.mutate(selectedSource.id)} disabled={healthMutation.isPending} className="w-full py-2 bg-surface-container-high text-on-surface-variant font-bold rounded-lg text-xs disabled:opacity-50">
                {healthMutation.isPending ? "Vérification..." : "Vérifier la santé"}
              </button>
            ) : null}
          </form>
        </div>

        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <div className="flex justify-between items-center mb-6">
            <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Health Snapshots</p>
            <span className="material-symbols-outlined text-tertiary cursor-pointer" onClick={() => selectedSource && healthMutation.mutate(selectedSource.id)}>
              refresh
            </span>
          </div>
          {snapshotsLoading ? (
            <div className="h-16 bg-surface-container-high rounded animate-pulse"></div>
          ) : !(snapshots ?? []).length ? (
            <div className="text-sm text-on-surface-variant">Aucun snapshot de santé disponible pour cette source.</div>
          ) : (
            <div className="space-y-6 relative before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
              {(snapshots ?? []).map((snapshot) => (
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
  );
}
