import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyTenantState } from "@/components/EmptyTenantState";
import { apiRequest } from "@/lib/queryClient";
import { mapAlert } from "@/lib/apiMappings";
import { filterAlertViews } from "@/lib/pageSearchFilters";
import { toast } from "@/hooks/use-toast";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

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

const STATUS_LABELS: Record<StatusFilter, string> = {
  NOUVEAU: "Nouveau",
  RECONNU: "Reconnu",
  RESOLU: "Résolu",
  ECARTE: "Écarté",
};

const SEVERITY_LABELS: Record<SeverityFilter, string> = {
  CRITIQUE: "Critique",
  HAUTE: "Haute",
  MOYENNE: "Moyenne",
  BASSE: "Basse",
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
  return "Impact non chiffré";
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

function getSourceInitials(platform: string): string {
  const normalized = platform.toLowerCase();
  if (normalized === "facebook") return "FB";
  if (normalized === "youtube") return "YT";
  if (normalized === "google_maps") return "GM";
  if (normalized === "instagram") return "IG";
  if (normalized === "import") return "IM";
  return platform.slice(0, 2).toUpperCase();
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
    NOUVEAU: "bg-monitor-container text-monitor",
    RECONNU: "bg-warning/10 text-warning",
    RESOLU: "bg-action-container text-action",
    ECARTE: "bg-surface-container-high text-on-surface-variant",
  };
  return (
    <span
      className={`text-[10px] font-bold px-2 py-1 rounded uppercase flex items-center gap-1.5 ${map[status]}`}
    >
      {status === "NOUVEAU" ? (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-monitor"></span>
      ) : status === "RESOLU" ? (
        <span className="material-symbols-outlined text-[12px]">check</span>
      ) : (
        <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      )}
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function SeverityDot({ severity }: { severity: SeverityFilter }) {
  const map: Record<SeverityFilter, string> = {
    CRITIQUE: "bg-error",
    HAUTE: "bg-warning",
    MOYENNE: "border border-warning/45 bg-warning/35",
    BASSE: "border border-outline bg-surface-container-highest",
  };
  return <span className={`w-3 h-3 rounded-full ${map[severity]}`}></span>;
}

function severityAccentClass(severity: SeverityFilter): string {
  if (severity === "CRITIQUE") return "bg-error";
  if (severity === "HAUTE") return "bg-warning";
  if (severity === "MOYENNE") return "bg-warning/45";
  return "bg-outline";
}

function severityToneClass(severity: SeverityFilter): string {
  if (severity === "CRITIQUE") return "bg-error-container text-error";
  if (severity === "HAUTE") return "bg-warning/10 text-warning";
  if (severity === "MOYENNE") return "bg-warning/10 text-warning";
  return "bg-surface-container-high text-on-surface-variant";
}

export default function Alertes() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [alertLimit, setAlertLimit] = useState(50);
  const queryClientHook = useQueryClient();

  const { data: alerts, isLoading: alertsLoading } = useQuery<AlertView[]>({
    queryKey: ["/api/alerts", statusFilter, severityFilter, alertLimit],
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
      params.set("limit", String(alertLimit));
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
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message || "Une erreur est survenue",
        variant: "destructive",
      });
    },
  });

  const alertsList = useMemo(
    () => filterAlertViews(alerts ?? [], searchQuery),
    [alerts, searchQuery],
  );

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

  if (!alertsLoading && alertsList.length === 0) {
    return (
      <AppShell
        headerSearchPlaceholder="Rechercher une alerte..."
        onSearch={setSearchQuery}
        avatarSrc={STITCH_AVATARS.alertes.src}
        avatarAlt={STITCH_AVATARS.alertes.alt}
      >
        <div className="p-8 min-h-[calc(100vh-64px)]">
          <EmptyTenantState
            title="Aucune alerte exploitable pour l'instant"
            description="Les alertes apparaîtront dès que la collecte et l'ABSA auront produit assez de signaux pour détecter une dérive ou un pic négatif."
          />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une alerte..."
      onSearch={setSearchQuery}
      avatarSrc={STITCH_AVATARS.alertes.src}
      avatarAlt={STITCH_AVATARS.alertes.alt}
    >
      <div className="mx-auto min-h-[calc(100vh-64px)] w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <PageHeader
          eyebrow="Risque détecté"
          tone="risk"
          title="Alertes à traiter"
          description="Chaque alerte signale un changement anormal dans les avis clients. Sélectionnez-la pour comprendre le problème, puis reconnaissez-la ou résolvez-la."
          actions={
            <div className="flex items-center gap-2 rounded-lg border border-outline-variant/60 bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
            <span className="h-2 w-2 animate-pulse rounded-full bg-error"></span>
            {alertsList.filter((alert) => alert.status !== "RESOLU" && alert.status !== "ECARTE").length} alertes actives
          </div>
          }
        />

        <section className="mt-8 mb-8 flex flex-wrap items-center gap-6 rounded-xl border border-outline-variant/60 bg-surface-container p-4">
          <div className="flex w-full flex-col items-start gap-2 sm:w-auto sm:flex-row sm:items-center sm:gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">
              Statut
            </span>
            <div className="flex flex-wrap gap-2">
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
          <div className="hidden h-6 w-px bg-outline-variant/30 sm:block"></div>
          <div className="flex w-full flex-col items-start gap-2 sm:w-auto sm:flex-row sm:items-center sm:gap-3">
            <span className="text-[10px] font-bold uppercase text-on-surface-variant tracking-wider">
              Sévérité
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { value: "CRITIQUE" as SeverityFilter, dotClass: "bg-error" },
                { value: "HAUTE" as SeverityFilter, dotClass: "bg-warning" },
                { value: "MOYENNE" as SeverityFilter, dotClass: "bg-warning/45" },
                { value: "BASSE" as SeverityFilter, dotClass: "bg-outline" },
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
                      ? "border border-monitor/35 bg-monitor-container/35 ring-1 ring-monitor/10"
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
            {alertsList.length >= alertLimit && (
              <button
                onClick={() => setAlertLimit((prev) => prev + 50)}
                className="w-full py-3 text-xs font-bold uppercase tracking-widest text-primary hover:bg-surface-container-high transition-colors rounded-sm"
              >
                Charger plus
              </button>
            )}
          </div>

          <div className="lg:col-span-7">
            {selectedAlert ? (
              <section className="bg-surface-container-low rounded-sm sticky top-24 overflow-hidden">
                <div className={`h-1 ${severityAccentClass(selectedAlert.severity)}`}></div>
                <div className="p-8">
                  <div className="mb-6 flex items-start gap-4">
                    <div
                      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${severityToneClass(selectedAlert.severity)}`}
                    >
                      <span className="material-symbols-outlined text-2xl">
                        warning
                      </span>
                    </div>
                    <div className="min-w-0">
                      <p className={`mb-2 inline-flex rounded-lg px-2.5 py-1 text-[10px] font-bold ${severityToneClass(selectedAlert.severity)}`}>
                        Alerte {SEVERITY_LABELS[selectedAlert.severity].toLowerCase()}
                      </p>
                      <h2 className="font-headline text-xl font-extrabold tracking-tight">
                        {selectedAlert.title}
                      </h2>
                      <p className="mt-1 text-xs text-on-surface-variant">
                        Détectée le {selectedAlert.detected_at}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-6">
                    <div>
                      <h3 className="mb-2 font-headline text-sm font-bold text-on-surface">
                        Ce qui a été détecté
                      </h3>
                      <p className="mb-3 text-[10px] text-on-surface-variant">
                        Résumé du changement anormal observé dans les données.
                      </p>
                      <p className="text-on-surface leading-relaxed text-sm">
                        {selectedAlert.description}
                      </p>
                    </div>

                    {selectedAlert.social_excerpts.length > 0 ? (
                      <div className="bg-surface-container-lowest p-5 rounded-sm border border-outline-variant/10">
                        <h4 className="mb-1 font-headline text-sm font-bold text-on-surface">
                          Avis à l’origine de l’alerte
                        </h4>
                        <p className="mb-4 text-[10px] text-on-surface-variant">Extraits consultables pour vérifier l’interprétation.</p>
                        <div className="space-y-4">
                          {selectedAlert.social_excerpts.map((excerpt, index) => (
                            <div key={`${excerpt.author}-${index}`} className="flex gap-3">
                              <div className="h-6 w-6 rounded-full bg-surface-container-highest shrink-0 flex items-center justify-center text-[9px] font-bold text-on-surface-variant">
                                {getSourceInitials(excerpt.platform)}
                              </div>
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
                          Impact Estimé
                        </span>
                        <span className="flex items-center gap-2 text-sm font-bold text-insight">
                          <span className="material-symbols-outlined text-sm">analytics</span>
                          {selectedAlert.estimated_impact}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-col gap-3 border-t border-outline-variant/20 pt-6 sm:flex-row">
                      {selectedAlert.status !== "RECONNU" && (
                        <button
                          onClick={() =>
                            updateStatusMutation.mutate({
                              id: selectedAlert.id,
                              status: "acknowledged",
                            })
                          }
                          disabled={updateStatusMutation.isPending}
                          className="flex-1 rounded-lg border border-monitor/20 bg-monitor-container px-4 py-3 text-xs font-bold text-monitor transition-colors hover:bg-monitor-container/70 disabled:opacity-50"
                          data-testid="btn-acknowledge"
                        >
                          {updateStatusMutation.isPending ? (
                            <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                          ) : (
                            "Marquer comme prise en charge"
                          )}
                        </button>
                      )}
                      {selectedAlert.status !== "ECARTE" && (
                        <button
                          onClick={() =>
                            updateStatusMutation.mutate({
                              id: selectedAlert.id,
                              status: "dismissed",
                            })
                          }
                          disabled={updateStatusMutation.isPending}
                          className="flex-1 rounded-lg border border-outline-variant bg-surface px-4 py-3 text-xs font-bold text-on-surface-variant transition-colors hover:bg-surface-container disabled:opacity-50"
                          data-testid="btn-dismiss"
                        >
                          {updateStatusMutation.isPending ? (
                            <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                          ) : (
                            "Écarter cette alerte"
                          )}
                        </button>
                      )}
                      {selectedAlert.status !== "RESOLU" && (
                        <button
                          onClick={() =>
                            updateStatusMutation.mutate({
                              id: selectedAlert.id,
                              status: "resolved",
                            })
                          }
                          disabled={updateStatusMutation.isPending}
                          className="flex-1 rounded-lg bg-action px-4 py-3 text-xs font-bold text-white transition-colors hover:bg-action/90 disabled:opacity-50"
                          data-testid="btn-resolve"
                        >
                          {updateStatusMutation.isPending ? (
                            <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                          ) : (
                            "Marquer comme résolue"
                          )}
                        </button>
                      )}
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
