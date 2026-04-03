import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import { mapWatchlist, mapWatchlistMetrics } from "@/lib/apiMappings";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

type TabFilter = "Toutes" | "Actives" | "Inactives";

interface WatchlistView {
  id: string;
  name: string;
  description: string;
  scope: string;
  is_active: boolean;
  owners: string[];
}

interface AspectView {
  name: string;
  score: number;
  is_negative?: boolean;
}

interface WatchlistMetricsView {
  nss_score: number;
  nss_delta: number;
  volume: number;
  volume_delta: number;
  aspects: AspectView[];
  quick_insight: string;
  last_updated: string;
}

function buildOwners(filters: Record<string, unknown>): string[] {
  const candidates = Object.keys(filters)
    .slice(0, 3)
    .map((key) => key.charAt(0).toUpperCase());
  return candidates.length ? candidates : ["R"];
}

function mapWatchlistView(value: unknown): WatchlistView {
  const watchlist = mapWatchlist(value);
  return {
    id: watchlist.watchlist_id,
    name: watchlist.watchlist_name,
    description: watchlist.description || "Aucune description disponible.",
    scope: (watchlist.scope_type || "global").replaceAll("_", " ").toUpperCase(),
    is_active: Boolean(watchlist.is_active),
    owners: buildOwners(watchlist.filters),
  };
}

function mapWatchlistMetricsView(value: unknown): WatchlistMetricsView {
  const metrics = mapWatchlistMetrics(value);
  const aspects = Object.entries(metrics.aspect_breakdown || {}).map(([name, score]) => ({
    name,
    score: Math.min(Math.abs(Number(score)), 100),
    is_negative: Number(score) < 0,
  }));
  return {
    nss_score: Number(metrics.nss_current ?? 0),
    nss_delta: Number(metrics.delta_nss ?? 0),
    volume: Number(metrics.volume_total ?? metrics.volume_current ?? 0),
    volume_delta: Number(metrics.volume_delta ?? 0),
    aspects,
    quick_insight:
      metrics.quick_insight ||
      "Aucun quick insight n'est encore disponible pour cette watchlist.",
    last_updated: metrics.computed_at || "Non calculé",
  };
}

function buildInsightsTitle(name: string): string {
  const parenthetical = name.match(/\(([^)]+)\)/)?.[1]?.trim();
  if (!parenthetical) {
    return "Quick Insights";
  }
  return `Quick Insights - ${parenthetical.replace(/^Tout\s+/i, "")}`;
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
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const watchlistsQuery = useQuery({
    queryKey: ["/api/watchlists"],
    queryFn: async () => {
      const activeRes = await apiRequest("GET", "/api/watchlists?is_active=true");
      const inactiveRes = await apiRequest("GET", "/api/watchlists?is_active=false");
      const active = ((await activeRes.json()) as unknown[]).map(mapWatchlistView);
      const all = ((await inactiveRes.json()) as unknown[]).map(mapWatchlistView);
      const merged = new Map<string, WatchlistView>();
      [...all, ...active].forEach((item) => {
        merged.set(item.id, item);
      });
      return Array.from(merged.values());
    },
  });

  const allWatchlists = watchlistsQuery.data ?? [];

  const filtered = useMemo(() => {
    return allWatchlists.filter((watchlist) => {
      if (tab === "Actives") return watchlist.is_active;
      if (tab === "Inactives") return !watchlist.is_active;
      return true;
    });
  }, [allWatchlists, tab]);

  const selectedWatchlist =
    filtered.find((watchlist) => watchlist.id === selectedId) ||
    allWatchlists.find((watchlist) => watchlist.id === selectedId) ||
    filtered[0] ||
    allWatchlists[0] ||
    null;

  const metricsQuery = useQuery({
    queryKey: ["/api/watchlists", selectedWatchlist?.id, "metrics"],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/watchlists/${selectedWatchlist?.id}/metrics`,
      );
      return mapWatchlistMetricsView(await res.json());
    },
    enabled: !!selectedWatchlist?.id,
  });

  const metricsData = metricsQuery.data;

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une watchlist..."
      onSearch={() => {}}
      avatarSrc={STITCH_AVATARS.watchlists.src}
      avatarAlt={STITCH_AVATARS.watchlists.alt}
    >
      <div className="p-8 flex gap-8">
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-end mb-8">
            <div>
              <span className="text-[10px] font-bold text-primary tracking-[0.2em] uppercase mb-1 block">
                SURVEILLANCE
              </span>
              <h1 className="font-headline text-3xl font-black tracking-tight">Watchlists</h1>
            </div>
            <div className="bg-surface-container-high p-1 rounded-lg flex gap-1">
              {(["Toutes", "Actives", "Inactives"] as TabFilter[]).map((filterValue) => (
                <button
                  key={filterValue}
                  onClick={() => setTab(filterValue)}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    tab === filterValue
                      ? "bg-surface-bright text-white shadow-sm"
                      : "text-on-surface-variant hover:text-white"
                  }`}
                >
                  {filterValue}
                </button>
              ))}
            </div>
          </div>

          {watchlistsQuery.isLoading ? (
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-48 bg-surface-container rounded-xl animate-pulse"></div>
              ))}
            </div>
          ) : watchlistsQuery.isError ? (
            <div className="bg-surface-container rounded-xl p-6 text-sm text-on-surface-variant">
              Impossible de charger les watchlists.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {filtered.map((watchlist) => (
                <div
                  key={watchlist.id}
                  onClick={() => setSelectedId(watchlist.id === selectedId ? null : watchlist.id)}
                  className={`group bg-surface-container hover:bg-surface-container-high transition-all duration-300 p-5 rounded-xl cursor-pointer relative overflow-hidden border ${
                    selectedWatchlist?.id === watchlist.id
                      ? "border-primary/20 bg-surface-container-high"
                      : "border-transparent hover:border-white/5"
                  }`}
                >
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

              {metricsQuery.isLoading ? (
                <div className="grid grid-cols-2 gap-4 mb-8">
                  {[1, 2].map((item) => (
                    <div key={item} className="h-20 bg-surface-container-low rounded-lg animate-pulse"></div>
                  ))}
                </div>
              ) : metricsQuery.isError || !metricsData ? (
                <div className="bg-surface-container-low p-4 rounded-lg mb-8 text-sm text-on-surface-variant">
                  Aucun snapshot métrique disponible pour cette watchlist.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="bg-surface-container-low p-4 rounded-lg">
                      <span className="text-[10px] font-bold text-on-surface-variant/60 uppercase mb-2 block">
                        Score NSS
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-white tracking-tighter">
                          {metricsData.nss_score}
                        </span>
                        <div className="flex items-center text-[10px] font-bold text-tertiary">
                          <span className="material-symbols-outlined text-sm">
                            {metricsData.nss_delta >= 0 ? "arrow_upward" : "arrow_downward"}
                          </span>
                          {Math.abs(metricsData.nss_delta)}
                        </div>
                      </div>
                    </div>
                    <div className="bg-surface-container-low p-4 rounded-lg">
                      <span className="text-[10px] font-bold text-on-surface-variant/60 uppercase mb-2 block">
                        Volume Feedback
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-white tracking-tighter">
                          {metricsData.volume >= 1000
                            ? `${(metricsData.volume / 1000).toFixed(1)}k`
                            : metricsData.volume}
                        </span>
                        <div className="flex items-center text-[10px] font-bold text-tertiary">
                          <span className="material-symbols-outlined text-sm">
                            {metricsData.volume_delta >= 0
                              ? "arrow_upward"
                              : "arrow_downward"}
                          </span>
                          {Math.abs(metricsData.volume_delta)}
                        </div>
                      </div>
                    </div>
                  </div>

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
                      {(metricsData.aspects.length ? metricsData.aspects : [{ name: "Aucun aspect", score: 0 }]).map(
                        (aspect) => (
                          <div key={aspect.name}>
                            <div className="flex justify-between text-xs mb-1.5">
                              <span className="text-on-surface/80">{aspect.name}</span>
                              <span
                                className={`font-bold ${
                                  aspect.is_negative ? "text-error" : "text-primary"
                                }`}
                              >
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
                        ),
                      )}
                    </div>
                  </div>
                </>
              )}

              <button className="w-full py-3 bg-surface-container-highest hover:bg-surface-bright transition-colors rounded-lg text-xs font-bold uppercase tracking-widest text-on-surface">
                Voir les détails analytiques
              </button>
            </div>

            <div className="bg-surface-container p-6 rounded-xl border border-white/5">
              <h4 className="text-xs font-bold text-on-surface mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary text-sm">insights</span>
                {buildInsightsTitle(selectedWatchlist.name)}
              </h4>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                {metricsData?.quick_insight ||
                  "Aucun quick insight n'est encore disponible pour cette watchlist."}
              </p>
            </div>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
