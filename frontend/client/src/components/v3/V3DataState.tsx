import { AlertTriangle, LoaderCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface V3DataStateProps {
  loading: boolean;
  onRetry: () => void;
}

export function V3DataState({ loading, onRetry }: V3DataStateProps) {
  if (loading) {
    return (
      <section className="cling-panel flex min-h-72 items-center justify-center p-8" aria-live="polite">
        <div className="text-center">
          <LoaderCircle className="mx-auto h-7 w-7 animate-spin text-primary" aria-hidden="true" />
          <h2 className="mt-4 font-headline text-base font-bold">Chargement des données métier</h2>
          <p className="mt-2 text-xs text-on-surface-variant">Les indicateurs ne sont pas affichés avant la réponse du service.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="cling-panel flex min-h-72 items-center justify-center p-8" role="alert">
      <div className="max-w-md text-center">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-error-container text-error">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </span>
        <h2 className="mt-4 font-headline text-lg font-bold">Données indisponibles</h2>
        <p className="mt-2 text-xs leading-5 text-on-surface-variant">La dernière requête a échoué. Aucun zéro ni état vide n’est déduit de cette panne.</p>
        <Button className="mt-5" variant="outline" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />Réessayer
        </Button>
      </div>
    </section>
  );
}
