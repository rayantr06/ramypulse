import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Check, ChevronDown, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { V3Monitor, V3SourcePlatform } from "@shared/v3";

const SOURCE_OPTIONS: Array<{ id: V3SourcePlatform; label: string; note: string }> = [
  { id: "facebook", label: "Facebook", note: "Pages et publications publiques" },
  { id: "tiktok", label: "TikTok", note: "Publications et commentaires publics" },
  { id: "youtube", label: "YouTube", note: "API officielle" },
  { id: "google_maps", label: "Google Maps", note: "Fournisseur pilote remplaçable" },
];

const schema = z.object({
  targetName: z.string().trim().min(2, "Indiquez une cible précise.").max(160),
  objective: z.enum(["customer_experience", "reputation", "campaign", "competition", "issue"]),
  objectiveText: z.string().trim().min(6, "Décrivez le résultat recherché en une phrase.").max(500),
  sources: z.array(z.enum(["facebook", "tiktok", "youtube", "google_maps"])).min(1, "Choisissez au moins une source."),
});

type FormValues = z.infer<typeof schema>;

export interface V3MonitorCreateValue {
  name: string;
  objective: V3Monitor["objective"];
  target_type: V3Monitor["targetType"];
  target_name: string;
  aliases: string[];
  exclusions: string[];
  languages: string[];
  territories: string[];
  sources: V3SourcePlatform[];
  competitors: string[];
  frequency_minutes: number;
  max_monthly_documents: number;
  max_monthly_cost_dzd: number;
}

interface Props {
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (value: V3MonitorCreateValue) => void;
}

function splitTerms(value: string): string[] {
  return Array.from(new Set(value.split(",").map((term) => term.trim()).filter(Boolean)));
}

export function V3MonitorComposer({ isSubmitting, onCancel, onSubmit }: Props) {
  const [prepared, setPrepared] = useState<FormValues | null>(null);
  const [aliases, setAliases] = useState("");
  const [exclusions, setExclusions] = useState("recrutement, emploi");
  const [territories, setTerritories] = useState("Algérie");
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { targetName: "", objective: "reputation", objectiveText: "", sources: ["facebook", "youtube", "google_maps"] },
  });

  function prepare(values: FormValues) {
    setAliases([values.targetName, values.targetName.replaceAll(" ", ""), values.targetName.split(" ").map((part) => part[0]).join("")].filter(Boolean).join(", "));
    setPrepared(values);
  }

  function submit() {
    if (!prepared) return;
    const typeByObjective: Record<V3Monitor["objective"], V3Monitor["targetType"]> = {
      customer_experience: "organization", reputation: "brand", campaign: "campaign", competition: "competitor", issue: "subject",
    };
    onSubmit({
      name: `${prepared.targetName} · ${prepared.objectiveText.slice(0, 54)}`,
      objective: prepared.objective,
      target_type: typeByObjective[prepared.objective],
      target_name: prepared.targetName,
      aliases: splitTerms(aliases),
      exclusions: splitTerms(exclusions),
      languages: ["fr", "ar", "darija", "arabizi"],
      territories: splitTerms(territories),
      sources: prepared.sources,
      competitors: [],
      frequency_minutes: 360,
      max_monthly_documents: 100_000,
      max_monthly_cost_dzd: 50_000,
    });
  }

  return (
    <div className="min-h-full bg-surface px-5 py-6 sm:px-8 sm:py-8">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between"><div><h2 className="font-headline text-2xl font-bold">Nouvelle surveillance</h2><p className="mt-1 text-xs text-on-surface-variant">Trois décisions, puis une vérification.</p></div><Button variant="ghost" size="icon" onClick={onCancel} aria-label="Fermer"><X className="h-4 w-4" /></Button></div>
        {!prepared ? (
          <Form {...form}>
            <form className="mt-7 space-y-6" onSubmit={form.handleSubmit(prepare)}>
              <FormField control={form.control} name="targetName" render={({ field }) => <FormItem><FormLabel>1. Cible</FormLabel><FormControl><Input {...field} className="h-12 rounded-xl bg-surface-container-low" placeholder="Marque, organisation, produit, campagne, concurrent ou sujet" autoFocus /></FormControl><FormMessage /></FormItem>} />
              <div className="grid gap-3 sm:grid-cols-[13rem_minmax(0,1fr)]">
                <FormField control={form.control} name="objective" render={({ field }) => <FormItem><FormLabel>2. Objectif</FormLabel><Select value={field.value} onValueChange={field.onChange}><FormControl><SelectTrigger className="h-12 rounded-xl bg-surface-container-low"><SelectValue /></SelectTrigger></FormControl><SelectContent><SelectItem value="customer_experience">Expérience client</SelectItem><SelectItem value="reputation">Réputation</SelectItem><SelectItem value="campaign">Campagne</SelectItem><SelectItem value="competition">Concurrence</SelectItem><SelectItem value="issue">Sujet / risque</SelectItem></SelectContent></Select><FormMessage /></FormItem>} />
                <FormField control={form.control} name="objectiveText" render={({ field }) => <FormItem><FormLabel>Résultat recherché</FormLabel><FormControl><Textarea {...field} className="min-h-24 resize-none rounded-xl bg-surface-container-low" placeholder="Ex. détecter rapidement les problèmes récurrents de service client" /></FormControl><FormMessage /></FormItem>} />
              </div>
              <FormField control={form.control} name="sources" render={() => <FormItem><FormLabel>3. Sources</FormLabel><div className="grid gap-2 sm:grid-cols-2">{SOURCE_OPTIONS.map((source) => <FormField key={source.id} control={form.control} name="sources" render={({ field }) => { const checked = field.value.includes(source.id); return <label className={`flex min-h-16 cursor-pointer items-center gap-3 rounded-xl border p-3 transition-colors ${checked ? "border-primary bg-primary-container" : "border-outline-variant bg-surface"}`}><Checkbox checked={checked} onCheckedChange={(next) => field.onChange(next ? [...field.value, source.id] : field.value.filter((value) => value !== source.id))} /><span><strong className="block text-xs text-on-surface">{source.label}</strong><small className="mt-0.5 block text-[9px] text-on-surface-variant">{source.note}</small></span></label>; }} />)}</div><FormMessage /></FormItem>} />
              <div className="flex flex-col-reverse gap-2 border-t border-outline-variant pt-5 sm:flex-row sm:justify-between"><Button variant="ghost" type="button" onClick={onCancel}>Annuler</Button><Button type="submit"><Sparkles className="mr-2 h-4 w-4" />Préparer le périmètre</Button></div>
            </form>
          </Form>
        ) : (
          <section className="mt-7">
            <div className="rounded-2xl bg-action-container p-5"><div className="flex items-center gap-2 text-sm font-semibold text-action"><Check className="h-4 w-4" />Périmètre préparé</div><p className="mt-2 text-xs leading-5 text-on-action-container">LIDAL a proposé les variantes linguistiques et les exclusions. Confirmez-les avant la première collecte.</p></div>
            <dl className="mt-5 divide-y divide-outline-variant border-y border-outline-variant text-sm"><div className="grid gap-1 py-4 sm:grid-cols-[9rem_1fr]"><dt className="text-[10px] font-semibold text-on-surface-variant">Cible</dt><dd className="font-semibold">{prepared.targetName}</dd></div><div className="grid gap-1 py-4 sm:grid-cols-[9rem_1fr]"><dt className="text-[10px] font-semibold text-on-surface-variant">Objectif</dt><dd>{prepared.objectiveText}</dd></div><div className="grid gap-1 py-4 sm:grid-cols-[9rem_1fr]"><dt className="text-[10px] font-semibold text-on-surface-variant">Sources</dt><dd>{prepared.sources.map((source) => SOURCE_OPTIONS.find((item) => item.id === source)?.label).join(" · ")}</dd></div></dl>
            <Collapsible className="mt-5 rounded-2xl border border-outline-variant bg-surface-container-low"><CollapsibleTrigger className="flex min-h-12 w-full items-center justify-between px-4 text-xs font-semibold">Réglages avancés générés <ChevronDown className="h-4 w-4" /></CollapsibleTrigger><CollapsibleContent className="space-y-4 border-t border-outline-variant p-4"><label className="block text-[10px] font-semibold text-on-surface-variant">Alias et variantes<Input value={aliases} onChange={(event) => setAliases(event.target.value)} className="mt-1.5 bg-surface" /></label><label className="block text-[10px] font-semibold text-on-surface-variant">Exclusions<Input value={exclusions} onChange={(event) => setExclusions(event.target.value)} className="mt-1.5 bg-surface" /></label><label className="block text-[10px] font-semibold text-on-surface-variant">Territoires<Input value={territories} onChange={(event) => setTerritories(event.target.value)} className="mt-1.5 bg-surface" /></label><p className="text-[9px] leading-4 text-on-surface-variant">Langues : français, arabe, darija et arabizi · collecte toutes les 6 h · arrêt automatique à 100 000 documents ou 50 000 DA/mois.</p></CollapsibleContent></Collapsible>
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-between"><Button variant="ghost" onClick={() => setPrepared(null)}>Modifier les trois choix</Button><Button disabled={isSubmitting} onClick={submit}>{isSubmitting ? "Création…" : "Confirmer et lancer"}</Button></div>
          </section>
        )}
      </div>
    </div>
  );
}
