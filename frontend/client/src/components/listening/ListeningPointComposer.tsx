import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, ImagePlus, MessageSquareText, Mic2, QrCode, Star } from "lucide-react";
import { useForm } from "react-hook-form";
import { useLocation } from "wouter";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateListeningPoint } from "@/hooks/useListeningPoints";

const composerSchema = z.object({
  targetType: z.enum(["product", "location", "service", "campaign"]),
  targetName: z.string().trim().min(2, "Précisez la cible du QR."),
  internalName: z.string().trim().min(2, "Donnez un nom interne au point d’écoute."),
  responsiblePerson: z.string().trim().min(2, "Indiquez la personne responsable."),
  channels: z.object({
    rating: z.boolean(),
    text: z.boolean(),
    audio: z.boolean(),
    image: z.boolean(),
  }),
  lowRatingAlert: z.boolean(),
  alertThreshold: z.coerce.number().int().min(1).max(3),
}).refine(
  (value) => value.channels.text || value.channels.audio || value.channels.image,
  { path: ["channels"], message: "Activez au moins un canal de réponse." },
);

type ComposerValues = z.infer<typeof composerSchema>;

const TARGET_TYPES: Array<{ value: ComposerValues["targetType"]; label: string }> = [
  { value: "product", label: "Produit" },
  { value: "location", label: "Lieu" },
  { value: "service", label: "Service" },
  { value: "campaign", label: "Campagne" },
];

const CHANNELS = [
  { key: "rating" as const, label: "Note", description: "Évaluation de 1 à 5 étoiles", icon: Star },
  { key: "text" as const, label: "Texte", description: "Un message libre et multilingue", icon: MessageSquareText },
  { key: "audio" as const, label: "Audio", description: "Durée locale uniquement", icon: Mic2 },
  { key: "image" as const, label: "Photo", description: "Nom du fichier uniquement", icon: ImagePlus },
];

function createToken(values: ComposerValues): string {
  const slug = values.targetName
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 36) || values.targetType;
  const suffix = crypto.randomUUID().slice(0, 6);
  return `${slug}-${suffix}`;
}

export function ListeningPointComposer() {
  const [, setLocation] = useLocation();
  const createPoint = useCreateListeningPoint();
  const form = useForm<ComposerValues>({
    resolver: zodResolver(composerSchema),
    defaultValues: {
      targetType: "product",
      targetName: "",
      internalName: "",
      responsiblePerson: "Responsable expérience client",
      channels: { rating: true, text: true, audio: true, image: true },
      lowRatingAlert: true,
      alertThreshold: 2,
    },
  });
  const channels = form.watch("channels");
  const lowRatingAlert = form.watch("lowRatingAlert");

  function submit(values: ComposerValues) {
    createPoint.mutate(
      {
        name: values.internalName,
        token: createToken(values),
        status: "active",
        targetType: values.targetType,
        targetName: values.targetName,
        ownerName: values.responsiblePerson,
        channels: values.channels,
        alertEnabled: values.lowRatingAlert,
        alertThreshold: values.alertThreshold,
      },
      { onSuccess: () => setLocation("/listening-points") },
    );
  }

  return (
    <main className="min-h-screen bg-surface-container-lowest px-4 py-6 text-on-surface sm:px-6 lg:px-8">
      <section className="mx-auto max-w-3xl overflow-hidden rounded-[2rem] border border-outline-variant bg-surface shadow-ambient">
        <header className="border-b border-outline-variant px-5 py-6 sm:px-8">
          <button
            type="button"
            className="flex items-center gap-2 text-xs font-semibold text-on-surface-variant hover:text-primary"
            onClick={() => setLocation("/listening-points")}
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Retour aux points d’écoute
          </button>
          <div className="mt-6 flex items-start gap-4">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-pulse-glow">
              <QrCode className="h-6 w-6" aria-hidden="true" />
            </span>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary">Canal direct</p>
              <h1 className="mt-1 font-headline text-3xl font-semibold tracking-tight">Créer un point d’écoute</h1>
              <p className="mt-2 max-w-xl text-sm leading-6 text-on-surface-variant">
                Définissez précisément où le QR sera placé et comment les personnes pourront répondre.
              </p>
            </div>
          </div>
        </header>

        <form className="space-y-7 p-5 sm:p-8" onSubmit={form.handleSubmit(submit)}>
          <fieldset>
            <legend className="font-headline text-lg font-semibold">Cible du QR</legend>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {TARGET_TYPES.map((type) => (
                <label key={type.value} className="cursor-pointer">
                  <input className="peer sr-only" type="radio" value={type.value} {...form.register("targetType")} />
                  <span className="flex min-h-12 items-center justify-center rounded-2xl border border-outline-variant bg-surface-container-low px-3 text-xs font-semibold text-on-surface-variant transition-colors peer-checked:border-primary peer-checked:bg-primary-container peer-checked:text-primary">
                    {type.label}
                  </span>
                </label>
              ))}
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="target-name">Nom de la cible</Label>
                <Input id="target-name" placeholder="Ex. Boisson Leticia 1 L" {...form.register("targetName")} />
                {form.formState.errors.targetName ? <p className="text-xs text-destructive">{form.formState.errors.targetName.message}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="internal-name">Nom interne</Label>
                <Input id="internal-name" placeholder="Ex. QR emballage pilote" {...form.register("internalName")} />
                {form.formState.errors.internalName ? <p className="text-xs text-destructive">{form.formState.errors.internalName.message}</p> : null}
              </div>
            </div>
          </fieldset>

          <section className="border-t border-outline-variant pt-7">
            <h2 className="font-headline text-lg font-semibold">Routage</h2>
            <div className="mt-4 space-y-2">
              <Label htmlFor="responsible-person">Personne responsable</Label>
              <Input id="responsible-person" {...form.register("responsiblePerson")} />
              {form.formState.errors.responsiblePerson ? <p className="text-xs text-destructive">{form.formState.errors.responsiblePerson.message}</p> : null}
            </div>
            <label className="mt-4 flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-outline-variant bg-surface-container-low p-4">
              <span>
                <span className="flex items-center gap-2 text-sm font-semibold"><Star className="h-4 w-4 text-primary" aria-hidden="true" />Alerte sur note faible</span>
                <span className="mt-1 block text-xs leading-5 text-on-surface-variant">Signale immédiatement un retour sous le seuil choisi.</span>
              </span>
              <input className="mt-1 h-4 w-4 accent-primary" type="checkbox" {...form.register("lowRatingAlert")} />
            </label>
            {lowRatingAlert ? (
              <div className="mt-4 space-y-2">
                <Label htmlFor="alert-threshold">Alerter si la note est inférieure ou égale à</Label>
                <select id="alert-threshold" className="h-11 w-full rounded-xl border border-input bg-surface px-3 text-sm" {...form.register("alertThreshold")}>
                  <option value="1">1 étoile</option>
                  <option value="2">2 étoiles</option>
                  <option value="3">3 étoiles</option>
                </select>
              </div>
            ) : null}
          </section>

          <fieldset className="border-t border-outline-variant pt-7">
            <legend className="font-headline text-lg font-semibold">Canaux activés</legend>
            <p className="mt-1 text-xs leading-5 text-on-surface-variant">Activez les formats utiles et conservez au moins un moyen d’expression.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {CHANNELS.map((channel) => {
                const active = channels[channel.key];
                const Icon = channel.icon;
                return (
                  <label key={channel.key} className={`cursor-pointer rounded-2xl border p-4 transition-colors ${active ? "border-primary bg-primary-container" : "border-outline-variant bg-surface-container-low"}`}>
                    <input className="sr-only" type="checkbox" {...form.register(`channels.${channel.key}`)} />
                    <span className="flex items-center justify-between gap-2">
                      <Icon className={`h-4 w-4 ${active ? "text-primary" : "text-on-surface-variant"}`} aria-hidden="true" />
                      {active ? <Check className="h-4 w-4 text-primary" aria-hidden="true" /> : null}
                    </span>
                    <span className="mt-3 block text-sm font-semibold">{channel.label}</span>
                    <span className="mt-1 block text-[10px] leading-4 text-on-surface-variant">{channel.description}</span>
                  </label>
                );
              })}
            </div>
            {form.formState.errors.channels ? <p className="mt-2 text-xs text-destructive">{form.formState.errors.channels.message}</p> : null}
          </fieldset>

          <footer className="flex flex-col-reverse gap-3 border-t border-outline-variant pt-6 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setLocation("/listening-points")}>Annuler</Button>
            <Button type="submit" disabled={createPoint.isPending}>
              <QrCode className="mr-2 h-4 w-4" aria-hidden="true" />
              {createPoint.isPending ? "Création…" : "Créer le QR"}
            </Button>
          </footer>
        </form>
      </section>
    </main>
  );
}

export default ListeningPointComposer;
