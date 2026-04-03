import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { Watchlist, WatchlistMetrics } from "@shared/schema";

const MOCK_WATCHLISTS: Watchlist[] = [
  {
    id: "1",
    name: "Ramy Citron (Tout Alger)",
    description: "Analyse comparative des parts de marché et du sentiment consommateur sur la gamme Citron dans la zone urbaine d'Alger.",
    scope: "RÉGION",
    is_active: true,
    owners: ["R", "A"],
  },
  {
    id: "2",
    name: "Disponibilité Oran",
    description: "Monitoring de la présence en rayon et des ruptures de stock critiques dans les hypermarchés d'Oran.",
    scope: "CANAL",
    is_active: true,
    owners: ["M"],
  },
  {
    id: "3",
    name: "Ramy Fraise 250ml",
    description: "Suivi du lancement produit et premiers retours consommateurs sur le format pocket 250ml Fraise.",
    scope: "PRODUIT",
    is_active: false,
    owners: ["S"],
  },
];

const MOCK_METRICS: WatchlistMetrics = {
  nss_score: 45,
  nss_delta: 5,
  volume: 1200,
  volume_delta: 300,
  aspects: [
    { name: "Goût", score: 85 },
    { name: "Prix", score: 62 },
    { name: "Disponibilité", score: 34, is_negative: true },
    { name: "Emballage", score: 78 },
    { name: "Fraîcheur", score: 91 },
  ],
  quick_insight: "Le sentiment positif sur le Goût est en hausse de 12% suite à la nouvelle campagne d'affichage dans le centre d'Alger. Attention aux retours sur la Disponibilité dans le quartier d'Hydra.",
  last_updated: "il y a 10m",
};

type TabFilter = "Toutes" | "Actives" | "Inactives";

// Map API watchlist to Watchlist schema
function mapWatchlistFromApi(w: Record<string, unknown>): Watchlist {
  return {
    id: String(w.id ?? w.watchlist_id ?? ""),
    name: String(w.name ?? ""),
    description: String(w.description ?? ""),
    scope: (w.scope as Watchlist["scope"]) ?? "PRODUIT",
    is_active: Boolean(w.is_active ?? true),
    owners: (w.owners as string[]) ?? [],
  };
}

// Map API metrics response to WatchlistMetrics schema
// API returns: { nss_current, nss_previous, delta_nss, volume_current, volume_previous, aspect_breakdown }
function mapMetricsFromApi(apiData: Record<string, unknown>): WatchlistMetrics {
  // Handle both API format and direct format
  const nssScore = Number(apiData.nss_current ?? apiData.nss_score ?? MOCK_METRICS.nss_score);
  const nssPrev = Number(apiData.nss_previous ?? 0);
  const nssDelta = Number(apiData.delta_nss ?? apiData.nss_delta ?? (nssScore - nssPrev));
  const volumeCurrent = Number(apiData.volume_current ?? apiData.volume ?? MOCK_METRICS.volume);
  const volumePrev = Number(apiData.volume_previous ?? 0);
  const volumeDelta = Number(apiData.volume_delta ?? (volumeCurrent - volumePrev));

  // aspect_breakdown can be array of { aspect, score, is_negative } or similar
  const rawAspects = (apiData.aspect_breakdown ?? apiData.aspects) as Array<Record<string, unknown>> | undefined;
  const aspects: WatchlistMetrics["aspects"] = rawAspects?.map((a) => ({
    name: String(a.name ?? a.aspect ?? ""),
    score: Number(a.score ?? a.pct ?? 0),
    is_negative: Boolean(a.is_negative ?? false),
  })) ?? MOCK_METRICS.aspects;

  return {
    nss_score: nssScore,
    nss_delta: nssDelta,
    volume: volumeCurrent,
    volume_delta: volumeDelta,
    aspects: aspects.length > 0 ? aspects : MOCK_METRICS.aspects,
    quick_insight: String(apiData.quick_insight ?? apiData.insight ?? MOCK_METRICS.quick_insight),
    last_updated: String(apiData.last_updated ?? MOCK_METRICS.last_updated),
  };
}

function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className="text-[10px] font-bold text-on-surface-variant tracking-wider uppercase mb-2 block">
      {scope}
    </span>
  );
}

export default function Watchlists() {
  const [tab, setTab] = useState<TabFilter>("Toutes");
  const [selectedId, setSelectedId] = useState<string | null>("1");

  const { data: watchlists, isLoading: watchlistsLoading } = useQuery<Watchlist[]>({
    queryKey: ["/api/watchlists"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/watchlists?is_active=true");
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.watchlists ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapWatchlistFromApi);
        return mapped.length > 0 ? mapped : MOCK_WATCHLISTS;
      } catch {
        return MOCK_WATCHLISTS;
      }
    },
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery<WatchlistMetrics>({
    queryKey: ["/api/watchlists", selectedId, "metrics"],
    queryFn: async () => {
      if (!selectedId) return MOCK_METRICS;
      try {
        const res = await apiRequest("GET", `/api/watchlists/${selectedId}/metrics`);
        const apiData = await res.json();
        return mapMetricsFromApi(apiData);
      } catch {
        return MOCK_METRICS;
      }
    },
    enabled: !!selectedId,
  });

  const allWatchlists = watchlists ?? MOCK_WATCHLISTS;
  const filtered = allWatchlists.filter((w) => {
    if (tab === "Actives") return w.is_active;
    if (tab === "Inactives") return !w.is_active;
    return true;
  });

  const metricsData = metrics ?? MOCK_METRICS;
  const selectedWatchlist = allWatchlists.find((w) => w.id === selectedId);

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une watchlist..."
      onSearch={() => {}}
    >
      <div className="p-8 flex gap-8">
        {/* Left: Grid */}
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-end mb-8">
            <div>
              <span className="text-[10px] font-bold text-primary tracking-[0.2em] uppercase mb-1 block">
                SURVEILLANCE
              </span>
              <h1 className="font-headline text-3xl font-black tracking-tight">Watchlists</h1>
            </div>
            <div className="bg-surface-container-high p-1 rounded-lg flex gap-1">
              {(["Toutes", "Actives", "Inactives"] as TabFilter[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    tab === t ? "bg-surface-bright text-white shadow-sm" : "text-on-surface-variant hover:text-white"
                  }`}
                  data-testid={`filter-tab-${t.toLowerCase()}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Card grid */}
          {watchlistsLoading ? (
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-surface-container rounded-xl animate-pulse"></div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {filtered.map((watchlist) => (
                <div
                  key={watchlist.id}
                  onClick={() => setSelectedId(watchlist.id === selectedId ? null : watchlist.id)}
                  className={`group bg-surface-container hover:bg-surface-container-high transition-all duration-300 p-5 rounded-xl cursor-pointer relative overflow-hidden border ${
                    selectedId === watchlist.id ? "border-primary/20 bg-surface-container-high" : "border-transparent hover:border-white/5"
                  }`}
                  data-testid={`watchlist-card-${watchlist.id}`}
                >
                  {/* Active/Inactive indicator */}
                  <div className="absolute top-0 right-0 p-4">
                    <div className="flex items-center gap-2">
                      {watchlist.is_active ? (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-tertiary shadow-[0_0_8px_#4cd6ff]"></span>
                          <span className="text-[10px] font-medium text-tertiary">ACTIF</span>
                        </>
                      ) : (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-on-surface-variant/30"></span>
                          <span className="text-[10px] font-medium text-on-surface-variant">INACTIF</span>
                        </>
                      )}
                    </div>
                  </div>

                  <ScopeBadge scope={watchlist.scope} />
                  <h3 className="font-headline font-semibold text-lg text-on-surface mb-2">
                    {watchlist.name}
                  </h3>
                  <p className="text-xs text-on-surface-variant leading-relaxed mb-6 line-clamp-2">
                    {watchlist.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <div className="flex -space-x-2">
                      {watchlist.owners.map((owner) => (
                        <div
                          key={owner}
                          className="w-6 h-6 rounded-full border-2 border-surface bg-surface-container-highest flex items-center justify-center text-[10px] font-bold"
                        >
                          {owner}
                        </div>
                      ))}
                    </div>
                    <span className="material-symbols-outlined text-on-surface-variant/30 group-hover:text-primary transition-colors text-lg">
                      chevron_right
                    </span>
                  </div>
                </div>
              ))}

              {/* Add new card */}
              <div className="group border-2 border-dashed border-white/5 hover:border-primary/20 hover:bg-primary/5 transition-all duration-300 p-5 rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer">
                <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-primary">add</span>
                </div>
                <span className="text-xs font-semibold text-on-surface-variant group-hover:text-primary transition-colors">
                  Créer une watchlist
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Detail panel */}
        {selectedWatchlist && (
          <aside className="w-[380px] flex flex-col gap-4 shrink-0">
            <div className="glass-panel rounded-xl p-6 border border-white/5 shadow-2xl">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className="text-[10px] font-bold text-primary tracking-widest uppercase mb-1 block">
                    SÉLECTION
                  </span>
                  <h2 className="font-headline font-semibold text-xl">{selectedWatchlist.name}</h2>
                </div>
                <button className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                  <span className="material-symbols-outlined text-on-surface-variant">more_vert</span>
                </button>
              </div>

              {/* Metrics Grid */}
              {metricsLoading ? (
                <div className="grid grid-cols-2 gap-4 mb-8">
                  {[1, 2].map((i) => (
                    <div key={i} className="h-20 bg-surface-container-low rounded-lg animate-pulse"></div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 mb-8">
                  <div className="bg-surface-container-low p-4 rounded-lg">
                    <span className="text-[10px] font-bold text-on-surface-variant/60 uppercase mb-2 block">Score NSS</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-white tracking-tighter">{metricsData.nss_score}</span>
                      <div className="flex items-center text-[10px] font-bold text-tertiary">
                        <span className="material-symbols-outlined text-sm">arrow_upward</span>
                        {metricsData.nss_delta}
                      </div>
                    </div>
                  </div>
                  <div className="bg-surface-container-low p-4 rounded-lg">
                    <span className="text-[10px] font-bold text-on-surface-variant/60 uppercase mb-2 block">Volume Feedback</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-white tracking-tighter">
                        {metricsData.volume >= 1000 ? `${(metricsData.volume / 1000).toFixed(1)}k` : metricsData.volume}
                      </span>
                      <div className="flex items-center text-[10px] font-bold text-tertiary">
                        <span className="material-symbols-outlined text-sm">arrow_upward</span>
                        {metricsData.volume_delta}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Aspect Breakdown */}
              <div className="space-y-4 mb-8">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">
                    Répartition par Aspect
                  </span>
                  <span className="text-[10px] text-on-surface-variant/40 italic">
                    Mise à jour {metricsData.last_updated}
                  </span>
                </div>
                <div className="space-y-3">
                  {metricsData.aspects.map((aspect) => (
                    <div key={aspect.name}>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-on-surface/80">{aspect.name}</span>
                        <span className={`font-bold ${aspect.is_negative ? "text-error" : "text-primary"}`}>
                          {aspect.score}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            aspect.is_negative
                              ? "bg-error"
                              : "bg-gradient-to-r from-primary to-primary-container"
                          }`}
                          style={{ width: `${aspect.score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <button className="w-full py-3 bg-surface-container-highest hover:bg-surface-bright transition-colors rounded-lg text-xs font-bold uppercase tracking-widest text-on-surface">
                Voir les détails analytiques
              </button>
            </div>

            {/* Quick Insights */}
            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <h4 className="text-xs font-bold text-on-surface mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary text-sm">insights</span>
                Quick Insights
              </h4>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                {metricsData.quick_insight}
              </p>
            </div>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
