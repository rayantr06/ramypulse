import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import { mapAlert } from "@/lib/apiMappings";

type StatusFilter = "NOUVEAU" | "RECONNU" | "RESOLU" | "ECARTE";
type SeverityFilter = "CRITIQUE" | "HAUTE" | "MOYENNE" | "BASSE";

interface SocialExcerpt {
  author: string;
  platform: string;
  text: string;
}

interface AlertView {
  id: string;
  title: string;
  description: string;
  severity: SeverityFilter;
  status: StatusFilter;
  location: string;
  estimated_impact: string;
  detected_at: string;
  social_excerpts: SocialExcerpt[];
}

const STATUS_TO_API: Record<StatusFilter, string> = {
  NOUVEAU: "new",
  RECONNU: "acknowledged",
  RESOLU: "resolved",
  ECARTE: "dismissed",
};

function mapSeverity(value: string | undefined | null): SeverityFilter {
  if (value === "critical") return "CRITIQUE";
  if (value === "high") return "HAUTE";
  if (value === "medium") return "MOYENNE";
  return "BASSE";
}

function mapStatus(value: string | undefined | null): StatusFilter {
  if (value === "acknowledged") return "RECONNU";
  if (value === "resolved") return "RESOLU";
  if (value === "dismissed") return "ECARTE";
  return "NOUVEAU";
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function buildImpactLabel(payload: Record<string, unknown>): string {
  const numericValue =
    typeof payload.value === "number"
      ? payload.value
      : typeof payload.current === "number"
        ? payload.current
        : null;
  if (numericValue != null) {
    return `${numericValue > 0 ? "+" : ""}${numericValue} pts`;
  }
  if (typeof payload.metric === "string") {
    return String(payload.metric).toUpperCase();
  }
  return "Impact non chiffre";
}

function buildLocation(payload: Record<string, unknown>, navigationUrl: string | null | undefined): string {
  if (typeof payload.wilaya === "string" && payload.wilaya) return payload.wilaya;
  if (typeof payload.region === "string" && payload.region) return payload.region;
  if (typeof payload.segment === "string" && payload.segment) return payload.segment;
  if (navigationUrl) return "Lien de contexte disponible";
  return "Non renseignée";
}

function buildSocialExcerpts(payload: Record<string, unknown>): SocialExcerpt[] {
  const excerpts = Array.isArray(payload.social_excerpts)
    ? payload.social_excerpts
    : Array.isArray(payload.examples)
      ? payload.examples
      : [];

  return excerpts
    .map((item) => asRecord(item))
    .map((item) => ({
      author: typeof item.author === "string" ? item.author : "Source",
      platform: typeof item.platform === "string" ? item.platform : "web",
      text: typeof item.text === "string" ? item.text : "",
    }))
    .filter((item) => item.text);
}

function mapAlertView(value: unknown): AlertView {
  const alert = mapAlert(value);
  const payload = asRecord(alert.alert_payload);
  return {
    id: alert.alert_id,
    title: alert.title,
    description: alert.description || "Aucune description disponible.",
    severity: mapSeverity(alert.severity),
    status: mapStatus(alert.status),
    location: buildLocation(payload, alert.navigation_url),
    estimated_impact: buildImpactLabel(payload),
    detected_at: alert.detected_at || "-",
    social_excerpts: buildSocialExcerpts(payload),
  };
}

function StatusBadge({ status }: { status: StatusFilter }) {
  const map: Record<StatusFilter, string> = {
    NOUVEAU: "bg-blue-500/10 text-blue-400",
    RECONNU: "bg-yellow-500/10 text-yellow-400",
    RESOLU: "bg-green-500/10 text-green-400",
    ECARTE: "bg-gray-500/10 text-gray-400",
  };
  return (
    <span
      className={`text-[10px] font-bold px-2 py-1 rounded uppercase flex items-center gap-1.5 ${map[status]}`}
    >
      {status === "NOUVEAU" ? (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
      ) : status === "RESOLU" ? (
        <span className="material-symbols-outlined text-[12px]">check</span>
      ) : (
        <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      )}
      {status}
    </span>
  );
}

function SeverityDot({ severity }: { severity: SeverityFilter }) {
  const map: Record<SeverityFilter, string> = {
    CRITIQUE: "bg-error shadow-[0_0_8px_rgba(255,180,171,0.5)]",
    HAUTE: "bg-primary-container",
    MOYENNE: "bg-yellow-400",
    BASSE: "bg-tertiary",
  };
  return <span className={`w-3 h-3 rounded-full ${map[severity]}`}></span>;
}

function severityBorderClass(severity: SeverityFilter): string {
  const map: Record<SeverityFilter, string> = {
    CRITIQUE: "border-error",
    HAUTE: "border-primary-container",
    MOYENNE: "border-yellow-400",
    BASSE: "border-tertiary",
  };
  return map[severity];
}

function severityGradient(severity: SeverityFilter): string {
  if (severity === "CRITIQUE") return "from-error to-error-container";
  if (severity === "HAUTE") return "from-primary-container to-primary";
  return "from-tertiary to-tertiary-container";
}

export default function Alertes() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClientHook = useQueryClient();

  const { data: alerts, isLoading: alertsLoading } = useQuery<AlertView[]>({
    queryKey: ["/api/alerts", statusFilter, severityFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", STATUS_TO_API[statusFilter]);
      if (severityFilter) {
        const severity =
          severityFilter === "CRITIQUE"
            ? "critical"
            : severityFilter === "HAUTE"
              ? "high"
              : severityFilter === "MOYENNE"
                ? "medium"
                : "low";
        params.set("severity", severity);
      }
      params.set("limit", "50");
      const res = await apiRequest("GET", `/api/alerts?${params.toString()}`);
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapAlertView);
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "acknowledged" | "resolved" | "dismissed" }) => {
      const res = await apiRequest("PUT", `/api/alerts/${id}/status`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/alerts"] });
    },
  });

  const alertsList = alerts ?? [];

  useEffect(() => {
    if (!alertsList.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !alertsList.some((alert) => alert.id === selectedId)) {
      setSelectedId(alertsList[0].id);
    }
  }, [alertsList, selectedId]);

  const selectedAlert = useMemo(() => {
    return alertsList.find((alert) => alert.id === selectedId) ?? null;
  }, [alertsList, selectedId]);

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une alerte..."
      onSearch={() => {}}
    >
      <div className="p-8 min-h-[calc(100vh-64px)]">
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
            Système en ligne : {alertsList.filter((alert) => alert.status !== "RESOLU" && alert.status !== "ECARTE").length} alertes actives
          </div>
        </div>

        <section className="bg-surface-container rounded-sm p-4 mb-8 flex flex-wrap items-center gap-6 border-l-2 border-primary">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">
              Statut
            </span>
            <div className="flex gap-2">
              {(["NOUVEAU", "RECONNU", "RESOLU", "ECARTE"] as StatusFilter[]).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(statusFilter === status ? null : status)}
                  className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                    statusFilter === status
                      ? "bg-surface-container-highest text-primary border border-primary/20"
                      : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                  data-testid={`filter-status-${status.toLowerCase()}`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
          <div className="w-px h-6 bg-outline-variant/30"></div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">
              Severite
            </span>
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
          <div className="lg:col-span-5 space-y-3">
            {alertsLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-24 bg-surface-container-low rounded-sm animate-pulse"
                ></div>
              ))
            ) : alertsList.length === 0 ? (
              <div className="bg-surface-container-low rounded-sm p-5 text-sm text-on-surface-variant">
                Aucune alerte disponible pour les filtres courants.
              </div>
            ) : (
              alertsList.map((alert) => (
                <article
                  key={alert.id}
                  onClick={() => setSelectedId(alert.id)}
                  className={`p-5 rounded-sm cursor-pointer transition-all duration-200 ${
                    selectedAlert?.id === alert.id
                      ? `bg-surface-container-high border-l-4 ${severityBorderClass(alert.severity)} ring-1 ring-white/10`
                      : "bg-surface-container-low hover:bg-surface-container"
                  } ${alert.status === "RESOLU" || alert.status === "ECARTE" ? "opacity-60" : ""}`}
                  data-testid={`alert-item-${alert.id}`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <SeverityDot severity={alert.severity} />
                      <h3 className="font-headline font-bold text-base leading-tight">
                        {alert.title}
                      </h3>
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
                    {selectedAlert?.id === alert.id ? (
                      <span className="material-symbols-outlined text-primary text-sm">
                        keyboard_arrow_right
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>

          <div className="lg:col-span-7">
            {selectedAlert ? (
              <section className="bg-surface-container-low rounded-sm sticky top-24 overflow-hidden">
                <div className={`h-1 bg-gradient-to-r ${severityGradient(selectedAlert.severity)}`}></div>
                <div className="p-8">
                  <div className="flex items-center gap-4 mb-6">
                    <div
                      className={`w-12 h-12 rounded-sm flex items-center justify-center ${
                        selectedAlert.severity === "CRITIQUE"
                          ? "bg-error/10"
                          : "bg-primary/10"
                      }`}
                    >
                      <span
                        className={`material-symbols-outlined text-2xl ${
                          selectedAlert.severity === "CRITIQUE"
                            ? "text-error"
                            : "text-primary"
                        }`}
                      >
                        warning
                      </span>
                    </div>
                    <div>
                      <h2 className="text-xl font-headline font-extrabold tracking-tight">
                        Details de l'Alerte
                      </h2>
                      <p className="text-on-surface-variant text-xs">
                        ID: {selectedAlert.id} | Severite: {selectedAlert.severity}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary mb-3">
                        Analyse Complète
                      </h4>
                      <p className="text-on-surface leading-relaxed text-sm">
                        {selectedAlert.description}
                      </p>
                    </div>

                    {selectedAlert.social_excerpts.length > 0 ? (
                      <div className="bg-surface-container-lowest p-5 rounded-sm border border-outline-variant/10">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-tertiary mb-4">
                          Extraits Sociaux (Temps Réel)
                        </h4>
                        <div className="space-y-4">
                          {selectedAlert.social_excerpts.map((excerpt, index) => (
                            <div key={`${excerpt.author}-${index}`} className="flex gap-3">
                              <div className="h-6 w-6 rounded-full bg-surface-container-highest shrink-0"></div>
                              <div>
                                <span className="text-xs font-bold block mb-1">
                                  {excerpt.author}{" "}
                                  <span className="text-on-surface-variant font-normal">
                                    @{excerpt.platform}
                                  </span>
                                </span>
                                <p className="text-xs italic text-on-surface-variant">
                                  {excerpt.text}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-surface-container p-4 rounded-sm">
                        <span className="text-[10px] text-on-surface-variant uppercase block mb-1">
                          Localisation
                        </span>
                        <span className="text-sm font-bold flex items-center gap-2">
                          <span className="material-symbols-outlined text-sm">location_on</span>
                          {selectedAlert.location}
                        </span>
                      </div>
                      <div className="bg-surface-container p-4 rounded-sm">
                        <span className="text-[10px] text-on-surface-variant uppercase block mb-1">
                          Impact Estime
                        </span>
                        <span className="text-sm font-bold flex items-center gap-2 text-tertiary">
                          <span className="material-symbols-outlined text-sm">analytics</span>
                          {selectedAlert.estimated_impact}
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-3 pt-6 border-t border-outline-variant/20">
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            id: selectedAlert.id,
                            status: "acknowledged",
                          })
                        }
                        className="flex-1 bg-surface-container-high hover:bg-surface-bright text-on-surface font-bold py-3 px-4 rounded-sm text-xs transition-colors border border-outline-variant/30 uppercase tracking-widest"
                        data-testid="btn-acknowledge"
                      >
                        Reconnaitre
                      </button>
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            id: selectedAlert.id,
                            status: "dismissed",
                          })
                        }
                        className="flex-1 bg-surface-container-high hover:bg-surface-bright text-primary font-bold py-3 px-4 rounded-sm text-xs transition-colors border border-primary/20 uppercase tracking-widest"
                        data-testid="btn-dismiss"
                      >
                        Ecarter
                      </button>
                      <button
                        onClick={() =>
                          updateStatusMutation.mutate({
                            id: selectedAlert.id,
                            status: "resolved",
                          })
                        }
                        className="flex-1 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed font-bold py-3 px-4 rounded-sm text-xs hover:opacity-90 transition-opacity uppercase tracking-widest"
                        data-testid="btn-resolve"
                      >
                        Resoudre
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
