import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  CircleSlash2,
  Clock3,
  ExternalLink,
  FileCheck2,
  Filter,
  Gauge,
  MapPinned,
  MessageSquareText,
  ShieldAlert,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { V3DataState } from "@/components/v3/V3DataState";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useV3Context, useV3Mentions, useV3Signals } from "@/hooks/useV3Data";
import { v3Api } from "@/lib/v3Api";
import type { V3Signal, V3SignalSeverity, V3SignalStatus } from "@shared/v3";

const SEVERITY_LABELS: Record<V3SignalSeverity, string> = {
  critical: "Critique",
  high: "Élevée",
  medium: "Moyenne",
  low: "Faible",
};

const STATUS_LABELS: Record<V3SignalStatus, string> = {
  new: "Nouveau",
  investigating: "En vérification",
  confirmed: "Confirmé",
  dismissed: "Faux positif",
  converted: "Dossier ouvert",
};

const caseSchema = z.object({
  ownerName: z.string().trim().min(2, "Indiquez un responsable."),
  dueDate: z.string().min(1, "Choisissez une échéance."),
});
type CaseFormValues = z.infer<typeof caseSchema>;

function defaultDueDate(): string {
  const value = new Date();
  value.setDate(value.getDate() + 3);
  return value.toISOString().slice(0, 10);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function selectedSignalFromHash(): string | null {
  const query = window.location.hash.split("?", 2)[1] ?? "";
  return new URLSearchParams(query).get("selected");
}

export default function Signals() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { organizationId, live } = useV3Context();
  const signalsQuery = useV3Signals();
  const mentionsQuery = useV3Mentions();
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("active");
  const signals = useMemo(() => (signalsQuery.data ?? []).filter((signal) => {
    const severityMatches = severityFilter === "all" || signal.severity === severityFilter;
    const statusMatches = statusFilter === "all"
      || (statusFilter === "active" && !["dismissed", "converted"].includes(signal.status))
      || signal.status === statusFilter;
    return severityMatches && statusMatches;
  }), [severityFilter, signalsQuery.data, statusFilter]);
  const [selectedId, setSelectedId] = useState<string | null>(selectedSignalFromHash);
  const selected = signals.find((signal) => signal.id === selectedId) ?? signals[0] ?? null;
  const evidence = (mentionsQuery.data ?? []).filter((mention) => selected?.evidenceIds.includes(mention.id));
  const [caseDialogSignal, setCaseDialogSignal] = useState<V3Signal | null>(null);
  const caseForm = useForm<CaseFormValues>({
    resolver: zodResolver(caseSchema),
    defaultValues: { ownerName: "", dueDate: defaultDueDate() },
  });

  function updateDemoSignal(signalId: string, status: V3SignalStatus) {
    queryClient.setQueryData<V3Signal[]>(
      ["/api/v3/signals", { clientId: organizationId }],
      (current = []) => current.map((signal) => signal.id === signalId ? { ...signal, status } : signal),
    );
  }

  const transitionMutation = useMutation({
    mutationFn: ({ signal, status, reason }: { signal: V3Signal; status: V3SignalStatus; reason: string }) =>
      live ? v3Api.transitionSignal(organizationId, signal.id, status, reason) : Promise.resolve({ ...signal, status }),
    onSuccess: (updated) => {
      updateDemoSignal(updated.id, updated.status);
      toast({ title: "Signal mis à jour", description: STATUS_LABELS[updated.status] });
    },
    onError: (error: Error) => toast({ variant: "destructive", title: "Mise à jour impossible", description: error.message }),
  });

  const caseMutation = useMutation({
    mutationFn: ({ signal, values }: { signal: V3Signal; values: CaseFormValues }) => live
      ? v3Api.createCase(organizationId, {
          signal_id: signal.id,
          title: signal.title,
          priority: signal.severity,
          owner_name: values.ownerName,
          due_at: new Date(`${values.dueDate}T17:00:00`).toISOString(),
          expected_outcome: "Confirmer la cause, assigner une action et mesurer l’évolution.",
        })
      : Promise.resolve({ id: `case_${signal.id}` }),
    onSuccess: (_, variables) => {
      const signal = variables.signal;
      updateDemoSignal(signal.id, "converted");
      setCaseDialogSignal(null);
      caseForm.reset({ ownerName: "", dueDate: defaultDueDate() });
      toast({ title: "Dossier créé", description: "Le signal est maintenant suivi dans Actions." });
    },
    onError: (error: Error) => toast({ variant: "destructive", title: "Création impossible", description: error.message }),
  });

  if (signalsQuery.isLoading || mentionsQuery.isLoading || signalsQuery.isError || mentionsQuery.isError) {
    const loading = signalsQuery.isLoading || mentionsQuery.isLoading;
    return <AppShell><div className="mx-auto w-full max-w-[1580px] space-y-5 px-4 py-7 sm:px-6 lg:px-8"><PageHeader eyebrow="Synchronisation" title="Signaux" description="Chargement de la file et des preuves reliées." /><V3DataState loading={loading} onRetry={() => { void Promise.all([signalsQuery.refetch(), mentionsQuery.refetch()]); }} /></div></AppShell>;
  }

  return (
    <AppShell>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-5 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-7">
        <PageHeader
          eyebrow={`${signals.length} dans la file`}
          tone="risk"
          title="Signaux"
          description="Vérifiez les changements détectés, inspectez les preuves puis confirmez, rejetez ou ouvrez un dossier."
          actions={<div className="flex gap-2"><Select value={severityFilter} onValueChange={setSeverityFilter}><SelectTrigger className="h-9 w-36 rounded-full bg-surface"><Filter className="mr-1 h-3.5 w-3.5" /><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Toutes gravités</SelectItem><SelectItem value="high">Élevée</SelectItem><SelectItem value="medium">Moyenne</SelectItem><SelectItem value="low">Faible</SelectItem></SelectContent></Select><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="h-9 w-40 rounded-full bg-surface"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="active">À traiter</SelectItem><SelectItem value="all">Tous les états</SelectItem><SelectItem value="confirmed">Confirmés</SelectItem><SelectItem value="dismissed">Faux positifs</SelectItem><SelectItem value="converted">Dossiers ouverts</SelectItem></SelectContent></Select></div>}
        />

        <div className="grid min-h-[38rem] gap-5 xl:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.28fr)]">
          <section className="cling-panel overflow-hidden" aria-label="File des signaux">
            <header className="border-b border-outline-variant px-5 py-4"><h2 className="font-headline text-base font-bold">File opérationnelle</h2><p className="mt-1 text-[10px] text-on-surface-variant">Triée par priorité déterministe.</p></header>
            <div className="divide-y divide-outline-variant">
              {signals.map((signal) => (
                <button key={signal.id} type="button" onClick={() => setSelectedId(signal.id)} className={`flex w-full gap-3 px-5 py-4 text-left transition-colors ${selected?.id === signal.id ? "bg-primary-container" : "hover:bg-surface-container-low"}`}>
                  <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${signal.severity === "high" || signal.severity === "critical" ? "bg-error-container text-error" : "bg-surface-container text-on-surface-variant"}`}><ShieldAlert className="h-4 w-4" /></span>
                  <span className="min-w-0 flex-1"><span className="line-clamp-2 text-sm font-semibold leading-5 text-on-surface">{signal.title}</span><span className="mt-2 flex flex-wrap gap-2 text-[9px] text-on-surface-variant"><strong className="text-error">{SEVERITY_LABELS[signal.severity]}</strong><span>{signal.mentionCount} mentions</span><span>{STATUS_LABELS[signal.status]}</span></span></span>
                  <span className="font-headline text-lg font-extrabold tabular-nums">{signal.priorityScore}</span>
                  <ChevronRight className="mt-1 h-4 w-4 text-on-surface-variant" />
                </button>
              ))}
              {!signals.length ? <p className="px-5 py-12 text-center text-sm text-on-surface-variant">Aucun signal ne correspond à ces filtres.</p> : null}
            </div>
          </section>

          {selected ? (
            <section className="cling-panel overflow-hidden" aria-label="Détail du signal">
              <div className="border-b border-outline-variant p-5 sm:p-6">
                <div className="flex flex-wrap items-center gap-2 text-[9px] font-semibold"><span className="rounded-full bg-error-container px-2.5 py-1 text-error">{SEVERITY_LABELS[selected.severity]}</span><span className="rounded-full bg-surface-container px-2.5 py-1 text-on-surface-variant">{STATUS_LABELS[selected.status]}</span><span className="text-on-surface-variant">Détecté le {formatDate(selected.detectedAt)}</span></div>
                <h2 className="mt-4 max-w-3xl font-headline text-2xl font-bold leading-tight text-on-surface">{selected.title}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant">{selected.summary}</p>
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-xl bg-surface-container-low p-3"><MessageSquareText className="h-4 w-4 text-primary" /><strong className="mt-2 block font-headline text-lg">{selected.mentionCount}</strong><span className="text-[9px] text-on-surface-variant">mentions</span></div>
                  <div className="rounded-xl bg-surface-container-low p-3"><Gauge className="h-4 w-4 text-insight" /><strong className="mt-2 block font-headline text-lg">{Math.round(selected.confidence * 100)}%</strong><span className="text-[9px] text-on-surface-variant">confiance</span></div>
                  <div className="rounded-xl bg-surface-container-low p-3"><Clock3 className="h-4 w-4 text-action" /><strong className="mt-2 block font-headline text-lg">{selected.velocityPercent == null ? "—" : `+${selected.velocityPercent}%`}</strong><span className="text-[9px] text-on-surface-variant">vitesse</span></div>
                  <div className="rounded-xl bg-surface-container-low p-3"><MapPinned className="h-4 w-4 text-monitor" /><strong className="mt-2 block line-clamp-1 text-sm">{selected.territory ?? "Non localisé"}</strong><span className="text-[9px] text-on-surface-variant">territoire</span></div>
                </div>
              </div>

              <div className="grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.68fr)]">
                <div>
                  <h3 className="font-headline text-sm font-bold text-on-surface">Pourquoi ce signal existe</h3>
                  <p className="mt-2 rounded-xl bg-insight-container p-4 text-xs leading-5 text-on-insight-container">{selected.explanation}</p>
                  <h3 className="mt-6 font-headline text-sm font-bold text-on-surface">Preuves reliées</h3>
                  <div className="mt-3 space-y-3">
                    {evidence.map((mention) => (
                      <article key={mention.id} className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                        <p dir="auto" className="text-sm leading-6 text-on-surface">“{mention.text}”</p>
                        <div className="mt-3 flex flex-wrap items-center gap-2 text-[9px] text-on-surface-variant"><span className="capitalize">{mention.source.replace("_", " ")}</span><span>{mention.language}</span><span>{mention.territory}</span><span>{formatDate(mention.publishedAt)}</span>{mention.sourceUrl ? <a href={mention.sourceUrl} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 font-semibold text-primary">Original <ExternalLink className="h-3 w-3" /></a> : null}</div>
                      </article>
                    ))}
                    {!evidence.length ? <p className="text-xs text-on-surface-variant">Les preuves ne sont pas disponibles dans cet environnement.</p> : null}
                  </div>
                </div>
                <aside>
                  <h3 className="font-headline text-sm font-bold text-on-surface">Calcul de priorité · {selected.priorityScore}/100</h3>
                  <div className="mt-3 space-y-3">
                    {selected.priorityFactors.map((factor) => (
                      <div key={factor.label}><div className="flex justify-between text-[9px]"><span className="font-semibold text-on-surface">{factor.label}</span><span className="text-on-surface-variant">{factor.value} · poids {Math.round(factor.weight * 100)}%</span></div><div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-container-high"><div className="h-full rounded-full bg-primary" style={{ width: `${factor.value}%` }} /></div></div>
                    ))}
                  </div>
                  <div className="mt-6 space-y-2 border-t border-outline-variant pt-5">
                    <Button className="w-full justify-between" disabled={transitionMutation.isPending || selected.status === "confirmed" || evidence.length === 0} onClick={() => transitionMutation.mutate({ signal: selected, status: "confirmed", reason: "Preuves vérifiées par un utilisateur" })}><CheckCircle2 className="h-4 w-4" />Confirmer le signal<ArrowRight className="h-4 w-4" /></Button>
                    <Button variant="outline" className="w-full justify-between" disabled={caseMutation.isPending || selected.status !== "confirmed" || evidence.length === 0} onClick={() => setCaseDialogSignal(selected)}><FileCheck2 className="h-4 w-4" />Ouvrir un dossier<ArrowRight className="h-4 w-4" /></Button>
                    <Button variant="ghost" className="w-full justify-start text-on-surface-variant" disabled={transitionMutation.isPending || selected.status === "dismissed"} onClick={() => transitionMutation.mutate({ signal: selected, status: "dismissed", reason: "Faux positif confirmé par un utilisateur" })}><CircleSlash2 className="mr-2 h-4 w-4" />Marquer comme faux positif</Button>
                  </div>
                  <p className="mt-4 text-[9px] leading-4 text-on-surface-variant">Aucune action externe n’est exécutée. Chaque changement d’état est journalisé.</p>
                </aside>
              </div>
            </section>
          ) : (
            <section className="cling-panel flex items-center justify-center p-8 text-center text-sm text-on-surface-variant">Sélectionnez un signal pour afficher ses preuves.</section>
          )}
        </div>
      </div>
      <Dialog open={Boolean(caseDialogSignal)} onOpenChange={(open) => !open && setCaseDialogSignal(null)}>
        <DialogContent className="rounded-2xl border-outline-variant bg-surface sm:max-w-md">
          <DialogHeader><DialogTitle>Ouvrir un dossier</DialogTitle><DialogDescription>Un dossier exige un responsable, une échéance et des preuves déjà confirmées.</DialogDescription></DialogHeader>
          <Form {...caseForm}>
            <form className="space-y-4" onSubmit={caseForm.handleSubmit((values) => caseDialogSignal && caseMutation.mutate({ signal: caseDialogSignal, values }))}>
              <FormField control={caseForm.control} name="ownerName" render={({ field }) => <FormItem><FormLabel>Responsable</FormLabel><FormControl><Input {...field} placeholder="Nom du responsable" /></FormControl><FormMessage /></FormItem>} />
              <FormField control={caseForm.control} name="dueDate" render={({ field }) => <FormItem><FormLabel>Échéance</FormLabel><FormControl><Input {...field} type="date" /></FormControl><FormMessage /></FormItem>} />
              <Button className="w-full" type="submit" disabled={caseMutation.isPending}>{caseMutation.isPending ? "Ouverture…" : "Confirmer le dossier"}</Button>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
