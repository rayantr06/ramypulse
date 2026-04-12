import { useMemo, useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  mapOnboardingAnalysis,
  type OnboardingAlertProfile,
  type OnboardingAnalysis,
  type OnboardingRecommendedChannel,
  type OnboardingSuggestedSource,
  type OnboardingSuggestedWatchlist,
  type OnboardingWarning,
} from "@/lib/apiMappings";
import { toast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import {
  buildSmartOnboardingConfirmPayload,
  buildWatchWizardPayload,
  suggestBrandKeywords,
} from "@/lib/watchWizard";
import { setStoredTenantId } from "@/lib/tenantContext";

interface WatchOnboardingWizardProps {
  onRunCreated: (payload: { run_id: string; client_id: string; watchlist_id: string }) => void;
}

type WizardMode = "smart" | "manual";

interface ConfirmResponse {
  run_id: string;
  client_id: string;
  watchlist_id: string;
  watch_seed_watchlist_id?: string;
}

const DEFAULT_MANUAL_CHANNELS = ["public_url_seed", "web_search"];
const DEFAULT_LANGUAGES = ["fr", "ar"];

function formatChannelLabel(channel: string): string {
  if (channel === "public_url_seed") return "Page publique seed";
  if (channel === "web_search") return "Recherche web";
  if (channel === "google_maps") return "Google Maps";
  if (channel === "youtube") return "YouTube";
  return channel.charAt(0).toUpperCase() + channel.slice(1);
}

function warningTone(severity: string): string {
  if (severity === "error") return "border-error/40 bg-error/10 text-error";
  if (severity === "info") return "border-primary/20 bg-primary/5 text-on-surface";
  return "border-primary/20 bg-surface-container-high text-on-surface";
}

function selectionDefaults(analysis: OnboardingAnalysis) {
  return {
    sourceUrls: analysis.suggested_sources.map((source) => source.url),
    channels: analysis.recommended_channels
      .filter((channel) => channel.enabled_by_default)
      .map((channel) => channel.channel),
    watchlists: analysis.suggested_watchlists
      .filter((watchlist) => watchlist.enabled_by_default)
      .map((watchlist) => watchlist.name),
    alertProfiles: analysis.suggested_alert_profiles
      .filter((profile) => profile.enabled_by_default)
      .map((profile) => profile.profile_name),
  };
}

function ManualWatchOnboardingFlow({
  brandName,
  productName,
  onBrandNameChange,
  onProductNameChange,
  onRunCreated,
  onBackToSmart,
}: {
  brandName: string;
  productName: string;
  onBrandNameChange: (value: string) => void;
  onProductNameChange: (value: string) => void;
  onRunCreated: (payload: { run_id: string; client_id: string; watchlist_id: string }) => void;
  onBackToSmart: () => void;
}) {
  const [step, setStep] = useState<1 | 2>(1);
  const [seedUrl, setSeedUrl] = useState("");
  const [channels, setChannels] = useState<string[]>(DEFAULT_MANUAL_CHANNELS);
  const [languages, setLanguages] = useState<string[]>(DEFAULT_LANGUAGES);

  const suggestedKeywords = useMemo(
    () => suggestBrandKeywords(`${brandName} ${productName}`.trim()),
    [brandName, productName],
  );

  const createRun = useMutation({
    mutationFn: async () => {
      const clientResponse = await apiRequest("POST", "/api/clients", {
        client_name: brandName.trim(),
      });
      const clientPayload = await clientResponse.json();
      const clientId = String(clientPayload.client_id);

      await apiRequest("PUT", "/api/clients/active", { client_id: clientId });
      setStoredTenantId(clientId);

      const watchlistPayload = buildWatchWizardPayload({
        name: `${brandName.trim()} watch`,
        description: `${brandName.trim()} expo watchlist`,
        brand_name: brandName,
        product_name: productName,
        seed_urls: seedUrl ? [seedUrl] : [],
        channels,
        languages,
      });
      const watchlistResponse = await apiRequest("POST", "/api/watchlists", watchlistPayload);
      const watchlistPayloadResponse = await watchlistResponse.json();
      const watchlistId = String(watchlistPayloadResponse.watchlist_id);

      const runResponse = await apiRequest("POST", "/api/watch-runs", {
        watchlist_id: watchlistId,
        requested_channels: channels,
      });
      const runPayload = await runResponse.json();
      return {
        run_id: String(runPayload.run_id),
        client_id: clientId,
        watchlist_id: watchlistId,
      };
    },
    onSuccess: (payload) => onRunCreated(payload),
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message || "Le wizard manuel a echoue.",
        variant: "destructive",
      });
    },
  });

  const canAdvance = brandName.trim().length > 0;
  const canLaunch = brandName.trim().length > 0 && channels.length > 0;

  const toggleChannel = (channel: string) => {
    setChannels((current) =>
      current.includes(channel)
        ? current.filter((value) => value !== channel)
        : [...current, channel],
    );
  };

  return (
    <div className="mx-auto max-w-4xl rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
      <div className="mb-8 flex items-start justify-between gap-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
            Wizard manuel
          </p>
          <h1 className="mt-3 font-headline text-4xl font-black tracking-tight text-on-surface">
            Lancez un premier run watch-first sans analyse fournisseur
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-on-surface-variant">
            Ce mode reprend le flow historique. Utilisez-le si vous preferez un parametrage direct
            ou si les providers smart ne sont pas disponibles localement.
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <Button variant="outline" onClick={onBackToSmart}>
            Retour smart onboarding
          </Button>
          <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-right">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Etape {step} / 2
            </p>
            <p className="mt-2 text-xs text-on-surface-variant">
              {step === 1 ? "Client et perimetre" : "Seeds et canaux"}
            </p>
          </div>
        </div>
      </div>

      {step === 1 ? (
        <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                Marque / entreprise
              </label>
              <Input
                data-testid="input-brand-name"
                value={brandName}
                onChange={(event) => onBrandNameChange(event.target.value)}
                placeholder="Cevital Elio"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                Produit surveille
              </label>
              <Input
                data-testid="input-product-name"
                value={productName}
                onChange={(event) => onProductNameChange(event.target.value)}
                placeholder="Elio"
              />
            </div>
          </div>

          <aside className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Mots-cles suggeres
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {suggestedKeywords.length > 0 ? (
                suggestedKeywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-on-surface"
                  >
                    {keyword}
                  </span>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">
                  Les suggestions apparaitront des que la marque est renseignee.
                </p>
              )}
            </div>
          </aside>

          <div className="lg:col-span-2 flex justify-end">
            <Button
              data-testid="btn-next-watch-step"
              disabled={!canAdvance}
              onClick={() => setStep(2)}
            >
              Continuer
            </Button>
          </div>
        </section>
      ) : (
        <section className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-3">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                URL publique seed
              </label>
              <Input
                data-testid="input-seed-url"
                value={seedUrl}
                onChange={(event) => setSeedUrl(event.target.value)}
                placeholder="https://example.com/brand"
              />
              <p className="text-xs leading-5 text-on-surface-variant">
                Une page publique aide la premiere collecte. Le produit reste utile meme sans OAuth.
              </p>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                  Canaux actives
                </p>
                <div className="mt-4 space-y-3 text-sm">
                  {["public_url_seed", "web_search", "youtube", "google_maps"].map((channel) => (
                    <label key={channel} className="flex items-center gap-3">
                      <input
                        data-testid={
                          channel === "public_url_seed" || channel === "web_search"
                            ? `checkbox-channel-${channel}`
                            : undefined
                        }
                        type="checkbox"
                        checked={channels.includes(channel)}
                        onChange={() => toggleChannel(channel)}
                      />
                      <span>{formatChannelLabel(channel)}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
                <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                  Langues optionnelles
                </label>
                <select
                  multiple
                  className="mt-4 min-h-24 w-full rounded-xl border border-outline-variant/15 bg-surface-container-highest px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary/40"
                  value={languages}
                  onChange={(event) =>
                    setLanguages(
                      Array.from(event.target.selectedOptions, (option) => option.value),
                    )
                  }
                >
                  <option value="fr">Francais</option>
                  <option value="ar">Arabe</option>
                  <option value="en">Anglais</option>
                </select>
              </div>
            </div>
          </div>

          {createRun.error ? (
            <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
              {(createRun.error as Error).message}
            </div>
          ) : null}

          <div className="flex items-center justify-between gap-3">
            <Button variant="outline" onClick={() => setStep(1)}>
              Retour
            </Button>
            <Button
              data-testid="btn-launch-watch-run"
              disabled={!canLaunch || createRun.isPending}
              onClick={() => createRun.mutate()}
            >
              {createRun.isPending ? "Lancement..." : "Lancer l'analyse"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

function SmartReviewSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">{title}</p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function WatchOnboardingWizard({ onRunCreated }: WatchOnboardingWizardProps) {
  const [mode, setMode] = useState<WizardMode>("smart");
  const [brandName, setBrandName] = useState("");
  const [productName, setProductName] = useState("");
  const [analysis, setAnalysis] = useState<OnboardingAnalysis | null>(null);
  const [selectedSourceUrls, setSelectedSourceUrls] = useState<string[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [selectedWatchlistNames, setSelectedWatchlistNames] = useState<string[]>([]);
  const [selectedAlertProfileNames, setSelectedAlertProfileNames] = useState<string[]>([]);

  const suggestedKeywords = useMemo(
    () => suggestBrandKeywords(`${brandName} ${productName}`.trim()),
    [brandName, productName],
  );

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/onboarding/analyze", {
        brand_name: brandName.trim(),
        ...(productName.trim() ? { product_name: productName.trim() } : {}),
      });
      return mapOnboardingAnalysis(await response.json());
    },
    onSuccess: (payload) => {
      setAnalysis(payload);
      const defaults = selectionDefaults(payload);
      setSelectedSourceUrls(defaults.sourceUrls);
      setSelectedChannels(defaults.channels);
      setSelectedWatchlistNames(defaults.watchlists);
      setSelectedAlertProfileNames(defaults.alertProfiles);
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message || "L'analyse smart a echoue.",
        variant: "destructive",
      });
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!analysis) {
        throw new Error("Aucune analyse a confirmer.");
      }
      const response = await apiRequest(
        "POST",
        "/api/onboarding/confirm",
        buildSmartOnboardingConfirmPayload({
          analysis,
          brand_name: brandName.trim(),
          selected_source_urls: selectedSourceUrls,
          selected_channels: selectedChannels,
          selected_watchlist_names: selectedWatchlistNames,
          selected_alert_profile_names: selectedAlertProfileNames,
        }),
      );
      const payload = (await response.json()) as ConfirmResponse;
      if (!payload.run_id || !payload.client_id || !(payload.watchlist_id || payload.watch_seed_watchlist_id)) {
        throw new Error("Le premier run n'a pas ete retourne par le backend.");
      }
      return {
        run_id: String(payload.run_id),
        client_id: String(payload.client_id),
        watchlist_id: String(payload.watchlist_id || payload.watch_seed_watchlist_id),
      };
    },
    onSuccess: (payload) => {
      setStoredTenantId(payload.client_id);
      onRunCreated(payload);
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message || "La confirmation onboarding a echoue.",
        variant: "destructive",
      });
    },
  });

  const selectedWatchlists = useMemo(
    () =>
      (analysis?.suggested_watchlists ?? []).filter((watchlist) =>
        selectedWatchlistNames.includes(watchlist.name),
      ),
    [analysis, selectedWatchlistNames],
  );
  const selectedAnalysisWatchlistsCount = selectedWatchlists.filter(
    (watchlist) => watchlist.role === "analysis",
  ).length;

  const canAnalyze = brandName.trim().length > 0;
  const canConfirm =
    Boolean(analysis) &&
    selectedChannels.length > 0 &&
    selectedWatchlists.some((watchlist) => watchlist.scope_type === "watch_seed") &&
    selectedAnalysisWatchlistsCount >= 2 &&
    selectedAnalysisWatchlistsCount <= 4;

  const toggleSelection = (
    value: string,
    currentValues: string[],
    setter: (values: string[]) => void,
    options: { locked?: boolean } = {},
  ) => {
    if (options.locked) {
      return;
    }
    setter(
      currentValues.includes(value)
        ? currentValues.filter((item) => item !== value)
        : [...currentValues, value],
    );
  };

  if (mode === "manual") {
    return (
      <ManualWatchOnboardingFlow
        brandName={brandName}
        productName={productName}
        onBrandNameChange={setBrandName}
        onProductNameChange={setProductName}
        onRunCreated={onRunCreated}
        onBackToSmart={() => setMode("smart")}
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.22)]">
      <div className="mb-8 flex items-start justify-between gap-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
            Smart onboarding
          </p>
          <h1 className="mt-3 font-headline text-4xl font-black tracking-tight text-on-surface">
            Analysez, revisez, puis confirmez votre premier perimetre de veille
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant">
            Le flow intelligent prepare un tenant, des sources draft, une watchlist watch_seed et
            des watchlists d'analyse. Rien n'est cree tant que la revue finale n'est pas confirmee.
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <Button
            data-testid="btn-switch-manual-onboarding"
            variant="outline"
            onClick={() => setMode("manual")}
          >
            Passer au wizard manuel
          </Button>
          <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-right">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              {analysis ? "Etape 2 / 2" : "Etape 1 / 2"}
            </p>
            <p className="mt-2 text-xs text-on-surface-variant">
              {analysis ? "Revue obligatoire" : "Brief marque"}
            </p>
          </div>
        </div>
      </div>

      {!analysis ? (
        <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                Marque / entreprise
              </label>
              <Input
                data-testid="input-brand-name"
                value={brandName}
                onChange={(event) => setBrandName(event.target.value)}
                placeholder="Yaghurt Plus"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                Produit surveille
              </label>
              <Input
                data-testid="input-product-name"
                value={productName}
                onChange={(event) => setProductName(event.target.value)}
                placeholder="Yaourt"
              />
            </div>
            {analyzeMutation.error ? (
              <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                {(analyzeMutation.error as Error).message}
              </div>
            ) : null}
            <div className="flex justify-end">
              <Button
                data-testid="btn-smart-analyze"
                disabled={!canAnalyze || analyzeMutation.isPending}
                onClick={() => analyzeMutation.mutate()}
              >
                {analyzeMutation.isPending ? "Analyse..." : "Analyser la marque"}
              </Button>
            </div>
          </div>

          <aside className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Mots-cles suggeres
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {suggestedKeywords.length > 0 ? (
                suggestedKeywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-on-surface"
                  >
                    {keyword}
                  </span>
                ))
              ) : (
                <p className="text-sm text-on-surface-variant">
                  Les suggestions apparaitront des que la marque est renseignee.
                </p>
              )}
            </div>
          </aside>
        </section>
      ) : (
        <section data-testid="smart-review-screen" className="space-y-6">
          {analysis.warnings.length > 0 ? (
            <SmartReviewSection title="Warnings">
              <div className="space-y-3">
                {analysis.warnings.map((warning: OnboardingWarning) => (
                  <div
                    key={warning.code}
                    className={`rounded-xl border px-4 py-3 text-sm ${warningTone(warning.severity)}`}
                  >
                    <p className="font-bold uppercase tracking-[0.14em] text-[10px]">
                      {warning.code}
                    </p>
                    <p className="mt-1">{warning.message}</p>
                  </div>
                ))}
              </div>
            </SmartReviewSection>
          ) : null}

          {analysis.fallback_used ? (
            <div className="rounded-2xl border border-primary/20 bg-primary/5 px-5 py-4 text-sm text-on-surface">
              L'analyse a bascule en heuristique. Vous pouvez continuer cette revue ou revenir au
              wizard manuel si vous preferez un parametrage explicite.
            </div>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-2">
            <SmartReviewSection title="Channels">
              <div className="space-y-3 text-sm">
                {analysis.recommended_channels.map((channel: OnboardingRecommendedChannel) => (
                  <label key={channel.channel} className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedChannels.includes(channel.channel)}
                      onChange={() =>
                        toggleSelection(
                          channel.channel,
                          selectedChannels,
                          setSelectedChannels,
                        )
                      }
                    />
                    <span>
                      <span className="block font-medium text-on-surface">
                        {formatChannelLabel(channel.channel)}
                      </span>
                      <span className="text-xs text-on-surface-variant">{channel.reason}</span>
                    </span>
                  </label>
                ))}
              </div>
            </SmartReviewSection>

            <SmartReviewSection title="Sources draft">
              <div className="space-y-3 text-sm">
                {analysis.suggested_sources.map((source: OnboardingSuggestedSource) => (
                  <label key={source.url} className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedSourceUrls.includes(source.url)}
                      onChange={() =>
                        toggleSelection(
                          source.url,
                          selectedSourceUrls,
                          setSelectedSourceUrls,
                        )
                      }
                    />
                    <span>
                      <span className="block font-medium text-on-surface">{source.label}</span>
                      <span className="text-xs text-on-surface-variant">
                        {formatChannelLabel(source.channel)} · {source.status}
                      </span>
                      <span className="mt-1 block text-xs text-on-surface-variant">
                        {source.reason}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </SmartReviewSection>

            <SmartReviewSection title="Watchlists">
              <div className="space-y-3 text-sm">
                {analysis.suggested_watchlists.map((watchlist: OnboardingSuggestedWatchlist) => {
                  const locked = watchlist.role === "seed";
                  return (
                    <label key={watchlist.name} className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedWatchlistNames.includes(watchlist.name)}
                        disabled={locked}
                        onChange={() =>
                          toggleSelection(
                            watchlist.name,
                            selectedWatchlistNames,
                            setSelectedWatchlistNames,
                            { locked },
                          )
                        }
                      />
                      <span>
                        <span className="block font-medium text-on-surface">
                          {watchlist.name}
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          {watchlist.scope_type} · {watchlist.role}
                        </span>
                        <span className="mt-1 block text-xs text-on-surface-variant">
                          {watchlist.reason}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </SmartReviewSection>

            <SmartReviewSection title="Alertes et credentials">
              <div className="space-y-4 text-sm">
                {analysis.required_credentials.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                      Credentials requis
                    </p>
                    {analysis.required_credentials.map((credential) => (
                      <div key={`${credential.platform}-${credential.credential_type}`}>
                        <p className="font-medium">
                          {credential.platform} · {credential.credential_type}
                        </p>
                        <p className="text-xs text-on-surface-variant">{credential.reason}</p>
                      </div>
                    ))}
                  </div>
                ) : null}

                {analysis.suggested_alert_profiles.map((profile: OnboardingAlertProfile) => (
                  <label key={profile.profile_name} className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedAlertProfileNames.includes(profile.profile_name)}
                      onChange={() =>
                        toggleSelection(
                          profile.profile_name,
                          selectedAlertProfileNames,
                          setSelectedAlertProfileNames,
                        )
                      }
                    />
                    <span>
                      <span className="block font-medium text-on-surface">
                        {profile.profile_name}
                      </span>
                      <span className="text-xs text-on-surface-variant">{profile.reason}</span>
                    </span>
                  </label>
                ))}

                {analysis.deferred_agent_config.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                      Deferred agent config
                    </p>
                    {analysis.deferred_agent_config.map((item) => (
                      <div key={item.key}>
                        <p className="font-medium text-on-surface">{item.key}</p>
                        <p className="text-xs text-on-surface-variant">{item.reason}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </SmartReviewSection>
          </div>

          <div className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5 text-sm text-on-surface-variant">
            {selectedAnalysisWatchlistsCount < 2 || selectedAnalysisWatchlistsCount > 4 ? (
              <p>
                Selection invalide: conservez exactement 1 watch_seed et entre 2 et 4 watchlists
                d'analyse avant de confirmer.
              </p>
            ) : (
              <p>
                Revue complete. La confirmation va creer le tenant si necessaire, les objets V1,
                puis lancer le premier run sur watch_seed.
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <Button variant="outline" onClick={() => setAnalysis(null)}>
              Revenir au brief
            </Button>
            <Button
              data-testid="btn-confirm-smart-onboarding"
              disabled={!canConfirm || confirmMutation.isPending}
              onClick={() => confirmMutation.mutate()}
            >
              {confirmMutation.isPending ? "Confirmation..." : "Confirmer et lancer le premier run"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
