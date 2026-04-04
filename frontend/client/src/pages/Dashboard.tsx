import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { DashboardSummary, DashboardAlert, DashboardAction } from "@shared/schema";

function SeverityBadge({ severity }: { severity: string }) {
  if (severity === "critical") {
    return <span className="text-[10px] font-bold text-error uppercase">Critique</span>;
  }
  if (severity === "high") {
    return <span className="text-[10px] font-bold text-primary uppercase">Haute</span>;
  }
  return <span className="text-[10px] font-bold text-gray-500 uppercase">{severity}</span>;
}

function severityIconBg(severity: string) {
  if (severity === "critical") return "bg-error/10 text-error";
  if (severity === "high") return "bg-primary/10 text-primary";
  return "bg-surface-container-highest text-gray-400";
}

function severityIcon(severity: string) {
  if (severity === "critical") return "error";
  if (severity === "high") return "warning";
  return "info";
}

function trendIcon(trend: string) {
  if (trend === "up") return "trending_up";
  if (trend === "down") return "trending_down";
  return "trending_flat";
}

function trendColor(trend: string) {
  if (trend === "up") return "text-tertiary";
  if (trend === "down") return "text-error";
  return "text-gray-400";
}

function priorityColor(priority: string) {
  if (priority === "high") return "bg-primary/10";
  if (priority === "medium") return "bg-tertiary/10";
  return "bg-on-surface-variant/10";
}

function priorityIconColor(priority: string) {
  if (priority === "high") return "text-primary";
  if (priority === "medium") return "text-tertiary";
  return "text-on-surface-variant";
}

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ["/api/dashboard/summary"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/summary");
      return res.json();
    },
  });

  const { data: alertsData, isLoading: alertsLoading } = useQuery<{ critical_alerts: DashboardAlert[] }>({
    queryKey: ["/api/dashboard/alerts-critical"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/alerts-critical");
      return res.json();
    },
  });

  const { data: actionsData, isLoading: actionsLoading } = useQuery<{ top_actions: DashboardAction[] }>({
    queryKey: ["/api/dashboard/top-actions"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/dashboard/top-actions");
      return res.json();
    },
  });

  const healthScore = summary?.health_score ?? 0;
  const alertsList = alertsData?.critical_alerts ?? [];
  const actionsList = actionsData?.top_actions ?? [];

  const circumference = 2 * Math.PI * 88;
  const dashOffset = circumference * (1 - healthScore / 100);

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
          </div>
        </div>

        {/* Bento Grid 1: Health Score + Critical Alerts */}
        <div className="grid grid-cols-12 gap-6">
          {/* Brand Health Score Gauge */}
          <div
            className="col-span-12 lg:col-span-4 bg-surface-container p-6 rounded-xl flex flex-col items-center justify-center relative overflow-hidden"
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
                    cx="96" cy="96" fill="transparent" r="88"
                    stroke="currentColor" strokeWidth="8"
                  />
                  <circle
                    className="text-primary"
                    cx="96" cy="96" fill="transparent" r="88"
                    stroke="currentColor"
                    strokeDasharray={circumference}
                    strokeDashoffset={dashOffset}
                    strokeWidth="8" strokeLinecap="round"
                    style={{ transition: "stroke-dashoffset 1s ease" }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl font-black tracking-tighter text-on-surface" data-testid="nss-score">
                    {healthScore}
                  </span>
                  <span className="text-xs font-bold text-on-surface-variant">/ 100</span>
                </div>
              </div>
            )}
            <div className="mt-6 text-center">
              <p className={`text-sm font-semibold flex items-center gap-1 justify-center ${trendColor(summary?.health_trend ?? "flat")}`}>
                <span className="material-symbols-outlined text-sm">{trendIcon(summary?.health_trend ?? "flat")}</span>
                {summary?.nss_progress_pts !== undefined
                  ? `${summary.nss_progress_pts > 0 ? "+" : ""}${summary.nss_progress_pts} pts`
                  : "—"}
              </p>
              <p className="text-[11px] text-gray-500 mt-2 italic leading-relaxed max-w-xs">
                {summary?.summary_text ?? "Chargement..."}
              </p>
            </div>
          </div>

          {/* Critical Alerts */}
          <div className="col-span-12 lg:col-span-8 bg-surface-container p-6 rounded-xl flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">
                ALERTES CRITIQUES
              </span>
              {alertsList.length > 0 && (
                <span className="px-2 py-0.5 bg-error-container text-error text-[10px] font-bold rounded">
                  {alertsList.length} ACTIVE{alertsList.length > 1 ? "S" : ""}
                </span>
              )}
            </div>
            {alertsLoading ? (
              <div className="space-y-2 flex-1">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-surface-container-low rounded-sm animate-pulse"></div>
                ))}
              </div>
            ) : alertsList.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                <span className="material-symbols-outlined mr-2 text-tertiary">check_circle</span>
                Aucune alerte critique. Tout est sous contrôle.
              </div>
            ) : (
              <div className="space-y-2 flex-1">
                {alertsList.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="flex items-center gap-4 p-4 bg-surface-container-low hover:bg-surface-container-high transition-colors duration-200 cursor-pointer rounded-sm"
                  >
                    <div className={`w-10 h-10 rounded-sm flex items-center justify-center ${severityIconBg(alert.severity)}`}>
                      <span className="material-symbols-outlined">{severityIcon(alert.severity)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-on-surface truncate">{alert.title}</h4>
                      <p className="text-xs text-gray-500 line-clamp-1">{alert.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <SeverityBadge severity={alert.severity} />
                      <p className="text-[10px] text-gray-600 mt-1">{alert.created_at}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI Actions */}
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
          ) : actionsList.length === 0 ? (
            <div className="bg-surface-container-low border border-outline-variant/10 p-8 rounded-sm text-center">
              <span className="material-symbols-outlined text-4xl text-gray-600 mb-2">auto_awesome</span>
              <p className="text-sm text-gray-500">Aucune recommandation active.</p>
              <a href="#/recommandations" className="text-xs text-primary font-bold mt-2 inline-block">
                Générer des recommandations
              </a>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {actionsList.map((action) => (
                <div
                  key={action.recommendation_id}
                  className="bg-surface-container-low border border-outline-variant/10 p-6 hover:bg-surface-container-high transition-all duration-300 cursor-pointer rounded-sm"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-2 rounded-sm ${priorityColor(action.priority)}`}>
                      <span className={`material-symbols-outlined text-2xl ${priorityIconColor(action.priority)}`}>
                        auto_awesome
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-tertiary uppercase">{action.priority}</span>
                      <p className="text-xs text-gray-500 mt-1">{action.target_platform}</p>
                    </div>
                  </div>
                  <h4 className="text-base font-bold text-on-surface mb-3 font-headline">{action.title}</h4>
                  <a
                    href="#/recommandations"
                    className="w-full py-2.5 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed text-[11px] font-bold rounded-sm uppercase tracking-wider block text-center mt-4"
                  >
                    VOIR DÉTAILS
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
