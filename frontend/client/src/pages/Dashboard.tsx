import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { AppShell } from "@/components/AppShell";
import { EmptyTenantState } from "@/components/EmptyTenantState";
import { apiRequest } from "@/lib/queryClient";
import {
  mapApiStatus,
  mapDashboardActions,
  mapDashboardAlerts,
  mapDashboardSummary,
} from "@/lib/apiMappings";

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
  icon: string;
}

interface DashboardActionView {
  id: string;
  title: string;
  description: string;
  priority: string;
  icon: string;
  ctaLabel: string;
  targetPlatform: string;
  confidence: number;
}

interface ApiStatusView {
  apiStatus: string;
  latencyMs: number | null;
}

function severityLabel(severity: string): string {
  if (severity === "critical") return "Urgent";
  if (severity === "high") return "Haute";
  return "Analyse";
}

function severityIcon(severity: string): string {
  if (severity === "critical") return "warning";
  if (severity === "high") return "error";
  return "monitoring";
}

function severityIconBg(severity: string): string {
  if (severity === "critical") return "bg-error/10 text-error";
  if (severity === "high") return "bg-primary/10 text-primary";
  return "bg-surface-container-highest text-gray-400";
}

function priorityIcon(priority: string, fallback?: string): string {
  if (fallback) return fallback;
  if (priority === "high") return "rocket_launch";
  if (priority === "medium") return "auto_awesome";
  return "pending_actions";
}

function priorityColor(priority: string): string {
  if (priority === "high") return "bg-primary/10 text-primary";
  if (priority === "medium") return "bg-tertiary/10 text-tertiary";
  return "bg-on-surface-variant/10 text-on-surface-variant";
}

function trendCopy(summary: DashboardSummaryView): string {
  if (summary.trend === "up") return `Sentiment global en hausse (+${summary.delta} pts)`;
  if (summary.trend === "down") return `Sentiment global en baisse (${summary.delta} pts)`;
  return "Sentiment global stable";
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
    icon: severityIcon(alert.severity),
  }));
}

function mapActionViews(value: unknown): DashboardActionView[] {
  return mapDashboardActions(value).map((action) => ({
    id: action.recommendation_id,
    title: action.title,
    description: action.description || "Aucune description détaillée disponible.",
    priority: action.priority,
    icon: priorityIcon(action.priority, action.icon),
    ctaLabel: action.cta_label || "VOIR DETAILS",
    targetPlatform: action.target_platform || "Toutes",
    confidence: Math.round(Number(action.confidence_score ?? 0) * 100),
  }));
}

function SeverityBadge({ severity }: { severity: string }) {
  const label = severityLabel(severity);
  const className =
    severity === "critical"
      ? "text-[10px] font-bold text-error uppercase"
      : severity === "high"
        ? "text-[10px] font-bold text-primary uppercase"
        : "text-[10px] font-bold text-gray-500 uppercase";
  return <span className={className}>{label}</span>;
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

  const { data: apiStatus } = useQuery<ApiStatusView>({
    queryKey: ["/api/status"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/status");
      const status = mapApiStatus(await res.json());
      return {
        apiStatus: status.api_status,
        latencyMs: status.latency_ms,
      };
    },
  });

  const summaryView = summary ?? {
    score: 0,
    trend: "flat" as const,
    delta: 0,
    summary: "Pas de données suffisantes pour établir un diagnostic.",
    totalMentions: 0,
    period: "sur la période chargée",
    regionalDistribution: [],
    productPerformance: [],
  };
  const currentAlerts = alertsList ?? [];
  const currentActions = actionsList ?? [];
  const statusView = apiStatus ?? {
    apiStatus: "Indisponible",
    latencyMs: null,
  };

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
        <div className="p-8">
          <EmptyTenantState
            title="Le dashboard attend les premiers signaux"
            description="La collecte watch-first est lancée, mais il faut encore quelques documents normalisés pour calculer la santé de marque, les alertes et les recommandations."
          />
        </div>
      </AppShell>
    );
  }

  const circumference = 2 * Math.PI * 88;
  const dashOffset = circumference * (1 - summaryView.score / 100);

  return (
    <AppShell>
      <div className="p-8 space-y-8">
        <div className="flex items-end justify-between">
          <div>
            <span className="text-[10px] font-bold text-primary uppercase tracking-widest block mb-1">
              Vue d'ensemble
            </span>
            <h2 className="text-3xl font-extrabold tracking-tight font-headline">
              Tableau de bord
            </h2>
          </div>
          <div className="flex gap-2">
            <div className="bg-surface-container px-3 py-1.5 rounded text-[11px] font-semibold text-on-surface-variant flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
              Direct Temps Réel
            </div>
            <div className="bg-surface-container px-3 py-1.5 rounded text-[11px] font-semibold text-on-surface-variant">
              Algérie (Toutes régions)
            </div>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div
            className="col-span-12 lg:col-span-4 bg-surface-container p-6 rounded-xl flex flex-col items-center justify-center relative overflow-hidden group"
            data-testid="card-health-score"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-50"></div>
            <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest absolute top-6 left-6">
              SANTÉ DE LA MARQUE
            </span>
            {summaryLoading ? (
              <div className="w-48 h-48 rounded-full bg-surface-container-high animate-pulse mt-4"></div>
            ) : (
              <div className="relative w-48 h-48 flex items-center justify-center mt-4">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 192 192">
                  <circle
                    className="text-surface-container-highest"
                    cx="96"
                    cy="96"
                    fill="transparent"
                    r="88"
                    stroke="currentColor"
                    strokeWidth="8"
                  />
                  <circle
                    className="text-primary"
                    cx="96"
                    cy="96"
                    fill="transparent"
                    r="88"
                    stroke="currentColor"
                    strokeDasharray={circumference}
                    strokeDashoffset={dashOffset}
                    strokeWidth="8"
                    strokeLinecap="round"
                    style={{ transition: "stroke-dashoffset 1s ease" }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span
                    className="text-5xl font-black tracking-tighter text-on-surface"
                    data-testid="nss-score"
                  >
                    {summaryView.score}
                  </span>
                  <span className="text-xs font-bold text-on-surface-variant">/ 100</span>
                </div>
              </div>
            )}
            <div className="mt-6 text-center">
              <p className="text-sm font-semibold text-tertiary flex items-center gap-1 justify-center">
                <span className="material-symbols-outlined text-sm">
                  {summaryView.trend === "up"
                    ? "trending_up"
                    : summaryView.trend === "down"
                      ? "trending_down"
                      : "trending_flat"}
                </span>
                {trendCopy(summaryView)}
              </p>
              <p className="text-[11px] text-gray-500 mt-1 italic">
                Base sur {summaryView.totalMentions.toLocaleString("fr-FR")} mentions {summaryView.period}
              </p>
              <p className="text-[11px] text-gray-500 mt-2 italic">{summaryView.summary}</p>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-8 bg-surface-container p-6 rounded-xl flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">
                ALERTES CRITIQUES
              </span>
              <span className="px-2 py-0.5 bg-error-container text-error text-[10px] font-bold rounded">
                {currentAlerts.length} NOUVELLES
              </span>
            </div>
            {alertsLoading ? (
              <div className="space-y-2 flex-1">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-16 bg-surface-container-low rounded-sm animate-pulse"
                  ></div>
                ))}
              </div>
            ) : currentAlerts.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-sm text-on-surface-variant bg-surface-container-low rounded-sm">
                Aucune alerte critique active.
              </div>
            ) : (
              <div className="space-y-2 flex-1">
                {currentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    onClick={() => navigate("/alertes")}
                    className="flex items-center gap-4 p-4 bg-surface-container-low hover:bg-surface-container-high transition-colors duration-200 group cursor-pointer rounded-sm"
                    data-testid={`alert-card-${alert.id}`}
                  >
                    <div
                      className={`w-10 h-10 rounded-sm flex items-center justify-center ${severityIconBg(alert.severity)}`}
                    >
                      <span className="material-symbols-outlined">{alert.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-on-surface truncate">
                        {alert.title}
                      </h4>
                      <p className="text-xs text-gray-500 line-clamp-1">{alert.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <SeverityBadge severity={alert.severity} />
                      <p className="text-[10px] text-gray-600 mt-1">{alert.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">
              ACTIONS RECOMMANDÉES PAR L'IA
            </span>
            <div className="h-px flex-1 bg-outline-variant/10"></div>
          </div>
          {actionsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-48 bg-surface-container-low rounded-sm animate-pulse"
                ></div>
              ))}
            </div>
          ) : currentActions.length === 0 ? (
            <div className="bg-surface-container-low border border-outline-variant/10 p-6 rounded-sm text-sm text-on-surface-variant">
              Aucune recommandation active disponible.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {currentActions.map((action) => (
                <div
                  key={action.id}
                  className="bg-surface-container-low border border-outline-variant/10 p-6 hover:bg-surface-container-high transition-all duration-300 group cursor-pointer rounded-sm"
                  data-testid={`action-card-${action.id}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-2 rounded-sm ${priorityColor(action.priority)}`}>
                      <span className="material-symbols-outlined text-2xl">{action.icon}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-tertiary uppercase">
                        CONFIANCE
                      </span>
                      <p className="text-xl font-black text-on-surface tracking-tighter">
                        {action.confidence}%
                      </p>
                    </div>
                  </div>
                  <h4 className="text-base font-bold text-on-surface mb-3 font-headline">
                    {action.title}
                  </h4>
                  <p className="text-sm text-gray-500 mb-8 leading-relaxed flex-1">
                    {action.description}
                  </p>
                  <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                    {action.targetPlatform}
                  </p>
                  <button
                    className="w-full py-2.5 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed text-[11px] font-bold rounded-sm group-hover:scale-[1.02] transition-transform uppercase tracking-wider"
                    onClick={() => navigate("/recommandations")}
                    type="button"
                  >
                    {action.ctaLabel}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-7 bg-surface-container p-6 rounded-xl">
            <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest block mb-6">
              VENTES PAR PRODUIT (7 JOURS)
            </span>
            {summaryLoading ? (
              <div className="space-y-5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-8 bg-surface-container-high rounded animate-pulse"></div>
                ))}
              </div>
            ) : summaryView.productPerformance.length === 0 ? (
              <div className="bg-surface-container-low rounded-sm p-6 text-sm text-on-surface-variant leading-relaxed">
                Pas encore assez de données produit pour alimenter cette vue.
              </div>
            ) : (
              <div className="space-y-5">
                {summaryView.productPerformance.map((product, index) => (
                  <div key={product.product} className="relative">
                    <div className="flex justify-between items-end mb-2">
                      <span className="text-sm font-bold">{product.product}</span>
                      <span
                        className={`text-xs font-bold ${
                          product.trendPct >= 0 ? "text-tertiary" : "text-error"
                        }`}
                      >
                        {product.trendPct >= 0 ? "+" : ""}
                        {product.trendPct}%
                      </span>
                    </div>
                    <div className="h-2 bg-surface-container-highest w-full rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-700"
                        style={{
                          width: `${product.relativeVolume}%`,
                          opacity: 1 - index * 0.2,
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="col-span-12 lg:col-span-5 bg-surface-container p-6 rounded-xl flex flex-col">
            <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest block mb-4">
              DISTRIBUTION RÉGIONALE
            </span>
            <div className="flex-1 bg-surface-container-low rounded-sm relative overflow-hidden p-4">
              {summaryLoading ? (
                <div className="relative space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-4 bg-surface-container-high rounded animate-pulse"></div>
                  ))}
                </div>
              ) : summaryView.regionalDistribution.length === 0 ? (
                <div className="h-full flex items-center justify-center text-center text-sm text-on-surface-variant max-w-xs mx-auto leading-relaxed">
                  Pas encore assez de données régionales pour alimenter cette vue.
                </div>
              ) : (
                <div className="relative space-y-3">
                  {summaryView.regionalDistribution.map((region) => (
                    <div key={region.wilaya} className="flex items-center justify-between text-[11px]">
                      <span className="font-bold text-on-surface">{region.wilaya}</span>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-1 bg-primary rounded-full"
                          style={{ width: `${region.pct * 1.2}px` }}
                        ></div>
                        <span className="text-gray-400 w-8 text-right">{region.pct}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <footer className="pt-2 flex justify-between items-center text-[10px] text-gray-600 font-bold uppercase tracking-widest">
          <div className="flex gap-4">
            <span>{`API Status: ${statusView.apiStatus}`}</span>
            <span>
              {statusView.latencyMs == null
                ? "Latency: n/a"
                : `Latency: ${statusView.latencyMs}ms`}
            </span>
          </div>
          <div>© 2024 RamyPulse Intelligence Unit</div>
        </footer>
      </div>
    </AppShell>
  );
}
