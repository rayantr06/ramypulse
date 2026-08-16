import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  parseDelimitedWatchValues,
  suggestWatchKeywords,
  type WatchWizardInput,
} from "@/lib/watchWizard";

const SUBJECT_OPTIONS = [
  { value: "keyword", label: "Sujet", icon: "travel_explore" },
  { value: "brand", label: "Marque", icon: "brand_awareness" },
  { value: "product", label: "Produit", icon: "inventory_2" },
  { value: "campaign", label: "Campagne", icon: "campaign" },
  { value: "publication", label: "Publication", icon: "link" },
  { value: "competitor", label: "Concurrent", icon: "compare_arrows" },
] as const;

const CHANNEL_OPTIONS = [
  {
    value: "web_search",
    label: "Web",
    detail: "Recherche adaptative",
    capability: "Disponible",
  },
  {
    value: "public_url_seed",
    label: "URL publique",
    detail: "Page ou publication precise",
    capability: "Acces direct",
  },
  {
    value: "google_maps",
    label: "Google Maps",
    detail: "Avis d'etablissements",
    capability: "Disponible",
  },
  {
    value: "youtube",
    label: "YouTube",
    detail: "Videos et commentaires",
    capability: "Disponible",
  },
  {
    value: "facebook",
    label: "Facebook",
    detail: "Pages et publications publiques",
    capability: "Apify / OAuth",
  },
  {
    value: "instagram",
    label: "Instagram",
    detail: "Profils et publications publiques",
    capability: "Apify / OAuth",
  },
  {
    value: "press",
    label: "Presse",
    detail: "Articles et actualites",
    capability: "Discovery",
  },
  {
    value: "reddit",
    label: "Reddit",
    detail: "Discussions publiques",
    capability: "Discovery",
  },
] as const;

const watchScopeSchema = z.object({
  name: z.string().trim().min(1, "Donnez un nom a cette surveillance."),
  description: z.string(),
  subject_type: z.enum([
    "keyword",
    "brand",
    "product",
    "campaign",
    "publication",
    "competitor",
  ]),
  brand_name: z.string(),
  product_name: z.string(),
  keywords_text: z
    .string()
    .refine(
      (value) => parseDelimitedWatchValues(value).length > 0,
      "Ajoutez au moins un mot-cle.",
    ),
  excluded_keywords_text: z.string(),
  seed_urls_text: z.string(),
  competitors_text: z.string(),
  regions_text: z.string(),
  channels: z.array(z.string()).min(1, "Sélectionnez au moins une source."),
  languages: z.array(z.string()),
  period_days: z.number().int().min(1).max(365),
  min_volume: z.number().int().min(0).max(1_000_000),
});

type WatchScopeFormValues = z.infer<typeof watchScopeSchema>;

export interface WatchScopeSubmitValue {
  payload: WatchWizardInput;
  requestedChannels: string[];
}

interface WatchScopeFormProps {
  isSubmitting?: boolean;
  presentation?: "card" | "drawer";
  onCancel: () => void;
  onSubmit: (value: WatchScopeSubmitValue) => void;
}

const DEFAULT_VALUES: WatchScopeFormValues = {
  name: "",
  description: "",
  subject_type: "keyword",
  brand_name: "",
  product_name: "",
  keywords_text: "",
  excluded_keywords_text: "",
  seed_urls_text: "",
  competitors_text: "",
  regions_text: "",
  channels: ["web_search", "public_url_seed"],
  languages: ["fr", "ar"],
  period_days: 30,
  min_volume: 5,
};

function FieldLabel({ children }: { children: string }) {
  return (
    <label className="text-[10px] font-bold uppercase tracking-[0.18em] text-on-surface-variant">
      {children}
    </label>
  );
}

function ErrorText({ message }: { message?: string }) {
  return message ? <p className="text-xs text-error">{message}</p> : null;
}

export function WatchScopeForm({
  isSubmitting = false,
  presentation = "card",
  onCancel,
  onSubmit,
}: WatchScopeFormProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [keywordsWereEdited, setKeywordsWereEdited] = useState(false);
  const form = useForm<WatchScopeFormValues>({
    resolver: zodResolver(watchScopeSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const brandName = form.watch("brand_name");
  const productName = form.watch("product_name");
  const keywordsText = form.watch("keywords_text");
  const subjectType = form.watch("subject_type");
  const channels = form.watch("channels");
  const languages = form.watch("languages");

  useEffect(() => {
    if (keywordsWereEdited) {
      return;
    }

    const suggestions = suggestWatchKeywords(brandName, productName);
    form.setValue("keywords_text", suggestions.join(", "));
  }, [brandName, form, keywordsWereEdited, productName]);

  const keywordPreview = useMemo(
    () => parseDelimitedWatchValues(keywordsText),
    [keywordsText],
  );

  const toggleListValue = (
    field: "channels" | "languages",
    value: string,
  ) => {
    const current = form.getValues(field);
    form.setValue(
      field,
      current.includes(value)
        ? current.filter((candidate) => candidate !== value)
        : [...current, value],
      { shouldValidate: true },
    );
  };

  const goToCoverage = async () => {
    const valid = await form.trigger(["name", "subject_type", "keywords_text"]);
    if (valid) {
      setStep(2);
    }
  };

  const submit = form.handleSubmit((values) => {
    onSubmit({
      payload: {
        name: values.name,
        description: values.description,
        subject_type: values.subject_type,
        brand_name: values.brand_name,
        product_name: values.product_name,
        keywords: parseDelimitedWatchValues(values.keywords_text),
        excluded_keywords: parseDelimitedWatchValues(values.excluded_keywords_text),
        seed_urls: parseDelimitedWatchValues(values.seed_urls_text),
        competitors: parseDelimitedWatchValues(values.competitors_text),
        channels: values.channels,
        languages: values.languages,
        regions: parseDelimitedWatchValues(values.regions_text),
        period_days: values.period_days,
        min_volume: values.min_volume,
      },
      requestedChannels: values.channels,
    });
  });

  return (
    <form
      onSubmit={submit}
      className={`col-span-full overflow-hidden bg-surface-container ${
        presentation === "drawer"
          ? "min-h-full"
          : "rounded-2xl border border-primary/20 shadow-2xl"
      }`}
      data-testid="watch-scope-form"
    >
      <div className="grid border-b border-outline-variant/15 xl:grid-cols-[1fr_auto]">
        <div className="p-6 xl:p-8">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
            Nouvelle surveillance
          </p>
          <h2 className="mt-3 font-headline text-2xl font-black tracking-tight text-on-surface">
            Définissez le signal, puis choisissez où l’écouter
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant">
            Les mots-clés pilotent la collecte. Les sources publiques, les comptes connectés et
            les connecteurs externes restent visibles séparément.
          </p>
        </div>
        <div className="flex items-center gap-3 border-t border-outline-variant/15 px-6 py-4 xl:border-l xl:border-t-0">
          {[1, 2].map((item) => (
            <div key={item} className="flex items-center gap-2">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-black ${
                  step === item
                    ? "border-primary bg-primary text-on-primary-fixed"
                    : "border-outline-variant/20 bg-surface-container-high text-on-surface-variant"
                }`}
              >
                {item}
              </span>
              <span className="text-[10px] font-semibold text-on-surface-variant sm:text-xs">
                {item === 1 ? "Signal" : "Couverture"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {step === 1 ? (
        <div className="grid gap-8 p-6 xl:grid-cols-[0.85fr_1.15fr] xl:p-8">
          <section className="space-y-5">
            <div className="space-y-2">
              <FieldLabel>Nom de la surveillance</FieldLabel>
              <Input
                {...form.register("name")}
                data-testid="input-watchlist-name"
                placeholder="Reputation produit Elio"
              />
              <ErrorText message={form.formState.errors.name?.message} />
            </div>

            <div className="space-y-2">
              <FieldLabel>Contexte de surveillance (optionnel)</FieldLabel>
              <Textarea
                {...form.register("description")}
                placeholder="Suivre les avis sur le lancement et detecter les signaux de disponibilite."
                className="min-h-20"
              />
            </div>

            <div className="space-y-2">
              <FieldLabel>Objectif</FieldLabel>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {SUBJECT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={subjectType === option.value}
                    onClick={() => form.setValue("subject_type", option.value)}
                    className={`flex items-center gap-2 rounded-xl border px-3 py-3 text-left text-xs font-semibold transition-colors ${
                      subjectType === option.value
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-outline-variant/15 bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <span className="material-symbols-outlined text-base">{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <FieldLabel>Marque ou organisation</FieldLabel>
                <Input {...form.register("brand_name")} placeholder="Cevital" />
              </div>
              <div className="space-y-2">
                <FieldLabel>Produit ou campagne</FieldLabel>
                <Input {...form.register("product_name")} placeholder="Elio" />
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                  Requête de surveillance
                </p>
                <p className="mt-2 text-xs leading-5 text-on-surface-variant">
                  Séparez les expressions par une virgule ou une nouvelle ligne.
                </p>
              </div>
              <span className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-primary">
                {keywordPreview.length} signal{keywordPreview.length > 1 ? "s" : ""}
              </span>
            </div>

            <div className="mt-5 space-y-2">
              <FieldLabel>Mots-clés inclus</FieldLabel>
              <Textarea
                {...form.register("keywords_text", {
                  onChange: () => setKeywordsWereEdited(true),
                })}
                data-testid="input-watch-keywords"
                placeholder="elio, huile elio, cevital elio"
                className="min-h-28"
              />
              <ErrorText message={form.formState.errors.keywords_text?.message} />
            </div>

            {keywordPreview.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2" aria-label="Mots-clés actifs">
                {keywordPreview.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-full border border-primary/20 bg-surface-container px-3 py-1 text-xs text-on-surface"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            ) : null}

            <div className="mt-5 space-y-2">
              <FieldLabel>Mots-clés exclus</FieldLabel>
              <Input
                {...form.register("excluded_keywords_text")}
                data-testid="input-watch-excluded-keywords"
                placeholder="emploi, recrutement, stage"
              />
            </div>
          </section>
        </div>
      ) : (
        <div className="grid gap-8 p-6 xl:grid-cols-[1.2fr_0.8fr] xl:p-8">
          <section>
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                  Sources de collecte
                </p>
                <p className="mt-2 text-sm text-on-surface-variant">
                  Activez uniquement les canaux utiles à cette surveillance.
                </p>
              </div>
              <span className="text-xs font-semibold text-on-surface-variant">
                {channels.length} active{channels.length > 1 ? "s" : ""}
              </span>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {CHANNEL_OPTIONS.map((channel) => {
                const selected = channels.includes(channel.value);
                return (
                  <button
                    key={channel.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleListValue("channels", channel.value)}
                    className={`rounded-2xl border p-4 text-left transition-colors ${
                      selected
                        ? "border-primary/40 bg-primary/10"
                        : "border-outline-variant/15 bg-surface-container-high hover:border-outline-variant/30"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-bold text-on-surface">{channel.label}</p>
                        <p className="mt-1 text-xs text-on-surface-variant">{channel.detail}</p>
                      </div>
                      <span
                        className={`material-symbols-outlined text-lg ${
                          selected ? "text-primary" : "text-on-surface-variant"
                        }`}
                      >
                        {selected ? "check_circle" : "radio_button_unchecked"}
                      </span>
                    </div>
                    <p className="mt-4 text-[10px] font-bold uppercase tracking-wider text-primary">
                      {channel.capability}
                    </p>
                  </button>
                );
              })}
            </div>
            <ErrorText message={form.formState.errors.channels?.message} />
          </section>

          <section className="space-y-5 rounded-2xl border border-outline-variant/15 bg-surface-container-high p-5">
            <div className="space-y-2">
              <FieldLabel>URLs de départ</FieldLabel>
              <Textarea
                {...form.register("seed_urls_text")}
                data-testid="input-watch-seed-urls"
                placeholder={"https://example.com/publication\nhttps://example.com/produit"}
              />
            </div>

            <div className="space-y-2">
              <FieldLabel>Concurrents</FieldLabel>
              <Input {...form.register("competitors_text")} placeholder="Ifri, Hamoud" />
            </div>

            <div className="space-y-2">
              <FieldLabel>Régions ou wilayas</FieldLabel>
              <Input
                {...form.register("regions_text")}
                data-testid="input-watch-regions"
                placeholder="Alger, Oran, Constantine"
              />
            </div>

            <div className="space-y-2">
              <FieldLabel>Langues</FieldLabel>
              <div className="flex flex-wrap gap-2">
                {[
                    ["fr", "Français"],
                  ["ar", "Arabe / Daridja"],
                  ["en", "Anglais"],
                ].map(([value, label]) => {
                  const selected = languages.includes(value);
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggleListValue("languages", value)}
                      className={`rounded-full border px-3 py-2 text-xs font-semibold ${
                        selected
                          ? "border-primary/40 bg-primary/10 text-primary"
                          : "border-outline-variant/15 text-on-surface-variant"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <FieldLabel>Fenêtre (jours)</FieldLabel>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  {...form.register("period_days", { valueAsNumber: true })}
                  data-testid="input-watch-period-days"
                />
              </div>
              <div className="space-y-2">
                <FieldLabel>Seuil volume</FieldLabel>
                <Input
                  type="number"
                  min={0}
                  {...form.register("min_volume", { valueAsNumber: true })}
                  data-testid="input-watch-min-volume"
                />
              </div>
            </div>
          </section>
        </div>
      )}

      <div className={`flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant/15 bg-surface-container-high px-6 py-4 xl:px-8 ${presentation === "drawer" ? "sticky bottom-0 z-10" : ""}`}>
        <Button type="button" variant="outline" onClick={step === 1 ? onCancel : () => setStep(1)}>
          {step === 1 ? "Annuler" : "Retour au signal"}
        </Button>
        {step === 1 ? (
          <Button
            key="watch-scope-next"
            type="button"
            onClick={(event) => {
              event.preventDefault();
              void goToCoverage();
            }}
            data-testid="btn-next-watch-scope"
          >
            Choisir les sources
          </Button>
        ) : (
          <Button
            key="watch-scope-submit"
            type="submit"
            disabled={isSubmitting}
            data-testid="btn-submit-watchlist"
          >
            {isSubmitting ? "Lancement..." : "Créer et lancer la collecte"}
          </Button>
        )}
      </div>
    </form>
  );
}
