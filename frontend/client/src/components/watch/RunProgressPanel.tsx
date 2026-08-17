import { useLocation } from "wouter";

import { Button } from "@/components/ui/button";
import { setStoredOnboardingRun } from "@/lib/onboardingRunState";
import { setStoredTenantId } from "@/lib/tenantContext";

const DEMO_TENANT_ID =
  ((import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_SAFE_EXPO_CLIENT_ID as string | undefined) || "ramy-demo";

const STAGES = [
  { key: "collecting", label: "Collecte des sources" },
  { key: "normalizing", label: "Normalisation" },
  { key: "indexing", label: "Indexation et artefacts" },
  { key: "finished", label: "Run termine" },
] as const;

interface WatchRunStep {
  step_key: string;
  stage?: string | null;
  collector_key?: string | null;
  status: string;
  records_seen: number;
  error_message?: string | null;
}

interface WatchRunPayload {
  run_id: string;
  client_id: string;
  status: string;
  stage: string;
  records_collected: number;
  steps?: Record<string, WatchRunStep>;
}

interface RunProgressPanelProps {
  run?: WatchRunPayload | null;
  isLoading?: boolean;
  showNoDataState?: boolean;
}

function getStageIndex(stageKey: string): number {
  return STAGES.findIndex((stage) => stage.key === stageKey);
}

function getFailedStageIndex(run: WatchRunPayload | null | undefined): number {
  if (!run) {
    return -1;
  }

  const failedStep = Object.values(run.steps || {}).find((step) => step.status === "error");
  if (failedStep?.stage) {
    return getStageIndex(failedStep.stage);
  }

  if (run.status === "error") {
    return getStageIndex(run.stage);
  }

  return -1;
}

function resolveStageState(run: WatchRunPayload | null | undefined, stageKey: string) {
  if (!run) return "pending";
  const stageIndex = getStageIndex(stageKey);
  const failedStageIndex = getFailedStageIndex(run);
  if (failedStageIndex >= 0) {
    if (stageIndex > failedStageIndex) {
      return "pending";
    }
    if (stageIndex === failedStageIndex) {
      return "error";
    }
  }
  if (run.stage === stageKey) return run.status === "error" ? "error" : "running";
  const stageSteps = Object.values(run.steps || {}).filter((step) => step.stage === stageKey);
  if (stageSteps.some((step) => step.status === "error")) return "error";
  if (stageSteps.some((step) => step.status === "running")) return "running";
  if (stageSteps.length > 0 && stageSteps.some((step) => step.status === "success")) return "success";
  if (stageSteps.length > 0 && stageSteps.every((step) => step.status === "skipped")) return "skipped";
  if (getStageIndex(run.stage) > stageIndex && stageIndex >= 0) return "success";
  if (run.stage === "finished" && stageKey === "finished") return run.status === "error" ? "error" : "success";
  return "pending";
}

function stageBadgeClass(state: string): string {
  switch (state) {
    case "running":
      return "border-primary/30 bg-primary/10 text-primary";
    case "success":
      return "border-tertiary/30 bg-tertiary/10 text-tertiary";
    case "skipped":
      return "border-amber-400/30 bg-amber-400/10 text-amber-300";
    case "error":
      return "border-error/30 bg-error/10 text-error";
    default:
      return "border-outline-variant/15 bg-surface-container-high text-on-surface-variant";
  }
}

function stageCopy(state: string): string {
  switch (state) {
    case "running":
      return "En cours";
    case "success":
      return "Termine";
    case "skipped":
      return "Ignore";
    case "error":
      return "Erreur";
    default:
      return "En attente";
  }
}

function isRunFailed(run: WatchRunPayload | null | undefined): boolean {
  if (!run) {
    return false;
  }

  if (run.status === "error") {
    return true;
  }

  return Object.values(run.steps || {}).some((step) => step.status === "error");
}

function getRunFailureMessage(run: WatchRunPayload | null | undefined): string {
  if (!run) {
    return "Le run a echoue avant de retourner des details exploitables.";
  }

  const failedStep = Object.values(run.steps || {}).find((step) => step.status === "error");
  if (failedStep?.error_message) {
    return failedStep.error_message;
  }

  return "Une etape a echoue. Verifiez les credentials, les dependances ou les quotas fournisseurs.";
}

export function RunProgressPanel({
  run,
  isLoading = false,
  showNoDataState = false,
}: RunProgressPanelProps) {
  const [, setLocation] = useLocation();
  const collectorSteps = Object.values(run?.steps || {}).filter((step) => step.collector_key);
  const failed = isRunFailed(run);
  const showCompletedNoDataState = showNoDataState && !failed;
  const failureMessage = getRunFailureMessage(run);

  const restartInitialization = () => {
    setStoredOnboardingRun(null);
    setLocation("/nouveau-client");
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
              Pipeline d'initialisation
            </p>
            <h2 className="mt-3 font-headline text-3xl font-black tracking-tight text-on-surface">
              {run ? `Run ${run.run_id}` : "Initialisation du run"}
            </h2>
            <p className="mt-3 text-sm text-on-surface-variant">
              {isLoading
                ? "Connexion au moteur de collecte..."
                : `Client ${run?.client_id || "-"} • ${run?.records_collected ?? 0} documents collectes`}
            </p>
          </div>

          <Button
            data-testid="btn-switch-to-demo-tenant"
            variant="outline"
            onClick={() => {
              setStoredOnboardingRun(null);
              setStoredTenantId(DEMO_TENANT_ID);
              setLocation("/");
            }}
          >
            Explorer un exemple abouti : Ramy (8 jours de donnees)
          </Button>
        </div>

        {failed ? (
          <div className="mt-6 rounded-2xl border border-error/30 bg-error/10 p-5 text-error">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em]">Une etape a echoue</p>
            <p className="mt-3 text-lg font-black">Le pipeline est arrete sur l'etape en erreur.</p>
            <p className="mt-3 text-sm text-on-surface">{failureMessage}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button onClick={restartInitialization}>Relancer l'initialisation</Button>
              <Button variant="outline" onClick={restartInitialization}>
                Reprendre le wizard
              </Button>
            </div>
          </div>
        ) : null}

        {showCompletedNoDataState ? (
          <div className="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-5 text-on-surface">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Run termine sans signaux exploitables
            </p>
            <p className="mt-3 text-lg font-black">
              L'initialisation est terminee, mais le dashboard ne peut pas encore afficher de vraies donnees.
            </p>
            <p className="mt-3 text-sm text-on-surface-variant">
              Aucune mention normalisee exploitable n'a encore ete produite pour ce tenant. Ajustez les seeds, les canaux ou relancez l'initialisation.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button onClick={restartInitialization}>Relancer l'initialisation</Button>
              <Button variant="outline" onClick={restartInitialization}>
                Reprendre le wizard
              </Button>
            </div>
          </div>
        ) : null}

        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {STAGES.map((stage) => {
            const state = resolveStageState(run, stage.key);
            return (
              <div
                key={stage.key}
                data-testid={`watch-run-stage-${stage.key}`}
                className={`rounded-2xl border p-5 ${stageBadgeClass(state)}`}
              >
                <p className="text-[10px] font-bold uppercase tracking-[0.18em]">{stage.label}</p>
                <p className="mt-3 text-lg font-black">{stageCopy(state)}</p>
              </div>
            );
          })}
        </div>

        <div className="mt-8 rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
            Collecteurs actives
          </p>
          <div className="mt-4 space-y-3">
            {collectorSteps.length > 0 ? (
              collectorSteps.map((step) => (
                <div
                  key={step.step_key}
                  className="flex items-center justify-between gap-4 rounded-xl border border-outline-variant/10 bg-surface-container px-4 py-3 text-sm"
                >
                  <div>
                    <p className="font-semibold text-on-surface">{step.collector_key}</p>
                    {step.error_message ? (
                      <p className="text-xs text-on-surface-variant">{step.error_message}</p>
                    ) : null}
                  </div>
                  <span className="text-xs uppercase tracking-[0.16em] text-on-surface-variant">
                    {step.status} • {step.records_seen}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-on-surface-variant">
                Les etapes de collecte apparaitront des que le run renverra ses premiers statuts.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
