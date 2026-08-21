import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Database,
  MessageSquareText,
  Radio,
  ShieldAlert,
  Target,
  TrendingDown,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "wouter";

import { AppShell } from "@/components/AppShell";
import { DemoSourceFlow } from "@/components/demo/DemoSourceFlow";
import { PageHeader } from "@/components/PageHeader";
import { V3DataState } from "@/components/v3/V3DataState";
import { useV3Actions, useV3Overview, useV3Signals } from "@/hooks/useV3Data";

const TOOLTIP_STYLE = {
  border: "1px solid hsl(var(--outline-variant))",
  borderRadius: "12px",
  background: "hsl(var(--surface))",
  boxShadow: "0 10px 28px hsl(var(--shadow-color) / 0.1)",
  color: "hsl(var(--on-surface))",
  fontSize: "12px",
} as const;

function formatPeriod(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" }).format(new Date(value));
}

function severityLabel(value: string): string {
  if (value === "critical") return "Critique";
  if (value === "high") return "Élevée";
  if (value === "medium") return "Moyenne";
  return "Faible";
}

export default function Dashboard() {
  const overviewQuery = useV3Overview();
  const signalsQuery = useV3Signals();
  const actionsQuery = useV3Actions();
  const overview = overviewQuery.data;
  const signals = signalsQuery.data ?? [];
  const actions = actionsQuery.data ?? [];
  const openSignals = signals.filter((signal) => !["dismissed", "converted"].includes(signal.status));
  const activeActions = actions.filter((action) => !["resolved", "closed"].includes(action.status));

  if (overviewQuery.isLoading || signalsQuery.isLoading || actionsQuery.isLoading || overviewQuery.isError || signalsQuery.isError || actionsQuery.isError) {
    const loading = overviewQuery.isLoading || signalsQuery.isLoading || actionsQuery.isLoading;
    return <AppShell><div className="mx-auto w-full max-w-[1580px] space-y-5 px-4 py-7 sm:px-6 lg:px-8"><PageHeader eyebrow="Synchronisation" title="Aujourd’hui" description="Chargement de la situation opérationnelle." /><V3DataState loading={loading} onRetry={() => { void Promise.all([overviewQuery.refetch(), signalsQuery.refetch(), actionsQuery.refetch()]); }} /></div></AppShell>;
  }

  return (
    <AppShell>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-5 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-7">
        <PageHeader
          eyebrow="Données de démonstration"
          tone="setup"
          title="Aujourd’hui"
          description="Ce qui a réellement changé, pourquoi cela compte et quelle action demande une décision humaine."
          actions={overview ? (
            <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-outline-variant bg-surface px-3 text-[10px] font-semibold text-on-surface-variant">
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              {formatPeriod(overview.period.start)} — {formatPeriod(overview.period.end)}
            </span>
          ) : null}
        />

        <DemoSourceFlow />

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6" aria-label="Indicateurs transparents">
          <article className="dashboard-stat" data-testid="card-health-score">
            <div className="dashboard-stat__icon bg-primary-container text-primary"><MessageSquareText className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Mentions qualifiées</p><p className="dashboard-stat__value">{overview?.qualifiedMentions ?? "—"}</p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-insight-container text-insight"><Target className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Sentiment net</p><p className="dashboard-stat__value" data-testid="nss-score">{overview?.netSentiment == null ? "—" : `${overview.netSentiment > 0 ? "+" : ""}${overview.netSentiment}`}<span> pts</span></p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-error-container text-error"><TrendingDown className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Taux négatif</p><p className="dashboard-stat__value">{overview?.negativeRatePercent ?? "—"}<span>%</span></p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-error-container text-error"><ShieldAlert className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Signaux ouverts</p><p className="dashboard-stat__value">{openSignals.length}</p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-action-container text-action"><Clock3 className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Prise en charge médiane</p><p className="dashboard-stat__value">{overview?.medianTimeToOwnershipHours ?? "—"}<span> h</span></p></div>
          </article>
          <article className="dashboard-stat">
            <div className="dashboard-stat__icon bg-monitor-container text-monitor"><Database className="h-4 w-4" /></div>
            <div><p className="dashboard-stat__label">Couverture analytique</p><p className="dashboard-stat__value">{overview?.analyticalCoveragePercent ?? "—"}<span>%</span></p></div>
          </article>
        </section>

        {overview?.insufficientSample ? (
          <div className="rounded-2xl border border-outline-variant bg-surface px-4 py-3 text-xs text-on-surface-variant">
            Échantillon insuffisant : aucune variation n’est interprétée avec moins de 30 mentions qualifiées.
          </div>
        ) : null}

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(21rem,0.8fr)]">
          <article className="cling-panel overflow-hidden">
            <header className="flex flex-wrap items-start justify-between gap-3 border-b border-outline-variant px-5 py-4 sm:px-6">
              <div>
                <h2 className="font-headline text-base font-bold text-on-surface">Signaux qui demandent une décision</h2>
                <p className="mt-1 text-[10px] text-on-surface-variant">Chaque ligne conserve son seuil, sa confiance et ses preuves.</p>
              </div>
              <Link href="/signals" className="inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary px-3 text-xs font-semibold text-primary-foreground">
                Ouvrir la file <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </header>
            <div className="divide-y divide-outline-variant">
              {signalsQuery.isLoading ? (
                <div className="h-56 animate-pulse bg-surface-container-low" />
              ) : openSignals.length === 0 ? (
                <div className="flex min-h-40 items-center gap-3 px-6 py-8 text-sm text-on-surface-variant"><CheckCircle2 className="h-5 w-5 text-success" />Aucun signal ouvert.</div>
              ) : openSignals.slice(0, 4).map((signal) => (
                <Link key={signal.id} href={`/signals?selected=${signal.id}`} className="dashboard-alert-row group">
                  <span className={`dashboard-alert-row__severity ${signal.severity === "low" ? "bg-surface-container text-on-surface-variant" : ""}`}><ShieldAlert className="h-4 w-4" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="line-clamp-1 text-sm font-semibold text-on-surface">{signal.title}</span>
                    <span className="mt-1 line-clamp-1 text-[10px] text-on-surface-variant">{signal.explanation}</span>
                    <span className="mt-2 flex flex-wrap gap-2 text-[9px] text-on-surface-variant">
                      <strong className="text-error">{severityLabel(signal.severity)}</strong>
                      <span>{signal.mentionCount} mentions</span>
                      <span>{Math.round(signal.confidence * 100)}% confiance</span>
                      <span>{signal.evidenceIds.length} preuve{signal.evidenceIds.length > 1 ? "s" : ""}</span>
                    </span>
                  </span>
                  <span className="font-headline text-xl font-extrabold tabular-nums text-on-surface">{signal.priorityScore}<small className="ml-0.5 text-[9px] font-medium text-on-surface-variant">/100</small></span>
                  <ArrowRight className="h-4 w-4 text-on-surface-variant transition-transform group-hover:translate-x-0.5" />
                </Link>
              ))}
            </div>
          </article>

          <article className="cling-panel p-5 sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <div><h2 className="font-headline text-base font-bold text-on-surface">Moteurs de l’évolution</h2><p className="mt-1 text-[10px] text-on-surface-variant">Écart en points face à la période précédente.</p></div>
              <span className="rounded-full bg-surface-container px-2.5 py-1 text-[9px] font-semibold text-on-surface-variant">Base comparable</span>
            </div>
            <div className="mt-4 h-64" role="img" aria-label="Aspects responsables de l'évolution">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview?.topDrivers ?? []} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 8 }}>
                  <CartesianGrid horizontal={false} stroke="hsl(var(--outline-variant))" strokeDasharray="3 5" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: "hsl(var(--on-surface-variant))" }} />
                  <YAxis dataKey="aspect" type="category" width={112} axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: "hsl(var(--on-surface))" }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="deltaPoints" name="Écart" fill="hsl(var(--primary))" radius={[0, 7, 7, 0]} maxBarSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <article className="cling-panel p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div><h2 className="font-headline text-base font-bold text-on-surface">Actions à faire avancer</h2><p className="mt-1 text-[10px] text-on-surface-variant">Responsable, échéance et mesure d’impact restent visibles.</p></div>
              <Link href="/actions" className="text-xs font-semibold text-primary hover:underline">Voir les dossiers</Link>
            </div>
            <div className="mt-4 divide-y divide-outline-variant border-y border-outline-variant">
              {activeActions.slice(0, 3).map((action) => (
                <div key={action.id} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center sm:gap-5">
                  <div><p className="text-sm font-semibold text-on-surface">{action.title}</p><p className="mt-1 line-clamp-1 text-[10px] text-on-surface-variant">{action.expectedImpact}</p></div>
                  <span className="text-[10px] font-semibold text-on-surface-variant">{action.ownerName ?? "Non assignée"}</span>
                  <span className="rounded-full bg-action-container px-2.5 py-1 text-[9px] font-semibold text-action">{action.status === "in_progress" ? "En cours" : "À lancer"}</span>
                </div>
              ))}
            </div>
            {overview?.overdueActions ? <p className="mt-3 text-[10px] font-semibold text-error">{overview.overdueActions} action en retard demande une décision.</p> : null}
          </article>

          <article className="cling-panel p-5 sm:p-6">
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-action-container text-action"><Radio className="h-4 w-4" /></span><div><h2 className="font-headline text-base font-bold text-on-surface">Santé des sources</h2><p className="mt-1 text-[10px] text-on-surface-variant">Fraîcheur, réussite et couverture — sans masquer les lacunes.</p></div></div>
            <div className="mt-4 space-y-3">
              {(overview?.sourceHealth ?? []).map((source) => (
                <div key={source.source} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
                  <div>
                    <div className="flex items-center justify-between gap-3 text-[10px]"><strong className="capitalize text-on-surface">{source.source.replace("_", " ")}</strong><span className={source.status === "healthy" ? "text-success" : "text-warning"}>{source.status === "healthy" ? "Opérationnelle" : "Couverture partielle"}</span></div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-container-high"><div className="h-full rounded-full bg-primary" style={{ width: `${source.successRatePercent}%` }} /></div>
                  </div>
                  <span className="text-right text-[9px] tabular-nums text-on-surface-variant">{source.successRatePercent}%<br />{source.freshnessMinutes ?? "—"} min</span>
                </div>
              ))}
            </div>
            <Link href="/sources" className="mt-5 inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline">Ouvrir la console des sources <ArrowRight className="h-3.5 w-3.5" /></Link>
          </article>
        </section>

        <footer className="flex flex-col gap-2 border-t border-outline-variant pt-4 text-[10px] text-on-surface-variant sm:flex-row sm:items-center sm:justify-between">
          <span>Cohorte KPI : annotations valides, exploitables, pertinentes et sans contexte parent requis.</span>
          <span>{overview?.validAnnotations ?? 0} annotations valides / {overview?.collectedDocuments ?? 0} documents collectés</span>
        </footer>
      </div>
    </AppShell>
  );
}
