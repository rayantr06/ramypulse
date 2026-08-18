import { FormEvent, useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { ProfileMark } from "@/components/ProfileMark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatTenantLabel } from "@/lib/productNavigation";
import { getStoredTenantId, setStoredTenantId, useTenantId } from "@/lib/tenantContext";
import { getTenantBranding } from "@/lib/tenantBranding";

export function TenantSwitcher() {
  const tenantId = useTenantId();
  const tenantLabel = formatTenantLabel(tenantId);
  const tenantBranding = getTenantBranding(tenantId, tenantLabel);
  const [draftTenantId, setDraftTenantId] = useState(getStoredTenantId() ?? "");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setDraftTenantId(tenantId ?? "");
  }, [tenantId]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStoredTenantId(draftTenantId.trim() || null);
    setIsOpen(false);
  }

  function handleClear() {
    setDraftTenantId("");
    setStoredTenantId(null);
    setIsOpen(false);
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          className="group hidden min-w-0 items-center gap-2 rounded-full border border-outline-variant/60 bg-surface px-3 py-2 text-left transition-colors hover:border-primary/20 hover:bg-primary-container/35 sm:flex"
          type="button"
          aria-label="Changer l’espace client"
        >
          <ProfileMark
            className="h-7 w-7 rounded-lg"
            imageAlt={tenantBranding.logoAlt}
            imageSrc={tenantBranding.logoSrc}
            label={tenantLabel}
          />
          <span className="min-w-0">
            <span className="block text-[9px] font-bold uppercase tracking-[0.16em] text-on-surface-variant">
              Espace client
            </span>
            <span className="block max-w-36 truncate text-xs font-semibold text-on-surface">
              {tenantLabel}
            </span>
          </span>
          <ChevronDown className="h-4 w-4 text-on-surface-variant transition-transform group-data-[state=open]:rotate-180" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 rounded-xl border-outline-variant bg-popover p-4 shadow-ambient">
        <div className="mb-4">
          <p className="font-headline text-sm font-bold text-on-surface">Changer d’espace client</p>
          <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">
            Toutes les données et analyses restent isolées par organisation.
          </p>
        </div>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold uppercase tracking-[0.14em] text-on-surface-variant" htmlFor="tenant-id">
              Identifiant organisation
            </label>
            <Input
              id="tenant-id"
              className="h-10 border-outline-variant bg-surface-container-high text-sm"
              onChange={(event) => setDraftTenantId(event.target.value)}
              placeholder="ramy_client_001"
              value={draftTenantId}
            />
          </div>
          <div className="flex items-center justify-between gap-3 pt-1">
            <Button size="sm" type="button" variant="ghost" onClick={handleClear}>
              Effacer
            </Button>
            <Button size="sm" type="submit">
              Activer
            </Button>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  );
}
