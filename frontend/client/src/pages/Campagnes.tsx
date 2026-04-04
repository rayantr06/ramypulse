import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { Campaign, CampaignImpact } from "@shared/schema";

const STATUS_LABELS: Record<string, string> = {
  planned: "Planifiée",
  active: "Active",
  completed: "Terminée",
  cancelled: "Annulée",
};

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: "bg-tertiary/10 text-tertiary",
    planned: "bg-secondary-container text-on-secondary-container",
    completed: "bg-surface-container-highest text-on-surface-variant",
    cancelled: "bg-error/10 text-error",
  };
  return (
    <span className={`px-2 py-1 rounded-sm text-[10px] font-bold uppercase tracking-widest ${map[status ?? ""] ?? "bg-surface-container text-on-surface-variant"}`}>
      {STATUS_LABELS[status ?? ""] ?? status}
    </span>
  );
}

export default function Campagnes() {
  const [filter, setFilter] = useState<"all" | "active" | "archive">("all");
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [form, setForm] = useState({
    campaign_name: "",
    campaign_type: "Influenceur",
    platform: "instagram",
    influencer_handle: "",
    budget_dza: "",
    start_date: "",
    end_date: "",
  });

  const qc = useQueryClient();

  const { data: campaigns, isLoading: campaignsLoading } = useQuery<Campaign[]>({
    queryKey: ["/api/campaigns"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/campaigns");
      return res.json();
    },
  });

  const { data: impact, isLoading: impactLoading } = useQuery<CampaignImpact>({
    queryKey: ["/api/campaigns", selectedCampaign, "impact"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/campaigns/${selectedCampaign}/impact`);
      return res.json();
    },
    enabled: !!selectedCampaign,
  });

  const createMutation = useMutation({
    mutationFn: async (data: typeof form) => {
      const res = await apiRequest("POST", "/api/campaigns", {
        campaign_name: data.campaign_name,
        campaign_type: data.campaign_type,
        platform: data.platform,
        influencer_handle: data.influencer_handle || undefined,
        budget_dza: data.budget_dza ? parseInt(data.budget_dza) : undefined,
        start_date: data.start_date || undefined,
        end_date: data.end_date || undefined,
        keywords,
      });
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/campaigns"] });
      setForm({ campaign_name: "", campaign_type: "Influenceur", platform: "instagram", influencer_handle: "", budget_dza: "", start_date: "", end_date: "" });
      setKeywords([]);
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await apiRequest("PUT", `/api/campaigns/${id}/status`, { status });
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/campaigns"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/campaigns/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/campaigns"] });
      setSelectedCampaign(null);
    },
  });

  const allCampaigns = campaigns ?? [];
  const filteredCampaigns = allCampaigns.filter((c) => {
    if (filter === "active") return c.status === "active";
    if (filter === "archive") return c.status === "completed" || c.status === "cancelled";
    return true;
  });

  const preNss = impact?.phases?.pre?.nss;
  const activeNss = impact?.phases?.active?.nss;
  const postNss = impact?.phases?.post?.nss;

  return (
    <AppShell headerSearchPlaceholder="Rechercher une campagne..." onSearch={() => {}}>
      <div className="p-8 max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="flex items-end justify-between">
          <div>
            <span className="text-[10px] font-bold tracking-[0.2em] text-primary uppercase">
              Gestion Opérationnelle
            </span>
            <h2 className="text-3xl font-headline font-extrabold tracking-tighter mt-1">
              Campagnes Marketing
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left: New Campaign Form + Impact Panel */}
          <section className="col-span-12 lg:col-span-4 space-y-6">
            <div className="bg-surface-container-low rounded-lg p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between border-b border-surface-container-highest pb-4">
                <h3 className="font-headline font-bold text-lg">Nouvelle Campagne</h3>
              </div>
              <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Nom</label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    placeholder="ex: Ramy Citron Été 2024"
                    value={form.campaign_name}
                    onChange={(e) => setForm({ ...form, campaign_name: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Type</label>
                    <select className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" value={form.campaign_type} onChange={(e) => setForm({ ...form, campaign_type: e.target.value })}>
                      <option>Influenceur</option>
                      <option>Sponsoring</option>
                      <option>Social Media</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Plateforme</label>
                    <select className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
                      <option value="instagram">Instagram</option>
                      <option value="youtube">YouTube</option>
                      <option value="facebook">Facebook</option>
                      <option value="google_maps">Google Maps</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Influenceur</label>
                  <input className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" placeholder="@handle" value={form.influencer_handle} onChange={(e) => setForm({ ...form, influencer_handle: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Budget (DZA)</label>
                  <input className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" placeholder="500000" type="number" value={form.budget_dza} onChange={(e) => setForm({ ...form, budget_dza: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Début</label>
                    <input className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fin</label>
                    <input className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Mots-clés</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {keywords.map((kw) => (
                      <span key={kw} onClick={() => setKeywords((prev) => prev.filter((k) => k !== kw))} className="px-2 py-1 bg-primary/10 border border-primary/20 text-[10px] text-primary cursor-pointer hover:bg-error/10 hover:text-error transition-colors">
                        {kw}
                      </span>
                    ))}
                    <input className="bg-surface-container-highest text-[10px] px-2 py-1 w-24 focus:outline-none" placeholder="+ Ajouter" value={newKeyword} onChange={(e) => setNewKeyword(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); if (newKeyword.trim()) { setKeywords((prev) => [...prev, newKeyword.startsWith("#") ? newKeyword : `#${newKeyword}`]); setNewKeyword(""); } } }} />
                  </div>
                </div>
                <button type="submit" disabled={createMutation.isPending || !form.campaign_name} className="w-full py-3 bg-primary text-on-primary-fixed font-bold text-xs uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-50 rounded-sm">
                  {createMutation.isPending ? "Création..." : "Lancer la Campagne"}
                </button>
              </form>
            </div>

            {/* Impact Analysis */}
            {selectedCampaign && (
              <div className="bg-surface-container-low rounded-lg p-6 space-y-5">
                <div>
                  <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Analyse d'Impact</p>
                  <h3 className="font-headline font-bold text-lg mt-1">
                    {impact?.campaign_name ?? "NSS Evolution"}
                  </h3>
                </div>
                {impactLoading ? (
                  <div className="space-y-4">
                    {[1, 2, 3].map((i) => (<div key={i} className="h-12 bg-surface-container-high rounded animate-pulse"></div>))}
                  </div>
                ) : impact ? (
                  <div className="space-y-4">
                    {[
                      { label: "Pré-campagne", nss: preNss, volume: impact.phases.pre.volume, color: "text-on-surface-variant" },
                      { label: "Pendant", nss: activeNss, volume: impact.phases.active.volume, color: "text-primary" },
                      { label: "Post-campagne", nss: postNss, volume: impact.phases.post.volume, color: "text-tertiary" },
                    ].map(({ label, nss, volume, color }) => (
                      <div key={label} className="flex items-center justify-between">
                        <div>
                          <p className={`text-[10px] uppercase ${color}`}>{label}</p>
                          <p className="font-headline font-bold text-sm">{nss != null ? `${nss} NSS` : "—"}</p>
                        </div>
                        <span className="text-[10px] text-gray-500">{volume} signaux</span>
                      </div>
                    ))}
                    {impact.uplift_nss != null && (
                      <div className={`p-3 rounded-sm ${impact.uplift_nss > 0 ? "bg-tertiary/10" : "bg-error/10"}`}>
                        <span className={`text-sm font-bold ${impact.uplift_nss > 0 ? "text-tertiary" : "text-error"}`}>
                          Uplift: {impact.uplift_nss > 0 ? "+" : ""}{impact.uplift_nss} pts NSS
                        </span>
                      </div>
                    )}
                    {!impact.is_reliable && (
                      <p className="text-[10px] text-gray-500 italic">{impact.reliability_note}</p>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </section>

          {/* Right: Campaigns Table */}
          <section className="col-span-12 lg:col-span-8 space-y-6">
            <div className="bg-surface-container-low rounded-lg overflow-hidden">
              <div className="p-6 flex items-center justify-between border-b border-surface-container-highest">
                <div>
                  <h3 className="font-headline font-bold text-lg">Suivi des Campagnes</h3>
                  <p className="text-xs text-on-surface-variant">
                    {allCampaigns.filter((c) => c.status === "active").length} campagnes actives
                  </p>
                </div>
                <div className="flex items-center gap-1 bg-surface-container-highest p-1 rounded-sm">
                  {([["all", "Toutes"], ["active", "Actives"], ["archive", "Archives"]] as const).map(([key, label]) => (
                    <button key={key} onClick={() => setFilter(key)} className={`px-3 py-1 text-[10px] font-bold rounded-sm transition-colors ${filter === key ? "bg-surface-bright text-on-surface" : "text-on-surface-variant hover:text-on-surface"}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                {campaignsLoading ? (
                  <div className="p-6 space-y-3">
                    {[1, 2, 3].map((i) => (<div key={i} className="h-14 bg-surface-container-high rounded animate-pulse"></div>))}
                  </div>
                ) : filteredCampaigns.length === 0 ? (
                  <div className="p-12 text-center text-gray-500">
                    <span className="material-symbols-outlined text-4xl mb-2">campaign</span>
                    <p className="text-sm">Aucune campagne trouvée.</p>
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-surface-container-lowest/50">
                      <tr>
                        {["Campagne", "Plateforme", "Statut", "Budget", "Dates"].map((h) => (
                          <th key={h} className="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-container-highest/30">
                      {filteredCampaigns.map((c) => (
                        <tr key={c.campaign_id} onClick={() => setSelectedCampaign(c.campaign_id === selectedCampaign ? null : c.campaign_id)} className={`hover:bg-surface-container-high/40 transition-colors cursor-pointer ${selectedCampaign === c.campaign_id ? "bg-surface-container-high/60" : ""} ${c.status === "cancelled" ? "opacity-50" : ""}`}>
                          <td className="px-6 py-5">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-surface-container-high rounded flex items-center justify-center border border-surface-container-highest shrink-0">
                                <span className="material-symbols-outlined text-primary text-sm">campaign</span>
                              </div>
                              <div>
                                <p className="text-sm font-bold">{c.campaign_name}</p>
                                <p className="text-[10px] text-on-surface-variant">{c.influencer_handle || c.campaign_type || "—"}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5"><span className="text-xs text-on-surface-variant">{c.platform ?? "—"}</span></td>
                          <td className="px-6 py-5"><StatusBadge status={c.status ?? "planned"} /></td>
                          <td className="px-6 py-5 text-right"><span className="text-sm font-bold">{c.budget_dza ? c.budget_dza.toLocaleString("fr-FR") + " DA" : "—"}</span></td>
                          <td className="px-6 py-5"><span className="text-[10px] text-on-surface-variant">{c.start_date ?? "—"} → {c.end_date ?? "—"}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
