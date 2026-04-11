import { Link } from "wouter";

interface EmptyTenantStateProps {
  title: string;
  description: string;
}

export function EmptyTenantState({ title, description }: EmptyTenantStateProps) {
  return (
    <div className="rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.18)]">
      <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-primary">
        Tenant en cours d'initialisation
      </p>
      <h3 className="mt-3 font-headline text-2xl font-black tracking-tight text-on-surface">
        {title}
      </h3>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
        {description}
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Link href="/nouveau-client">
          <a className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-primary-foreground">
            Nouveau client
          </a>
        </Link>
        <span className="text-xs text-on-surface-variant">
          Lancez une watchlist pour remplir progressivement le dashboard, l'explorer et les alertes.
        </span>
      </div>
    </div>
  );
}
