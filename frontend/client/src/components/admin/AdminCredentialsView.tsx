import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { CredentialSummary } from "@shared/schema";
import { mapCredentialSummary } from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";
import { toast } from "@/hooks/use-toast";

interface CredentialFormState {
  entity_type: string;
  entity_name: string;
  platform: string;
  account_id: string;
  access_token: string;
  app_id: string;
  app_secret: string;
  extra_config_text: string;
}

const PLATFORM_OPTIONS = [
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "google_maps", label: "Google Maps" },
  { value: "youtube", label: "YouTube" },
  { value: "import", label: "Import" },
  { value: "tiktok", label: "TikTok" },
];

const CREDENTIAL_ENTITY_OPTIONS = [
  { value: "brand", label: "Brand" },
  { value: "influencer", label: "Influencer" },
];

function blankCredentialForm(): CredentialFormState {
  return {
    entity_type: "brand",
    entity_name: "",
    platform: "instagram",
    account_id: "",
    access_token: "",
    app_id: "",
    app_secret: "",
    extra_config_text: "{}",
  };
}

function parseObjectJson(value: string, label: string): Record<string, unknown> {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} doit être un objet JSON`);
  }
  return parsed as Record<string, unknown>;
}

export function AdminCredentialsView() {
  const queryClientHook = useQueryClient();
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>(blankCredentialForm());
  const [credentialError, setCredentialError] = useState<string | null>(null);

  const { data: credentials, isLoading: credentialsLoading } = useQuery<CredentialSummary[]>({
    queryKey: ["/api/social-metrics/credentials"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/social-metrics/credentials");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapCredentialSummary);
    },
  });

  const credentialOptions = credentials ?? [];

  const createCredentialMutation = useMutation({
    mutationFn: async (form: CredentialFormState) => {
      const res = await apiRequest("POST", "/api/social-metrics/credentials", {
        entity_type: form.entity_type,
        entity_name: form.entity_name,
        platform: form.platform,
        account_id: form.account_id || undefined,
        access_token: form.access_token || undefined,
        app_id: form.app_id || undefined,
        app_secret: form.app_secret || undefined,
        extra_config: parseObjectJson(form.extra_config_text, "extra_config"),
      });
      return res.json();
    },
    onSuccess: () => {
      setCredentialForm(blankCredentialForm());
      setCredentialError(null);
      queryClientHook.invalidateQueries({ queryKey: ["/api/social-metrics/credentials"] });
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const deactivateCredentialMutation = useMutation({
    mutationFn: async (credentialId: string) => {
      await apiRequest("DELETE", `/api/social-metrics/credentials/${credentialId}`);
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/social-metrics/credentials"] });
      queryClientHook.invalidateQueries({ queryKey: ["/api/admin/sources"] });
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const handleCredentialSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCredentialError(null);
    try {
      parseObjectJson(credentialForm.extra_config_text, "extra_config");
      createCredentialMutation.mutate(credentialForm);
    } catch (error) {
      setCredentialError(error instanceof Error ? error.message : "extra_config invalide");
    }
  };

  return (
    <div className="grid grid-cols-12 gap-8 items-start">
      <div className="col-span-12 lg:col-span-7 bg-surface-container rounded-xl border border-white/5 overflow-hidden">
        <div className="p-6 border-b border-white/5">
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Credentials</p>
          <h2 className="text-xl font-headline font-bold mt-1">Platform Access Registry</h2>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-container-high/30">
            <tr>
              {["Entité", "Plateforme", "Type", "Statut", "Actions"].map((heading) => (
                <th key={heading} className="px-6 py-3 font-bold opacity-70 text-xs uppercase">{heading}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {credentialsLoading ? (
              <tr>
                <td colSpan={5} className="px-6 py-4">
                  <div className="h-10 bg-surface-container-high rounded animate-pulse"></div>
                </td>
              </tr>
            ) : (
              credentialOptions.map((credential) => (
                <tr key={credential.credential_id}>
                  <td className="px-6 py-4">
                    <div className="font-semibold">{credential.entity_name}</div>
                    <div className="text-xs text-on-surface-variant">{credential.account_id || credential.credential_id}</div>
                  </td>
                  <td className="px-6 py-4">{credential.platform}</td>
                  <td className="px-6 py-4 uppercase text-xs font-bold">{credential.entity_type}</td>
                  <td className="px-6 py-4">{credential.is_active ? "Actif" : "Désactivé"}</td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={() => deactivateCredentialMutation.mutate(credential.credential_id)} disabled={!credential.is_active || deactivateCredentialMutation.isPending} className="text-xs font-bold text-error disabled:opacity-40">
                      Désactiver
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="col-span-12 lg:col-span-5 bg-surface-container p-6 rounded-xl border border-white/5">
        <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">Nouveau credential</p>
        <form className="space-y-4" onSubmit={handleCredentialSubmit}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="field-entity-type" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Type d'entité</label>
              <select id="field-entity-type" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={credentialForm.entity_type} onChange={(event) => setCredentialForm({ ...credentialForm, entity_type: event.target.value })}>
                {CREDENTIAL_ENTITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="field-cred-platform" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Plateforme</label>
              <select id="field-cred-platform" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={credentialForm.platform} onChange={(event) => setCredentialForm({ ...credentialForm, platform: event.target.value })}>
                {PLATFORM_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="field-entity-name" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Nom de l'entité</label>
            <input id="field-entity-name" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="Nom de l'entité" value={credentialForm.entity_name} onChange={(event) => setCredentialForm({ ...credentialForm, entity_name: event.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="field-account-id" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Account ID</label>
              <input id="field-account-id" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="Account ID" value={credentialForm.account_id} onChange={(event) => setCredentialForm({ ...credentialForm, account_id: event.target.value })} />
            </div>
            <div>
              <label htmlFor="field-app-id" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">App ID</label>
              <input id="field-app-id" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="App ID" value={credentialForm.app_id} onChange={(event) => setCredentialForm({ ...credentialForm, app_id: event.target.value })} />
            </div>
          </div>
          <div>
            <label htmlFor="field-access-token" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Access Token</label>
            <input id="field-access-token" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="password" placeholder="Access Token" value={credentialForm.access_token} onChange={(event) => setCredentialForm({ ...credentialForm, access_token: event.target.value })} />
          </div>
          <div>
            <label htmlFor="field-app-secret" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">App Secret</label>
            <input id="field-app-secret" className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="password" placeholder="App Secret" value={credentialForm.app_secret} onChange={(event) => setCredentialForm({ ...credentialForm, app_secret: event.target.value })} />
          </div>
          <div>
            <label htmlFor="field-extra-config" className="block text-xs font-bold text-on-surface-variant mb-1 ml-1">Configuration extra</label>
            <textarea id="field-extra-config" className="w-full bg-[#0d0e10] p-3 rounded-lg font-mono text-[11px] text-primary/80 h-24 overflow-y-auto border border-white/5" value={credentialForm.extra_config_text} onChange={(event) => setCredentialForm({ ...credentialForm, extra_config_text: event.target.value })} />
          </div>
          {credentialError ? <p className="text-xs text-error">{credentialError}</p> : null}
          <button type="submit" disabled={createCredentialMutation.isPending} className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
            {createCredentialMutation.isPending ? "Création..." : "Créer le credential"}
          </button>
        </form>
      </div>
    </div>
  );
}
