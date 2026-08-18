import { useMemo, useState } from "react";
import { useLocation } from "wouter";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowRight, Clock3, Database, Plus, Radar, Search, ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { V3DataState } from "@/components/v3/V3DataState";
import { V3MonitorComposer, type V3MonitorCreateValue } from "@/components/watch/V3MonitorComposer";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useToast } from "@/hooks/use-toast";
import { useV3Context, useV3Monitors, useV3Overview } from "@/hooks/useV3Data";
import { v3Api } from "@/lib/v3Api";
import type { V3Monitor } from "@shared/v3";

const OBJECTIVE_LABELS: Record<V3Monitor["objective"], string> = {
  customer_experience: "Expérience client", reputation: "Réputation", campaign: "Campagne", competition: "Concurrence", issue: "Sujet / risque",
};

function formatFreshness(value: string | null): string {
  if (!value) return "Collecte non lancée";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  return minutes < 60 ? `Il y a ${minutes} min` : `Il y a ${Math.round(minutes / 60)} h`;
}

export default function Watchlists() {
  const [location, setLocation] = useLocation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { organizationId, live } = useV3Context();
  const monitorsQuery = useV3Monitors();
  const overviewQuery = useV3Overview();
  const monitors = monitorsQuery.data ?? [];
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const filtered = useMemo(() => monitors.filter((monitor) => `${monitor.name} ${monitor.targetName} ${OBJECTIVE_LABELS[monitor.objective]}`.toLocaleLowerCase("fr").includes(query.toLocaleLowerCase("fr"))), [monitors, query]);
  const selected = filtered.find((monitor) => monitor.id === selectedId) ?? filtered[0] ?? null;
  const showCreate = location === "/watchlists/new";

  const createMutation = useMutation({
    mutationFn: async (value: V3MonitorCreateValue) => {
      if (live) return v3Api.createMonitor(organizationId, { ...value });
      const now = new Date().toISOString();
      return {
        id: `mon_${crypto.randomUUID()}`,
        organizationId,
        name: value.name,
        objective: value.objective,
        targetType: value.target_type,
        targetName: value.target_name,
        aliases: value.aliases,
        exclusions: value.exclusions,
        languages: value.languages,
        territories: value.territories,
        sources: value.sources,
        competitors: value.competitors,
        frequencyMinutes: value.frequency_minutes,
        maxMonthlyDocuments: value.max_monthly_documents,
        maxMonthlyCostDzd: value.max_monthly_cost_dzd,
        active: true,
        lastCollectedAt: null,
        coverageNote: "Première collecte en attente.",
        createdAt: now,
        updatedAt: now,
      } satisfies V3Monitor & { createdAt: string; updatedAt: string };
    },
    onSuccess: (monitor) => {
      queryClient.setQueryData<V3Monitor[]>(["/api/v3/monitors", { clientId: organizationId }], (current = []) => [monitor, ...current]);
      setSelectedId(monitor.id);
      setLocation("/watchlists");
      toast({ title: "Surveillance créée", description: "Le périmètre est enregistré. La première collecte peut maintenant démarrer." });
    },
    onError: (error: Error) => toast({ variant: "destructive", title: "Création impossible", description: error.message }),
  });

  if (monitorsQuery.isLoading || overviewQuery.isLoading || monitorsQuery.isError || overviewQuery.isError) {
    const loading = monitorsQuery.isLoading || overviewQuery.isLoading;
    return <AppShell><div className="mx-auto w-full max-w-[1580px] space-y-5 px-4 py-7 sm:px-6 lg:px-8"><PageHeader eyebrow="Synchronisation" title="Surveillances" description="Chargement des périmètres et de leur couverture." /><V3DataState loading={loading} onRetry={() => { void Promise.all([monitorsQuery.refetch(), overviewQuery.refetch()]); }} /></div></AppShell>;
  }

  return (
    <AppShell headerSearchPlaceholder="Rechercher une surveillance…" onSearch={setQuery}>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-5 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-7">
        <PageHeader eyebrow={`${monitors.filter((monitor) => monitor.active).length} actives`} tone="monitor" title="Surveillances" description="Chaque périmètre relie une cible, un objectif, des sources, des limites de coût et une couverture visible." actions={<Button onClick={() => setLocation("/watchlists/new")}><Plus className="mr-2 h-4 w-4" />Créer une surveillance</Button>} />

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-primary-container text-primary"><Radar className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Périmètres actifs</p><p className="dashboard-stat__value">{monitors.filter((item) => item.active).length}</p></div></article>
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-insight-container text-insight"><Database className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Sources configurées</p><p className="dashboard-stat__value">{new Set(monitors.flatMap((item) => item.sources)).size}</p></div></article>
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-action-container text-action"><ShieldCheck className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Couverture analytique</p><p className="dashboard-stat__value">{overviewQuery.data?.analyticalCoveragePercent ?? "—"}<span>%</span></p></div></article>
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-surface-container text-on-surface-variant"><Activity className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Documents / mois max.</p><p className="dashboard-stat__value">{Math.round(monitors.reduce((sum, item) => sum + item.maxMonthlyDocuments, 0) / 1_000)}<span> k</span></p></div></article>
        </section>

        <div className="grid min-h-[36rem] gap-5 xl:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.28fr)]">
          <section className="cling-panel overflow-hidden">
            <div className="border-b border-outline-variant p-4"><label className="relative block"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" /><input value={query} onChange={(event) => setQuery(event.target.value)} className="h-10 w-full rounded-full border border-transparent bg-surface-container pl-10 pr-4 text-xs focus:border-primary/30 focus:outline-none" placeholder="Cible, objectif ou source" /></label></div>
            <div className="divide-y divide-outline-variant">
              {filtered.map((monitor) => <button key={monitor.id} type="button" onClick={() => setSelectedId(monitor.id)} className={`flex w-full gap-3 px-5 py-4 text-left transition-colors ${selected?.id === monitor.id ? "bg-primary-container" : "hover:bg-surface-container-low"}`}><span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${monitor.active ? "bg-action-container text-action" : "bg-surface-container text-on-surface-variant"}`}><Radar className="h-4 w-4" /></span><span className="min-w-0 flex-1"><span className="line-clamp-1 text-sm font-semibold">{monitor.targetName}</span><span className="mt-1 block text-[10px] text-on-surface-variant">{OBJECTIVE_LABELS[monitor.objective]} · {monitor.sources.length} sources</span><span className="mt-2 flex items-center gap-1 text-[9px] text-on-surface-variant"><Clock3 className="h-3 w-3" />{formatFreshness(monitor.lastCollectedAt)}</span></span><ArrowRight className="mt-2 h-4 w-4 text-on-surface-variant" /></button>)}
              {!filtered.length ? <p className="px-5 py-12 text-center text-sm text-on-surface-variant">Aucune surveillance ne correspond à cette recherche.</p> : null}
            </div>
          </section>

          {selected ? <section className="cling-panel overflow-hidden"><header className="border-b border-outline-variant p-5 sm:p-6"><div className="flex flex-wrap gap-2 text-[9px] font-semibold"><span className="rounded-full bg-primary-container px-2.5 py-1 text-primary">{OBJECTIVE_LABELS[selected.objective]}</span><span className={`rounded-full px-2.5 py-1 ${selected.active ? "bg-action-container text-action" : "bg-surface-container text-on-surface-variant"}`}>{selected.active ? "En collecte" : "Suspendue"}</span></div><h2 className="mt-4 font-headline text-2xl font-bold">{selected.targetName}</h2><p className="mt-2 text-sm leading-6 text-on-surface-variant">{selected.name}</p></header><div className="grid gap-6 p-5 sm:p-6 lg:grid-cols-2"><div><h3 className="font-headline text-sm font-bold">Périmètre confirmé</h3><dl className="mt-3 divide-y divide-outline-variant text-xs"><div className="py-3"><dt className="text-[9px] font-semibold text-on-surface-variant">Alias</dt><dd className="mt-1">{selected.aliases.join(" · ") || "Aucun"}</dd></div><div className="py-3"><dt className="text-[9px] font-semibold text-on-surface-variant">Exclusions</dt><dd className="mt-1">{selected.exclusions.join(" · ") || "Aucune"}</dd></div><div className="py-3"><dt className="text-[9px] font-semibold text-on-surface-variant">Langues</dt><dd className="mt-1">{selected.languages.join(" · ")}</dd></div><div className="py-3"><dt className="text-[9px] font-semibold text-on-surface-variant">Territoires</dt><dd className="mt-1">{selected.territories.join(" · ")}</dd></div></dl></div><div><h3 className="font-headline text-sm font-bold">Collecte et limites</h3><div className="mt-3 space-y-3">{selected.sources.map((source) => <div key={source} className="flex items-center justify-between rounded-xl bg-surface-container-low px-3 py-3 text-xs"><span className="capitalize">{source.replace("_", " ")}</span><span className="text-[9px] font-semibold text-success">Configurée</span></div>)}</div><p className="mt-4 text-[10px] leading-5 text-on-surface-variant">Toutes les {selected.frequencyMinutes / 60} h · arrêt à {selected.maxMonthlyDocuments.toLocaleString("fr-FR")} documents ou {selected.maxMonthlyCostDzd.toLocaleString("fr-FR")} DA/mois.</p><p className="mt-3 rounded-xl bg-surface-container-low p-3 text-[9px] leading-4 text-on-surface-variant">{selected.coverageNote}</p></div></div></section> : <section className="cling-panel flex items-center justify-center p-8 text-sm text-on-surface-variant">Créez votre première surveillance.</section>}
        </div>
      </div>

      <Sheet open={showCreate} onOpenChange={(open) => setLocation(open ? "/watchlists/new" : "/watchlists")}><SheetContent side="right" className="w-full overflow-y-auto border-outline-variant bg-surface p-0 sm:max-w-[52rem]"><SheetHeader className="sr-only"><SheetTitle>Nouvelle surveillance</SheetTitle><SheetDescription>Cible, objectif et sources.</SheetDescription></SheetHeader><V3MonitorComposer isSubmitting={createMutation.isPending} onCancel={() => setLocation("/watchlists")} onSubmit={(value) => createMutation.mutate(value)} /></SheetContent></Sheet>
    </AppShell>
  );
}
