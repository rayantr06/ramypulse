import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
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
import { mapDashboardActions, mapDashboardAlerts, mapDashboardSummary } from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";
import { useTenantId } from "@/lib/tenantContext";
import { isDemoMode } from "@/lib/demoMode";

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

const DEMO_SUMMARY: DashboardSummaryView = {
  score: 72,
  trend: "up",
  delta: 5,
  summary: "La perception progresse, mais deux signaux négatifs demandent une vérification.",
  totalMentions: 200,
  period: "90 derniers jours",
  regionalDistribution: [
    { wilaya: "Alger", pct: 28 },
    { wilaya: "Oran", pct: 22 },
    { wilaya: "Constantine", pct: 20 },
    { wilaya: "Annaba", pct: 16 },
  ],
  productPerformance: [
    { product: "Yaourt Abricot 150 g", trendPct: 10, relativeVolume: 82 },
    { product: "Lait fermenté", trendPct: 4, relativeVolume: 61 },
    { product: "Fromage frais", trendPct: -3, relativeVolume: 44 },
  ],
};

const DEMO_ALERTS: DashboardAlertView[] = [
  {
    id: "demo-alert-1",
    title: "Volume de mentions négatives en hausse",
    description: "Hausse de 45 % des avis négatifs sur Google Maps, concentrée dans trois wilayas.",
    severity: "critical",
    timestamp: "2026-08-16T16:32:00Z",
  },
  {
    id: "demo-alert-2",
    title: "Baisse du score sur l’aspect goût",
    description: "Le score associé au goût recule de 12 points sur les commentaires récents.",
    severity: "high",
    timestamp: "2026-08-16T14:18:00Z",
  },
];

const DEMO_ACTIONS: DashboardActionView[] = [
  {
    id: "demo-action-1",
    title: "Vérifier les lots et points de vente concernés",
    description: "Comparer les verbatims récents par wilaya avant de lancer une action corrective ciblée.",
    priority: "high",
    ctaLabel: "Examiner la recommandation",
    targetPlatform: "Google Maps",
    confidence: 84,
    isAvailable: true,
  },
];

function mapSummaryView(value: unknown): DashboardSummaryView {
  const summary = mapDashboardSummary(value);
  return {
    score: summary.health_score,
    trend: summary.health_trend,
    delta: summary.nss_progress_pts,
    summary: summary.summary_text,
    totalMentions: summary.total_mentions,
    period: summary.period,
    regionalDistribution: summary.regional_distribution.map((item) => ({ wilaya: item.wilaya, pct: item.pct })),
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
  if (alertCount > 0) return `${alertCount} alerte${alertCount > 1 ? "s" : ""} à traiter aujourd’hui.`;
  if (summary.trend === "down") return "La perception recule : cherchez le point de rupture.";
  if (summary.trend === "up") return "La perception progresse : identifiez ce qui fonctionne.";
  return "La situation reste stable, sans urgence détectée.";
}

function situationSummary(summary: DashboardSummaryView, alertCount: number): string {
  if (alertCount === 0) return summary.summary;
  const movement = summary.trend === "down"
    ? `recule de ${Math.abs(summary.delta)} points`
    : summary.trend === "up"
      ? `progresse de ${Math.abs(summary.delta)} points`
      : "reste stable";
  return `La perception globale ${movement}. ${alertCount} ${alertCount > 1 ? "signaux demandent" : "signal demande"} une vérification.`;
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
  const tenantId = useTenantId();
  const demoMode = isDemoMode();
  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummaryView>({
    queryKey: ["/api/dashboard/summary", { tenantId }],
    queryFn: async () => demoMode
      ? DEMO_SUMMARY
      : mapSummaryView(await (await apiRequest("GET", "/api/dashboard/summary")).json()),
  });
  const { data: alertsList, isLoading: alertsLoading } = useQuery<DashboardAlertView[]>({
    queryKey: ["/api/dashboard/alerts-critical", { tenantId }],
    queryFn: async () => demoMode
      ? DEMO_ALERTS
      : mapAlertViews(await (await apiRequest("GET", "/api/dashboard/alerts-critical")).json()),
  });
  const { data: actionsList, isLoading: actionsLoading } = useQuery<DashboardActionView[]>({
    queryKey: ["/api/dashboard/top-actions", { tenantId }],
    queryFn: async () => demoMode
      ? DEMO_ACTIONS
      : mapActionViews(await (await apiRequest("GET", "/api/dashboard/top-actions")).json()),
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
  const shouldShowEmptyTenantState = !summaryLoading && !alertsLoading && !actionsLoading
    && summaryView.totalMentions === 0 && currentAlerts.length === 0 && currentActions.length === 0;

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
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-7 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-8">
        <PageHeader
          eyebrow="Surveiller"
          tone="monitor"
          title="Situation du jour"
          description="Un parcours lisible du signal jusqu’à la décision, avec les preuves à portée de main."
          descriptionClassName="hidden sm:block"
        />

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Indicateurs de la situation">
          <article className="dashboard-stat" data-testid="card-health-score">
            <div className="dashboard-stat__icon bg-primary-container text-primary"><Radio className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Perception</p><p className="dashboard-stat__value" data-testid="nss-score">{summaryView.score}<span>/100</span></p></div>
          </article>
          <article className="dashboard-stat">
            <div className={`dashboard-stat__icon ${summaryView.trend === "down" ? "bg-error-container text-error" : "bg-action-container text-action"}`}>
              {summaryView.trend === "down" ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
            </div>
            <div><p className="dashboard-stat__label">Évolution</p><p className={`dashboard-stat__value ${summaryView.trend === "down" ? "text-error" : "text-action"}`}>{summaryView.trend === "flat" ? "Stable" : `${summaryView.delta > 0 ? "+" : ""}${summaryView.delta}`}<span>{summaryView.trend === "flat" ? "" : " pts"}</span></p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-insight-container text-insight"><MessageSquareText className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Avis analysés</p><p className="dashboard-stat__value">{formatCompactNumber(summaryView.totalMentions)}</p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-error-container text-error"><ShieldAlert className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Alertes à traiter</p><p className="dashboard-stat__value">{currentAlerts.length}<span> ouvertes</span></p></div>
          </article>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(19rem,0.75fr)]">
          <div className="cling-panel overflow-hidden">
            <div className="flex items-start justify-between gap-4 border-b border-outline-variant px-5 py-4 sm:px-6">
              <div>
                <h2 className="font-headline text-base font-bold text-on-surface">Alertes prioritaires</h2>
                <p className="mt-1 text-[10px] text-on-surface-variant">File de traitement des signaux qui nécessitent une vérification aujourd’hui.</p>
              </div>
              <Link href="/alertes" className="flex shrink-0 items-center gap-1 text-xs font-semibold text-primary hover:underline">Tout afficher <ArrowRight className="h-3.5 w-3.5" /></Link>
            </div>
            {alertsLoading ? (
              <div className="space-y-px bg-outline-variant">{[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse bg-surface" />)}</div>
            ) : currentAlerts.length === 0 ? (
              <div className="flex items-center gap-3 p-6"><CircleCheck className="h-5 w-5 text-success" /><p className="text-xs text-on-surface-variant">Aucune alerte prioritaire. La surveillance continue.</p></div>
            ) : currentAlerts.slice(0, 4).map((alert) => (
              <button key={alert.id} onClick={() => navigate("/alertes")} className="dashboard-alert-row group" data-testid={`alert-card-${alert.id}`} type="button">
                <span className="dashboard-alert-row__severity"><ShieldAlert className="h-4 w-4" /></span>
                <span className="min-w-0 flex-1">
                  <span className="line-clamp-2 text-sm font-semibold leading-5 text-on-surface sm:line-clamp-1">{alert.title}</span>
                  <span className="mt-1 line-clamp-1 text-[10px] text-on-surface-variant">{alert.description}</span>
                  <span className="mt-1.5 flex items-center gap-2 text-[9px] sm:hidden"><strong className="font-semibold text-error">{severityLabel(alert.severity)}</strong><span className="text-on-surface-variant">{formatTimestamp(alert.timestamp)}</span></span>
                </span>
                <span className="hidden text-right text-[9px] font-semibold text-on-surface-variant sm:block"><strong className="block text-error">{severityLabel(alert.severity)}</strong>{formatTimestamp(alert.timestamp)}</span>
                <ArrowRight className="h-4 w-4 shrink-0 text-on-surface-variant transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>

          <aside className="cling-panel p-5 sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-insight-container text-insight"><Compass className="h-4 w-4" /></span><h2 className="font-headline text-base font-bold text-on-surface">Analyse du jour</h2></div>
              <span className="rounded-full bg-surface-container px-2.5 py-1 text-[9px] font-semibold text-on-surface-variant">{summaryView.period}</span>
            </div>
            <h3 className="mt-5 font-headline text-base font-bold leading-snug text-on-surface">{situationSummary(summaryView, currentAlerts.length)}</h3>
            <div className="mt-4 rounded-xl bg-surface-container-low p-3.5">
              <p className="text-[9px] font-semibold text-on-surface-variant">Signal le mieux étayé</p>
              <p className="mt-1.5 line-clamp-3 text-xs leading-5 text-on-surface">{primaryAlert?.description ?? summaryView.summary}</p>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-outline-variant pt-4"><span className="text-[9px] text-on-surface-variant">Confiance à confirmer · {formatCompactNumber(summaryView.totalMentions)} avis</span><Button variant="outline" size="sm" className="gap-1.5" onClick={() => navigate("/explorateur")}>Voir les preuves <ArrowRight className="h-3.5 w-3.5" /></Button></div>
          </aside>
        </section>

        <section className="cling-panel p-5 sm:p-6" aria-labelledby="decision-trace-title">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><h2 id="decision-trace-title" className="font-headline text-base font-bold text-on-surface">Du signal à la décision</h2><p className="mt-1 text-[10px] text-on-surface-variant">Une synthèse compacte avant validation humaine.</p></div>
            <span className={`rounded-full px-2.5 py-1 text-[9px] font-semibold ${topAction?.isAvailable ? "bg-action-container text-action" : "bg-error-container text-error"}`}>{topAction?.isAvailable ? `${topAction.confidence}% confiance` : "Contrôle requis"}</span>
          </div>
          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.15fr)_minmax(0,1fr)]">
            <article className="decision-summary-step"><span className="decision-summary-step__icon bg-error-container text-error"><ShieldAlert className="h-4 w-4" /></span><div className="min-w-0"><p className="decision-summary-step__label">1 · Signal détecté</p><p className="mt-1 truncate text-sm font-semibold text-on-surface">{primaryAlert?.title ?? "Aucun signal critique"}</p><button type="button" onClick={() => navigate("/alertes")} className="mt-2 text-[10px] font-semibold text-primary hover:underline">Voir les preuves</button></div></article>
            <article className="decision-summary-step"><span className="decision-summary-step__icon bg-insight-container text-insight"><Compass className="h-4 w-4" /></span><div><p className="decision-summary-step__label">2 · Ce que cela signifie</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-on-surface-variant">{situationSummary(summaryView, currentAlerts.length)}</p></div></article>
            <article className="decision-summary-step"><span className="decision-summary-step__icon bg-action-container text-action"><Lightbulb className="h-4 w-4" /></span><div className="min-w-0 flex-1"><p className="decision-summary-step__label">3 · Décision proposée</p><p className="mt-1 line-clamp-1 text-sm font-semibold text-on-surface">{topAction?.title ?? "Consolider les signaux"}</p><Button size="sm" className="mt-2 w-full justify-between bg-action text-white hover:bg-action/90" onClick={() => navigate("/recommandations")}>{topAction?.ctaLabel ?? "Voir la recommandation"}<ArrowRight className="h-3.5 w-3.5" /></Button></div></article>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)]">
          <div className="cling-panel p-5 sm:p-6">
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-insight-container text-insight"><MessageSquareText className="h-4 w-4" /></span><div><h2 className="font-headline text-sm font-bold text-on-surface">Produits à surveiller</h2><p className="mt-0.5 text-[10px] text-on-surface-variant">Évolution de la perception par produit.</p></div></div>
            <div className="mt-6 space-y-5">
              {summaryLoading ? [1, 2, 3].map((item) => <div key={item} className="h-9 animate-pulse rounded-lg bg-surface-container-high" />) : summaryView.productPerformance.length === 0 ? (
                <p className="rounded-xl bg-surface-container p-5 text-xs text-on-surface-variant">Pas encore assez de données produit pour comparer les signaux.</p>
              ) : summaryView.productPerformance.map((product) => (
                <div key={product.product}><div className="mb-2 flex items-end justify-between gap-3"><span className="truncate text-xs font-semibold text-on-surface">{product.product}</span><span className={`text-xs font-bold ${product.trendPct >= 0 ? "text-success" : "text-error"}`}>{product.trendPct >= 0 ? "+" : ""}{product.trendPct}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-surface-container-highest"><div className="h-full rounded-full bg-insight" style={{ width: `${product.relativeVolume}%` }} /></div></div>
              ))}
            </div>
          </div>
          <div className="cling-panel p-5 sm:p-6">
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-monitor-container text-monitor"><MapPinned className="h-4 w-4" /></span><div><h2 className="font-headline text-sm font-bold text-on-surface">Où les clients s’expriment</h2><p className="mt-0.5 text-[10px] text-on-surface-variant">Part des avis analysés par wilaya.</p></div></div>
            <div className="mt-6 space-y-3">
              {summaryLoading ? [1, 2, 3, 4].map((item) => <div key={item} className="h-8 animate-pulse rounded-lg bg-surface-container-high" />) : summaryView.regionalDistribution.length === 0 ? (
                <p className="rounded-xl bg-surface-container p-5 text-xs text-on-surface-variant">La localisation apparaîtra dès que les sources fourniront assez de contexte.</p>
              ) : summaryView.regionalDistribution.map((region) => (
                <div key={region.wilaya} className="grid grid-cols-[minmax(0,1fr)_6rem_2.5rem] items-center gap-3"><span className="truncate text-xs font-semibold text-on-surface">{region.wilaya}</span><div className="h-1.5 overflow-hidden rounded-full bg-surface-container-highest"><div className="h-full rounded-full bg-monitor" style={{ width: `${region.pct}%` }} /></div><span className="text-right text-[10px] font-bold text-on-surface-variant">{region.pct}%</span></div>
              ))}
            </div>
          </div>
        </section>

        <footer className="flex flex-col gap-3 border-t border-outline-variant pt-5 text-[10px] text-on-surface-variant sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-4"><span className="flex items-center gap-1.5 font-semibold text-success"><Radio className="h-3.5 w-3.5" />Collecte active</span><span>Données analysées {summaryView.period}</span></div>
          <Link href="/admin-sources" className="font-semibold text-monitor hover:underline">Vérifier les sources de données</Link>
        </footer>
      </div>
    </AppShell>
  );
}
