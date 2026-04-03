import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { Campaign, CampaignImpact } from "@shared/schema";

const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: "1",
    name: "Ramy Citron Summer",
    type: "Influenceur",
    platform: "Instagram",
    influencer: "@rifka.bjm",
    budget_dza: 1250000,
    start_date: "2024-07-01",
    end_date: "2024-07-31",
    keywords: ["#RamyCitron", "#Ete2024"],
    status: "ACTIVE",
    impact_nss: 12.4,
  },
  {
    id: "2",
    name: "Lancement Ramy Orange",
    type: "Sponsoring",
    platform: "YouTube",
    influencer: "@meriem.halim",
    budget_dza: 850000,
    start_date: "2024-08-01",
    end_date: "2024-08-31",
    keywords: ["#RamyOrange"],
    status: "PLANIFIÉE",
  },
  {
    id: "3",
    name: "Bac 2024 Celebration",
    type: "Social Media",
    platform: "Facebook",
    influencer: "@cheb.mohamet",
    budget_dza: 450000,
    start_date: "2024-06-01",
    end_date: "2024-06-30",
    keywords: ["#Bac2024", "#Ramy"],
    status: "TERMINÉE",
    impact_nss: 5.2,
  },
  {
    id: "4",
    name: "Test Flash Promo",
    type: "Social Media",
    platform: "Instagram",
    influencer: "",
    budget_dza: 0,
    start_date: "2024-05-01",
    end_date: "2024-05-15",
    keywords: [],
    status: "ANNULÉE",
  },
];

const MOCK_IMPACT: CampaignImpact = {
  pre_campaign_nss: 42.5,
  during_campaign_nss: 58.2,
  post_campaign_nss: 51.8,
  uplift_pct: 15.7,
  retention_pct: 22,
  ai_insight:
    "L'Uplift majeur est corrélé aux segments 18-24 ans suite au live de Numidia. La rétention post-campagne reste 22% supérieure à la moyenne trimestrielle.",
};

// Map API campaign response to Campaign schema
function mapCampaignFromApi(c: Record<string, unknown>): Campaign {
  return {
    id: String(c.id ?? c.campaign_id ?? ""),
    name: String(c.name ?? ""),
    type: String(c.type ?? "Social Media"),
    platform: String(c.platform ?? c.target_platform ?? ""),
    influencer: String(c.influencer ?? ""),
    budget_dza: Number(c.budget_dza ?? 0),
    start_date: String(c.start_date ?? ""),
    end_date: String(c.end_date ?? ""),
    keywords: (c.keywords as string[]) ?? [],
    status: (c.status as Campaign["status"]) ?? "PLANIFIÉE",
    impact_nss: c.impact_nss != null ? Number(c.impact_nss) : undefined,
  };
}

function mapImpactFromApi(apiData: Record<string, unknown>): CampaignImpact {
  return {
    pre_campaign_nss: Number(apiData.pre_campaign_nss ?? MOCK_IMPACT.pre_campaign_nss),
    during_campaign_nss: Number(apiData.during_campaign_nss ?? MOCK_IMPACT.during_campaign_nss),
    post_campaign_nss: Number(apiData.post_campaign_nss ?? MOCK_IMPACT.post_campaign_nss),
    uplift_pct: Number(apiData.uplift_pct ?? MOCK_IMPACT.uplift_pct),
    retention_pct: Number(apiData.retention_pct ?? MOCK_IMPACT.retention_pct),
    ai_insight: String(apiData.ai_insight ?? MOCK_IMPACT.ai_insight),
  };
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ACTIVE: "bg-tertiary/10 text-tertiary",
    PLANIFIÉE: "bg-secondary-container text-on-secondary-container",
    TERMINÉE: "bg-surface-container-highest text-on-surface-variant",
    ANNULÉE: "bg-error/10 text-error",
  };
  return (
    <span className={`px-2 py-1 rounded-sm text-[10px] font-bold uppercase tracking-widest ${map[status] ?? "bg-surface-container text-on-surface-variant"}`}>
      {status}
    </span>
  );
}

export default function Campagnes() {
  const [filter, setFilter] = useState<"TOUTES" | "ACTIVES" | "ARCHIVES">("TOUTES");
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>(["#RamyCitron", "#Ete2024"]);
  const [newKeyword, setNewKeyword] = useState("");
  const [form, setForm] = useState({
    name: "",
    type: "Influenceur",
    platform: "Instagram",
    influencer: "",
    budget_dza: "",
    start_date: "",
    end_date: "",
  });

  const queryClientHook = useQueryClient();

  const { data: campaigns, isLoading: campaignsLoading } = useQuery<Campaign[]>({
    queryKey: ["/api/campaigns"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/campaigns");
        const apiData = await res.json();
        const list = Array.isArray(apiData) ? apiData : (apiData.campaigns ?? []);
        return (list as Array<Record<string, unknown>>).map(mapCampaignFromApi);
      } catch {
        return MOCK_CAMPAIGNS;
      }
    },
  });

  const { data: impact, isLoading: impactLoading } = useQuery<CampaignImpact>({
    queryKey: ["/api/campaigns", selectedCampaign, "impact"],
    queryFn: async () => {
      if (!selectedCampaign) return MOCK_IMPACT;
      try {
        const res = await apiRequest("GET", `/api/campaigns/${selectedCampaign}/impact`);
        const apiData = await res.json();
        return mapImpactFromApi(apiData);
      } catch {
        return MOCK_IMPACT;
      }
    },
    enabled: !!selectedCampaign,
  });

  const createMutation = useMutation({
    mutationFn: async (data: typeof form) => {
      const res = await apiRequest("POST", "/api/campaigns", {
        ...data,
        budget_dza: parseInt(data.budget_dza),
        keywords,
      });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/campaigns"] });
      setForm({ name: "", type: "Influenceur", platform: "Instagram", influencer: "", budget_dza: "", start_date: "", end_date: "" });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await apiRequest("PUT", `/api/campaigns/${id}/status`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/campaigns"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/campaigns/${id}`);
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/campaigns"] });
      setSelectedCampaign(null);
    },
  });

  const allCampaigns = campaigns ?? MOCK_CAMPAIGNS;
  const filteredCampaigns = allCampaigns.filter((c) => {
    if (filter === "ACTIVES") return c.status === "ACTIVE";
    if (filter === "ARCHIVES") return c.status === "TERMINÉE" || c.status === "ANNULÉE";
    return true;
  });

  const impactData = impact ?? MOCK_IMPACT;

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une campagne..."
      onSearch={() => {}}
    >
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
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-surface-container-high hover:bg-surface-bright text-on-surface text-xs font-bold transition-all rounded-sm">
              EXPORTER DATA
            </button>
            <button
              className="px-6 py-2 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed text-xs font-bold transition-transform active:scale-95 shadow-lg shadow-primary/10 rounded-sm"
              data-testid="btn-create-campaign"
            >
              CRÉER UNE CAMPAGNE
            </button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left: New Campaign Form + Impact Panel */}
          <section className="col-span-12 lg:col-span-4 space-y-6">
            {/* Form */}
            <div className="bg-surface-container-low rounded-lg p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between border-b border-surface-container-highest pb-4">
                <h3 className="font-headline font-bold text-lg">Nouvelle Campagne</h3>
                <span className="material-symbols-outlined text-primary cursor-pointer">expand_less</span>
              </div>
              <form
                className="space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  createMutation.mutate(form);
                }}
              >
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Nom de la Campagne
                  </label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    placeholder="ex: Ramy Citron Été 2024"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    data-testid="input-campaign-name"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Type</label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={form.type}
                      onChange={(e) => setForm({ ...form, type: e.target.value })}
                    >
                      <option>Influenceur</option>
                      <option>Sponsoring</option>
                      <option>Social Media</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Plateforme</label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={form.platform}
                      onChange={(e) => setForm({ ...form, platform: e.target.value })}
                    >
                      <option>Instagram</option>
                      <option>TikTok</option>
                      <option>YouTube</option>
                      <option>Facebook</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Influenceur Algérien
                  </label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    placeholder="@numidialz_official"
                    value={form.influencer}
                    onChange={(e) => setForm({ ...form, influencer: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Budget (DZA)</label>
                  <div className="relative">
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 pr-10 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      placeholder="500,000"
                      type="number"
                      value={form.budget_dza}
                      onChange={(e) => setForm({ ...form, budget_dza: e.target.value })}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-on-surface-variant/50">DA</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Début</label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      type="date"
                      value={form.start_date}
                      onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Fin</label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      type="date"
                      value={form.end_date}
                      onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Mots-clés</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {keywords.map((kw) => (
                      <span
                        key={kw}
                        onClick={() => setKeywords((prev) => prev.filter((k) => k !== kw))}
                        className="px-2 py-1 bg-primary/10 border border-primary/20 text-[10px] text-primary cursor-pointer hover:bg-error/10 hover:text-error hover:border-error/20 transition-colors"
                      >
                        {kw}
                      </span>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        if (newKeyword.trim()) {
                          setKeywords((prev) => [...prev, newKeyword.startsWith("#") ? newKeyword : `#${newKeyword}`]);
                          setNewKeyword("");
                        }
                      }}
                      className="px-2 py-1 bg-surface-container-highest text-[10px] text-on-surface-variant hover:text-primary transition-colors"
                    >
                      + Ajouter
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="w-full py-3 bg-primary text-on-primary-fixed font-bold text-xs uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-50 rounded-sm"
                  data-testid="btn-submit-campaign"
                >
                  {createMutation.isPending ? "Création..." : "Lancer la Campagne"}
                </button>
              </form>
            </div>

            {/* Impact Analysis */}
            <div className="bg-surface-container-low rounded-lg p-6 space-y-5">
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Analyse d'Impact
                </p>
                <h3 className="font-headline font-bold text-lg mt-1">NSS Evolution</h3>
              </div>
              {impactLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-surface-container-high rounded animate-pulse"></div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {[
                    { label: "Pré-campagne", value: impactData.pre_campaign_nss, color: "bg-on-surface-variant", textColor: "text-on-surface-variant", delta: null },
                    { label: "Pendant", value: impactData.during_campaign_nss, color: "bg-primary", textColor: "text-primary", delta: `+${impactData.uplift_pct}%` },
                    { label: "Post-campagne", value: impactData.post_campaign_nss, color: "bg-tertiary", textColor: "text-tertiary", delta: `-${(impactData.during_campaign_nss - impactData.post_campaign_nss).toFixed(1)}%` },
                  ].map(({ label, value, color, textColor, delta }) => (
                    <div key={label} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-8 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className={`w-full ${color}`} style={{ height: `${(value / impactData.during_campaign_nss) * 100}%` }}></div>
                        </div>
                        <div>
                          <p className={`text-[10px] uppercase ${textColor}`}>{label}</p>
                          <p className="font-headline font-bold text-sm">{value} NSS</p>
                        </div>
                      </div>
                      {delta && (
                        <div className={`flex items-center text-[10px] font-bold ${delta.startsWith("+") ? "text-tertiary" : "text-error"}`}>
                          <span className="material-symbols-outlined text-sm">{delta.startsWith("+") ? "arrow_drop_up" : "arrow_drop_down"}</span>
                          {delta}
                        </div>
                      )}
                      {!delta && <span className="text-[10px] text-on-surface-variant/40">— Base</span>}
                    </div>
                  ))}
                </div>
              )}
              <div className="bg-surface-container-high p-4 rounded-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-tertiary text-sm">auto_awesome</span>
                  <span className="text-[10px] font-bold uppercase text-tertiary tracking-wider">Insight IA</span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">{impactData.ai_insight}</p>
              </div>
            </div>
          </section>

          {/* Right: Campaigns Table */}
          <section className="col-span-12 lg:col-span-8 space-y-6">
            <div className="bg-surface-container-low rounded-lg overflow-hidden">
              <div className="p-6 flex items-center justify-between border-b border-surface-container-highest">
                <div>
                  <h3 className="font-headline font-bold text-lg">Suivi des Campagnes</h3>
                  <p className="text-xs text-on-surface-variant">
                    {allCampaigns.filter((c) => c.status === "ACTIVE").length} campagnes actives sur le marché algérien
                  </p>
                </div>
                <div className="flex items-center gap-1 bg-surface-container-highest p-1 rounded-sm">
                  {(["TOUTES", "ACTIVES", "ARCHIVES"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-3 py-1 text-[10px] font-bold rounded-sm transition-colors ${
                        filter === f ? "bg-surface-bright text-on-surface" : "text-on-surface-variant hover:text-on-surface"
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                {campaignsLoading ? (
                  <div className="p-6 space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-14 bg-surface-container-high rounded animate-pulse"></div>
                    ))}
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-surface-container-lowest/50">
                      <tr>
                        {["Campagne / Influenceur", "Plateforme", "Statut", "Budget (DZA)", "Impact NSS"].map((h, i) => (
                          <th
                            key={h}
                            className={`px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ${i > 1 ? "text-center" : ""}`}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-container-highest/30">
                      {filteredCampaigns.map((campaign) => (
                        <tr
                          key={campaign.id}
                          onClick={() => setSelectedCampaign(campaign.id === selectedCampaign ? null : campaign.id)}
                          className={`hover:bg-surface-container-high/40 transition-colors group cursor-pointer ${
                            selectedCampaign === campaign.id ? "bg-surface-container-high/60" : ""
                          } ${campaign.status === "ANNULÉE" ? "opacity-50" : ""}`}
                          data-testid={`campaign-row-${campaign.id}`}
                        >
                          <td className="px-6 py-5">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-surface-container-high rounded flex items-center justify-center overflow-hidden border border-surface-container-highest shrink-0">
                                <span className="material-symbols-outlined text-primary text-sm">campaign</span>
                              </div>
                              <div>
                                <p className="text-sm font-bold group-hover:text-primary transition-colors">{campaign.name}</p>
                                <p className="text-[10px] text-on-surface-variant">
                                  {campaign.influencer || "—"}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <span className="text-xs font-medium text-on-surface-variant">{campaign.platform}</span>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <StatusBadge status={campaign.status} />
                          </td>
                          <td className="px-6 py-5 text-right">
                            <p className="text-sm font-headline font-bold">
                              {campaign.budget_dza > 0 ? campaign.budget_dza.toLocaleString("fr-FR") : "—"}
                            </p>
                          </td>
                          <td className="px-6 py-5 text-right">
                            {campaign.impact_nss != null ? (
                              <div className="flex items-center justify-end gap-1 text-tertiary">
                                <span className="material-symbols-outlined text-sm">trending_up</span>
                                <span className="text-sm font-bold">+{campaign.impact_nss}</span>
                              </div>
                            ) : (
                              <span className="text-[10px] font-bold text-on-surface-variant">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Performance quick cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Top Performeur (Mois)</p>
                <div className="mt-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full border-2 border-primary/20 p-0.5 flex items-center justify-center bg-surface-container-highest">
                    <span className="material-symbols-outlined text-primary text-sm">person</span>
                  </div>
                  <div>
                    <h4 className="font-headline font-bold text-lg">@rifka.bjm</h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-on-surface-variant">ROI 4.2x</span>
                      <span className="w-1 h-1 bg-on-surface-variant rounded-full"></span>
                      <span className="text-xs text-tertiary">+18% Engagement</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-tertiary/5 rounded-full blur-3xl group-hover:bg-tertiary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Budget Total Engagé</p>
                <div className="mt-3">
                  <h4 className="font-headline font-black text-xl tracking-tight">
                    {allCampaigns.reduce((sum, c) => sum + c.budget_dza, 0).toLocaleString("fr-FR")}
                    <span className="text-sm font-normal text-on-surface-variant ml-1">DZA</span>
                  </h4>
                  <div className="w-full h-1 bg-surface-container-highest mt-2 rounded-full overflow-hidden">
                    <div className="h-full bg-primary w-[72%]"></div>
                  </div>
                  <p className="text-[10px] text-on-surface-variant mt-1 uppercase font-bold">72% de l'allocation trimestrielle</p>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
