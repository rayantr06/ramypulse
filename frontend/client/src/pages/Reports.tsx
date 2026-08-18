import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  Download,
  FileBarChart2,
  FileClock,
  Mail,
  Plus,
  ShieldCheck,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { V3DataState } from "@/components/v3/V3DataState";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { useV3Context, useV3Reports } from "@/hooks/useV3Data";
import { v3Api } from "@/lib/v3Api";
import type { V3Report } from "@shared/v3";

const REPORT_LABELS: Record<V3Report["reportType"], string> = {
  daily: "Brief quotidien",
  weekly: "Synthèse hebdomadaire",
  crisis: "Rapport de crise",
  reputation: "Réputation",
  territory: "Territoire",
  product: "Produit",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}

export default function Reports() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { organizationId, live } = useV3Context();
  const reportsQuery = useV3Reports();
  const reports = reportsQuery.data ?? [];
  const [selectedType, setSelectedType] = useState<V3Report["reportType"]>("weekly");

  const createMutation = useMutation({
    mutationFn: async () => {
      const end = new Date();
      const start = new Date(end);
      start.setDate(start.getDate() - (selectedType === "daily" ? 1 : 7));
      const payload = {
        title: `${REPORT_LABELS[selectedType]} · ${formatDate(end.toISOString())}`,
        report_type: selectedType,
        period_start: start.toISOString(),
        period_end: end.toISOString(),
      };
      if (live) return v3Api.createReport(organizationId, payload);
      return {
        id: crypto.randomUUID(), title: payload.title, reportType: selectedType,
        periodStart: payload.period_start, periodEnd: payload.period_end,
        status: "draft" as const, generatedAt: null, downloadUrl: null, evidenceCount: 0,
      };
    },
    onSuccess: (created) => {
      queryClient.setQueryData<V3Report[]>(["/api/v3/reports", { clientId: organizationId }], (current = []) => [created, ...current]);
      toast({ title: "Brouillon créé", description: "Le rapport doit encore être vérifié avant diffusion." });
    },
    onError: (error: Error) => toast({ variant: "destructive", title: "Création impossible", description: error.message }),
  });

  if (reportsQuery.isLoading || reportsQuery.isError) {
    return <AppShell><div className="mx-auto w-full max-w-[1580px] space-y-5 px-4 py-7 sm:px-6 lg:px-8"><PageHeader eyebrow="Synchronisation" title="Rapports" description="Chargement de la bibliothèque de rapports." /><V3DataState loading={reportsQuery.isLoading} onRetry={() => { void reportsQuery.refetch(); }} /></div></AppShell>;
  }

  return (
    <AppShell>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-5 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-7">
        <PageHeader
          eyebrow="Exports vérifiables"
          tone="insight"
          title="Rapports"
          description="Créez une photographie d’une période sans perdre les métriques, la couverture et les preuves qui la soutiennent."
        />

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
          <article className="cling-panel overflow-hidden">
            <header className="flex flex-wrap items-start justify-between gap-3 border-b border-outline-variant px-5 py-4 sm:px-6"><div><h2 className="font-headline text-base font-bold">Bibliothèque</h2><p className="mt-1 text-[10px] text-on-surface-variant">Brouillons, rapports prêts et provenance des données.</p></div><span className="rounded-full bg-surface-container px-2.5 py-1 text-[9px] font-semibold text-on-surface-variant">{reports.length} rapports</span></header>
            <div className="divide-y divide-outline-variant">
              {reports.map((report) => (
                <article key={report.id} className="grid gap-3 px-5 py-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center sm:px-6">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-insight-container text-insight"><FileBarChart2 className="h-4 w-4" /></span>
                  <div><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-on-surface">{report.title}</h3><span className={`rounded-full px-2 py-1 text-[8px] font-semibold ${report.status === "ready" ? "bg-action-container text-action" : "bg-surface-container text-on-surface-variant"}`}>{report.status === "ready" ? "Prêt" : "Brouillon"}</span></div><p className="mt-1 text-[10px] text-on-surface-variant">{REPORT_LABELS[report.reportType]} · {formatDate(report.periodStart)} — {formatDate(report.periodEnd)} · {report.evidenceCount} preuves</p></div>
                  <div className="flex gap-2"><Button size="sm" variant="outline" disabled={!report.downloadUrl} onClick={() => report.downloadUrl && window.open(report.downloadUrl, "_blank")}><Download className="mr-1.5 h-3.5 w-3.5" />PDF</Button><Button size="sm" variant="ghost" disabled={report.status !== "ready"} onClick={() => toast({ title: "Diffusion non activée", description: "L’envoi email nécessite une confirmation et un fournisseur configuré." })}><Mail className="h-3.5 w-3.5" /></Button></div>
                </article>
              ))}
            </div>
          </article>

          <aside className="cling-panel p-5 sm:p-6">
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-container text-primary"><FileClock className="h-4 w-4" /></span><div><h2 className="font-headline text-base font-bold">Nouveau rapport</h2><p className="mt-1 text-[10px] text-on-surface-variant">Choisissez le cadre, puis contrôlez le brouillon.</p></div></div>
            <div className="mt-5 grid grid-cols-2 gap-2">
              {(["daily", "weekly", "crisis", "reputation", "territory", "product"] as const).map((type) => (
                <button key={type} type="button" onClick={() => setSelectedType(type)} className={`min-h-12 rounded-xl border px-3 py-2 text-left text-[10px] font-semibold transition-colors ${selectedType === type ? "border-primary bg-primary-container text-primary" : "border-outline-variant bg-surface text-on-surface-variant hover:bg-surface-container-low"}`}>{REPORT_LABELS[type]}</button>
              ))}
            </div>
            <div className="mt-4 rounded-xl bg-surface-container-low p-4 text-[10px] leading-5 text-on-surface-variant"><div className="flex items-center gap-2 font-semibold text-on-surface"><ShieldCheck className="h-4 w-4 text-action" />Contenu contrôlable</div><p className="mt-1">Le rapport inclut la période, les formules, la couverture et les identifiants de preuve. Les métriques absentes restent absentes.</p></div>
            <Button className="mt-4 w-full justify-between" disabled={createMutation.isPending} onClick={() => createMutation.mutate()}><Plus className="h-4 w-4" />Créer le brouillon<span className="flex items-center gap-1 text-[9px] opacity-80"><CalendarDays className="h-3 w-3" />{REPORT_LABELS[selectedType]}</span></Button>
            <p className="mt-3 text-[9px] text-on-surface-variant">L’export et l’email ne sont disponibles qu’après génération et validation.</p>
          </aside>
        </section>
      </div>
    </AppShell>
  );
}
