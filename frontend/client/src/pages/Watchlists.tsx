import { useMemo, useState } from "react";
import { useLocation } from "wouter";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  CircleOff,
  Gauge,
  Plus,
  Radar,
  SearchX,
  Sparkles,
  Trash2,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import {
  WatchScopeForm,
  type WatchScopeSubmitValue,
} from "@/components/watch/WatchScopeForm";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "@/hooks/use-toast";
import { mapWatchlist, mapWatchlistMetrics } from "@/lib/apiMappings";
import { filterWatchlistViews } from "@/lib/pageSearchFilters";
import { apiRequest } from "@/lib/queryClient";
import { useTenantId } from "@/lib/tenantContext";
import { buildWatchWizardPayload } from "@/lib/watchWizard";

type TabFilter = "Toutes" | "Actives" | "Inactives";

interface WatchlistView {
  id: string;
  name: string;
  description: string;
  scope: string;
  is_active: boolean;
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

function mapWatchlistView(value: unknown): WatchlistView {
  const watchlist = mapWatchlist(value);
  return {
    id: watchlist.watchlist_id,
    name: watchlist.watchlist_name,
    description: watchlist.description || "Aucune description disponible.",
    scope: (watchlist.scope_type || "global").replaceAll("_", " ").toUpperCase(),
    is_active: Boolean(watchlist.is_active),
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
      "Aucun enseignement automatique n’est encore disponible pour cette surveillance.",
    last_updated: metrics.computed_at || "Non calculé",
  };
}

function buildInsightsTitle(name: string): string {
  const parenthetical = name.match(/\(([^)]+)\)/)?.[1]?.trim();
  if (!parenthetical) return "Lecture rapide";
  return `Lecture rapide · ${parenthetical.replace(/^Tout\s+/i, "")}`;
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    notation: value >= 1_000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export default function Watchlists() {
  const [location, setLocation] = useLocation();
  const clientId = useTenantId();
  const [tab, setTab] = useState<TabFilter>("Toutes");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const queryClient = useQueryClient();
  const showCreateForm = location === "/watchlists/new";

  const watchlistsQuery = useQuery({
    queryKey: ["/api/watchlists", { clientId }],
    queryFn: async () => {
      const activeRes = await apiRequest("GET", "/api/watchlists?is_active=true");
      const inactiveRes = await apiRequest("GET", "/api/watchlists?is_active=false");
      const active = ((await activeRes.json()) as unknown[]).map(mapWatchlistView);
      const inactive = ((await inactiveRes.json()) as unknown[]).map(mapWatchlistView);
      const merged = new Map<string, WatchlistView>();
      [...inactive, ...active].forEach((item) => merged.set(item.id, item));
      return Array.from(merged.values());
    },
    enabled: Boolean(clientId),
  });

  const allWatchlists = watchlistsQuery.data ?? [];
  const activeCount = allWatchlists.filter((watchlist) => watchlist.is_active).length;
  const scopeCount = new Set(allWatchlists.map((watchlist) => watchlist.scope)).size;

  const filtered = useMemo(() => {
    const tabFiltered = allWatchlists.filter((watchlist) => {
      if (tab === "Actives") return watchlist.is_active;
      if (tab === "Inactives") return !watchlist.is_active;
      return true;
    });
    return filterWatchlistViews(tabFiltered, searchQuery);
  }, [allWatchlists, searchQuery, tab]);

  const selectedWatchlist =
    allWatchlists.find((watchlist) => watchlist.id === selectedId) || filtered[0] || null;

  const metricsQuery = useQuery({
    queryKey: ["/api/watchlists/metrics", { clientId, watchlistId: selectedWatchlist?.id }],
    queryFn: async () => {
      const res = await apiRequest(
        "GET",
        `/api/watchlists/${selectedWatchlist?.id}/metrics`,
      );
      return mapWatchlistMetricsView(await res.json());
    },
    enabled: Boolean(selectedWatchlist?.id),
  });

  const metricsData = metricsQuery.data;

  function setCreateOpen(open: boolean) {
    setLocation(open ? "/watchlists/new" : "/watchlists");
  }

  const createMutation = useMutation({
    mutationFn: async (input: WatchScopeSubmitValue) => {
      const watchlistResponse = await apiRequest(
        "POST",
        "/api/watchlists",
        buildWatchWizardPayload(input.payload),
      );
      const watchlist = (await watchlistResponse.json()) as { watchlist_id: string };
      const watchlistId = String(watchlist.watchlist_id);

      try {
        const runResponse = await apiRequest("POST", "/api/watch-runs", {
          watchlist_id: watchlistId,
          requested_channels: input.requestedChannels,
        });
        const run = (await runResponse.json()) as { run_id?: string };
        return {
          watchlist_id: watchlistId,
          run_id: run.run_id ? String(run.run_id) : null,
          run_error: null,
        };
      } catch (error) {
        return {
          watchlist_id: watchlistId,
          run_id: null,
          run_error:
            error instanceof Error ? error.message : "La première collecte n’a pas pu démarrer.",
        };
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/watchlists", { clientId }] });
      setCreateOpen(false);
      setSelectedId(data.watchlist_id);

      if (data.run_error) {
        toast({
          title: "Surveillance créée, collecte non lancée",
          description: data.run_error,
          variant: "destructive",
        });
        return;
      }

      toast({
        title: "Surveillance active",
        description: data.run_id
          ? `La collecte ${data.run_id} vient de démarrer.`
          : "La première collecte vient de démarrer.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Création impossible",
        description: error.message || "Vérifiez le périmètre puis réessayez.",
        variant: "destructive",
      });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (watchlistId: string) => {
      await apiRequest("DELETE", `/api/watchlists/${watchlistId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/watchlists", { clientId }] });
      setSelectedId(null);
      toast({ title: "Surveillance désactivée" });
    },
    onError: (error: Error) => {
      toast({
        title: "Désactivation impossible",
        description: error.message || "Réessayez dans quelques instants.",
        variant: "destructive",
      });
    },
  });

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une surveillance…"
      onSearch={setSearchQuery}
    >
      <div className="page-enter mx-auto w-full max-w-[1580px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <PageHeader
          eyebrow="Surveiller"
          tone="monitor"
          title="Sujets surveillés"
          description="Retrouvez les marques, produits et sujets écoutés. Sélectionnez une ligne pour consulter son état et ses premiers résultats."
          actions={
            <Button
              onClick={() => setCreateOpen(true)}
              className="gap-2"
              data-testid="btn-create-watchlist"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Créer une surveillance
            </Button>
          }
        />

        <section className="mt-6 grid gap-3 sm:grid-cols-3" aria-label="Résumé des surveillances">
          <div className="rounded-2xl border border-action/15 bg-action-container/55 p-4">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-bold text-on-surface-variant">Surveillances actives</p>
              <Activity className="h-4 w-4 text-action" aria-hidden="true" />
            </div>
            <p className="metric-number mt-3 text-3xl font-extrabold text-on-surface">{activeCount}</p>
            <p className="mt-1 text-xs text-on-surface-variant">sur {allWatchlists.length} périmètres</p>
          </div>
          <div className="rounded-2xl border border-insight/15 bg-insight-container/55 p-4">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-bold text-on-surface-variant">Types de sujets</p>
              <Radar className="h-4 w-4 text-insight" aria-hidden="true" />
            </div>
            <p className="metric-number mt-3 text-3xl font-extrabold text-on-surface">{scopeCount}</p>
            <p className="mt-1 text-xs text-on-surface-variant">marques, produits ou sujets</p>
          </div>
          <div className="rounded-2xl border border-monitor/15 bg-monitor-container/55 p-4">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-bold text-on-surface-variant">État de la collecte</p>
              <Gauge className="h-4 w-4 text-monitor" aria-hidden="true" />
            </div>
            <p className="mt-3 font-headline text-lg font-bold text-on-surface">
              {activeCount > 0 ? "En écoute" : "À lancer"}
            </p>
            <p className="mt-1 text-xs text-on-surface-variant">mise à jour par canal configuré</p>
          </div>
        </section>

        <div className="mt-6 grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
          <section className="min-w-0 rounded-2xl border border-outline-variant/45 bg-surface-container-low p-3 sm:p-4">
            <div className="flex flex-col gap-3 border-b border-outline-variant/35 px-1 pb-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-headline text-sm font-bold text-on-surface">Périmètres suivis</h2>
                <p className="mt-1 text-xs text-on-surface-variant">Sélectionnez une ligne pour lire sa situation.</p>
              </div>
              <div className="flex rounded-xl border border-outline-variant/45 bg-surface p-1">
                {(["Toutes", "Actives", "Inactives"] as TabFilter[]).map((filterValue) => (
                  <button
                    key={filterValue}
                    onClick={() => setTab(filterValue)}
                    className={`rounded-lg px-3 py-1.5 text-[10px] font-semibold transition-colors ${
                      tab === filterValue
                        ? "bg-monitor text-white"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                    type="button"
                  >
                    {filterValue}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-3 space-y-2">
              {watchlistsQuery.isLoading ? (
                [1, 2, 3].map((item) => (
                  <div key={item} className="h-24 animate-pulse rounded-xl bg-surface-container-high" />
                ))
              ) : watchlistsQuery.isError ? (
                <div className="rounded-xl border border-error/20 bg-error/5 p-5 text-sm text-on-surface-variant">
                  Les surveillances ne peuvent pas être chargées. Vérifiez la connexion aux sources puis réessayez.
                </div>
              ) : filtered.length === 0 ? (
                <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-outline-variant/55 px-6 text-center">
                  <SearchX className="h-7 w-7 text-on-surface-variant" aria-hidden="true" />
                  <h3 className="mt-4 font-headline text-sm font-bold text-on-surface">Aucune surveillance trouvée</h3>
                  <p className="mt-2 max-w-sm text-xs leading-5 text-on-surface-variant">
                    Modifiez le filtre ou créez un nouveau périmètre avec ses mots-clés et ses sources.
                  </p>
                  <Button className="mt-4 gap-2" size="sm" onClick={() => setCreateOpen(true)}>
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Créer une surveillance
                  </Button>
                </div>
              ) : (
                filtered.map((watchlist) => {
                  const selected = selectedWatchlist?.id === watchlist.id;
                  return (
                    <button
                      key={watchlist.id}
                      onClick={() => setSelectedId(watchlist.id)}
                      className={`interactive-card flex w-full items-center gap-4 rounded-xl border p-4 text-left ${
                        selected
                          ? "border-monitor/30 bg-monitor-container/55"
                          : "border-transparent bg-surface-container"
                      }`}
                      type="button"
                    >
                      <span
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                          watchlist.is_active
                            ? "bg-success/10 text-success"
                            : "bg-surface-container-highest text-on-surface-variant"
                        }`}
                      >
                        {watchlist.is_active ? (
                          <Radar className="h-5 w-5" aria-hidden="true" />
                        ) : (
                          <CircleOff className="h-5 w-5" aria-hidden="true" />
                        )}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="truncate font-headline text-sm font-bold text-on-surface">{watchlist.name}</span>
                          <span className="rounded-full border border-outline-variant/45 px-2 py-0.5 text-[9px] font-bold tracking-wide text-on-surface-variant">
                            {watchlist.scope}
                          </span>
                        </span>
                        <span className="mt-1.5 block truncate text-xs text-on-surface-variant">{watchlist.description}</span>
                      </span>
                      <span className={`hidden text-[9px] font-bold uppercase tracking-wider sm:block ${watchlist.is_active ? "text-success" : "text-on-surface-variant"}`}>
                        {watchlist.is_active ? "En écoute" : "Désactivée"}
                      </span>
                      <ArrowRight className={`h-4 w-4 shrink-0 ${selected ? "text-primary" : "text-on-surface-variant"}`} aria-hidden="true" />
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <aside className="min-w-0 xl:sticky xl:top-32 xl:self-start">
            {selectedWatchlist ? (
              <div className="overflow-hidden rounded-2xl border border-outline-variant/50 bg-surface-container">
                <div className="border-b border-outline-variant/40 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-primary">SÉLECTION</p>
                      <h2 className="mt-2 truncate font-headline text-lg font-bold text-on-surface">{selectedWatchlist.name}</h2>
                      <p className="mt-1 text-xs text-on-surface-variant">{selectedWatchlist.scope}</p>
                    </div>
                    <button
                      onClick={() => deactivateMutation.mutate(selectedWatchlist.id)}
                      disabled={deactivateMutation.isPending || !selectedWatchlist.is_active}
                      title="Désactiver cette surveillance"
                      className="flex h-9 w-9 items-center justify-center rounded-xl border border-outline-variant/45 text-on-surface-variant transition-colors hover:border-error/40 hover:bg-error/8 hover:text-error disabled:cursor-not-allowed disabled:opacity-35"
                      data-testid="btn-deactivate-watchlist"
                      type="button"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>

                <div className="p-5">
                  {metricsQuery.isLoading ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="h-24 animate-pulse rounded-xl bg-surface-container-high" />
                      <div className="h-24 animate-pulse rounded-xl bg-surface-container-high" />
                    </div>
                  ) : metricsQuery.isError || !metricsData ? (
                    <div className="rounded-xl border border-outline-variant/40 bg-surface-container-low p-4 text-xs leading-5 text-on-surface-variant">
                      Aucun calcul n’est encore disponible. La première collecte alimentera le score et les aspects.
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl bg-surface-container-low p-4">
                          <p className="text-[9px] font-bold uppercase tracking-wider text-on-surface-variant">Score NSS</p>
                          <div className="mt-2 flex items-baseline gap-2">
                            <span className="metric-number text-3xl font-extrabold text-on-surface">{metricsData.nss_score}</span>
                            <span className={metricsData.nss_delta >= 0 ? "text-success" : "text-error"}>
                              {metricsData.nss_delta >= 0 ? "+" : ""}{metricsData.nss_delta}
                            </span>
                          </div>
                        </div>
                        <div className="rounded-xl bg-surface-container-low p-4">
                          <p className="text-[9px] font-bold uppercase tracking-wider text-on-surface-variant">Mentions</p>
                          <div className="mt-2 flex items-baseline gap-2">
                            <span className="metric-number text-3xl font-extrabold text-on-surface">{formatCompactNumber(metricsData.volume)}</span>
                            <span className={metricsData.volume_delta >= 0 ? "text-success" : "text-error"}>
                              {metricsData.volume_delta >= 0 ? "+" : ""}{metricsData.volume_delta}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="mt-5">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-on-surface-variant">Répartition par Aspect</p>
                          <p className="truncate text-[9px] text-on-surface-variant/65">{formatTimestamp(metricsData.last_updated)}</p>
                        </div>
                        <div className="mt-3 space-y-3">
                          {(metricsData.aspects.length ? metricsData.aspects : [{ name: "Aucun aspect", score: 0 }]).slice(0, 4).map((aspect) => (
                            <div key={aspect.name}>
                              <div className="mb-1.5 flex justify-between text-[10px]">
                                <span className="truncate text-on-surface-variant">{aspect.name}</span>
                                <span className={aspect.is_negative ? "font-bold text-error" : "font-bold text-primary"}>{aspect.score}%</span>
                              </div>
                              <div className="h-1.5 overflow-hidden rounded-full bg-surface-container-highest">
                                <div
                                  className={`h-full rounded-full ${aspect.is_negative ? "bg-error" : "bg-primary"}`}
                                  style={{ width: `${aspect.score}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  <div className="mt-5 rounded-xl border border-tertiary/20 bg-tertiary/5 p-4">
                    <div className="flex items-center gap-2 text-tertiary">
                      <Sparkles className="h-4 w-4" aria-hidden="true" />
                      <p className="text-[9px] font-bold uppercase tracking-[0.16em]">{buildInsightsTitle(selectedWatchlist.name)}</p>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-on-surface-variant">
                      {metricsData?.quick_insight || "Les premiers enseignements apparaîtront après la collecte."}
                    </p>
                  </div>

                  <Button
                    variant="secondary"
                    className="mt-5 w-full justify-between"
                    onClick={() => setLocation(`/explorateur?watchlist=${selectedWatchlist.id}`)}
                  >
                    Voir les détails analytiques
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-outline-variant/55 p-6 text-center">
                <Radar className="mx-auto h-6 w-6 text-on-surface-variant" aria-hidden="true" />
                <p className="mt-3 text-xs text-on-surface-variant">Sélectionnez une surveillance pour lire sa situation.</p>
              </div>
            )}
          </aside>
        </div>
      </div>

      <Sheet open={showCreateForm} onOpenChange={setCreateOpen}>
        <SheetContent
          side="right"
          className="w-full overflow-y-auto border-outline-variant/55 bg-surface-container p-0 sm:max-w-[860px]"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Nouvelle surveillance</SheetTitle>
            <SheetDescription>Définissez le signal et les sources à surveiller.</SheetDescription>
          </SheetHeader>
          <WatchScopeForm
            presentation="drawer"
            isSubmitting={createMutation.isPending}
            onCancel={() => setCreateOpen(false)}
            onSubmit={(value) => createMutation.mutate(value)}
          />
        </SheetContent>
      </Sheet>
    </AppShell>
  );
}
