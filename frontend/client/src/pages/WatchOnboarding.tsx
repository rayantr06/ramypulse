import { useLocation } from "wouter";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { setStoredTenantId } from "@/lib/tenantContext";

export default function WatchOnboarding() {
  const [, setLocation] = useLocation();

  function activateDemoTenant() {
    setStoredTenantId("ramy_client_001");
    setLocation("/");
  }

  function clearTenant() {
    setStoredTenantId(null);
  }

  return (
    <AppShell sidebarFooterSubtitle="Nouveau client">
      <div className="min-h-[calc(100vh-4rem)] p-8 flex items-center justify-center">
        <div className="max-w-2xl w-full rounded-2xl border border-outline-variant/15 bg-surface-container p-8 shadow-[0_24px_80px_rgba(0,0,0,0.25)]">
          <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-primary mb-3">
            Nouveau client
          </p>
          <h1 className="text-4xl font-black tracking-tight font-headline text-on-surface mb-4">
            Configurez votre tenant pour commencer
          </h1>
          <p className="max-w-xl text-sm leading-6 text-on-surface-variant mb-8">
            Ajoutez un identifiant client pour activer les vues produit. Une fois un tenant
            enregistré, la page d&apos;accueil bascule vers le tableau de bord.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={activateDemoTenant}>Charger un tenant de démo</Button>
            <Button variant="outline" onClick={clearTenant}>
              Réinitialiser
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
