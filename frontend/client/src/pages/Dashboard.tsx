import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BellRing,
  CircleCheck,
  Compass,
  Lightbulb,
  MapPinned,
  MessageSquareText,
  Radio,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Link, useLocation } from "wouter";

import { AppShell } from "@/components/AppShell";
import { EmptyTenantState } from "@/components/EmptyTenantState";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import {
  mapDashboardActions,
  mapDashboardAlerts,
  mapDashboardSummary,
} from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";

interface DashboardSummaryView {
  score: number;
  trend: "up" | "down" | "flat";
  delta: number;
  summary: string;
  totalMentions: number;
  period: string;
  regionalDistribution: Array<{ wilaya: string; pct: number }>;
  productPerformance: Array<{ product: string; trendPct: number; relativeVolume: number }>;
}

interface DashboardAlertView {
  id: string;
  title: string;
  description: string;
  severity: string;
  timestamp: string;
}

interface DashboardActionView {
  id: string;
  title: string;
  description: string;
  priority: string;
  ctaLabel: string;
  targetPlatform: string;
  confidence: number;
  isAvailable: boolean;
}

function mapSummaryView(value: unknown): DashboardSummaryView {
  const summary = mapDashboardSummary(value);
  return {
    score: summary.health_score,
    trend: summary.health_trend,
    delta: summary.nss_progress_pts,
    summary: summary.summary_text,
    totalMentions: summary.total_mentions,
    period: summary.period,
    regionalDistribution: summary.regional_distribution.map((item) => ({
      wilaya: item.wilaya,
      pct: item.pct,
    })),
    productPerformance: summary.product_performance.map((item) => ({
      product: item.product,
      trendPct: item.trend_pct,
      relativeVolume: item.relative_volume,
    })),
  };
}

function mapAlertViews(value: unknown): DashboardAlertView[] {
  return mapDashboardAlerts(value).map((alert) => ({
    id: alert.alert_id,
    title: alert.title,
    description: alert.description,
    severity: alert.severity,
    timestamp: alert.created_at,
  }));
}

function mapActionViews(value: unknown): DashboardActionView[] {
  return mapDashboardActions(value).map((action) => {
    const sourceText = `${action.title} ${action.description || ""}`.toLocaleLowerCase("fr");
    const isAvailable = !sourceText.includes("erreur de parsing") && !sourceText.includes("parsing error");

    return {
      id: action.recommendation_id,
      title: isAvailable ? action.title : "Recommandation en attente de validation",
      description: isAvailable
        ? action.description || "Aucun détail disponible."
        : "Le moteur n’a pas produit de recommandation structurée. L’analyse doit être vérifiée avant toute action.",
      priority: action.priority,
      ctaLabel: isAvailable ? action.cta_label || "Voir l’action" : "Examiner l’analyse",
      targetPlatform: isAvailable ? action.target_platform || "Toutes" : "Contrôle requis",
      confidence: Math.round(Number(action.confidence_score ?? 0) * 100),
      isAvailable,
    };
  });
}

function situationTitle(summary: DashboardSummaryView, alertCount: number): string {
  if (alertCount > 0) {
    return `${alertCount} alerte${alertCount > 1 ? "s" : ""} critique${alertCount > 1 ? "s" : ""} à traiter aujourd’hui.`;
  }
  if (summary.trend === "down") return "La perception recule : cherchez le point de rupture.";
  if (summary.trend === "up") return "La perception progresse : identifiez ce qui fonctionne.";
  return "La situation reste stable, sans urgence détectée.";
}

function situationSummary(summary: DashboardSummaryView, alertCount: number): string {
  if (alertCount > 0) {
    const movement = summary.trend === "down"
      ? `recule de ${Math.abs(summary.delta)} points`
      : summary.trend === "up"
        ? `progresse de ${Math.abs(summary.delta)} points`
        : "reste stable";
    return `La perception globale ${movement}, mais ${alertCount} changement${alertCount > 1 ? "s" : ""} anormal${alertCount > 1 ? "aux" : ""} nécessite${alertCount > 1 ? "nt" : ""} une vérification.`;
  }
  return summary.summary;
}

function severityLabel(severity: string): string {
  if (severity === "critical") return "Critique";
  if (severity === "high") return "Haute";
  return "À analyser";
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

export default function Dashboard() {
  const [, navigate] = useLocation();
  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummaryView>({
    queryKey: ["/api/dashboard/summary"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/summary");
      return mapSummaryView(await res.json());
    },
  });

  const { data: alertsList, isLoading: alertsLoading } = useQuery<DashboardAlertView[]>({
    queryKey: ["/api/dashboard/alerts-critical"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/alerts-critical");
      return mapAlertViews(await res.json());
    },
  });

  const { data: actionsList, isLoading: actionsLoading } = useQuery<DashboardActionView[]>({
    queryKey: ["/api/dashboard/top-actions"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/top-actions");
      return mapActionViews(await res.json());
    },
  });

  const summaryView = summary ?? {
    score: 0,
    trend: "flat" as const,
    delta: 0,
    summary: "Les premiers signaux alimenteront bientôt le briefing.",
    totalMentions: 0,
    period: "sur la période chargée",
    regionalDistribution: [],
    productPerformance: [],
  };
  const currentAlerts = alertsList ?? [];
  const currentActions = actionsList ?? [];
  const shouldShowEmptyTenantState =
    !summaryLoading &&
    !alertsLoading &&
    !actionsLoading &&
    summaryView.totalMentions === 0 &&
    currentAlerts.length === 0 &&
    currentActions.length === 0;

  if (shouldShowEmptyTenantState) {
    return (
      <AppShell>
        <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
          <EmptyTenantState
            title="Votre centre de veille est prêt"
            description="Créez une première surveillance pour collecter les signaux, détecter les alertes et produire des recommandations vérifiables."
          />
        </div>
      </AppShell>
    );
  }

  const primaryAlert = currentAlerts[0] ?? null;
  const topAction = currentActions[0] ?? null;

  return (
    <AppShell>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-7 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <PageHeader
          eyebrow="Surveiller"
          tone="monitor"
          title="Situation du jour"
          description="Les changements clients, leur explication et l’action à valider."
        />

        <section
          className={`overflow-hidden rounded-2xl border bg-surface ${
            currentAlerts.length > 0 ? "border-error/25" : "border-outline-variant"
          }`}
          aria-labelledby="daily-brief-title"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant px-5 py-3 sm:px-7">
            <div className="flex items-center gap-2 text-xs font-semibold text-on-surface">
              <Radio className="h-3.5 w-3.5 text-success" aria-hidden="true" />
              Brief opérationnel actualisé
            </div>
            <span className="text-[10px] text-on-surface-variant">{summaryView.period}</span>
          </div>

          <div className="grid lg:grid-cols-[11rem_minmax(0,1fr)_18rem]">
            <div className={`hidden gap-4 p-5 lg:flex lg:flex-col lg:items-start lg:justify-between lg:border-r lg:border-outline-variant lg:p-7 ${currentAlerts.length > 0 ? "bg-error-container/55" : "bg-action-container/55"}`}>
              <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${currentAlerts.length > 0 ? "bg-error text-white" : "bg-action text-white"}`}>
                {currentAlerts.length > 0 ? <ShieldAlert className="h-5 w-5" aria-hidden="true" /> : <CircleCheck className="h-5 w-5" aria-hidden="true" />}
              </span>
              <div>
                <p className={`metric-number text-4xl font-extrabold ${currentAlerts.length > 0 ? "text-error" : "text-action"}`}>{currentAlerts.length}</p>
                <p className="mt-1 text-xs font-semibold leading-4 text-on-surface">
                  {currentAlerts.length === 1 ? "alerte prioritaire" : "alertes prioritaires"}
                </p>
              </div>
            </div>

            <div className="p-6 sm:p-8 lg:p-9">
              <h2 id="daily-brief-title" className="max-w-3xl font-headline text-[clamp(1.65rem,3vw,2.65rem)] font-extrabold leading-[1.08] tracking-[-0.04em] text-on-surface">
                {situationTitle(summaryView, currentAlerts.length)}
              </h2>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant">
                {situationSummary(summaryView, currentAlerts.length)}
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                {currentAlerts.length > 0 ? (
                  <Button className="gap-2 bg-error text-white hover:bg-error/90" onClick={() => navigate("/alertes")}>
                    <BellRing className="h-4 w-4" aria-hidden="true" />
                    Traiter les alertes
                  </Button>
                ) : (
                  <Button className="gap-2" onClick={() => navigate("/explorateur")}>
                    <Compass className="h-4 w-4" aria-hidden="true" />
                    Explorer les avis
                  </Button>
                )}
                <Button variant="outline" className="gap-2" onClick={() => navigate("/watchlists")}>
                  <span className="sm:hidden">Surveillances</span>
                  <span className="hidden sm:inline">Vérifier les surveillances</span>
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-3 border-t border-outline-variant bg-surface-container-low lg:grid-cols-1 lg:border-l lg:border-t-0">
              <div className="p-4 sm:p-5" data-testid="card-health-score">
                <p className="text-[10px] font-semibold text-on-surface-variant">Perception</p>
                {summaryLoading ? (
                  <div className="mt-3 h-9 animate-pulse rounded-lg bg-surface-container-high" />
                ) : (
                  <div className="mt-2 flex items-end gap-1.5">
                    <span className="metric-number text-3xl font-extrabold text-on-surface" data-testid="nss-score">{summaryView.score}</span>
                    <span className="pb-1 text-[10px] text-on-surface-variant">/100</span>
                  </div>
                )}
                <div className={`mt-2 flex items-center gap-1 text-[9px] font-bold ${summaryView.trend === "down" ? "text-error" : "text-success"}`}>
                  {summaryView.trend === "down" ? <TrendingDown className="h-3 w-3" /> : summaryView.trend === "up" ? <TrendingUp className="h-3 w-3" /> : null}
                  {summaryView.trend === "flat" ? "Stable" : `${summaryView.delta > 0 ? "+" : ""}${summaryView.delta} pts`}
                </div>
              </div>
              <div className="border-l border-outline-variant p-4 sm:p-5 lg:border-l-0 lg:border-t">
                <p className="text-[10px] font-semibold text-on-surface-variant">Avis analysés</p>
                <p className="metric-number mt-2 text-3xl font-extrabold text-on-surface">{formatCompactNumber(summaryView.totalMentions)}</p>
              </div>
              <div className="border-l border-outline-variant p-4 sm:p-5 lg:border-l-0 lg:border-t">
                <p className="text-[10px] font-semibold text-on-surface-variant">État du suivi</p>
                <p className={`mt-2 text-xs font-bold ${currentAlerts.length > 0 ? "text-error" : "text-action"}`}>
                  {currentAlerts.length > 0 ? "Action requise" : "Sous contrôle"}
                </p>
              </div>
            </div>
          </div>
        </section>

        <section aria-labelledby="decision-trace-title">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h2 id="decision-trace-title" className="font-headline text-xl font-bold tracking-tight text-on-surface">Du signal à la décision</h2>
              <p className="mt-1 text-xs leading-5 text-on-surface-variant">LIDAL Pulse relie le changement détecté, son interprétation et l’action à valider.</p>
            </div>
            <Link href="/explorateur" className="hidden items-center gap-1.5 text-xs font-semibold text-insight hover:underline sm:flex">
              Approfondir l’analyse <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="decision-flow overflow-hidden rounded-2xl border border-outline-variant bg-surface">
            <div className="grid lg:grid-cols-3">
              <article className="decision-flow-step decision-flow-step--risk relative min-w-0 border-b border-outline-variant p-6 lg:border-b-0 lg:border-r">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-error-container text-error">
                      <ShieldAlert className="h-4.5 w-4.5" aria-hidden="true" />
                    </span>
                    <div>
                      <p className="font-headline text-sm font-bold text-on-surface">1 · Signal détecté</p>
                      <p className="mt-0.5 text-[10px] text-on-surface-variant">Ce qui a changé</p>
                    </div>
                  </div>
                  {primaryAlert ? <span className="badge-urgent">{severityLabel(primaryAlert.severity)}</span> : null}
                </div>
                {alertsLoading ? (
                  <div className="mt-6 h-32 animate-pulse rounded-xl bg-surface-container-high" />
                ) : primaryAlert ? (
                  <div className="mt-6">
                    <h3 className="break-words font-headline text-lg font-bold leading-snug text-on-surface">{primaryAlert.title}</h3>
                    <p className="mt-3 line-clamp-3 text-xs leading-5 text-on-surface-variant">{primaryAlert.description}</p>
                    <div className="mt-5 flex items-center justify-between gap-3">
                      <span className="text-[10px] text-on-surface-variant">Détectée {formatTimestamp(primaryAlert.timestamp)}</span>
                      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => navigate("/alertes")}>
                        Voir les preuves <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-8 flex items-start gap-3">
                    <CircleCheck className="h-5 w-5 shrink-0 text-success" aria-hidden="true" />
                    <p className="text-xs leading-5 text-on-surface-variant">Aucun changement anormal ne demande de vérification immédiate.</p>
                  </div>
                )}
              </article>

              <article className="decision-flow-step decision-flow-step--insight relative min-w-0 border-b border-outline-variant p-6 lg:border-b-0 lg:border-r">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-insight-container text-insight">
                    <Compass className="h-4.5 w-4.5" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-headline text-sm font-bold text-on-surface">2 · Ce que cela signifie</p>
                    <p className="mt-0.5 text-[10px] text-on-surface-variant">Interprétation des avis</p>
                  </div>
                </div>
                <div className="mt-6">
                  <p className="text-sm font-semibold leading-6 text-on-surface">{situationSummary(summaryView, currentAlerts.length)}</p>
                  <dl className="mt-5 grid grid-cols-2 gap-3 border-y border-outline-variant py-4">
                    <div>
                      <dt className="text-[9px] text-on-surface-variant">Perception</dt>
                      <dd className="metric-number mt-1 text-xl font-extrabold text-on-surface">{summaryView.score}/100</dd>
                    </div>
                    <div>
                      <dt className="text-[9px] text-on-surface-variant">Évolution</dt>
                      <dd className={`metric-number mt-1 text-xl font-extrabold ${summaryView.trend === "down" ? "text-error" : "text-success"}`}>
                        {summaryView.trend === "flat" ? "Stable" : `${summaryView.delta > 0 ? "+" : ""}${summaryView.delta} pts`}
                      </dd>
                    </div>
                  </dl>
                  <Button variant="outline" size="sm" className="mt-5 gap-1.5" onClick={() => navigate("/explorateur")}>
                    Explorer les verbatims <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </article>

              <article className="decision-flow-step decision-flow-step--action relative min-w-0 p-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-action-container text-action">
                      <Lightbulb className="h-4.5 w-4.5" aria-hidden="true" />
                    </span>
                    <div>
                      <p className="font-headline text-sm font-bold text-on-surface">3 · Décision proposée</p>
                      <p className="mt-0.5 text-[10px] text-on-surface-variant">À vérifier avant d’agir</p>
                    </div>
                  </div>
                  {topAction ? (
                    <span className={`text-[10px] font-semibold ${topAction.isAvailable ? "text-action" : "text-error"}`}>
                      {topAction.isAvailable ? `${topAction.confidence}% confiance` : "Contrôle requis"}
                    </span>
                  ) : null}
                </div>
                {actionsLoading ? (
                  <div className="mt-6 h-32 animate-pulse rounded-xl bg-surface-container-high" />
                ) : topAction ? (
                  <div className="mt-6">
                    <span className="rounded-full border border-action/20 bg-action-container px-2.5 py-1 text-[9px] font-bold text-action">Canal · {topAction.targetPlatform}</span>
                    <h3 className="mt-4 break-words font-headline text-lg font-bold leading-snug text-on-surface">{topAction.title}</h3>
                    <p className="mt-3 line-clamp-3 text-xs leading-5 text-on-surface-variant">{topAction.description}</p>
                    <Button className="mt-5 w-full justify-between bg-action text-white hover:bg-action/90" onClick={() => navigate("/recommandations")}>
                      {topAction.ctaLabel}
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                ) : (
                  <p className="mt-8 text-xs leading-5 text-on-surface-variant">Une action apparaîtra lorsque les signaux seront suffisamment consolidés.</p>
                )}
              </article>
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="font-headline text-sm font-bold text-on-surface">File de traitement</h3>
                <p className="mt-0.5 text-[10px] text-on-surface-variant">Les alertes sont classées par niveau d’urgence.</p>
              </div>
              <Link href="/alertes" className="flex items-center gap-1.5 text-xs font-semibold text-error hover:underline">
                Tout afficher <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="overflow-hidden rounded-2xl border border-outline-variant bg-surface">
              {alertsLoading ? (
                <div className="space-y-px bg-outline-variant">
                  {[1, 2].map((item) => <div key={item} className="h-20 animate-pulse bg-surface-container-low" />)}
                </div>
              ) : currentAlerts.length === 0 ? (
                <div className="flex items-center gap-3 p-5">
                  <CircleCheck className="h-5 w-5 text-success" aria-hidden="true" />
                  <p className="text-xs text-on-surface-variant">La file est vide. La surveillance continue en arrière-plan.</p>
                </div>
              ) : (
                currentAlerts.slice(0, 3).map((alert, index) => (
                  <button
                    key={alert.id}
                    onClick={() => navigate("/alertes")}
                    className="group grid w-full gap-3 border-b border-outline-variant p-4 text-left transition-colors last:border-b-0 hover:bg-surface-container-low sm:grid-cols-[2rem_minmax(0,1fr)_8rem_1.5rem] sm:items-center sm:px-5"
                    data-testid={`alert-card-${alert.id}`}
                    type="button"
                  >
                    <span className="metric-number text-xs font-bold text-error">{String(index + 1).padStart(2, "0")}</span>
                    <span className="min-w-0">
                      <span className="block truncate font-headline text-sm font-bold text-on-surface">{alert.title}</span>
                      <span className="mt-1 block truncate text-[10px] text-on-surface-variant">{alert.description}</span>
                    </span>
                    <span className="text-[9px] font-bold uppercase tracking-wider text-error sm:text-right">
                      {severityLabel(alert.severity)} · {formatTimestamp(alert.timestamp)}
                    </span>
                    <ArrowRight className="hidden h-4 w-4 text-on-surface-variant transition-transform group-hover:translate-x-0.5 sm:block" aria-hidden="true" />
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)]">
          <div className="rounded-2xl border border-outline-variant bg-surface p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-insight-container text-insight"><MessageSquareText className="h-4 w-4" /></span>
              <div>
                <h2 className="font-headline text-sm font-bold text-on-surface">Produits à surveiller</h2>
                <p className="mt-0.5 text-[10px] text-on-surface-variant">Évolution de la perception pour chaque produit analysé.</p>
              </div>
            </div>
            <div className="mt-6 space-y-5">
              {summaryLoading ? (
                [1, 2, 3].map((item) => <div key={item} className="h-9 animate-pulse rounded-lg bg-surface-container-high" />)
              ) : summaryView.productPerformance.length === 0 ? (
                <p className="rounded-xl bg-surface-container p-5 text-xs text-on-surface-variant">Pas encore assez de données produit pour comparer les signaux.</p>
              ) : (
                summaryView.productPerformance.map((product) => (
                  <div key={product.product}>
                    <div className="mb-2 flex items-end justify-between gap-3">
                      <span className="truncate text-xs font-semibold text-on-surface">{product.product}</span>
                      <span className={`text-xs font-bold ${product.trendPct >= 0 ? "text-success" : "text-error"}`}>{product.trendPct >= 0 ? "+" : ""}{product.trendPct}%</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-container-highest">
                      <div className="h-full rounded-full bg-insight" style={{ width: `${product.relativeVolume}%` }} />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-outline-variant bg-surface p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-monitor-container text-monitor"><MapPinned className="h-4 w-4" /></span>
              <div>
                <h2 className="font-headline text-sm font-bold text-on-surface">Où les clients s’expriment</h2>
                <p className="mt-0.5 text-[10px] text-on-surface-variant">Part des avis analysés pour chaque wilaya.</p>
              </div>
            </div>
            <div className="mt-6 space-y-3">
              {summaryLoading ? (
                [1, 2, 3, 4].map((item) => <div key={item} className="h-8 animate-pulse rounded-lg bg-surface-container-high" />)
              ) : summaryView.regionalDistribution.length === 0 ? (
                <p className="rounded-xl bg-surface-container p-5 text-xs text-on-surface-variant">La localisation apparaîtra dès que les sources fourniront assez de contexte.</p>
              ) : (
                summaryView.regionalDistribution.map((region) => (
                  <div key={region.wilaya} className="grid grid-cols-[minmax(0,1fr)_6rem_2.5rem] items-center gap-3">
                    <span className="truncate text-xs font-semibold text-on-surface">{region.wilaya}</span>
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-container-highest"><div className="h-full rounded-full bg-monitor" style={{ width: `${region.pct}%` }} /></div>
                    <span className="text-right text-[10px] font-bold text-on-surface-variant">{region.pct}%</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <footer className="flex flex-col gap-3 border-t border-outline-variant pt-5 text-[10px] text-on-surface-variant sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5 font-semibold text-success">
              <Radio className="h-3.5 w-3.5" aria-hidden="true" />
              Collecte active
            </span>
            <span>Données analysées {summaryView.period}</span>
          </div>
          <Link href="/admin-sources" className="font-semibold text-monitor hover:underline">
            Vérifier les sources de données
          </Link>
        </footer>
      </div>
    </AppShell>
  );
}
