import { Radio } from "lucide-react";

import { AppShell } from "@/components/AppShell";

export function TenantReadinessScreen() {
  return (
    <AppShell sidebarFooterSubtitle="Préparation de l’espace">
      <div className="mx-auto flex min-h-[70vh] max-w-4xl items-center px-4 py-10 sm:px-6 lg:px-8">
        <div
          data-testid="tenant-readiness-screen"
          className="w-full rounded-3xl border border-outline-variant/55 bg-surface-container-low p-7 sm:p-10"
        >
          <div className="flex items-center gap-3 text-primary">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10">
              <Radio className="h-5 w-5 animate-pulse" aria-hidden="true" />
            </span>
            <p className="text-[9px] font-bold uppercase tracking-[0.2em]">Préparation de votre espace</p>
          </div>
          <h1 className="mt-6 max-w-2xl font-headline text-3xl font-extrabold tracking-tight text-on-surface sm:text-4xl">
            Nous synchronisons les signaux disponibles.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-on-surface-variant">
            LIDAL Pulse vérifie les données existantes et reprend automatiquement une collecte interrompue. Cette étape ne prend généralement que quelques secondes.
          </p>
          <div className="mt-8 space-y-2">
            <div className="h-2 w-full animate-pulse rounded-full bg-surface-container-high" />
            <div className="h-2 w-3/5 animate-pulse rounded-full bg-surface-container-high" />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
