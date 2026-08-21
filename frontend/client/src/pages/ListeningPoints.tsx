import { useMemo, useRef, useState } from "react";
import { Check, Clipboard, Download, ExternalLink, Plus, QrCode, Radio, ScanLine } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Link } from "wouter";

import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { useListeningPoints, useListeningPointSubmissions } from "@/hooks/useListeningPoints";
import type { ListeningPointStatus } from "@/lib/listeningPoints";

const STATUS_LABELS: Record<ListeningPointStatus, string> = {
  active: "Actif",
  paused: "En pause",
  closed: "Fermé",
};

const STATUS_CLASSES: Record<ListeningPointStatus, string> = {
  active: "bg-action-container text-action",
  paused: "bg-surface-container-high text-on-surface-variant",
  closed: "bg-error-container text-error",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-DZ", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function ListeningPoints() {
  const pointsQuery = useListeningPoints();
  const points = pointsQuery.data ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const qrContainerRef = useRef<HTMLDivElement>(null);
  const selectedPoint = points.find((point) => point.id === selectedId) ?? points[0] ?? null;
  const submissionsQuery = useListeningPointSubmissions(selectedPoint?.id ?? "");
  const submissions = useMemo(
    () => [...(submissionsQuery.data ?? [])].sort((left, right) => right.createdAt.localeCompare(left.createdAt)),
    [submissionsQuery.data],
  );

  const feedbackHref = selectedPoint ? `/#/feedback/${selectedPoint.token}` : "";
  const feedbackUrl = typeof window === "undefined" ? feedbackHref : `${window.location.origin}${feedbackHref}`;
  const activeCount = points.filter((point) => point.status === "active").length;
  const scanCount = points.reduce((total, point) => total + point.scanCount, 0);

  async function copyFeedbackUrl() {
    if (!feedbackUrl) return;
    await navigator.clipboard.writeText(feedbackUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  }

  function downloadQrCode() {
    const svg = qrContainerRef.current?.querySelector("svg");
    if (!svg || !selectedPoint) return;
    const source = new XMLSerializer().serializeToString(svg);
    const objectUrl = URL.createObjectURL(new Blob([source], { type: "image/svg+xml" }));
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = `qr-${selectedPoint.token}.svg`;
    anchor.click();
    URL.revokeObjectURL(objectUrl);
  }

  return (
    <AppShell>
      <main className="mx-auto w-full max-w-[92rem] px-4 py-6 sm:px-6 lg:px-8" data-testid="listening-points-page">
        <PageHeader
          eyebrow="Collecte directe"
          title="Points d’écoute"
          description="Placez un QR sur un produit ou un lieu, puis retrouvez chaque retour local dans une file d’analyse vérifiable."
          actions={(
            <Link href="/listening-points/new" className="inline-flex h-11 items-center justify-center rounded-full bg-primary px-5 text-xs font-bold text-primary-foreground shadow-pulse-glow transition-transform hover:-translate-y-0.5">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nouveau point
            </Link>
          )}
        />

        <section className="mt-7 grid gap-3 sm:grid-cols-3" aria-label="Indicateurs des points d’écoute">
          <article className="rounded-2xl border border-outline-variant bg-surface p-5 shadow-ambient">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-on-surface-variant">Points actifs</p>
            <p className="mt-3 font-headline text-3xl font-semibold">{activeCount}</p>
            <p className="mt-1 text-xs text-on-surface-variant">sur {points.length} configurés</p>
          </article>
          <article className="rounded-2xl border border-outline-variant bg-surface p-5 shadow-ambient">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-on-surface-variant">Scans enregistrés</p>
            <p className="mt-3 font-headline text-3xl font-semibold">{scanCount}</p>
            <p className="mt-1 text-xs text-on-surface-variant">compteur local déterministe</p>
          </article>
          <article className="rounded-2xl border border-outline-variant bg-surface p-5 shadow-ambient">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-on-surface-variant">À analyser</p>
            <p className="mt-3 font-headline text-3xl font-semibold">{submissions.length}</p>
            <p className="mt-1 text-xs text-on-surface-variant">pour le point sélectionné</p>
          </article>
        </section>

        <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1fr)_23rem]">
          <section className="overflow-hidden rounded-[1.75rem] border border-outline-variant bg-surface shadow-ambient">
            <header className="flex items-center justify-between gap-4 border-b border-outline-variant px-5 py-4 sm:px-6">
              <div>
                <h2 className="font-headline text-lg font-semibold">QR déployés</h2>
                <p className="mt-1 text-xs text-on-surface-variant">Sélectionnez un point pour ouvrir son lien et consulter ses retours.</p>
              </div>
              <Radio className="h-5 w-5 text-primary" aria-hidden="true" />
            </header>
            <div className="divide-y divide-outline-variant">
              {points.map((point) => {
                const selected = point.id === selectedPoint?.id;
                return (
                  <button
                    key={point.id}
                    type="button"
                    className={`grid w-full gap-4 px-5 py-5 text-left transition-colors sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-6 ${selected ? "bg-primary-container" : "hover:bg-surface-container-low"}`}
                    onClick={() => setSelectedId(point.id)}
                    aria-pressed={selected}
                  >
                    <span className="flex min-w-0 items-start gap-4">
                      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${selected ? "bg-primary text-primary-foreground" : "bg-surface-container text-on-surface-variant"}`}>
                        <ScanLine className="h-5 w-5" aria-hidden="true" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-headline text-base font-semibold text-on-surface">{point.name}</span>
                        <span className="mt-1 block truncate font-mono text-[10px] text-on-surface-variant">/{point.token}</span>
                      </span>
                    </span>
                    <span className="flex items-center gap-3 sm:justify-end">
                      <span className={`rounded-full px-3 py-1.5 text-[10px] font-bold ${STATUS_CLASSES[point.status]}`}>{STATUS_LABELS[point.status]}</span>
                      <span className="text-[10px] text-on-surface-variant">{point.scanCount} scan{point.scanCount === 1 ? "" : "s"}</span>
                    </span>
                  </button>
                );
              })}
              {!points.length ? <p className="px-6 py-12 text-center text-sm text-on-surface-variant">Aucun point d’écoute pour cet espace.</p> : null}
            </div>
          </section>

          <aside className="rounded-[1.75rem] border border-outline-variant bg-inverse-surface p-5 text-inverse-on-surface shadow-ambient sm:p-6">
            {selectedPoint ? (
              <>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-inverse-primary">QR sélectionné</p>
                    <h2 className="mt-2 font-headline text-xl font-semibold">{selectedPoint.name}</h2>
                  </div>
                  <QrCode className="h-6 w-6 text-inverse-primary" aria-hidden="true" />
                </div>
                <div ref={qrContainerRef} className="mx-auto mt-6 w-fit rounded-3xl bg-inverse-on-surface p-4 text-inverse-surface">
                  <QRCodeSVG
                    data-testid="listening-point-qr"
                    value={feedbackUrl}
                    size={208}
                    level="M"
                    marginSize={1}
                    fgColor="currentColor"
                  />
                </div>
                <p className="mt-4 break-all text-center font-mono text-[10px] leading-5 opacity-70">{feedbackUrl}</p>
                <div className="mt-5 grid grid-cols-2 gap-2">
                  <Button type="button" variant="secondary" onClick={() => void copyFeedbackUrl()}>
                    {copied ? <Check className="mr-2 h-4 w-4" aria-hidden="true" /> : <Clipboard className="mr-2 h-4 w-4" aria-hidden="true" />}
                    {copied ? "Copié" : "Copier"}
                  </Button>
                  <Button type="button" variant="secondary" onClick={downloadQrCode}>
                    <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                    Télécharger
                  </Button>
                </div>
                <a
                  href={feedbackHref}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 flex h-11 items-center justify-center rounded-xl border border-inverse-primary/30 text-xs font-semibold text-inverse-primary transition-colors hover:bg-inverse-on-surface/10"
                >
                  Tester le formulaire
                  <ExternalLink className="ml-2 h-4 w-4" aria-hidden="true" />
                </a>
              </>
            ) : null}
          </aside>
        </div>

        <section className="mt-6 overflow-hidden rounded-[1.75rem] border border-outline-variant bg-surface shadow-ambient">
          <header className="border-b border-outline-variant px-5 py-4 sm:px-6">
            <h2 className="font-headline text-lg font-semibold">Derniers retours locaux</h2>
            <p className="mt-1 text-xs text-on-surface-variant">Les contenus restent en attente tant qu’ils n’ont pas été analysés et vérifiés.</p>
          </header>
          <div className="divide-y divide-outline-variant">
            {submissions.slice(0, 6).map((submission) => (
              <article key={submission.id} className="grid gap-3 px-5 py-5 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-start sm:px-6" data-testid="pending-submission">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-container font-headline text-sm font-bold text-primary">{submission.rating}/5</span>
                <div>
                  <p className="text-sm leading-6 text-on-surface">{submission.text || "Retour sans message texte"}</p>
                  <p className="mt-1 text-[10px] text-on-surface-variant">
                    {submission.imageName ? `Fichier local : ${submission.imageName} · ` : ""}
                    {submission.audioDurationSeconds ? `Durée audio locale : ${submission.audioDurationSeconds} s · ` : ""}
                    {formatDate(submission.createdAt)}
                  </p>
                </div>
                <span className="w-fit rounded-full bg-monitor-container px-3 py-1.5 text-[10px] font-bold text-monitor">En attente</span>
              </article>
            ))}
            {!submissions.length ? (
              <div className="px-6 py-12 text-center">
                <p className="font-headline text-base font-semibold">Aucun retour local pour ce point</p>
                <p className="mt-2 text-xs text-on-surface-variant">Ouvrez le formulaire de test pour vérifier le parcours de collecte.</p>
              </div>
            ) : null}
          </div>
        </section>
      </main>
    </AppShell>
  );
}
