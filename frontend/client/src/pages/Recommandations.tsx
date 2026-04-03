import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { RecommendationContext, Recommendation } from "@shared/schema";

const MOCK_CONTEXT: RecommendationContext = {
  nss_global: 45,
  volume: 1200,
  active_alerts: 4,
  last_run: "Il y a 2h",
};

const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "1",
    run_id: "RUN-001",
    priority: "URGENT",
    title: "Ajuster le stock: Ramy Orange",
    rationale: "Transférer 450 unités du hub Tlemcen vers Oran-Est pour éviter la péremption et répondre au pic local.",
    target: "Tlemcen → Oran",
    timing: "< 24 heures",
    kpi_impact: "+12% Ventes",
    status: "ACTIVE",
    created_at: "2024-10-20",
    confidence: 92,
    provider: "Anthropic Claude 3",
    model: "claude-3-opus",
    summary: "L'analyse des flux logistiques sur la région Ouest indique un surstock critique sur les produits Ramy Orange 1L à Tlemcen.",
  },
  {
    id: "2",
    run_id: "RUN-001",
    priority: "MOYEN",
    title: "Boost Promo Facebook",
    rationale: "Augmenter le budget publicitaire de 15% sur le segment 'Familles' à Alger Centre pendant le week-end.",
    target: "Alger (C)",
    timing: "Week-end",
    kpi_impact: "ROI est. 4.2x",
    status: "ACTIVE",
    created_at: "2024-10-20",
    confidence: 88,
    provider: "Anthropic Claude 3",
    model: "claude-3-opus",
    summary: "Segment familles sous-exploité à Alger Centre.",
  },
  {
    id: "3",
    run_id: "RUN-001",
    priority: "BAS",
    title: "Maintenance Préventive",
    rationale: "Planifier une inspection de la chaîne de remplissage L-3 à l'usine de Boumerdès (vibrations détectées).",
    target: "Boumerdès",
    timing: "3-5 Jours",
    kpi_impact: "Arrêt prod.",
    status: "ACTIVE",
    created_at: "2024-10-20",
    confidence: 75,
    provider: "Anthropic Claude 3",
    model: "claude-3-opus",
    summary: "Maintenance préventive recommandée.",
  },
];

function PriorityBadge({ priority }: { priority: string }) {
  const map: Record<string, string> = {
    URGENT: "bg-error/10 text-error",
    MOYEN: "bg-primary/10 text-primary",
    BAS: "bg-gray-500/10 text-gray-500",
  };
  return (
    <span className={`px-2 py-0.5 text-[10px] font-black rounded-sm uppercase tracking-tighter ${map[priority] ?? ""}`}>
      {priority}
    </span>
  );
}

const RUN_HISTORY = [
  { date: "20 Oct, 09:15", trigger: "Planifié", count: 12, confidence: 88, provider: "Anthropic", model: "claude-3-opus", status: "COMPLÉTÉ", statusColor: "text-tertiary", dotColor: "bg-tertiary" },
  { date: "19 Oct, 23:45", trigger: "Alerte", count: 5, confidence: 74, provider: "Ollama Local", model: "mistral-7b", status: "ARCHIVÉ", statusColor: "text-gray-500", dotColor: "bg-gray-500" },
  { date: "19 Oct, 18:20", trigger: "Manuel", count: 2, confidence: 95, provider: "OpenAI", model: "gpt-4o", status: "ÉCHOUÉ", statusColor: "text-error", dotColor: "bg-error" },
];

// Map API context-preview response to RecommendationContext
function mapContextFromApi(apiData: Record<string, unknown>): RecommendationContext {
  return {
    nss_global: Number(apiData.nss_global ?? apiData.nss_score ?? MOCK_CONTEXT.nss_global),
    volume: Number(apiData.volume ?? apiData.total_volume ?? MOCK_CONTEXT.volume),
    active_alerts: Number(apiData.active_alerts ?? apiData.alerts_count ?? MOCK_CONTEXT.active_alerts),
    last_run: String(apiData.last_run ?? apiData.last_run_at ?? MOCK_CONTEXT.last_run),
  };
}

// Map API recommendation to Recommendation schema
function mapRecommendationFromApi(r: Record<string, unknown>): Recommendation {
  return {
    id: String(r.id ?? r.recommendation_id ?? ""),
    run_id: String(r.run_id ?? ""),
    priority: (r.priority as Recommendation["priority"]) ?? "MOYEN",
    title: String(r.title ?? ""),
    rationale: String(r.rationale ?? r.description ?? ""),
    target: String(r.target ?? r.target_platform ?? ""),
    timing: String(r.timing ?? ""),
    kpi_impact: String(r.kpi_impact ?? ""),
    status: (r.status as Recommendation["status"]) ?? "ACTIVE",
    created_at: String(r.created_at ?? ""),
    confidence: Number(r.confidence ?? 80),
    provider: String(r.provider ?? ""),
    model: String(r.model ?? ""),
    summary: String(r.summary ?? ""),
  };
}

// Default providers list
const DEFAULT_PROVIDERS = [
  { id: "ollama", name: "Ollama Local", models: ["llama3-70b-instruct-q4_K_M", "mistral-7b"] },
  { id: "anthropic", name: "Anthropic Claude", models: ["claude-3-opus", "claude-3-sonnet"] },
  { id: "openai", name: "OpenAI GPT", models: ["gpt-4o", "gpt-4-turbo"] },
  { id: "google", name: "Google Gemini", models: ["gemini-pro"] },
];

export default function Recommandations() {
  const [genForm, setGenForm] = useState({
    trigger_type: "Manuel",
    provider: "Ollama Local",
    model: "llama3-70b-instruct-q4_K_M",
  });
  const [isGenerating, setIsGenerating] = useState(false);

  const queryClientHook = useQueryClient();

  const { data: providersRaw } = useQuery<typeof DEFAULT_PROVIDERS>({
    queryKey: ["/api/recommendations/providers"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/recommendations/providers");
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.providers ?? []);
        return list.length > 0 ? list : DEFAULT_PROVIDERS;
      } catch {
        return DEFAULT_PROVIDERS;
      }
    },
  });

  const { data: context, isLoading: contextLoading } = useQuery<RecommendationContext>({
    queryKey: ["/api/recommendations/context-preview"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/recommendations/context-preview?trigger_type=manual");
        const apiData = await res.json();
        return mapContextFromApi(apiData);
      } catch {
        return MOCK_CONTEXT;
      }
    },
  });

  const { data: recommendations, isLoading: recoLoading } = useQuery<Recommendation[]>({
    queryKey: ["/api/recommendations"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/recommendations?status=active");
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.recommendations ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapRecommendationFromApi);
        return mapped.length > 0 ? mapped : MOCK_RECOMMENDATIONS;
      } catch {
        return MOCK_RECOMMENDATIONS;
      }
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/recommendations/generate", {
        trigger_type: genForm.trigger_type,
        provider: genForm.provider,
        model: genForm.model,
      });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/recommendations"] });
      setIsGenerating(false);
    },
    onError: () => setIsGenerating(false),
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await apiRequest("PUT", `/api/recommendations/${id}/status`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/recommendations"] });
    },
  });

  const contextData = context ?? MOCK_CONTEXT;
  const recos = recommendations ?? MOCK_RECOMMENDATIONS;
  const activeRecos = recos.filter((r) => r.status === "ACTIVE");
  const providers = providersRaw ?? DEFAULT_PROVIDERS;

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une recommandation..."
      onSearch={() => {}}
    >
      <div className="p-8 max-w-7xl mx-auto space-y-10">
        {/* Section 1: Generate */}
        <section>
          <header className="mb-6">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">Module IA</span>
            <h2 className="font-headline font-extrabold text-3xl tracking-tight">Générer des recommandations</h2>
          </header>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Config form */}
            <div className="lg:col-span-2 bg-surface-container rounded-lg p-6 space-y-5">
              <div className="grid grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase text-gray-500">Type de Déclencheur</label>
                  <select
                    className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    value={genForm.trigger_type}
                    onChange={(e) => setGenForm({ ...genForm, trigger_type: e.target.value })}
                    data-testid="select-trigger-type"
                  >
                    <option>Manuel</option>
                    <option>Depuis une alerte</option>
                    <option>Planifié (Cron)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold uppercase text-gray-500">Fournisseur d'IA</label>
                  <select
                    className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    value={genForm.provider}
                    onChange={(e) => setGenForm({ ...genForm, provider: e.target.value })}
                    data-testid="select-provider"
                  >
                    {providers.map((p) => (
                      <option key={p.id ?? p.name}>{p.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase text-gray-500">Nom du Modèle / Endpoint</label>
                <input
                  className="w-full bg-surface-container-highest border-none text-sm py-3 px-4 rounded-sm focus:ring-1 focus:ring-primary/40 focus:outline-none"
                  type="text"
                  value={genForm.model}
                  onChange={(e) => setGenForm({ ...genForm, model: e.target.value })}
                  data-testid="input-model-name"
                />
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <div className="flex gap-4">
                  <div className="px-3 py-1.5 bg-surface-container-high rounded-sm">
                    <span className="text-[10px] font-bold text-gray-500 uppercase block">Tokens Estimés</span>
                    <span className="text-sm font-bold text-tertiary">2.4k</span>
                  </div>
                  <div className="px-3 py-1.5 bg-surface-container-high rounded-sm">
                    <span className="text-[10px] font-bold text-gray-500 uppercase block">Coût est.</span>
                    <span className="text-sm font-bold text-white">0.00$</span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setIsGenerating(true);
                    generateMutation.mutate();
                  }}
                  disabled={generateMutation.isPending}
                  className="bg-gradient-to-r from-primary to-primary-container text-on-primary-container px-8 py-3 rounded-sm font-bold flex items-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50"
                  data-testid="btn-generate"
                >
                  <span className="material-symbols-outlined text-sm">rocket_launch</span>
                  <span>{generateMutation.isPending ? "Génération..." : "Générer"}</span>
                </button>
              </div>
            </div>

            {/* Context Stats */}
            {contextLoading ? (
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-24 bg-surface-container rounded-lg animate-pulse"></div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {[
                  { icon: "query_stats", color: "text-primary", borderColor: "border-primary/20", value: contextData.nss_global, label: "NSS Global" },
                  { icon: "database", color: "text-tertiary", borderColor: "border-tertiary/20", value: `${contextData.volume >= 1000 ? (contextData.volume / 1000).toFixed(1) + "k" : contextData.volume}`, label: "Volume" },
                  { icon: "warning", color: "text-error", borderColor: "border-error/20", value: contextData.active_alerts, label: "Alertes Actives" },
                  { icon: "history", color: "text-gray-500", borderColor: "border-white/5", value: null, label: "Dernière run", subValue: contextData.last_run },
                ].map(({ icon, color, borderColor, value, label, subValue }) => (
                  <div
                    key={label}
                    className={`bg-surface-container p-4 rounded-lg flex flex-col justify-between border-l-2 ${borderColor}`}
                  >
                    <span className={`material-symbols-outlined text-xl ${color}`}>{icon}</span>
                    <div>
                      {value !== null ? (
                        <p className="text-2xl font-black font-headline tracking-tighter">{value}</p>
                      ) : (
                        <p className="text-lg font-bold font-headline leading-tight">{label}</p>
                      )}
                      <p className="text-[10px] font-bold uppercase text-gray-500">
                        {value !== null ? label : subValue}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Section 2: Active Recommendations */}
        <section>
          <div className="flex justify-between items-end mb-6">
            <header>
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">Analyse en cours</span>
              <h2 className="font-headline font-extrabold text-3xl tracking-tight">Recommandations actives</h2>
            </header>
            <button className="bg-surface-container-high px-4 py-2 rounded-sm text-xs font-bold hover:bg-surface-bright transition-colors">
              Tout Archiver
            </button>
          </div>

          {recoLoading ? (
            <div className="bg-surface-container rounded-lg p-6 grid grid-cols-1 md:grid-cols-3 gap-5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-surface-container-high rounded-lg animate-pulse"></div>
              ))}
            </div>
          ) : activeRecos.length > 0 && (
            <div className="bg-surface-container rounded-lg overflow-hidden border border-white/5">
              {/* Group header */}
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
                    <span className="material-symbols-outlined text-tertiary text-sm">verified</span>
                    <span className="text-sm font-bold">{activeRecos[0]?.confidence}% Confiance</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-[10px] font-bold uppercase text-gray-500">
                  <div className="flex items-center gap-1.5 bg-surface-dim px-2 py-1 rounded-sm">
                    <span className="material-symbols-outlined text-xs">memory</span>
                    <span>{activeRecos[0]?.provider}</span>
                  </div>
                  <span>Aujourd'hui, 14:32</span>
                </div>
              </div>

              {/* Analysis summary */}
              <div className="px-6 py-4 bg-surface-dim/40 border-b border-white/5">
                <p className="text-sm text-gray-300 leading-relaxed italic border-l-2 border-primary/40 pl-4">
                  "{activeRecos[0]?.summary}"
                </p>
              </div>

              {/* Recommendation cards */}
              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-5">
                {activeRecos.map((reco) => (
                  <div
                    key={reco.id}
                    className="bg-surface-container-high rounded-lg p-5 flex flex-col h-full border border-transparent hover:border-primary/20 transition-all"
                    data-testid={`reco-card-${reco.id}`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <PriorityBadge priority={reco.priority} />
                      <span className="material-symbols-outlined text-gray-500 text-sm cursor-pointer hover:text-white transition-colors">more_vert</span>
                    </div>
                    <h3 className="text-sm font-bold font-headline mb-2">{reco.title}</h3>
                    <p className="text-xs text-gray-400 mb-5 flex-1 leading-relaxed">{reco.rationale}</p>
                    <div className="space-y-2.5 mb-5">
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">Cible</span>
                        <span className="text-white font-medium">{reco.target}</span>
                      </div>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">Timing</span>
                        <span className="text-white font-medium">{reco.timing}</span>
                      </div>
                      <div className="flex justify-between items-center text-[11px]">
                        <span className="text-gray-500 uppercase font-bold">KPI Impact</span>
                        <span className="text-tertiary font-bold">{reco.kpi_impact}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => updateStatusMutation.mutate({ id: reco.id, status: "APPLIED" })}
                        className="flex-1 py-2 rounded-sm bg-primary/10 text-primary text-[11px] font-bold hover:bg-primary/20 transition-all"
                      >
                        Appliquer
                      </button>
                      <button
                        onClick={() => updateStatusMutation.mutate({ id: reco.id, status: "ARCHIVED" })}
                        className="p-2 rounded-sm bg-surface-container-highest text-gray-400 hover:text-white transition-all"
                      >
                        <span className="material-symbols-outlined text-sm">close</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Section 3: Run History */}
        <section>
          <header className="mb-6">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/60">Archives de l'IA</span>
            <h2 className="font-headline font-extrabold text-3xl tracking-tight">Historique des runs</h2>
          </header>
          <div className="bg-surface-container rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50">
                  {["Date", "Déclencheur", "# Recos", "Confiance", "Provider", "Modèle", "Statut"].map((h) => (
                    <th key={h} className="px-6 py-4 text-[10px] font-black uppercase text-gray-500 tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {RUN_HISTORY.map((run, i) => (
                  <tr key={i} className="hover:bg-surface-bright/30 transition-colors">
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
                          <div className="bg-tertiary h-full" style={{ width: `${run.confidence}%` }}></div>
                        </div>
                        <span className="text-xs font-bold">{run.confidence}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs">{run.provider}</td>
                    <td className="px-6 py-4 text-xs text-gray-500 font-mono">{run.model}</td>
                    <td className="px-6 py-4">
                      <span className={`flex items-center gap-1.5 text-[10px] font-bold ${run.statusColor}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${run.dotColor}`}></span>
                        {run.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* FAB */}
      <div className="fixed bottom-8 right-8 z-50">
        <button className="w-14 h-14 bg-gradient-to-br from-primary to-primary-container rounded-sm shadow-[0_10px_30px_rgba(245,102,0,0.3)] flex items-center justify-center text-on-primary-container hover:scale-110 active:scale-95 transition-all">
          <span className="material-symbols-outlined text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
        </button>
      </div>
    </AppShell>
  );
}
