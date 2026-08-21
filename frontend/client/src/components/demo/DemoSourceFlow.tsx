import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  MessageSquareText,
  ScanSearch,
} from "lucide-react";

import { LETICIA_DEMO_SCENARIO } from "@/lib/leticiaDemoScenario";

const CHANNEL_LABELS = {
  facebook: "Facebook",
  google_maps: "Google Maps",
  youtube: "YouTube",
  audio: "Audio autorisé",
} as const;

function channelLabel(channel: (typeof LETICIA_DEMO_SCENARIO.authorizedInputChannels)[number]): string {
  if (channel === "facebook") return CHANNEL_LABELS.facebook;
  if (channel === "google_maps") return CHANNEL_LABELS.google_maps;
  if (channel === "youtube") return CHANNEL_LABELS.youtube;
  if (channel === "audio") return CHANNEL_LABELS.audio;
  return channel.replaceAll("_", " ");
}

function FlowArrow() {
  return (
    <ArrowRight
      className="mx-auto h-4 w-4 rotate-90 text-on-surface-variant lg:rotate-0"
      aria-hidden="true"
    />
  );
}

export function DemoSourceFlow() {
  const channelLabels = LETICIA_DEMO_SCENARIO.authorizedInputChannels.map(
    channelLabel,
  );

  return (
    <section
      className="overflow-hidden rounded-2xl border border-outline-variant bg-surface"
      data-testid="demo-source-flow"
      aria-labelledby="demo-source-flow-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant px-4 py-2.5 sm:px-5">
        <div className="flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-primary" aria-hidden="true" />
          <h2 id="demo-source-flow-title" className="font-headline text-sm font-bold text-on-surface">
            Du point d’écoute à la décision
          </h2>
        </div>
        <span className="text-[9px] font-semibold text-on-surface-variant">
          Scénario de démonstration · disponibilité à Oran
        </span>
      </div>

      <div className="grid items-center gap-2 px-4 py-3 lg:grid-cols-[1.35fr_auto_1fr_auto_1fr_auto_1fr] lg:gap-3 sm:px-5">
        <div className="min-w-0">
          <p className="text-[9px] font-semibold text-on-surface-variant">Canaux d’écoute</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {[...channelLabels, "QR"].map((label) => (
              <span key={label} className="rounded-full bg-surface-container-high px-2 py-1 text-[9px] font-semibold text-on-surface">
                {label}
              </span>
            ))}
          </div>
        </div>
        <FlowArrow />

        <div className="flex items-start gap-2 rounded-xl bg-insight-container p-3 text-insight">
          <BrainCircuit className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p className="text-[10px] font-semibold leading-4">LIDAL AI comprend la langue et le contexte</p>
        </div>
        <FlowArrow />

        <div className="flex items-start gap-2 rounded-xl bg-surface-container-low p-3 text-on-surface">
          <ScanSearch className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          <p className="text-[10px] font-semibold leading-4">preuve exacte + aspect + alerte</p>
        </div>
        <FlowArrow />

        <div className="flex items-start gap-2 rounded-xl bg-action-container p-3 text-on-action-container">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p className="text-[10px] font-semibold leading-4">décision validée par l’équipe</p>
        </div>
      </div>
    </section>
  );
}
