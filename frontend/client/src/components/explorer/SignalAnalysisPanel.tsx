import {
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Languages,
  ListChecks,
  MessageSquareQuote,
  Route,
  ScanText,
  ShieldAlert,
  Target,
} from "lucide-react";

import {
  collectAnnotationEvidence,
  entityName,
  formatSlmLabel,
  sentimentTone,
  type SlmAnalysisEnvelope,
  type SlmEvidence,
} from "@/lib/slmV04";

interface SignalAnalysisPanelProps {
  text: string;
  sourceLabel: string;
  sourceUrl: string;
  dateLabel: string;
  locationLabel: string;
  legacySentiment: string;
  legacyAspect: string;
  analysis: SlmAnalysisEnvelope | null;
}

interface TextRange {
  start: number;
  end: number;
}

function evidenceRanges(text: string, evidence: SlmEvidence[]): TextRange[] {
  const ranges = evidence.flatMap((item) => {
    if (
      item.start !== null &&
      item.end !== null &&
      item.start >= 0 &&
      item.end > item.start &&
      item.end <= text.length
    ) {
      return [{ start: item.start, end: item.end }];
    }
    const start = text.toLocaleLowerCase().indexOf(item.text.toLocaleLowerCase());
    return start >= 0 ? [{ start, end: start + item.text.length }] : [];
  }).sort((left, right) => left.start - right.start);

  return ranges.reduce<TextRange[]>((merged, range) => {
    const previous = merged.at(-1);
    if (previous && range.start <= previous.end) {
      previous.end = Math.max(previous.end, range.end);
      return merged;
    }
    return [...merged, { ...range }];
  }, []);
}

function HighlightedSignal({ text, evidence }: { text: string; evidence: SlmEvidence[] }) {
  const ranges = evidenceRanges(text, evidence);
  if (ranges.length === 0) return <>{text}</>;

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start > cursor) nodes.push(text.slice(cursor, range.start));
    nodes.push(
      <mark
        key={`${range.start}-${range.end}-${index}`}
        className="rounded bg-insight-container px-0.5 text-on-surface"
      >
        {text.slice(range.start, range.end)}
      </mark>,
    );
    cursor = range.end;
  });
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return <>{nodes}</>;
}

function MetaChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-surface-container-high px-2.5 py-1 text-[10px] font-semibold text-on-surface-variant">
      {children}
    </span>
  );
}

export function SignalAnalysisPanel({
  text,
  sourceLabel,
  sourceUrl,
  dateLabel,
  locationLabel,
  legacySentiment,
  legacyAspect,
  analysis,
}: SignalAnalysisPanelProps) {
  if (!analysis) {
    return (
      <aside className="cling-panel min-w-0 overflow-hidden xl:sticky xl:top-24" data-testid="signal-analysis-panel">
        <div className="border-b border-outline-variant px-5 py-4 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-container-high text-on-surface-variant">
                <ScanText className="h-4 w-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="font-headline text-base font-bold text-on-surface">Dossier du signal</h2>
                <p className="mt-0.5 text-[10px] text-on-surface-variant">Analyse historique</p>
              </div>
            </div>
            <MetaChip>Ancien annotateur</MetaChip>
          </div>
        </div>

        <div className="space-y-5 p-5 sm:p-6">
          <blockquote className="max-w-[72ch] text-sm leading-6 text-on-surface" dir="auto">
            « {text} »
          </blockquote>
          <div className="flex flex-wrap gap-2">
            <MetaChip>{legacySentiment}</MetaChip>
            <MetaChip>{legacyAspect}</MetaChip>
            <MetaChip>{sourceLabel}</MetaChip>
          </div>
          <div className="rounded-xl bg-warning/10 p-4 text-xs leading-5 text-warning">
            Ce signal n’a pas encore été retraité par le SLM V0.4. Les intentions,
            émotions, entités et preuves détaillées ne sont donc pas disponibles.
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant pt-4 text-[10px] text-on-surface-variant">
            <span>{dateLabel} · {locationLabel}</span>
            {sourceUrl ? (
              <a className="inline-flex items-center gap-1 font-semibold text-primary hover:underline" href={sourceUrl} rel="noreferrer" target="_blank">
                Ouvrir la source <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            ) : null}
          </div>
        </div>
      </aside>
    );
  }

  const { annotation } = analysis;
  const evidence = collectAnnotationEvidence(annotation);
  const isValidated = analysis.validationStatus === "valid";
  const shouldReview = annotation.requiresParentContext || !annotation.isExploitable || !isValidated;

  return (
    <aside className="cling-panel min-w-0 overflow-hidden xl:sticky xl:top-24" data-testid="signal-analysis-panel">
      <div className="border-b border-outline-variant px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-insight-container text-insight">
              <ScanText className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="font-headline text-base font-bold text-on-surface">Dossier du signal</h2>
              <p className="mt-0.5 text-[10px] text-on-surface-variant">Analyse compilée et vérifiable</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <MetaChip>SLM {annotation.schemaVersion}</MetaChip>
            <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold ${
              shouldReview ? "bg-warning/10 text-warning" : "bg-success/10 text-success"
            }`}>
              {shouldReview ? (analysis.validationStatus === "unknown" ? "À confirmer" : "Contrôle requis") : "Validée"}
            </span>
          </div>
        </div>
      </div>

      <div className="max-h-none space-y-6 overflow-visible p-5 sm:p-6 xl:max-h-[calc(100vh-9rem)] xl:overflow-y-auto">
        {shouldReview ? (
          <div className="flex gap-3 rounded-xl bg-warning/10 p-4 text-warning">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p className="text-xs leading-5">
              {annotation.requiresParentContext
                ? "Le commentaire dépend d’un message parent. Vérifiez le contexte avant toute décision."
                : !annotation.isExploitable
                  ? `Le texte est inexploitable${annotation.nonExploitableReason ? ` : ${formatSlmLabel(annotation.nonExploitableReason)}` : "."}`
                  : "La validation technique de cette annotation doit être vérifiée."}
            </p>
          </div>
        ) : null}

        <section aria-labelledby="signal-original-title">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 id="signal-original-title" className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <MessageSquareQuote className="h-4 w-4 text-insight" aria-hidden="true" />
              Verbatim et preuves
            </h3>
            <span className="text-[10px] text-on-surface-variant">{evidence.length} extrait{evidence.length > 1 ? "s" : ""}</span>
          </div>
          <blockquote className="rounded-xl bg-surface-container-low p-4 text-sm leading-6 text-on-surface" dir="auto">
            « <HighlightedSignal text={text} evidence={evidence} /> »
          </blockquote>
        </section>

        <section className="grid grid-cols-1 divide-y divide-outline-variant overflow-hidden rounded-xl bg-surface-container-low sm:grid-cols-3 sm:divide-x sm:divide-y-0" aria-label="Lecture globale du signal">
          <div className="min-w-0 px-3 py-3">
            <p className="text-[9px] font-semibold text-on-surface-variant">Sentiment</p>
            <span className={`mt-2 inline-flex rounded-full px-2 py-1 text-[10px] font-bold ${sentimentTone(annotation.sentiment.label)}`}>
              {formatSlmLabel(annotation.sentiment.label)}
            </span>
          </div>
          <div className="min-w-0 px-3 py-3">
            <p className="text-[9px] font-semibold text-on-surface-variant">Émotion</p>
            <p className="mt-2 text-xs font-bold leading-4 text-on-surface">{formatSlmLabel(annotation.sentiment.emotion)}</p>
          </div>
          <div className="min-w-0 px-3 py-3">
            <p className="text-[9px] font-semibold text-on-surface-variant">Pertinence</p>
            <p className="mt-2 text-xs font-bold leading-4 text-on-surface">{formatSlmLabel(annotation.businessRelevance)}</p>
          </div>
        </section>

        <section aria-labelledby="signal-aspects-title">
          <h3 id="signal-aspects-title" className="flex items-center gap-2 text-xs font-bold text-on-surface">
            <Target className="h-4 w-4 text-insight" aria-hidden="true" />
            Cibles et aspects
          </h3>
          {annotation.aspects.length > 0 ? (
            <div className="mt-3 divide-y divide-outline-variant border-y border-outline-variant">
              {annotation.aspects.map((aspect, index) => (
                <div key={`${aspect.family}-${aspect.attribute}-${index}`} className="py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-on-surface">{formatSlmLabel(aspect.family)}</p>
                      <p className="mt-0.5 text-[10px] text-on-surface-variant">
                        {aspect.attribute ? formatSlmLabel(aspect.attribute) : "Aspect général"}
                        {entityName(annotation, aspect.targetEntityId) ? ` · ${entityName(annotation, aspect.targetEntityId)}` : ""}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[9px] font-bold ${sentimentTone(aspect.sentiment)}`}>
                      {formatSlmLabel(aspect.sentiment)} · {formatSlmLabel(aspect.intensity)}
                    </span>
                  </div>
                  {aspect.evidence[0]?.text ? (
                    <p className="mt-2 text-[10px] leading-4 text-on-surface-variant" dir="auto">Preuve : « {aspect.evidence[0].text} »</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-xs text-on-surface-variant">Aucun aspect métier détecté.</p>
          )}
        </section>

        <section className="grid gap-5 sm:grid-cols-2">
          <div>
            <h3 className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <ListChecks className="h-4 w-4 text-insight" aria-hidden="true" />
              Intentions
            </h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {annotation.intents.length > 0
                ? annotation.intents.map((intent) => <MetaChip key={intent}>{formatSlmLabel(intent)}</MetaChip>)
                : <span className="text-xs text-on-surface-variant">Aucune intention explicite</span>}
            </div>
          </div>
          <div>
            <h3 className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <Bot className="h-4 w-4 text-insight" aria-hidden="true" />
              Entités
            </h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {annotation.entities.length > 0
                ? annotation.entities.map((entity) => <MetaChip key={entity.id}>{entity.name} · {formatSlmLabel(entity.type)}</MetaChip>)
                : <span className="text-xs text-on-surface-variant">Aucune entité nommée</span>}
            </div>
          </div>
        </section>

        <section
          className={`rounded-xl p-4 ${annotation.alerts.length > 0 ? "bg-error-container text-on-error-container" : "bg-surface-container-low text-on-surface"}`}
          aria-labelledby="signal-alerts-title"
        >
            <h3 id="signal-alerts-title" className="flex items-center gap-2 text-xs font-bold">
              <ShieldAlert className="h-4 w-4" aria-hidden="true" />
              Alertes
            </h3>
            {annotation.alerts.length > 0 ? <div className="mt-3 space-y-2">
              {annotation.alerts.map((alert, index) => (
                <div key={`${alert.type}-${index}`} className="flex items-start justify-between gap-3 text-xs">
                  <span>{formatSlmLabel(alert.type)}</span>
                  <strong>{formatSlmLabel(alert.severity)}</strong>
                </div>
              ))}
            </div> : (
              <p className="mt-2 text-[10px] leading-4 text-on-surface-variant">Aucune alerte typée détectée dans ce signal.</p>
            )}
        </section>

        <section className="rounded-xl bg-action-container p-4 text-on-action-container" aria-labelledby="signal-routing-title">
          <div className="flex items-start gap-3">
            {annotation.actionability.actionable
              ? <Route className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
            <div className="min-w-0 flex-1">
              <h3 id="signal-routing-title" className="text-xs font-bold">
                {annotation.actionability.actionable ? "À orienter" : "Aucune action requise"}
              </h3>
              <p className="mt-1 text-[10px] leading-4">
                {annotation.actionability.actionable
                  ? `${formatSlmLabel(annotation.actionability.queue)} · priorité ${formatSlmLabel(annotation.actionability.priority).toLocaleLowerCase()}`
                  : "Le signal reste consultable mais ne rejoint aucune file métier."}
              </p>
            </div>
          </div>
        </section>

        <section className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant pt-4 text-[10px] text-on-surface-variant">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1.5"><Languages className="h-3.5 w-3.5" aria-hidden="true" />{formatSlmLabel(annotation.language.dominant)}</span>
            {annotation.language.codeSwitching ? <span>Code-switching</span> : null}
            {annotation.sentiment.sarcasm ? <span>Sarcasme détecté</span> : null}
            <span>{formatSlmLabel(annotation.authorRole)}</span>
          </div>
          {sourceUrl ? (
            <a className="inline-flex items-center gap-1 font-semibold text-primary hover:underline" href={sourceUrl} rel="noreferrer" target="_blank">
              Ouvrir la source <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          ) : null}
        </section>

        <p className="text-[9px] leading-4 text-on-surface-variant">
          {sourceLabel} · {dateLabel} · {locationLabel}
          {analysis.modelVersion ? ` · ${analysis.modelVersion}` : ""}
          {analysis.compilerVersion ? ` · ${analysis.compilerVersion}` : ""}
          {analysis.inferenceMs !== null ? ` · ${analysis.inferenceMs} ms` : ""}
        </p>
      </div>
    </aside>
  );
}
