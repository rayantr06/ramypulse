import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/queryClient";
import { buildWatchWizardPayload, suggestBrandKeywords } from "@/lib/watchWizard";
import { setStoredTenantId } from "@/lib/tenantContext";

interface WatchOnboardingWizardProps {
  onRunCreated: (payload: { run_id: string; client_id: string; watchlist_id: string }) => void;
}

const DEFAULT_CHANNELS = ["public_url_seed", "web_search"];
const DEFAULT_LANGUAGES = ["fr", "ar"];

export function WatchOnboardingWizard({ onRunCreated }: WatchOnboardingWizardProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [brandName, setBrandName] = useState("");
  const [productName, setProductName] = useState("");
  const [seedUrl, setSeedUrl] = useState("");
  const [channels, setChannels] = useState<string[]>(DEFAULT_CHANNELS);
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
            Watch-first onboarding
          </p>
          <h1 className="mt-3 font-headline text-4xl font-black tracking-tight text-on-surface">
            Surveillez une marque avant même de connecter un compte officiel
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-on-surface-variant">
            Entrez une marque, ajoutez un seed public, puis lancez une collecte multi-source.
            Le flow reste compatible expo et directement réutilisable en bêta interne.
          </p>
        </div>
        <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-right">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
            Étape {step} / 2
          </p>
          <p className="mt-2 text-xs text-on-surface-variant">
            {step === 1 ? "Client et périmètre" : "Seeds et canaux"}
          </p>
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
                onChange={(event) => setBrandName(event.target.value)}
                placeholder="Cevital Elio"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
                Produit surveillé
              </label>
              <Input
                data-testid="input-product-name"
                value={productName}
                onChange={(event) => setProductName(event.target.value)}
                placeholder="Elio"
              />
            </div>
          </div>

          <aside className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Mots-clés suggérés
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
                  Les suggestions apparaîtront dès que la marque est renseignée.
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
                Une page publique aide la première collecte. Le produit reste utile même sans OAuth.
              </p>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                  Canaux activés
                </p>
                <div className="mt-4 space-y-3 text-sm">
                  <label className="flex items-center gap-3">
                    <input
                      data-testid="checkbox-channel-public_url_seed"
                      type="checkbox"
                      checked={channels.includes("public_url_seed")}
                      onChange={() => toggleChannel("public_url_seed")}
                    />
                    <span>Page publique seed</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      data-testid="checkbox-channel-web_search"
                      type="checkbox"
                      checked={channels.includes("web_search")}
                      onChange={() => toggleChannel("web_search")}
                    />
                    <span>Recherche web</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={channels.includes("youtube")}
                      onChange={() => toggleChannel("youtube")}
                    />
                    <span>YouTube</span>
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={channels.includes("google_maps")}
                      onChange={() => toggleChannel("google_maps")}
                    />
                    <span>Google Maps</span>
                  </label>
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
                  <option value="fr">Français</option>
                  <option value="ar">Arabe</option>
                  <option value="en">Anglais</option>
                </select>
                <p className="mt-2 text-xs leading-5 text-on-surface-variant">
                  Préselection par défaut : français et arabe. Vous pouvez ajouter ou retirer des langues.
                </p>
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
