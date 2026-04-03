import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { Alert } from "@shared/schema";

const MOCK_ALERTS: Alert[] = [
  {
    id: "1",
    title: "Chute de sentiment - Ramy Fraise (Alger)",
    description: "Volume inhabituel de mentions négatives détecté sur Facebook et Twitter. Les utilisateurs se plaignent d'un goût différent dans le lot #FR2024-03...",
    severity: "CRITIQUE",
    status: "NOUVEAU",
    location: "Alger (District 16)",
    estimated_impact: "-12% Engagement",
    detected_at: "il y a 5 min",
    social_excerpts: [
      { author: "Amine B.", platform: "Facebook", text: "\"Le goût du Ramy Fraise aujourd'hui est bizarre, comme un arrière-goût métallique. Quelqu'un d'autre a remarqué ?\"" },
      { author: "Sara Oran", platform: "Twitter", text: "\"Immangeable le dernier lot de jus, déçue par @RamyAlgerie...\"" },
    ],
  },
  {
    id: "2",
    title: "Rupture de Stock - Oran Ouest",
    description: "Le distributeur SARL El-Bahia signale une rupture de stock critique sur la gamme Ramy Orange 1L.",
    severity: "HAUTE",
    status: "RECONNU",
    location: "Oran (Ouest)",
    estimated_impact: "-8% Disponibilité",
    detected_at: "il y a 24 min",
    social_excerpts: [],
  },
  {
    id: "3",
    title: "Pic de Mentions - Constantine",
    description: "Hausse de 40% des requêtes Google Trends sur \"Promotion Ramy Ramadan\" dans la région Est.",
    severity: "MOYENNE",
    status: "EN_COURS",
    location: "Constantine",
    estimated_impact: "+40% Mentions",
    detected_at: "il y a 2 heures",
    social_excerpts: [],
  },
  {
    id: "4",
    title: "Mention Presse - El Watan",
    description: "Article positif sur l'engagement environnemental de Ramy publié ce matin.",
    severity: "BASSE",
    status: "RÉSOLU",
    location: "National",
    estimated_impact: "+5% Notoriété",
    detected_at: "résolu il y a 4 heures",
    social_excerpts: [],
  },
];

type StatusFilter = "NOUVEAU" | "RECONNU" | "EN_COURS" | "RÉSOLU";
type SeverityFilter = "CRITIQUE" | "HAUTE" | "MOYENNE" | "BASSE";

// Map frontend status display values to API values
const STATUS_TO_API: Record<StatusFilter, string> = {
  NOUVEAU: "new",
  RECONNU: "acknowledged",
  EN_COURS: "investigating",
  RÉSOLU: "resolved",
};

// Map API status values back to frontend display values
const API_TO_STATUS: Record<string, Alert["status"]> = {
  new: "NOUVEAU",
  acknowledged: "RECONNU",
  investigating: "EN_COURS",
  resolved: "RÉSOLU",
  NOUVEAU: "NOUVEAU",
  RECONNU: "RECONNU",
  EN_COURS: "EN_COURS",
  RÉSOLU: "RÉSOLU",
};

const SEVERITY_TO_API: Record<SeverityFilter, string> = {
  CRITIQUE: "critical",
  HAUTE: "high",
  MOYENNE: "medium",
  BASSE: "low",
};

// Map API alert response to Alert schema
function mapAlertFromApi(a: Record<string, unknown>): Alert {
  return {
    id: String(a.id ?? a.alert_id ?? ""),
    title: String(a.title ?? ""),
    description: String(a.description ?? ""),
    severity: (a.severity as Alert["severity"]) ?? "BASSE",
    status: API_TO_STATUS[String(a.status ?? "new")] ?? "NOUVEAU",
    location: String(a.location ?? a.wilaya ?? ""),
    estimated_impact: String(a.estimated_impact ?? ""),
    detected_at: String(a.detected_at ?? a.created_at ?? ""),
    social_excerpts: (a.social_excerpts as Alert["social_excerpts"]) ?? [],
  };
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    NOUVEAU: "bg-blue-500/10 text-blue-400",
    RECONNU: "bg-yellow-500/10 text-yellow-400",
    EN_COURS: "bg-purple-500/10 text-purple-400",
    RÉSOLU: "bg-green-500/10 text-green-400",
  };
  return (
    <span className={`text-[10px] font-bold px-2 py-1 rounded uppercase flex items-center gap-1.5 ${map[status] ?? ""}`}>
      {status === "NOUVEAU" && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>}
      {status === "RÉSOLU" && <span className="material-symbols-outlined text-[12px]">check</span>}
      {status}
    </span>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    CRITIQUE: "bg-error shadow-[0_0_8px_rgba(255,180,171,0.5)]",
    HAUTE: "bg-primary-container",
    MOYENNE: "bg-yellow-400",
    BASSE: "bg-tertiary",
  };
  return <span className={`w-3 h-3 rounded-full ${map[severity] ?? "bg-gray-400"}`}></span>;
}

function SeverityBorderClass(severity: string) {
  const map: Record<string, string> = {
    CRITIQUE: "border-error",
    HAUTE: "border-primary-container",
    MOYENNE: "border-yellow-400",
    BASSE: "border-tertiary",
  };
  return map[severity] ?? "border-gray-400";
}

export default function Alertes() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(MOCK_ALERTS[0]);

  const queryClientHook = useQueryClient();

  const { data: alerts, isLoading: alertsLoading } = useQuery<Alert[]>({
    queryKey: ["/api/alerts", statusFilter, severityFilter],
    queryFn: async () => {
      try {
        const params = new URLSearchParams();
        if (statusFilter) params.set("status", STATUS_TO_API[statusFilter]);
        if (severityFilter) params.set("severity", SEVERITY_TO_API[severityFilter]);
        params.set("limit", "50");
        const res = await apiRequest("GET", `/api/alerts?${params}`);
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.alerts ?? apiData.results ?? []);
        const mapped = (list as Array<Record<string, unknown>>).map(mapAlertFromApi);
        return mapped.length > 0 ? mapped : MOCK_ALERTS;
      } catch {
        return MOCK_ALERTS;
      }
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      // Map frontend status to API status
      const apiStatus = STATUS_TO_API[status as StatusFilter] ?? status.toLowerCase();
      const res = await apiRequest("PUT", `/api/alerts/${id}/status`, { status: apiStatus });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/alerts"] });
    },
  });

  const alertsList = alerts ?? MOCK_ALERTS;
  const filteredAlerts = alertsList.filter((a) => {
    if (statusFilter && a.status !== statusFilter) return false;
    if (severityFilter && a.severity !== severityFilter) return false;
    return true;
  });

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une alerte..."
      onSearch={() => {}}
    >
      <div className="p-8 min-h-[calc(100vh-64px)]">
        {/* Header */}
        <div className="flex justify-between items-end mb-8">
          <div>
            <span className="text-on-surface-variant text-[10px] uppercase tracking-[0.2em] mb-2 block font-bold">
              Surveillance Active
            </span>
            <h1 className="text-3xl font-headline font-extrabold tracking-tight text-on-surface">
              Console d'Alertes
            </h1>
          </div>
          <div className="flex items-center gap-2 text-xs text-on-surface-variant">
            <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
            Système en ligne : {alertsList.filter(a => a.status !== "RÉSOLU").length} alertes actives
          </div>
        </div>

        {/* Filter Bar */}
        <section className="bg-surface-container rounded-sm p-4 mb-8 flex flex-wrap items-center gap-6 border-l-2 border-primary">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">Statut</span>
            <div className="flex gap-2">
              {(["NOUVEAU", "RECONNU", "EN_COURS", "RÉSOLU"] as StatusFilter[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(statusFilter === s ? null : s)}
                  className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                    statusFilter === s
                      ? "bg-surface-container-highest text-primary border border-primary/20"
                      : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                  data-testid={`filter-status-${s.toLowerCase()}`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
          <div className="w-px h-6 bg-outline-variant/30"></div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">Sévérité</span>
            <div className="flex gap-2">
              {[
                { value: "CRITIQUE" as SeverityFilter, dotClass: "bg-error" },
                { value: "HAUTE" as SeverityFilter, dotClass: "bg-primary-container" },
                { value: "MOYENNE" as SeverityFilter, dotClass: "bg-yellow-400" },
                { value: "BASSE" as SeverityFilter, dotClass: "bg-tertiary" },
              ].map(({ value, dotClass }) => (
                <button
                  key={value}
                  onClick={() => setSeverityFilter(severityFilter === value ? null : value)}
                  className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors flex items-center gap-2 ${
                    severityFilter === value
                      ? "bg-surface-container-highest text-on-surface border border-outline-variant/30"
                      : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${dotClass}`}></span>
                  {value.charAt(0) + value.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Alerts List */}
          <div className="lg:col-span-5 space-y-3">
            {alertsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-24 bg-surface-container-low rounded-sm animate-pulse"></div>
              ))
            ) : (
              filteredAlerts.map((alert) => (
                <article
                  key={alert.id}
                  onClick={() => setSelectedAlert(alert)}
                  className={`p-5 rounded-sm cursor-pointer transition-all duration-200 ${
                    selectedAlert?.id === alert.id
                      ? `bg-surface-container-high border-l-4 ${SeverityBorderClass(alert.severity)} ring-1 ring-white/10`
                      : "bg-surface-container-low hover:bg-surface-container"
                  } ${alert.status === "RÉSOLU" ? "opacity-60" : ""}`}
                  data-testid={`alert-item-${alert.id}`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <SeverityDot severity={alert.severity} />
                      <h3 className="font-headline font-bold text-base leading-tight">{alert.title}</h3>
                    </div>
                    <StatusBadge status={alert.status} />
                  </div>
                  <p className="text-on-surface-variant text-sm mb-3 leading-relaxed line-clamp-2">
                    {alert.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-on-surface-variant/50 font-medium uppercase tracking-wider">
                      {alert.detected_at}
                    </span>
                    {selectedAlert?.id === alert.id && (
                      <span className="material-symbols-outlined text-primary text-sm">keyboard_arrow_right</span>
                    )}
                  </div>
                </article>
              ))
            )}
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-7">
            {selectedAlert ? (
              <section className="bg-surface-container-low rounded-sm sticky top-24 overflow-hidden">
                <div className={`h-1 bg-gradient-to-r ${selectedAlert.severity === "CRITIQUE" ? "from-error to-error-container" : selectedAlert.severity === "HAUTE" ? "from-primary-container to-primary" : "from-tertiary to-tertiary-container"}`}></div>
                <div className="p-8">
                  <div className="flex items-center gap-4 mb-6">
                    <div className={`w-12 h-12 rounded-sm flex items-center justify-center ${selectedAlert.severity === "CRITIQUE" ? "bg-error/10" : "bg-primary/10"}`}>
                      <span className={`material-symbols-outlined text-2xl ${selectedAlert.severity === "CRITIQUE" ? "text-error" : "text-primary"}`}>
                        warning
                      </span>
                    </div>
                    <div>
                      <h2 className="text-xl font-headline font-extrabold tracking-tight">Détails de l'Alerte</h2>
                      <p className="text-on-surface-variant text-xs">
                        ID: AL-{selectedAlert.id.padStart(4, "0")}-DZ | Sévérité: {selectedAlert.severity}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary mb-3">Analyse Complète</h4>
                      <p className="text-on-surface leading-relaxed text-sm">{selectedAlert.description}</p>
                    </div>

                    {selectedAlert.social_excerpts.length > 0 && (
                      <div className="bg-surface-container-lowest p-5 rounded-sm border border-outline-variant/10">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-tertiary mb-4">
                          Extraits Sociaux (Temps Réel)
                        </h4>
                        <div className="space-y-4">
                          {selectedAlert.social_excerpts.map((excerpt, i) => (
                            <div key={i} className="flex gap-3">
                              <div className="h-6 w-6 rounded-full bg-surface-container-highest shrink-0"></div>
                              <div>
                                <span className="text-xs font-bold block mb-1">
                                  {excerpt.author}{" "}
                                  <span className="text-on-surface-variant font-normal">@{excerpt.platform}</span>
                                </span>
                                <p className="text-xs italic text-on-surface-variant">{excerpt.text}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-surface-container p-4 rounded-sm">
                        <span className="text-[10px] text-on-surface-variant uppercase block mb-1">Localisation</span>
                        <span className="text-sm font-bold flex items-center gap-2">
                          <span className="material-symbols-outlined text-sm">location_on</span>
                          {selectedAlert.location}
                        </span>
                      </div>
                      <div className="bg-surface-container p-4 rounded-sm">
                        <span className="text-[10px] text-on-surface-variant uppercase block mb-1">Impact Estimé</span>
                        <span className={`text-sm font-bold flex items-center gap-2 ${selectedAlert.estimated_impact.startsWith("-") ? "text-error" : "text-tertiary"}`}>
                          <span className="material-symbols-outlined text-sm">
                            {selectedAlert.estimated_impact.startsWith("-") ? "trending_down" : "trending_up"}
                          </span>
                          {selectedAlert.estimated_impact}
                        </span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-6 border-t border-outline-variant/20">
                      <button
                        onClick={() => updateStatusMutation.mutate({ id: selectedAlert.id, status: "RECONNU" })}
                        className="flex-1 bg-surface-container-high hover:bg-surface-bright text-on-surface font-bold py-3 px-4 rounded-sm text-xs transition-colors border border-outline-variant/30 uppercase tracking-widest"
                        data-testid="btn-acknowledge"
                      >
                        Reconnaître
                      </button>
                      <button
                        onClick={() => updateStatusMutation.mutate({ id: selectedAlert.id, status: "EN_COURS" })}
                        className="flex-1 bg-surface-container-high hover:bg-surface-bright text-primary font-bold py-3 px-4 rounded-sm text-xs transition-colors border border-primary/20 uppercase tracking-widest"
                        data-testid="btn-investigate"
                      >
                        Investiguer
                      </button>
                      <button
                        onClick={() => updateStatusMutation.mutate({ id: selectedAlert.id, status: "RÉSOLU" })}
                        className="flex-1 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed font-bold py-3 px-4 rounded-sm text-xs hover:opacity-90 transition-opacity uppercase tracking-widest"
                        data-testid="btn-resolve"
                      >
                        Résoudre
                      </button>
                    </div>
                  </div>
                </div>
              </section>
            ) : (
              <div className="flex items-center justify-center h-64 text-on-surface-variant text-sm">
                Sélectionnez une alerte pour voir les détails
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
