import { Button } from "@/components/ui/button";
import { setStoredTenantId } from "@/lib/tenantContext";

const DEMO_TENANT_ID =
  ((import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    ?.VITE_SAFE_EXPO_CLIENT_ID as string | undefined) || "ramy-demo";

const STAGES = [
  { key: "collecting", label: "Collecte des sources" },
  { key: "normalizing", label: "Normalisation" },
  { key: "indexing", label: "Indexation et artefacts" },
  { key: "finished", label: "Run terminé" },
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
}

function resolveStageState(run: WatchRunPayload | null | undefined, stageKey: string) {
  if (!run) return "pending";
  if (run.stage === stageKey) return run.status === "error" ? "error" : "running";
  const stageSteps = Object.values(run.steps || {}).filter((step) => step.stage === stageKey);
  if (stageSteps.some((step) => step.status === "error")) return "error";
  if (stageSteps.some((step) => step.status === "running")) return "running";
  if (stageSteps.some((step) => step.status === "skipped")) return "skipped";
  if (stageSteps.length > 0 && stageSteps.every((step) => ["success", "skipped"].includes(step.status))) {
    return "success";
  }
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
      return "Terminé";
    case "skipped":
      return "Ignoré";
    case "error":
      return "Erreur";
    default:
      return "En attente";
  }
}

export function RunProgressPanel({ run, isLoading = false }: RunProgressPanelProps) {
  const collectorSteps = Object.values(run?.steps || {}).filter((step) => step.collector_key);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
              Analyse en cours
            </p>
            <h2 className="mt-3 font-headline text-3xl font-black tracking-tight text-on-surface">
              {run ? `Run ${run.run_id}` : "Initialisation du run"}
            </h2>
            <p className="mt-3 text-sm text-on-surface-variant">
              {isLoading
                ? "Connexion au moteur de collecte..."
                : `Client ${run?.client_id || "-"} • ${run?.records_collected ?? 0} documents collectés`}
            </p>
          </div>

          <Button
            data-testid="btn-switch-to-demo-tenant"
            variant="outline"
            onClick={() => {
              setStoredTenantId(DEMO_TENANT_ID);
              window.location.hash = "/";
            }}
          >
            Explorer un exemple abouti : Ramy (8 jours de données)
          </Button>
        </div>

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
            Collecteurs activés
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
                Les étapes de collecte apparaîtront dès que le run renverra ses premiers statuts.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
