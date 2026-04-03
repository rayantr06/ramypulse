import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { DashboardSummary, DashboardAlert, DashboardAction } from "@shared/schema";

// Mock data fallbacks for when API is unavailable
const MOCK_SUMMARY: DashboardSummary = {
  nss_score: 82,
  nss_trend: 4,
  total_mentions: 12400,
  period: "ce mois",
  regional_distribution: [
    { wilaya: "Alger", pct: 42 },
    { wilaya: "Oran", pct: 28 },
    { wilaya: "Constantine", pct: 15 },
    { wilaya: "Béjaïa", pct: 9 },
    { wilaya: "Autres", pct: 6 },
  ],
  product_performance: [
    { product: "Ramy Citron", trend_pct: 12.4, relative_volume: 78 },
    { product: "Ramy Orange", trend_pct: -2.1, relative_volume: 65 },
    { product: "Ramy Fraise", trend_pct: 8.7, relative_volume: 42 },
  ],
};

const MOCK_ALERTS: DashboardAlert[] = [
  {
    id: "1",
    title: "Sentiment Négatif: Ramy Citron à Oran",
    description: "Incompatibilité détectée entre la campagne actuelle et le sentiment régional.",
    severity: "URGENT",
    timestamp: "Il y a 14 min",
    icon: "sentiment_very_dissatisfied",
  },
  {
    id: "2",
    title: "Spike de mentions: YouTube",
    description: "Volume de contenu généré par les utilisateurs au-dessus de la normale (+45%).",
    severity: "ANALYSE",
    timestamp: "Il y a 2h",
    icon: "monitoring",
  },
  {
    id: "3",
    title: "Erreur de synchro: Google Maps",
    description: "Flux de données de points de vente interrompu pour la région Est.",
    severity: "SYSTÈME",
    timestamp: "Hier, 23:15",
    icon: "sync_problem",
  },
];

const MOCK_ACTIONS: DashboardAction[] = [
  {
    id: "1",
    title: "Répondre aux commentaires à Alger",
    description: "Forte concentration de demandes non résolues concernant la disponibilité de Ramy Fraise à Alger-Centre.",
    confidence: 92,
    icon: "forum",
    cta_label: "EXÉCUTER L'ACTION",
  },
  {
    id: "2",
    title: "Lancer une campagne à Béjaïa",
    description: "Tendance estivale en hausse. Opportunité de dominer la part de voix sur le segment boisson fraîche.",
    confidence: 88,
    icon: "rocket_launch",
    cta_label: "GÉNÉRER LE BRIEF",
  },
  {
    id: "3",
    title: "Ajuster le stock: Ramy Orange",
    description: "Prédiction de rupture de stock à Tlemcen d'ici 48h basée sur les tendances de consommation locales.",
    confidence: 75,
    icon: "inventory_2",
    cta_label: "COMMANDER STOCK",
  },
];

function SeverityBadge({ severity }: { severity: string }) {
  if (severity === "URGENT") {
    return <span className="text-[10px] font-bold text-error uppercase">Urgent</span>;
  }
  if (severity === "ANALYSE") {
    return <span className="text-[10px] font-bold text-tertiary uppercase">Analyse</span>;
  }
  return <span className="text-[10px] font-bold text-gray-500 uppercase">Système</span>;
}

function SeverityIconBg({ severity }: { severity: string }) {
  if (severity === "URGENT") return "bg-error/10 text-error";
  if (severity === "ANALYSE") return "bg-primary/10 text-primary";
  return "bg-surface-container-highest text-gray-400";
}

// Map API response fields to component schema
function mapSummaryFromApi(apiData: Record<string, unknown>): DashboardSummary {
  return {
    nss_score: (apiData.health_score as number) ?? (apiData.nss_score as number) ?? MOCK_SUMMARY.nss_score,
    nss_trend: (apiData.nss_progress_pts as number) ?? (apiData.nss_trend as number) ?? MOCK_SUMMARY.nss_trend,
    total_mentions: (apiData.total_mentions as number) ?? MOCK_SUMMARY.total_mentions,
    period: (apiData.period as string) ?? MOCK_SUMMARY.period,
    regional_distribution: (apiData.regional_distribution as DashboardSummary["regional_distribution"]) ?? MOCK_SUMMARY.regional_distribution,
    product_performance: (apiData.product_performance as DashboardSummary["product_performance"]) ?? MOCK_SUMMARY.product_performance,
  };
}

function mapAlertsFromApi(apiData: Record<string, unknown>): DashboardAlert[] {
  // API returns { critical_alerts: [...] }
  const rawAlerts = (apiData.critical_alerts as Array<Record<string, unknown>>) ?? [];
  if (!rawAlerts.length) return MOCK_ALERTS;
  return rawAlerts.map((a) => ({
    id: String(a.alert_id ?? a.id ?? ""),
    title: String(a.title ?? ""),
    description: String(a.description ?? ""),
    severity: (a.severity as DashboardAlert["severity"]) ?? "SYSTÈME",
    timestamp: String(a.created_at ?? a.timestamp ?? ""),
    icon: String(a.icon ?? "warning"),
  }));
}

function mapActionsFromApi(apiData: Record<string, unknown>): DashboardAction[] {
  // API returns { top_actions: [...] }
  const rawActions = (apiData.top_actions as Array<Record<string, unknown>>) ?? [];
  if (!rawActions.length) return MOCK_ACTIONS;
  return rawActions.map((a) => ({
    id: String(a.recommendation_id ?? a.id ?? ""),
    title: String(a.title ?? ""),
    description: String(a.description ?? a.rationale ?? ""),
    confidence: Number(a.priority ?? a.confidence ?? 80),
    icon: String(a.icon ?? "auto_awesome"),
    cta_label: String(a.cta_label ?? "EXÉCUTER L'ACTION"),
  }));
}

export default function Dashboard() {
  const { data: summaryRaw, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ["/api/dashboard/summary"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/dashboard/summary");
        const apiData = await res.json();
        return mapSummaryFromApi(apiData);
      } catch {
        return MOCK_SUMMARY;
      }
    },
  });

  const { data: alertsRaw, isLoading: alertsLoading } = useQuery<DashboardAlert[]>({
    queryKey: ["/api/dashboard/alerts-critical"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/dashboard/alerts-critical");
        const apiData = await res.json();
        return mapAlertsFromApi(apiData);
      } catch {
        return MOCK_ALERTS;
      }
    },
  });

  const { data: actionsRaw, isLoading: actionsLoading } = useQuery<DashboardAction[]>({
    queryKey: ["/api/dashboard/top-actions"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/dashboard/top-actions");
        const apiData = await res.json();
        return mapActionsFromApi(apiData);
      } catch {
        return MOCK_ACTIONS;
      }
    },
  });

  const data = summaryRaw ?? MOCK_SUMMARY;
  const alertsList = alertsRaw ?? MOCK_ALERTS;
  const actionsList = actionsRaw ?? MOCK_ACTIONS;

  // Gauge math: full circumference for r=88 ≈ 552.9
  const circumference = 2 * Math.PI * 88;
  const dashOffset = circumference * (1 - data.nss_score / 100);

  return (
    <AppShell>
      <div className="p-8 space-y-8">
        {/* Page header */}
        <div className="flex items-end justify-between">
          <div>
            <span className="text-[10px] font-bold text-primary uppercase tracking-widest block mb-1">
              Vue d'ensemble
            </span>
            <h2 className="text-3xl font-extrabold tracking-tight font-headline">Tableau de bord</h2>
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

        {/* Bento Grid 1: Health Score + Critical Alerts */}
        <div className="grid grid-cols-12 gap-6">
          {/* Brand Health Score Gauge */}
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
                  <span className="text-5xl font-black tracking-tighter text-on-surface" data-testid="nss-score">
                    {data.nss_score}
                  </span>
                  <span className="text-xs font-bold text-on-surface-variant">/ 100</span>
                </div>
              </div>
            )}
            <div className="mt-6 text-center">
              <p className="text-sm font-semibold text-tertiary flex items-center gap-1 justify-center">
                <span className="material-symbols-outlined text-sm">trending_up</span>
                Sentiment global en hausse (+{data.nss_trend}%)
              </p>
              <p className="text-[11px] text-gray-500 mt-1 italic">
                Basé sur {(data.total_mentions / 1000).toFixed(1)}k mentions {data.period}
              </p>
            </div>
          </div>

          {/* Critical Alerts */}
          <div className="col-span-12 lg:col-span-8 bg-surface-container p-6 rounded-xl flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">
                ALERTES CRITIQUES
              </span>
              <span className="px-2 py-0.5 bg-error-container text-error text-[10px] font-bold rounded">
                {alertsList.length} NOUVELLES
              </span>
            </div>
            {alertsLoading ? (
              <div className="space-y-2 flex-1">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-surface-container-low rounded-sm animate-pulse"></div>
                ))}
              </div>
            ) : (
              <div className="space-y-2 flex-1">
                {alertsList.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center gap-4 p-4 bg-surface-container-low hover:bg-surface-container-high transition-colors duration-200 group cursor-pointer rounded-sm"
                    data-testid={`alert-card-${alert.id}`}
                  >
                    <div className={`w-10 h-10 rounded-sm flex items-center justify-center ${SeverityIconBg({ severity: alert.severity })}`}>
                      <span className="material-symbols-outlined">{alert.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-on-surface truncate">{alert.title}</h4>
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

        {/* Bento Grid 2: AI Actions */}
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
                <div key={i} className="h-48 bg-surface-container-low rounded-sm animate-pulse"></div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {actionsList.map((action, idx) => (
                <div
                  key={action.id}
                  className="bg-surface-container-low border border-outline-variant/10 p-6 hover:bg-surface-container-high transition-all duration-300 group cursor-pointer rounded-sm"
                  data-testid={`action-card-${action.id}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-2 rounded-sm ${idx === 1 ? "bg-tertiary/10" : idx === 2 ? "bg-on-surface-variant/10" : "bg-primary/10"}`}>
                      <span
                        className={`material-symbols-outlined text-2xl ${idx === 1 ? "text-tertiary" : idx === 2 ? "text-on-surface-variant" : "text-primary"}`}
                      >
                        {action.icon}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-tertiary">CONFIANCE</span>
                      <p className="text-xl font-black text-on-surface tracking-tighter">{action.confidence}%</p>
                    </div>
                  </div>
                  <h4 className="text-base font-bold text-on-surface mb-3 font-headline">{action.title}</h4>
                  <p className="text-sm text-gray-500 mb-8 leading-relaxed flex-1">{action.description}</p>
                  <button className="w-full py-2.5 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed text-[11px] font-bold rounded-sm group-hover:scale-[1.02] transition-transform uppercase tracking-wider">
                    {action.cta_label}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom Grid: Product Performance + Regional Distribution */}
        <div className="grid grid-cols-12 gap-6">
          {/* Product Performance */}
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
            ) : (
              <div className="space-y-5">
                {data.product_performance.map((product) => (
                  <div key={product.product} className="relative">
                    <div className="flex justify-between items-end mb-2">
                      <span className="text-sm font-bold">{product.product}</span>
                      <span className={`text-xs font-bold ${product.trend_pct >= 0 ? "text-tertiary" : "text-error"}`}>
                        {product.trend_pct >= 0 ? "+" : ""}{product.trend_pct}%
                      </span>
                    </div>
                    <div className="h-2 bg-surface-container-highest w-full rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-700"
                        style={{ width: `${product.relative_volume}%`, opacity: 1 - (data.product_performance.indexOf(product) * 0.2) }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Regional Distribution */}
          <div className="col-span-12 lg:col-span-5 bg-surface-container p-6 rounded-xl flex flex-col">
            <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest block mb-4">
              DISTRIBUTION RÉGIONALE
            </span>
            <div className="flex-1 bg-surface-container-low rounded-sm relative overflow-hidden p-4">
              <div className="absolute inset-0 opacity-10">
                <div className="w-full h-full bg-gradient-to-br from-gray-800 to-black flex items-center justify-center">
                  <span className="material-symbols-outlined text-6xl text-gray-700">map</span>
                </div>
              </div>
              {summaryLoading ? (
                <div className="relative space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-4 bg-surface-container-high rounded animate-pulse"></div>
                  ))}
                </div>
              ) : (
                <div className="relative space-y-3">
                  {data.regional_distribution.map((region) => (
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
      </div>
    </AppShell>
  );
}
