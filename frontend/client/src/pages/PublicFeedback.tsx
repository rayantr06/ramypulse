import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, ImagePlus, Mic2, Pause, ShieldCheck, Star } from "lucide-react";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "wouter";
import { z } from "zod";

import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useListeningPoints, useSubmitListeningPointFeedback } from "@/hooks/useListeningPoints";

const feedbackSchema = z.object({
  rating: z.coerce.number().int().min(1, "Choisissez une note.").max(5),
  text: z.string().trim().max(1_500, "Votre message est trop long."),
  imageName: z.string().nullable(),
  audioDurationSeconds: z.number().int().positive().nullable(),
  consent: z.boolean().refine(Boolean, "Votre consentement est requis."),
});

type FeedbackValues = z.infer<typeof feedbackSchema>;

export default function PublicFeedback() {
  const { token } = useParams<{ token: string }>();
  const pointsQuery = useListeningPoints();
  const point = pointsQuery.data?.find((item) => item.token === token) ?? null;
  const submitFeedback = useSubmitListeningPointFeedback();
  const [submitted, setSubmitted] = useState(false);
  const [recordingStartedAt, setRecordingStartedAt] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const form = useForm<FeedbackValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      text: "",
      imageName: null,
      audioDurationSeconds: null,
      consent: false,
    },
  });
  const rating = form.watch("rating");
  const imageName = form.watch("imageName");
  const audioDurationSeconds = form.watch("audioDurationSeconds");

  function stopAudioTimer() {
    if (recordingStartedAt === null) return;
    const duration = Math.max(1, Math.round((Date.now() - recordingStartedAt) / 1_000));
    form.setValue("audioDurationSeconds", duration, { shouldValidate: true });
    setRecordingStartedAt(null);
  }

  function submit(values: FeedbackValues) {
    if (!point) return;
    form.clearErrors(["rating", "text"]);
    const hasEnabledResponse = Boolean(
      (point.channels.text && values.text)
      || (point.channels.image && values.imageName)
      || (point.channels.audio && values.audioDurationSeconds),
    );
    if (!hasEnabledResponse) {
      form.setError("text", { message: "Utilisez au moins un canal de réponse activé." });
      return;
    }
    const channels = [
      "rating",
      ...(point.channels.text && values.text ? ["text"] : []),
      ...(point.channels.image && values.imageName ? ["image"] : []),
      ...(point.channels.audio && values.audioDurationSeconds ? ["audio"] : []),
    ];
    submitFeedback.mutate(
      {
        listeningPointId: point.id,
        rating: values.rating,
        text: values.text,
        channels,
        imageName: values.imageName,
        audioDurationSeconds: values.audioDurationSeconds,
        consent: values.consent,
      },
      { onSuccess: () => setSubmitted(true) },
    );
  }

  if (pointsQuery.isLoading) {
    return <main className="flex min-h-screen items-center justify-center bg-surface-container-lowest text-sm text-on-surface-variant">Ouverture du formulaire…</main>;
  }

  if (!point || point.status !== "active") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface-container-lowest p-5 text-on-surface">
        <section className="w-full max-w-md rounded-[2rem] border border-outline-variant bg-surface p-7 text-center shadow-ambient">
          <BrandMark />
          <h1 className="mt-8 font-headline text-2xl font-semibold">Collecte indisponible</h1>
          <p className="mt-3 text-sm leading-6 text-on-surface-variant">Ce point d’écoute est en pause, fermé ou son lien n’est plus valide.</p>
        </section>
      </main>
    );
  }

  if (submitted) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface-container-lowest p-5 text-on-surface">
        <section className="w-full max-w-md rounded-[2rem] border border-outline-variant bg-surface p-7 text-center shadow-ambient">
          <BrandMark />
          <span className="mx-auto mt-8 flex h-16 w-16 items-center justify-center rounded-full bg-action-container text-action">
            <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
          </span>
          <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.15em] text-action">Retour enregistré localement</p>
          <h1 className="mt-2 font-headline text-3xl font-semibold">Merci, votre retour compte.</h1>
          <div className="mt-6 rounded-2xl border border-monitor/20 bg-monitor-container p-4 text-left">
            <p className="font-headline text-base font-semibold text-monitor">En attente d’analyse</p>
            <p className="mt-2 text-xs leading-5 text-on-surface-variant">Le retour apparaîtra dans le point d’écoute avec ce statut jusqu’à sa vérification.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-surface-container-lowest px-4 py-6 text-on-surface sm:py-10">
      <section className="mx-auto w-full max-w-lg overflow-hidden rounded-[2rem] border border-outline-variant bg-surface shadow-ambient">
        <header className="border-b border-outline-variant px-5 py-6 sm:px-7">
          <div className="flex items-center justify-between gap-4">
            <BrandMark />
            <span className="rounded-full bg-primary-container px-3 py-1.5 text-[9px] font-bold text-primary">Canal officiel</span>
          </div>
          <p className="mt-8 text-[10px] font-bold uppercase tracking-[0.15em] text-primary">{point.name}</p>
          <h1 className="mt-2 font-headline text-3xl font-semibold leading-tight">Comment s’est passée votre expérience ?</h1>
          <p className="mt-3 text-sm leading-6 text-on-surface-variant">Une minute suffit. Votre retour reste privé.</p>
        </header>

        <form className="space-y-6 px-5 py-6 sm:px-7" onSubmit={form.handleSubmit(submit)} data-testid="public-feedback-form">
          <fieldset>
            <legend className="text-sm font-semibold">Votre note</legend>
            <div className="mt-3 grid grid-cols-5 gap-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <label key={value} className="relative block cursor-pointer">
                  <input
                    type="radio"
                    value={value}
                    aria-label={`${value} étoile${value > 1 ? "s" : ""}`}
                    className="peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                    {...form.register("rating", { valueAsNumber: true })}
                  />
                  <span className="flex aspect-square items-center justify-center rounded-2xl border border-outline-variant bg-surface-container-low text-on-surface-variant transition-colors peer-checked:border-primary peer-checked:bg-primary peer-checked:text-primary-foreground">
                    <Star className="h-5 w-5" fill={typeof rating === "number" && value <= rating ? "currentColor" : "none"} aria-hidden="true" />
                  </span>
                </label>
              ))}
            </div>
            {form.formState.errors.rating ? <p className="mt-2 text-xs text-destructive">{form.formState.errors.rating.message}</p> : null}
          </fieldset>

          {point.channels.text ? <section>
            <label htmlFor="feedback-message" className="text-sm font-semibold">Votre message</label>
            <Textarea
              id="feedback-message"
              rows={5}
              maxLength={1_500}
              className="mt-3 resize-none rounded-2xl bg-surface-container-low text-base"
              placeholder="Qu’est-ce qui s’est bien ou mal passé ? كيفاش كانت تجربتك؟"
              {...form.register("text")}
            />
            {form.formState.errors.text ? <p className="mt-2 text-xs text-destructive">{form.formState.errors.text.message}</p> : null}
          </section> : null}

          {point.channels.audio || point.channels.image ? <div className="grid gap-3 sm:grid-cols-2">
            {point.channels.audio ? <section className="rounded-2xl border border-outline-variant bg-surface-container-low p-4">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-container text-primary"><Mic2 className="h-4 w-4" aria-hidden="true" /></span>
                <div>
                  <p className="text-xs font-semibold">Durée audio locale</p>
                  <p className="mt-1 text-[9px] leading-4 text-on-surface-variant">Aucun octet audio n’est enregistré ou téléversé.</p>
                </div>
              </div>
              {recordingStartedAt === null ? (
                <Button className="mt-4 w-full" type="button" variant="outline" onClick={() => setRecordingStartedAt(Date.now())}>
                  {audioDurationSeconds ? "Rechronométrer" : "Chronométrer"}
                </Button>
              ) : (
                <Button className="mt-4 w-full" type="button" variant="destructive" onClick={stopAudioTimer}>
                  <Pause className="mr-2 h-4 w-4" aria-hidden="true" />Arrêter
                </Button>
              )}
              {audioDurationSeconds ? <p className="mt-2 text-center text-[10px] text-on-surface-variant">{audioDurationSeconds} s conservées</p> : null}
            </section> : null}

            {point.channels.image ? <section className="rounded-2xl border border-outline-variant bg-surface-container-low p-4">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-insight-container text-insight"><ImagePlus className="h-4 w-4" aria-hidden="true" /></span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold">Nom du fichier photo</p>
                  <p className="mt-1 text-[9px] leading-4 text-on-surface-variant">La photo elle-même n’est pas téléversée.</p>
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="sr-only"
                aria-label="Choisir une photo"
                onChange={(event) => form.setValue("imageName", event.target.files?.[0]?.name ?? null, { shouldValidate: true })}
              />
              <Button className="mt-4 w-full" type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                {imageName ? "Changer le fichier" : "Choisir un fichier"}
              </Button>
              {imageName ? <p className="mt-2 truncate text-center text-[10px] text-on-surface-variant">{imageName}</p> : null}
            </section> : null}
          </div> : null}

          {!point.channels.text && form.formState.errors.text ? <p className="text-xs text-destructive">{form.formState.errors.text.message}</p> : null}

          <label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-surface-container-low p-4">
            <input type="checkbox" className="mt-0.5 h-4 w-4 accent-primary" {...form.register("consent")} />
            <span className="text-[10px] leading-5 text-on-surface-variant">J’accepte que ce retour soit analysé pour améliorer le produit ou le service.</span>
          </label>
          {form.formState.errors.consent ? <p className="text-xs text-destructive">{form.formState.errors.consent.message}</p> : null}

          <Button type="submit" size="lg" className="w-full rounded-2xl" disabled={submitFeedback.isPending}>
            {submitFeedback.isPending ? "Enregistrement…" : "Envoyer mon retour"}
          </Button>
          <p className="flex items-center justify-center gap-2 text-center text-[9px] text-on-surface-variant">
            <ShieldCheck className="h-3.5 w-3.5 text-action" aria-hidden="true" />
            Retour privé · aucune publication externe
          </p>
        </form>
      </section>
    </main>
  );
}
