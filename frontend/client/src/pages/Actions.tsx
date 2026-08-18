import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Bot,
  CalendarClock,
  CheckCircle2,
  CircleDashed,
  Clock3,
  FileCheck2,
  Link2,
  ListChecks,
  LockKeyhole,
  MessageSquareText,
  UserRound,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { V3DataState } from "@/components/v3/V3DataState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { useV3Actions, useV3Cases, useV3Context, useV3Signals } from "@/hooks/useV3Data";
import { v3Api } from "@/lib/v3Api";
import type { V3ActionItem, V3AgentDraft, V3CaseStatus } from "@shared/v3";

const STATUS_LABELS: Record<V3CaseStatus, string> = {
  open: "Ouvert",
  in_progress: "En cours",
  blocked: "Bloqué",
  resolved: "Résolu",
  closed: "Clôturé",
};

function formatDate(value: string | null): string {
  if (!value) return "Sans échéance";
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

export default function Actions() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { organizationId, live } = useV3Context();
  const casesQuery = useV3Cases();
  const actionsQuery = useV3Actions();
  const signalsQuery = useV3Signals();
  const cases = casesQuery.data ?? [];
  const actions = actionsQuery.data ?? [];
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const selectedCase = cases.find((item) => item.id === selectedCaseId) ?? cases[0] ?? null;
  const selectedActions = actions.filter((action) => action.caseId === selectedCase?.id);
  const sourceSignal = (signalsQuery.data ?? []).find((signal) => signal.id === selectedCase?.signalId);
  const [draft, setDraft] = useState<V3AgentDraft | null>(null);
  const [resultValues, setResultValues] = useState<Record<string, string>>({});

  const counts = useMemo(() => ({
    active: cases.filter((item) => !["resolved", "closed"].includes(item.status)).length,
    blocked: cases.filter((item) => item.status === "blocked").length,
    overdue: cases.reduce((total, item) => total + item.overdueActionCount, 0),
  }), [cases]);

  function updateDemoAction(actionId: string, status: V3CaseStatus, resultValue?: number) {
    queryClient.setQueryData<V3ActionItem[]>(
      ["/api/v3/actions", { clientId: organizationId }],
      (current = []) => current.map((action) => action.id === actionId ? { ...action, status, ...(resultValue == null ? {} : { resultValue }) } : action),
    );
  }

  const actionMutation = useMutation({
    mutationFn: ({ action, status, resultValue }: { action: V3ActionItem; status: V3CaseStatus; resultValue?: number }) => live
      ? v3Api.transitionAction(organizationId, action.id, status, `Statut ${status} confirmé dans LIDAL Pulse`, resultValue)
      : Promise.resolve({ ...action, status, ...(resultValue == null ? {} : { resultValue }) }),
    onSuccess: (action) => {
      updateDemoAction(action.id, action.status, action.resultValue ?? undefined);
      toast({ title: "Action mise à jour", description: STATUS_LABELS[action.status] });
    },
    onError: (error: Error) => toast({ variant: "destructive", title: "Mise à jour impossible", description: error.message }),
  });

  const draftMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCase) throw new Error("Sélectionnez un dossier.");
      const references: V3AgentDraft["citations"] = [
        ...(sourceSignal?.observationIds ?? []).map((id) => ({ kind: "observation" as const, id, label: `Observation ${id}` })),
        ...(sourceSignal?.evidenceIds ?? []).map((id) => ({ kind: "mention" as const, id, label: `Mention ${id}` })),
        ...selectedActions.filter((action) => action.metricId).map((action) => ({ kind: "metric" as const, id: action.metricId!, label: `Métrique ${action.metricId}` })),
      ].filter((reference, index, all) => all.findIndex((item) => item.kind === reference.kind && item.id === reference.id) === index);
      if (!references.length) throw new Error("Aucune preuve ou métrique vérifiable n’est reliée à ce dossier.");
      if (live) return v3Api.agentDraft(organizationId, {
        draft_type: "action_plan",
        references,
        instruction: "Préparer un plan d’action interne, sans envoyer ni modifier aucun objet.",
      });
      return {
        id: "draft_demo_action",
        draftType: "action_plan" as const,
        title: "Plan d’action à valider",
        content: "1. Vérifier l’échantillon de conversations. 2. Identifier le point de blocage dominant. 3. Tester une correction limitée. 4. Comparer le taux négatif après sept jours. Ce brouillon ne déclenche aucune action externe.",
        citations: references,
        generatedAt: new Date().toISOString(),
        model: "démo contrôlée",
        latencyMs: 0,
        estimatedCostUsd: 0,
      };
    },
    onSuccess: setDraft,
    onError: (error: Error) => toast({ variant: "destructive", title: "Brouillon impossible", description: error.message }),
  });

  if (casesQuery.isLoading || actionsQuery.isLoading || signalsQuery.isLoading || casesQuery.isError || actionsQuery.isError || signalsQuery.isError) {
    const loading = casesQuery.isLoading || actionsQuery.isLoading || signalsQuery.isLoading;
    return <AppShell><div className="mx-auto w-full max-w-[1580px] space-y-5 px-4 py-7 sm:px-6 lg:px-8"><PageHeader eyebrow="Synchronisation" title="Actions" description="Chargement des dossiers et de leur historique." /><V3DataState loading={loading} onRetry={() => { void Promise.all([casesQuery.refetch(), actionsQuery.refetch(), signalsQuery.refetch()]); }} /></div></AppShell>;
  }

  return (
    <AppShell>
      <div className="page-enter mx-auto w-full max-w-[1580px] space-y-5 px-4 pb-24 pt-5 sm:px-6 lg:px-8 lg:py-7">
        <PageHeader
          eyebrow="Validation humaine"
          tone="action"
          title="Actions"
          description="Transformez un signal confirmé en dossier assigné, suivez les mesures décidées et comparez l’impact avant/après."
        />

        <section className="grid grid-cols-3 gap-3" aria-label="Résumé des dossiers">
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-action-container text-action"><FileCheck2 className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Dossiers actifs</p><p className="dashboard-stat__value">{counts.active}</p></div></article>
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-error-container text-error"><Clock3 className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Actions en retard</p><p className="dashboard-stat__value">{counts.overdue}</p></div></article>
          <article className="dashboard-stat"><div className="dashboard-stat__icon bg-surface-container text-on-surface-variant"><CircleDashed className="h-4 w-4" /></div><div><p className="dashboard-stat__label">Dossiers bloqués</p><p className="dashboard-stat__value">{counts.blocked}</p></div></article>
        </section>

        <div className="grid min-h-[38rem] gap-5 xl:grid-cols-[minmax(19rem,0.65fr)_minmax(0,1.35fr)]">
          <section className="cling-panel overflow-hidden" aria-label="Liste des dossiers">
            <header className="border-b border-outline-variant px-5 py-4"><h2 className="font-headline text-base font-bold">Dossiers</h2><p className="mt-1 text-[10px] text-on-surface-variant">Un responsable, un état et un historique.</p></header>
            <div className="divide-y divide-outline-variant">
              {cases.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedCaseId(item.id)} className={`w-full px-5 py-4 text-left transition-colors ${selectedCase?.id === item.id ? "bg-action-container" : "hover:bg-surface-container-low"}`}>
                  <div className="flex items-start justify-between gap-3"><p className="text-sm font-semibold leading-5 text-on-surface">{item.title}</p><span className="rounded-full bg-surface px-2 py-1 text-[9px] font-semibold text-on-surface-variant">{STATUS_LABELS[item.status]}</span></div>
                  <div className="mt-3 flex flex-wrap gap-3 text-[9px] text-on-surface-variant"><span className="flex items-center gap-1"><UserRound className="h-3 w-3" />{item.ownerName ?? "Non assigné"}</span><span className="flex items-center gap-1"><CalendarClock className="h-3 w-3" />{formatDate(item.dueAt)}</span><span>{item.actionCount} action{item.actionCount > 1 ? "s" : ""}</span></div>
                </button>
              ))}
              {!cases.length ? <p className="px-5 py-12 text-center text-sm text-on-surface-variant">Aucun dossier. Confirmez un signal pour commencer.</p> : null}
            </div>
          </section>

          {selectedCase ? (
            <section className="cling-panel overflow-hidden">
              <header className="border-b border-outline-variant p-5 sm:p-6">
                <div className="flex flex-wrap items-center gap-2 text-[9px] font-semibold"><span className="rounded-full bg-action-container px-2.5 py-1 text-action">{STATUS_LABELS[selectedCase.status]}</span><span className="rounded-full bg-error-container px-2.5 py-1 text-error">Priorité {selectedCase.priority}</span><span className="text-on-surface-variant">Ouvert le {formatDate(selectedCase.openedAt)}</span></div>
                <h2 className="mt-4 font-headline text-2xl font-bold text-on-surface">{selectedCase.title}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">{selectedCase.expectedOutcome}</p>
                <div className="mt-4 flex flex-wrap gap-4 text-[10px] text-on-surface-variant"><span className="flex items-center gap-1.5"><UserRound className="h-3.5 w-3.5" />{selectedCase.ownerName ?? "À assigner"}</span><span className="flex items-center gap-1.5"><CalendarClock className="h-3.5 w-3.5" />Échéance {formatDate(selectedCase.dueAt)}</span>{sourceSignal ? <span className="flex items-center gap-1.5"><Link2 className="h-3.5 w-3.5" />Signal {sourceSignal.priorityScore}/100 · {sourceSignal.evidenceIds.length} preuves</span> : null}</div>
              </header>

              <div className="grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_minmax(19rem,0.72fr)]">
                <div>
                  <div className="flex items-center justify-between"><h3 className="font-headline text-sm font-bold">Plan d’exécution</h3><span className="text-[9px] text-on-surface-variant">{selectedActions.filter((item) => item.status === "resolved").length}/{selectedActions.length} terminées</span></div>
                  <div className="mt-3 divide-y divide-outline-variant border-y border-outline-variant">
                    {selectedActions.map((action) => {
                      const resultInput = resultValues[action.id] ?? "";
                      const canResolve = resultInput.trim() !== "" && Number.isFinite(Number(resultInput));
                      return (
                      <article key={action.id} className="py-4">
                        <div className="flex gap-3"><span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${action.status === "resolved" ? "bg-action-container text-action" : "bg-surface-container text-on-surface-variant"}`}>{action.status === "resolved" ? <CheckCircle2 className="h-4 w-4" /> : <ListChecks className="h-4 w-4" />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-2"><p className="text-sm font-semibold text-on-surface">{action.title}</p><span className="rounded-full bg-surface-container px-2 py-1 text-[9px] font-semibold text-on-surface-variant">{STATUS_LABELS[action.status]}</span></div><p className="mt-1 text-[10px] leading-4 text-on-surface-variant">{action.description}</p><div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-[9px] text-on-surface-variant">{action.ownerName ?? "Non assignée"} · {formatDate(action.dueAt)}</span>{action.status === "open" ? <Button size="sm" variant="outline" disabled={actionMutation.isPending} onClick={() => actionMutation.mutate({ action, status: "in_progress" })}>Démarrer</Button> : null}{action.status === "in_progress" ? <><Input aria-label={`Résultat mesuré pour ${action.title}`} className="h-8 w-28" type="number" step="any" value={resultInput} onChange={(event) => setResultValues((current) => ({ ...current, [action.id]: event.target.value }))} placeholder="Résultat" /><Button size="sm" disabled={actionMutation.isPending || !canResolve} onClick={() => actionMutation.mutate({ action, status: "resolved", resultValue: Number(resultInput) })}>Marquer résolue</Button></> : null}</div>{action.metricId ? <div className="mt-3 rounded-lg bg-surface-container-low px-3 py-2 text-[9px] text-on-surface-variant">Impact suivi : <strong className="text-on-surface">{action.metricId}</strong> · référence {action.baselineValue ?? "—"} · résultat {action.resultValue ?? "à mesurer"}</div> : null}</div></div>
                      </article>
                    ); })}
                  </div>
                </div>

                <aside className="rounded-2xl bg-insight-container p-5">
                  <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface text-insight"><Bot className="h-4 w-4" /></span><div><h3 className="font-headline text-sm font-bold text-on-surface">Agent LIDAL</h3><p className="mt-0.5 text-[9px] text-on-surface-variant">Analyse et brouillons uniquement</p></div></div>
                  <p className="mt-4 text-xs leading-5 text-on-insight-container">Préparez un plan relié au dossier, au signal et aux actions. Rien n’est assigné, envoyé ou publié sans votre confirmation.</p>
                  <Button className="mt-4 w-full justify-between" disabled={draftMutation.isPending} onClick={() => draftMutation.mutate()}><MessageSquareText className="h-4 w-4" />{draftMutation.isPending ? "Préparation…" : "Préparer un plan"}<ArrowRight className="h-4 w-4" /></Button>
                  {draft ? <div className="mt-4 rounded-xl bg-surface p-4"><div className="flex items-center gap-2 text-[9px] font-semibold text-action"><LockKeyhole className="h-3.5 w-3.5" />Brouillon · validation requise</div><h4 className="mt-2 text-sm font-semibold text-on-surface">{draft.title}</h4><p className="mt-2 text-[10px] leading-5 text-on-surface-variant">{draft.content}</p><div className="mt-3 flex flex-wrap gap-1.5">{draft.citations.map((citation) => <span key={citation.id} className="rounded-full bg-surface-container px-2 py-1 text-[8px] font-semibold text-on-surface-variant">{citation.id}</span>)}</div></div> : null}
                </aside>
              </div>
            </section>
          ) : <section className="cling-panel flex items-center justify-center p-8 text-sm text-on-surface-variant">Sélectionnez un dossier.</section>}
        </div>
      </div>
    </AppShell>
  );
}
