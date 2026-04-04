import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import {
  flattenProviderCatalog,
  getPrimaryRecommendation,
  mapContextPreview,
  mapRecommendation,
} from "@/lib/apiMappings";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

interface RecommendationContextView {
  nss_global: number | null;
  volume: number;
  active_alerts: number;
  active_watchlists: number;
  last_run: string;
  estimated_tokens: number;
}

interface RecommendationView {
  id: string;
  priority: string;
  title: string;
  rationale: string;
  target: string;
  timing: string;
  kpi_impact: string;
  status: string;
  created_at: string;
  confidence: number;
  provider: string;
  model: string;
  summary: string;
  count: number;
  trigger: string;
}

interface ProviderGroup {
  id: string;
  name: string;
  models: string[];
}

function toTriggerLabel(trigger: string | undefined | null): string {
  if (trigger === "alert") return "Depuis une alerte";
  if (trigger === "weekly_report") return "Planifié";
  return "Manuel";
}

function prettyProviderName(providerId: string | undefined | null): string {
  switch ((providerId || "").toLowerCase()) {
    case "ollama":
    case "ollama_local":
      return "Ollama Local";
    case "anthropic":
      return "Anthropic Claude";
    case "openai":
      return "OpenAI GPT";
    case "google":
    case "gemini":
      return "Google Gemini";
    default:
      return providerId || "-";
  }
}

function providerBadgeLabel(providerId: string, model: string): string {
  const base = prettyProviderName(providerId);
  return model ? `${base} ${model}` : base;
}

function formatRelativeRunLabel(value: string | undefined | null): string {
  if (!value || value === "-") return "Jamais";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  const diffMs = Date.now() - parsed.getTime();
  if (diffMs < 60 * 60 * 1000) {
    const minutes = Math.max(1, Math.round(diffMs / (60 * 1000)));
    return `Il y a ${minutes} min`;
  }
  if (diffMs < 24 * 60 * 60 * 1000) {
    const hours = Math.max(1, Math.round(diffMs / (60 * 60 * 1000)));
    return `Il y a ${hours}h`;
  }
  const days = Math.max(1, Math.round(diffMs / (24 * 60 * 60 * 1000)));
  return `Il y a ${days}j`;
}

function normalizePriority(value: string | undefined | null, confidence: number): string {
  const raw = (value || "").toUpperCase();
  if (raw.includes("HIGH") || raw.includes("URGENT")) return "URGENT";
  if (raw.includes("LOW") || raw.includes("BAS")) return "BAS";
  if (raw.includes("MED") || raw.includes("MOYEN")) return "MOYEN";
  if (confidence >= 85) return "URGENT";
  if (confidence >= 65) return "MOYEN";
  return "BAS";
}

function buildRecoView(value: unknown): RecommendationView {
  const recommendation = mapRecommendation(value);
  const primary = getPrimaryRecommendation(recommendation);
  const confidence = Number(recommendation.confidence_score ?? 0);
  return {
    id: recommendation.recommendation_id,
    priority: normalizePriority(primary?.priority, confidence),
    title: primary?.title || recommendation.analysis_summary || "Recommendation IA",
    rationale:
      primary?.description ||
      recommendation.data_quality_note ||
      "Aucun rationale détaillé n'est encore disponible.",
    target: primary?.target_platform || "Toutes",
    timing: primary?.timing || "A prioriser",
    kpi_impact: primary?.kpi_impact || "À évaluer",
    status: recommendation.status || "active",
    created_at: recommendation.created_at || "-",
    confidence,
    provider: recommendation.provider_used || "-",
    model: recommendation.model_used || "-",
    summary:
      recommendation.analysis_summary ||
      recommendation.data_quality_note ||
      "Analyse générée sans résumé complémentaire.",
    count: recommendation.recommendations.length,
    trigger: toTriggerLabel(recommendation.trigger_type),
  };
}

function buildContextView(value: unknown): RecommendationContextView {
  const context = mapContextPreview(value);
  return {
    nss_global: context.nss_global ?? null,
    volume: context.volume_total,
    active_alerts: context.active_alerts_count,
    active_watchlists: context.active_watchlists_count,
    last_run: context.trigger ? toTriggerLabel(context.trigger) : "n/a",
    estimated_tokens: context.estimated_tokens,
  };
}

function buildProviderGroups(value: unknown): ProviderGroup[] {
  const flat = flattenProviderCatalog(value);
  const grouped = new Map<string, ProviderGroup>();
  flat.forEach((provider) => {
    const current = grouped.get(provider.provider_id) || {
      id: provider.provider_id,
      name: prettyProviderName(provider.provider_id),
      models: [],
    };
    current.models.push(provider.model_id);
    grouped.set(provider.provider_id, current);
  });
  return Array.from(grouped.values());
}

function estimatedCostLabel(): string {
  return "Non disponible";
}

function PriorityBadge({ priority }: { priority: string }) {
  const map: Record<string, string> = {
    URGENT: "bg-error/10 text-error",
    MOYEN: "bg-primary/10 text-primary",
    BAS: "bg-gray-500/10 text-gray-500",
  };
  return (
    <span
      className={`px-2 py-0.5 text-[10px] font-black rounded-sm uppercase tracking-tighter ${
        map[priority] ?? ""
      }`}
    >
      {priority}
    </span>
  );
}

function statusLabel(status: string): { label: string; color: string; dotColor: string } {
  if (status === "active") {
    return { label: "COMPLÉTÉ", color: "text-tertiary", dotColor: "bg-tertiary" };
  }
  if (status === "archived") {
    return { label: "ARCHIVÉ", color: "text-gray-500", dotColor: "bg-gray-500" };
  }
  return { label: "ÉCHOUÉ", color: "text-error", dotColor: "bg-error" };
}

export default function Recommandations() {
  const queryClientHook = useQueryClient();
  const [genForm, setGenForm] = useState({
    trigger_type: "manual",
    provider: "",
    model: "",
  });

  const { data: providersRaw } = useQuery<ProviderGroup[]>({
    queryKey: ["/api/recommendations/providers"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/recommendations/providers");
      return buildProviderGroups(await res.json());
    },
  });

  const providers = providersRaw ?? [];

  const activeProvider = genForm.provider || providers[0]?.id || "";
  const availableModels =
    providers.find((provider) => provider.id === activeProvider)?.models ?? [];
  const activeModel = genForm.model || availableModels[0] || "";

  const { data: context, isLoading: contextLoading } = useQuery<RecommendationContextView>({
    queryKey: ["/api/recommendations/context-preview", genForm.trigger_type],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/recommendations/context-preview?trigger_type=${genForm.trigger_type}`,
      );
      return buildContextView(await res.json());
    },
  });

  const { data: recommendations, isLoading: recoLoading } = useQuery<RecommendationView[]>({
    queryKey: ["/api/recommendations"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/recommendations?limit=50");
      const payload = await res.json();
      const list = Array.isArray(payload) ? payload : [];
      return list.map(buildRecoView);
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/recommendations/generate", {
        trigger_type: genForm.trigger_type,
        provider: activeProvider || undefined,
        model: activeModel || undefined,
      });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/recommendations"] });
      queryClientHook.invalidateQueries({
        queryKey: ["/api/recommendations/context-preview", genForm.trigger_type],
      });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "archived" | "dismissed" }) => {
      const res = await apiRequest("PUT", `/api/recommendations/${id}/status`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/recommendations"] });
    },
  });

  const contextData = context ?? {
    nss_global: null,
    volume: 0,
    active_alerts: 0,
    active_watchlists: 0,
    last_run: "n/a",
    estimated_tokens: 0,
  };

  const recos = recommendations ?? [];
  const activeRecos = recos.filter((recommendation) => recommendation.status === "active");
  const latestRecommendation = recos[0] ?? null;
  const lastRunLabel = formatRelativeRunLabel(latestRecommendation?.created_at);
  const activeConfidence = activeRecos[0]?.confidence ?? latestRecommendation?.confidence ?? 0;
  const activeProviderBadge = providerBadgeLabel(
    activeRecos[0]?.provider || latestRecommendation?.provider || "",
    activeRecos[0]?.model || latestRecommendation?.model || "",
  );

  const runHistory = useMemo(() => {
    return recos.map((recommendation) => ({
      date: recommendation.created_at,
      trigger: recommendation.trigger,
      count: recommendation.count,
      confidence: recommendation.confidence,
      provider: recommendation.provider,
      model: recommendation.model,
      ...statusLabel(recommendation.status),
    }));
  }, [recos]);

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une recommandation..."
      onSearch={() => {}}
      avatarSrc={STITCH_AVATARS.recommandations.src}
      avatarAlt={STITCH_AVATARS.recommandations.alt}
    >
      <div className="p-8 max-w-7xl mx-auto space-y-10">
        <section>
          <header className="mb-6">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">
              Module IA
            </span>
            <h2 className="font-headline font-extrabold text-3xl tracking-tight">
              Générer des recommandations
            </h2>
          </header>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-surface-container rounded-lg p-6 space-y-5">
              <div className="grid grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase text-gray-500">
                    Type de Déclencheur
                  </label>
                  <select
                    className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    value={genForm.trigger_type}
                    onChange={(event) =>
                      setGenForm({ ...genForm, trigger_type: event.target.value })
                    }
                    data-testid="select-trigger-type"
                  >
                    <option value="manual">Manuel</option>
                    <option value="alert">Depuis une alerte</option>
                    <option value="weekly_report">Planifié (Cron)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase text-gray-500">
                    Fournisseur d'IA
                  </label>
                  <select
                    className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    value={activeProvider}
                    onChange={(event) =>
                      setGenForm({ ...genForm, provider: event.target.value, model: "" })
                    }
                    data-testid="select-provider"
                  >
                    {providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase text-gray-500">
                  Nom du Modèle / Endpoint
                </label>
                <select
                  className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                  value={activeModel}
                  onChange={(event) => setGenForm({ ...genForm, model: event.target.value })}
                  data-testid="input-model-name"
                >
                  {availableModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <div className="flex gap-4">
                  <div className="px-3 py-1.5 bg-surface-container-high rounded-sm">
                    <span className="text-[10px] font-bold text-gray-500 uppercase block">
                      Tokens Estimés
                    </span>
                    <span className="text-sm font-bold text-tertiary">
                      {contextData.estimated_tokens}
                    </span>
                  </div>
                  <div className="px-3 py-1.5 bg-surface-container-high rounded-sm">
                    <span className="text-[10px] font-bold text-gray-500 uppercase block">
                      Coût est.
                    </span>
                    <span className="text-sm font-bold text-white">
                      {estimatedCostLabel()}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                  className="bg-gradient-to-r from-primary to-primary-container text-on-primary-container px-8 py-3 rounded-sm font-bold flex items-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50"
                  data-testid="btn-generate"
                >
                  <span className="material-symbols-outlined text-sm">rocket_launch</span>
                  <span>{generateMutation.isPending ? "Génération..." : "Générer"}</span>
                </button>
              </div>
            </div>

            {contextLoading ? (
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((item) => (
                  <div
                    key={item}
                    className="h-24 bg-surface-container rounded-lg animate-pulse"
                  ></div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {[
                  {
                    icon: "query_stats",
                    color: "text-primary",
                    borderColor: "border-primary/20",
                    value: contextData.nss_global ?? "n/a",
                    label: "NSS Global",
                  },
                  {
                    icon: "database",
                    color: "text-tertiary",
                    borderColor: "border-tertiary/20",
                    value:
                      contextData.volume >= 1000
                        ? `${(contextData.volume / 1000).toFixed(1)}k`
                        : contextData.volume,
                    label: "Volume (m³)",
                  },
                  {
                    icon: "warning",
                    color: "text-error",
                    borderColor: "border-error/20",
                    value: contextData.active_alerts,
                    label: "Alertes Actives",
                  },
                  {
                    icon: "history",
                    color: "text-gray-500",
                    borderColor: "border-white/5",
                    value: "Dernière run",
                    label: lastRunLabel,
                  },
                ].map(({ icon, color, borderColor, value, label }) => (
                  <div
                    key={label}
                    className={`bg-surface-container p-4 rounded-lg flex flex-col justify-between border-l-2 ${borderColor}`}
                  >
                    <span className={`material-symbols-outlined text-xl ${color}`}>{icon}</span>
                    <div>
                      <p
                        className={`font-headline tracking-tighter ${
                          value === "Dernière run"
                            ? "text-lg font-bold leading-tight"
                            : "text-2xl font-black"
                        }`}
                      >
                        {value}
                      </p>
                      <p className="text-[10px] font-bold uppercase text-gray-500">
                        {label}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section>
          <div className="flex justify-between items-end mb-6">
            <header>
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">
                Analyse en cours
              </span>
              <h2 className="font-headline font-extrabold text-3xl tracking-tight">
                Recommandations actives
              </h2>
            </header>
            <div className="flex gap-2">
              <button
                className="bg-surface-container-high px-4 py-2 rounded-sm text-xs font-bold hover:bg-surface-bright transition-colors disabled:opacity-50"
                disabled={!activeRecos.length || updateStatusMutation.isPending}
                onClick={() => {
                  activeRecos.forEach((recommendation) => {
                    updateStatusMutation.mutate({
                      id: recommendation.id,
                      status: "archived",
                    });
                  });
                }}
                type="button"
              >
                Tout Archiver
              </button>
            </div>
          </div>

          {recoLoading ? (
            <div className="bg-surface-container rounded-lg p-6 grid grid-cols-1 md:grid-cols-3 gap-5">
              {[1, 2, 3].map((item) => (
                <div
                  key={item}
                  className="h-48 bg-surface-container-high rounded-lg animate-pulse"
                ></div>
              ))}
            </div>
          ) : activeRecos.length > 0 ? (
            <div className="bg-surface-container rounded-lg overflow-hidden border border-white/5">
              <div className="p-6 bg-surface-container-high/50 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                      {activeRecos.length}
                    </span>
                    <span className="text-sm font-bold">Actions recommandées</span>
                  </div>
                  <div className="h-4 w-px bg-white/10"></div>
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-tertiary text-sm">
                      verified
                    </span>
                    <span className="text-sm font-bold">
                      {activeConfidence}% Confiance
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-[10px] font-bold uppercase text-gray-500">
                  <div className="flex items-center gap-1.5 bg-surface-dim px-2 py-1 rounded-sm">
                    <span className="material-symbols-outlined text-xs">memory</span>
                    <span>{activeProviderBadge}</span>
                  </div>
                  <span>{latestRecommendation?.created_at || "-"}</span>
                </div>
              </div>

              <div className="px-6 py-4 bg-surface-dim/40 border-b border-white/5">
                <p className="text-sm text-gray-300 leading-relaxed italic border-l-2 border-primary/40 pl-4">
                  "{activeRecos[0]?.summary}"
                </p>
              </div>

              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-5">
                {activeRecos.map((recommendation) => (
                  <div
                    key={recommendation.id}
                    className="bg-surface-container-high rounded-lg p-5 flex flex-col h-full border border-transparent hover:border-primary/20 transition-all"
                    data-testid={`reco-card-${recommendation.id}`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <PriorityBadge priority={recommendation.priority} />
                      <span className="material-symbols-outlined text-gray-500 text-sm cursor-pointer hover:text-white transition-colors">
                        more_vert
                      </span>
                    </div>
                    <h3 className="text-sm font-bold font-headline mb-2">
                      {recommendation.title}
                    </h3>
                    <p className="text-xs text-gray-400 mb-5 flex-1 leading-relaxed">
                      {recommendation.rationale}
                    </p>
                    <div className="space-y-2.5 mb-5">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">Cible</span>
                        <span className="text-white font-medium">{recommendation.target}</span>
                      </div>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">Timing</span>
                        <span className="text-white font-medium">{recommendation.timing}</span>
                      </div>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">KPI Impact</span>
                        <span className="text-tertiary font-bold">
                          {recommendation.kpi_impact}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            id: recommendation.id,
                            status: "archived",
                          })
                        }
                        className="flex-1 py-2 rounded-sm bg-primary/10 text-primary text-[11px] font-bold hover:bg-primary/20 transition-all"
                      >
                        Archiver
                      </button>
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            id: recommendation.id,
                            status: "dismissed",
                          })
                        }
                        className="p-2 rounded-sm bg-surface-container-highest text-gray-400 hover:text-white transition-all"
                      >
                        <span className="material-symbols-outlined text-sm">close</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-surface-container rounded-lg p-6 text-sm text-on-surface-variant">
              Aucune recommandation active disponible.
            </div>
          )}
        </section>

        <section>
          <header className="mb-6">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">
              Archives de l'IA
            </span>
            <h2 className="font-headline font-extrabold text-3xl tracking-tight">
              Historique des runs
            </h2>
          </header>
          <div className="bg-surface-container rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50">
                  {[
                    "Date",
                    "Déclencheur",
                    "# Recos",
                    "Confiance",
                    "Provider",
                    "Modèle",
                    "Statut",
                  ].map((heading) => (
                    <th
                      key={heading}
                      className="px-6 py-4 text-[10px] font-black uppercase text-gray-500 tracking-wider"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {runHistory.map((run, index) => (
                  <tr key={`${run.date}-${index}`} className="hover:bg-surface-bright/30 transition-colors">
                    <td className="px-6 py-4 text-xs font-medium text-white">{run.date}</td>
                    <td className="px-6 py-4">
                      <span className="text-[10px] px-2 py-1 bg-surface-container-highest rounded-full text-gray-400">
                        {run.trigger}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-bold">{run.count}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1 bg-surface-container-highest rounded-full overflow-hidden">
                          <div
                            className="bg-tertiary h-full"
                            style={{ width: `${run.confidence}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-bold">{run.confidence}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs">{run.provider}</td>
                    <td className="px-6 py-4 text-xs text-gray-500 font-mono">{run.model}</td>
                    <td className="px-6 py-4">
                      <span className={`flex items-center gap-1.5 text-[10px] font-bold ${run.color}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${run.dotColor}`}></span>
                        {run.label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="fixed bottom-8 right-8 z-50">
        <button className="w-14 h-14 bg-gradient-to-br from-primary to-primary-container rounded-sm shadow-[0_10px_30px_rgba(245,102,0,0.3)] flex items-center justify-center text-on-primary-container hover:scale-110 active:scale-95 transition-all">
          <span
            className="material-symbols-outlined text-2xl"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            auto_awesome
          </span>
        </button>
      </div>
    </AppShell>
  );
}
