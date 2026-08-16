import { ArrowRight, Radar } from "lucide-react";
import { Link } from "wouter";

interface EmptyTenantStateProps {
  title: string;
  description: string;
}

export function EmptyTenantState({ title, description }: EmptyTenantStateProps) {
  return (
    <div className="workspace-grid overflow-hidden rounded-3xl border border-outline-variant/55 bg-surface-container-low p-7 sm:p-10">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-pulse-glow">
        <Radar className="h-6 w-6" aria-hidden="true" />
      </div>
      <p className="mt-6 text-[9px] font-bold uppercase tracking-[0.2em] text-primary">
        Premier signal
      </p>
      <h3 className="mt-3 max-w-2xl font-headline text-2xl font-extrabold tracking-tight text-on-surface sm:text-3xl">
        {title}
      </h3>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-on-surface-variant">
        {description}
      </p>
      <div className="mt-7 flex flex-wrap items-center gap-4">
        <Link
          href="/watchlists/new"
          className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-pulse-glow"
        >
          Créer une surveillance
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
        <span className="max-w-md text-xs leading-5 text-on-surface-variant">
          Choisissez un sujet, ses mots-clés et les sources publiques ou connectées à écouter.
        </span>
      </div>
    </div>
  );
}
