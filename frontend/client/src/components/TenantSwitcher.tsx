import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredTenantId, setStoredTenantId, useTenantId } from "@/lib/tenantContext";

export function TenantSwitcher() {
  const tenantId = useTenantId();
  const [draftTenantId, setDraftTenantId] = useState(getStoredTenantId() ?? "");

  useEffect(() => {
    setDraftTenantId(tenantId ?? "");
  }, [tenantId]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStoredTenantId(draftTenantId.trim() || null);
  }

  function handleClear() {
    setDraftTenantId("");
    setStoredTenantId(null);
  }

  return (
    <form className="flex items-center gap-2" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          Tenant
        </label>
        <Input
          className="h-9 w-44 bg-surface-container-highest border-outline-variant/20 text-xs"
          onChange={(event) => setDraftTenantId(event.target.value)}
          placeholder="ramy_client_001"
          value={draftTenantId}
        />
      </div>
      <Button size="sm" type="submit">
        Save
      </Button>
      <Button size="sm" type="button" variant="outline" onClick={handleClear}>
        Clear
      </Button>
      <span className="max-w-44 truncate text-[10px] uppercase tracking-widest text-on-surface-variant">
        {tenantId ? `Active: ${tenantId}` : "No tenant"}
      </span>
    </form>
  );
}
