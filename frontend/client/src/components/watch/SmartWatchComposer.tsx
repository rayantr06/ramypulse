import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  ChevronRight,
  Globe2,
  Languages,
  MapPin,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";

import { WatchScopeForm, type WatchScopeSubmitValue } from "@/components/watch/WatchScopeForm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { mapOnboardingAnalysis, type OnboardingAnalysis } from "@/lib/apiMappings";
import { formatTenantLabel } from "@/lib/productNavigation";
import { apiRequest } from "@/lib/queryClient";
import { useTenantId } from "@/lib/tenantContext";

interface SmartWatchComposerProps {
  isSubmitting?: boolean;
  onCancel: () => void;
  onSubmit: (value: WatchScopeSubmitValue) => void;
}

interface PreparedWatch {
  origin: "ai" | "automatic";
  sourceCount: number;
  alertProfileCount: number;
  value: WatchScopeSubmitValue;
}

const INTENT_EXAMPLES = [
  "Les avis sur le goût des yaourts Ramy en Algérie",
  "Les réactions négatives sous notre publication Instagram",
  "Comparer notre prix avec les concurrents à Alger et Oran",
];

const CHANNEL_LABELS: Record<string, string> = {
  facebook: "Facebook",
  google_maps: "Google Maps",
  instagram: "Instagram",
  public_url_seed: "Pages indiquées",
  web_search: "Web",
  youtube: "YouTube",
};

const REGION_HINTS = [
  "Alger",
  "Oran",
  "Constantine",
  "Annaba",
  "Sétif",
  "Béjaïa",
  "Blida",
  "Tlemcen",
];

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item ?? "").trim())
    .filter(Boolean);
}

function asSafeNumber(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function extractUrls(value: string): string[] {
  return Array.from(new Set(value.match(/https?:\/\/[^\s]+/gi) ?? []));
}

function extractRegions(value: string): string[] {
  const normalized = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return REGION_HINTS.filter((region) =>
    normalized.includes(region.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()),
  );
}

function inferSubjectType(intent: string): string {
  const normalized = intent.toLowerCase();
  if (/https?:\/\//.test(normalized) || normalized.includes("publication")) return "publication";
  if (normalized.includes("campagne")) return "campaign";
  if (normalized.includes("concurrent")) return "competitor";
  if (normalized.includes("produit")) return "product";
  if (normalized.includes("marque")) return "brand";
  return "keyword";
}

function cleanBrandName(tenantLabel: string): string {
  return tenantLabel
    .replace(/\s*·.*$/, "")
    .replace(/^Groupe\s+/i, "")
    .trim();
}

function buildPreparedWatch(
  intent: string,
  tenantLabel: string,
  analysis: OnboardingAnalysis | null,
): PreparedWatch {
  const normalizedIntent = intent.trim().replace(/\s+/g, " ");
  const seed = analysis?.suggested_watchlists.find((watchlist) => watchlist.role === "seed");
  const filters = seed?.filters ?? {};
  const recommendedChannels =
    analysis?.recommended_channels
      .filter((channel) => channel.enabled_by_default)
      .map((channel) => channel.channel) ?? [];
  const channels = recommendedChannels.length > 0
    ? recommendedChannels
    : ["web_search", "public_url_seed"];
  const suggestedUrls = analysis?.suggested_sources.map((source) => source.url) ?? [];
  const seedUrls = Array.from(new Set([...suggestedUrls, ...extractUrls(normalizedIntent)]));
  const inferredRegions = extractRegions(normalizedIntent);
  const filterRegions = asStringArray(filters.regions);
  const filterKeywords = asStringArray(filters.keywords);
  const languages = asStringArray(filters.languages);
  const shortIntent = normalizedIntent.length > 54
    ? `${normalizedIntent.slice(0, 51).trim()}…`
    : normalizedIntent;

  return {
    origin: analysis && !analysis.fallback_used ? "ai" : "automatic",
    sourceCount: seedUrls.length,
    alertProfileCount: analysis?.suggested_alert_profiles.filter(
      (profile) => profile.enabled_by_default,
    ).length ?? 0,
    value: {
      payload: {
        name: seed?.name?.trim() || `Veille · ${shortIntent}`,
        description: normalizedIntent,
        subject_type: inferSubjectType(normalizedIntent),
        brand_name: cleanBrandName(tenantLabel),
        product_name: normalizedIntent,
        keywords: filterKeywords.length > 0 ? filterKeywords : [normalizedIntent],
        excluded_keywords: asStringArray(filters.excluded_keywords),
        seed_urls: seedUrls,
        competitors: asStringArray(filters.competitors),
        channels,
        languages: languages.length > 0 ? languages : ["fr", "ar"],
        regions: filterRegions.length > 0 ? filterRegions : inferredRegions,
        period_days: Math.max(1, asSafeNumber(filters.period_days, 30)),
        min_volume: asSafeNumber(filters.min_volume, 5),
      },
      requestedChannels: channels,
    },
  };
}

function SummaryRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Globe2;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 border-b border-outline-variant/70 py-4 last:border-b-0">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-container text-primary">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-[10px] font-semibold text-on-surface-variant">{label}</p>
        <p className="mt-1 text-sm font-semibold leading-5 text-on-surface">{value}</p>
      </div>
    </div>
  );
}

export function SmartWatchComposer({
  isSubmitting = false,
  onCancel,
  onSubmit,
}: SmartWatchComposerProps) {
  const tenantId = useTenantId();
  const tenantLabel = formatTenantLabel(tenantId);
  const [intent, setIntent] = useState("");
  const [preparedWatch, setPreparedWatch] = useState<PreparedWatch | null>(null);
  const [mode, setMode] = useState<"guided" | "manual">("guided");

  const prepareMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/onboarding/analyze", {
        brand_name: cleanBrandName(tenantLabel),
        product_name: intent.trim(),
      });
      return mapOnboardingAnalysis(await response.json());
    },
    onSuccess: (analysis) => {
      setPreparedWatch(buildPreparedWatch(intent, tenantLabel, analysis));
    },
    onError: (error: Error) => {
      setPreparedWatch(buildPreparedWatch(intent, tenantLabel, null));
      toast({
        title: "Analyse IA indisponible",
        description: `${error.message || "Le service ne répond pas."} Une configuration standard a été préparée et reste modifiable.`,
        variant: "destructive",
      });
    },
  });

  const channelsLabel = useMemo(() => {
    if (!preparedWatch) return "";
    return preparedWatch.value.requestedChannels
      .map((channel) => CHANNEL_LABELS[channel] ?? channel)
      .join(" · ");
  }, [preparedWatch]);

  if (mode === "manual") {
    return (
      <div className="min-h-full bg-surface-container">
        <div className="flex items-center justify-between border-b border-outline-variant/70 px-6 py-4">
          <Button variant="ghost" onClick={() => setMode("guided")}>
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Revenir au mode guidé
          </Button>
          <span className="text-xs text-on-surface-variant">Réglages avancés</span>
        </div>
        <WatchScopeForm
          presentation="drawer"
          isSubmitting={isSubmitting}
          onCancel={onCancel}
          onSubmit={onSubmit}
        />
      </div>
    );
  }

  return (
    <div className="min-h-full bg-surface px-5 py-7 sm:px-8 sm:py-10" data-testid="smart-watch-composer">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between gap-4">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Fermer
          </Button>
          <span className="inline-flex items-center gap-2 rounded-full bg-primary-container px-3 py-1.5 text-[10px] font-bold text-primary">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Préparation assistée
          </span>
        </div>

        {!preparedWatch ? (
          <section className="pt-10 sm:pt-16">
            <h1 className="max-w-xl text-balance font-headline text-3xl font-extrabold tracking-tight text-on-surface sm:text-4xl">
              Que voulez-vous surveiller ?
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-on-surface-variant">
              Écrivez votre objectif comme vous l’expliqueriez à un collègue. LIDAL prépare les mots-clés, les sources et la couverture.
            </p>

            <div className="mt-8 rounded-2xl border border-outline-variant bg-surface-container-low p-3 shadow-panel">
              <Textarea
                autoFocus
                className="min-h-36 resize-none border-0 bg-transparent px-3 py-3 text-base leading-7 shadow-none focus-visible:ring-0"
                data-testid="watch-intent-input"
                onChange={(event) => setIntent(event.target.value)}
                placeholder="Ex. Surveiller les avis sur le goût des yaourts Ramy, surtout à Alger et Oran…"
                value={intent}
              />
              <div className="flex items-center justify-between gap-3 border-t border-outline-variant/70 px-2 pt-3">
                <button
                  className="text-xs font-semibold text-on-surface-variant underline-offset-4 hover:text-on-surface hover:underline"
                  onClick={() => setMode("manual")}
                  type="button"
                >
                  Paramètres manuels
                </button>
                <Button
                  data-testid="btn-prepare-watch"
                  disabled={intent.trim().length < 4 || prepareMutation.isPending}
                  onClick={() => prepareMutation.mutate()}
                >
                  {prepareMutation.isPending ? "Préparation…" : "Préparer la surveillance"}
                  {!prepareMutation.isPending ? <ChevronRight className="ml-2 h-4 w-4" aria-hidden="true" /> : null}
                </Button>
              </div>
            </div>

            <div className="mt-6">
              <p className="text-[10px] font-semibold text-on-surface-variant">Exemples</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {INTENT_EXAMPLES.map((example) => (
                  <button
                    className="rounded-full border border-outline-variant bg-surface px-3 py-2 text-left text-xs text-on-surface-variant transition-colors hover:border-primary/30 hover:text-on-surface"
                    key={example}
                    onClick={() => setIntent(example)}
                    type="button"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </section>
        ) : (
          <section className="pt-8" data-testid="smart-watch-review">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-success-container text-success">
              <Check className="h-5 w-5" strokeWidth={2.5} aria-hidden="true" />
            </div>
            <h1 className="mt-5 font-headline text-3xl font-extrabold tracking-tight text-on-surface">
              Votre surveillance est prête
            </h1>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Vérifiez l’essentiel. Les réglages techniques ont été préparés automatiquement.
            </p>

            <div className="mt-7 rounded-2xl border border-outline-variant bg-surface-container-low px-5 shadow-panel">
              <SummaryRow
                icon={Sparkles}
                label="Objectif compris"
                value={intent.trim()}
              />
              <SummaryRow icon={Globe2} label="Sources retenues" value={channelsLabel} />
              <SummaryRow
                icon={MapPin}
                label="Zone"
                value={
                  preparedWatch.value.payload.regions?.length
                    ? preparedWatch.value.payload.regions.join(" · ")
                    : "Algérie · sans restriction de wilaya"
                }
              />
              <SummaryRow
                icon={Languages}
                label="Langues comprises"
                value="Français · Arabe · Daridja"
              />
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-on-surface-variant">
              <span>{preparedWatch.value.payload.period_days} jours analysés</span>
              {preparedWatch.sourceCount > 0 ? (
                <span>{preparedWatch.sourceCount} page{preparedWatch.sourceCount > 1 ? "s" : ""} de départ</span>
              ) : null}
              {preparedWatch.alertProfileCount > 0 ? (
                <span>{preparedWatch.alertProfileCount} profil{preparedWatch.alertProfileCount > 1 ? "s" : ""} d’alerte</span>
              ) : null}
              <span>{preparedWatch.origin === "ai" ? "Préparée par l’IA" : "Configuration automatique"}</span>
            </div>

            <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Button variant="ghost" onClick={() => setPreparedWatch(null)}>
                  Reformuler
                </Button>
                <Button variant="ghost" onClick={() => setMode("manual")}>
                  <SlidersHorizontal className="mr-2 h-4 w-4" aria-hidden="true" />
                  Réglages avancés
                </Button>
              </div>
              <Button
                data-testid="btn-submit-watchlist"
                disabled={isSubmitting}
                onClick={() => onSubmit(preparedWatch.value)}
              >
                {isSubmitting ? "Lancement…" : "Créer et lancer"}
                {!isSubmitting ? <ChevronRight className="ml-2 h-4 w-4" aria-hidden="true" /> : null}
              </Button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
