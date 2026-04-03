import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import {
  buildCampaignCreatePayload,
  mapCampaign,
  mapCampaignImpact,
} from "@/lib/apiMappings";

type CampaignFilter = "TOUTES" | "ACTIVES" | "ARCHIVES";

interface CampaignView {
  id: string;
  name: string;
  type: string;
  platform: string;
  influencer: string;
  budget_dza: number | null;
  start_date: string;
  end_date: string;
  keywords: string[];
  status: string;
}

interface CampaignImpactView {
  pre_campaign_nss: number | null;
  during_campaign_nss: number | null;
  post_campaign_nss: number | null;
  uplift_pct: number | null;
  retention_pct: number | null;
  ai_insight: string;
}

function normalizeStatus(status: string | null | undefined): string {
  if (status === "active") return "ACTIVE";
  if (status === "completed") return "TERMINEE";
  if (status === "cancelled") return "ANNULEE";
  return "PLANIFIEE";
}

function mapCampaignView(value: unknown): CampaignView {
  const campaign = mapCampaign(value);
  return {
    id: campaign.campaign_id,
    name: campaign.campaign_name,
    type: campaign.campaign_type || "Social Media",
    platform: campaign.platform || "Toutes",
    influencer: campaign.influencer_handle || "Aucun influenceur renseigné",
    budget_dza: campaign.budget_dza ?? null,
    start_date: campaign.start_date || "-",
    end_date: campaign.end_date || "-",
    keywords: campaign.keywords,
    status: normalizeStatus(campaign.status),
  };
}

function mapCampaignImpactView(value: unknown): CampaignImpactView {
  const impact = mapCampaignImpact(value);
  const pre = impact.phases.pre?.nss ?? null;
  const during = impact.phases.active?.nss ?? null;
  const post = impact.phases.post?.nss ?? null;

  return {
    pre_campaign_nss: pre,
    during_campaign_nss: during,
    post_campaign_nss: post,
    uplift_pct: impact.uplift_nss ?? null,
    retention_pct:
      during != null && post != null && during !== 0
        ? Number((((post / during) * 100)).toFixed(1))
        : null,
    ai_insight: impact.reliability_note || "Analyse d'impact disponible.",
  };
}

function formatBudget(value: number | null): string {
  if (value == null || value <= 0) return "-";
  return value.toLocaleString("fr-FR");
}

function formatDelta(value: number | null): string {
  if (value == null) return "n/a";
  return `${value > 0 ? "+" : ""}${value}`;
}

function safeRatio(value: number | null, max: number | null): number {
  if (value == null || max == null || max <= 0) return 0;
  return Math.max(0, Math.min(100, (value / max) * 100));
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ACTIVE: "bg-tertiary/10 text-tertiary",
    PLANIFIEE: "bg-secondary-container text-on-secondary-container",
    TERMINEE: "bg-surface-container-highest text-on-surface-variant",
    ANNULEE: "bg-error/10 text-error",
  };

  return (
    <span
      className={`px-2 py-1 rounded-sm text-[10px] font-bold uppercase tracking-widest ${
        map[status] ?? "bg-surface-container text-on-surface-variant"
      }`}
    >
      {status}
    </span>
  );
}

export default function Campagnes() {
  const [filter, setFilter] = useState<CampaignFilter>("TOUTES");
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

  const queryClientHook = useQueryClient();

  const { data: campaigns, isLoading: campaignsLoading } = useQuery<CampaignView[]>({
    queryKey: ["/api/campaigns"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/campaigns");
      const payload = await res.json();
      const list = Array.isArray(payload) ? payload : [];
      return list.map(mapCampaignView);
    },
  });

  const { data: impact, isLoading: impactLoading } = useQuery<CampaignImpactView>({
    queryKey: ["/api/campaigns", selectedCampaign, "impact"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/campaigns/${selectedCampaign}/impact`);
      return mapCampaignImpactView(await res.json());
    },
    enabled: Boolean(selectedCampaign),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest(
        "POST",
        "/api/campaigns",
        buildCampaignCreatePayload({
          ...form,
          keywords,
        }),
      );
      return res.json();
    },
    onSuccess: () => {
      queryClientHook.invalidateQueries({ queryKey: ["/api/campaigns"] });
      setForm({
        campaign_name: "",
        campaign_type: "Influenceur",
        platform: "instagram",
        influencer_handle: "",
        budget_dza: "",
        start_date: "",
        end_date: "",
      });
      setKeywords([]);
    },
  });

  const allCampaigns = campaigns ?? [];
  const filteredCampaigns = useMemo(() => {
    return allCampaigns.filter((campaign) => {
      if (filter === "ACTIVES") return campaign.status === "ACTIVE";
      if (filter === "ARCHIVES") {
        return campaign.status === "TERMINEE" || campaign.status === "ANNULEE";
      }
      return true;
    });
  }, [allCampaigns, filter]);

  const impactData = impact ?? {
    pre_campaign_nss: null,
    during_campaign_nss: null,
    post_campaign_nss: null,
    uplift_pct: null,
    retention_pct: null,
    ai_insight: "Sélectionnez une campagne pour afficher son impact.",
  };

  const activeNss = impactData.during_campaign_nss;

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une campagne..."
      onSearch={() => {}}
    >
      <div className="p-8 max-w-7xl mx-auto space-y-8">
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
          <section className="col-span-12 lg:col-span-4 space-y-6">
            <div className="bg-surface-container-low rounded-lg p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between border-b border-surface-container-highest pb-4">
                <h3 className="font-headline font-bold text-lg">Nouvelle Campagne</h3>
                <span className="material-symbols-outlined text-primary cursor-pointer">
                  expand_less
                </span>
              </div>
              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  createMutation.mutate();
                }}
              >
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Nom de la Campagne
                  </label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    placeholder="ex: Ramy Citron Été 2024"
                    value={form.campaign_name}
                    onChange={(event) =>
                      setForm({ ...form, campaign_name: event.target.value })
                    }
                    data-testid="input-campaign-name"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                      Type
                    </label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={form.campaign_type}
                      onChange={(event) =>
                        setForm({ ...form, campaign_type: event.target.value })
                      }
                    >
                      <option>Influenceur</option>
                      <option>Sponsoring</option>
                      <option>Social Media</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                      Plateforme
                    </label>
                    <select
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      value={form.platform}
                      onChange={(event) => setForm({ ...form, platform: event.target.value })}
                    >
                      <option value="instagram">Instagram</option>
                      <option value="youtube">YouTube</option>
                      <option value="facebook">Facebook</option>
                      <option value="google_maps">Google Maps</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Influenceur Algerien
                  </label>
                  <input
                    className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    placeholder="@numidialz_official"
                    value={form.influencer_handle}
                    onChange={(event) =>
                      setForm({ ...form, influencer_handle: event.target.value })
                    }
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Budget (DZA)
                  </label>
                  <div className="relative">
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 pr-10 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      placeholder="500000"
                      type="number"
                      value={form.budget_dza}
                      onChange={(event) =>
                        setForm({ ...form, budget_dza: event.target.value })
                      }
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-on-surface-variant/50">
                      DA
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                      Debut
                    </label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      type="date"
                      value={form.start_date}
                      onChange={(event) =>
                        setForm({ ...form, start_date: event.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                      Fin
                    </label>
                    <input
                      className="w-full bg-surface-container-highest border-none rounded-sm text-sm py-2 px-3 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                      type="date"
                      value={form.end_date}
                      onChange={(event) => setForm({ ...form, end_date: event.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                    Mots-cles
                  </label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {keywords.map((keyword) => (
                      <span
                        key={keyword}
                        onClick={() =>
                          setKeywords((previous) =>
                            previous.filter((currentKeyword) => currentKeyword !== keyword),
                          )
                        }
                        className="px-2 py-1 bg-primary/10 border border-primary/20 text-[10px] text-primary cursor-pointer hover:bg-error/10 hover:text-error hover:border-error/20 transition-colors"
                      >
                        {keyword}
                      </span>
                    ))}
                    <input
                      className="bg-surface-container-highest text-[10px] px-2 py-1 w-28 focus:outline-none rounded-sm"
                      placeholder="+ Ajouter"
                      value={newKeyword}
                      onChange={(event) => setNewKeyword(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key !== "Enter") return;
                        event.preventDefault();
                        if (!newKeyword.trim()) return;
                        setKeywords((previous) => [
                          ...previous,
                          newKeyword.startsWith("#") ? newKeyword : `#${newKeyword}`,
                        ]);
                        setNewKeyword("");
                      }}
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !form.campaign_name.trim()}
                  className="w-full py-3 bg-primary text-on-primary-fixed font-bold text-xs uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-50 rounded-sm"
                  data-testid="btn-submit-campaign"
                >
                  {createMutation.isPending ? "Création..." : "Lancer la Campagne"}
                </button>
              </form>
            </div>

            <div className="bg-surface-container-low rounded-lg p-6 space-y-5">
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Analyse d'Impact
                </p>
                <h3 className="font-headline font-bold text-lg mt-1">NSS Evolution</h3>
              </div>
              {impactLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((item) => (
                    <div
                      key={item}
                      className="h-12 bg-surface-container-high rounded animate-pulse"
                    ></div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {[
                    {
                      label: "Pre-campagne",
                      value: impactData.pre_campaign_nss,
                      color: "bg-on-surface-variant",
                      textColor: "text-on-surface-variant",
                      delta: null,
                    },
                    {
                      label: "Pendant",
                      value: impactData.during_campaign_nss,
                      color: "bg-primary",
                      textColor: "text-primary",
                      delta: formatDelta(impactData.uplift_pct),
                    },
                    {
                      label: "Post-campagne",
                      value: impactData.post_campaign_nss,
                      color: "bg-tertiary",
                      textColor: "text-tertiary",
                      delta:
                        impactData.retention_pct == null
                          ? null
                          : `${impactData.retention_pct}% retention`,
                    },
                  ].map(({ label, value, color, textColor, delta }) => (
                    <div key={label} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-8 bg-surface-container-highest rounded-full overflow-hidden">
                          <div
                            className={`w-full ${color}`}
                            style={{ height: `${safeRatio(value, activeNss || value)}%` }}
                          ></div>
                        </div>
                        <div>
                          <p className={`text-[10px] uppercase ${textColor}`}>{label}</p>
                          <p className="font-headline font-bold text-sm">
                            {value == null ? "n/a" : `${value} NSS`}
                          </p>
                        </div>
                      </div>
                      {delta ? (
                        <div className="flex items-center text-[10px] font-bold text-tertiary">
                          <span className="material-symbols-outlined text-sm">
                            arrow_drop_up
                          </span>
                          {delta}
                        </div>
                      ) : (
                        <span className="text-[10px] text-on-surface-variant/40">Base</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="bg-surface-container-high p-4 rounded-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-tertiary text-sm">
                    auto_awesome
                  </span>
                  <span className="text-[10px] font-bold uppercase text-tertiary tracking-wider">
                    Insight IA
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {impactData.ai_insight}
                </p>
              </div>
            </div>
          </section>

          <section className="col-span-12 lg:col-span-8 space-y-6">
            <div className="bg-surface-container-low rounded-lg overflow-hidden">
              <div className="p-6 flex items-center justify-between border-b border-surface-container-highest">
                <div>
                  <h3 className="font-headline font-bold text-lg">Suivi des Campagnes</h3>
                  <p className="text-xs text-on-surface-variant">
                    {
                      allCampaigns.filter((campaign) => campaign.status === "ACTIVE").length
                    }{" "}
                    campagnes actives sur le marche algerien
                  </p>
                </div>
                <div className="flex items-center gap-1 bg-surface-container-highest p-1 rounded-sm">
                  {(["TOUTES", "ACTIVES", "ARCHIVES"] as const).map((nextFilter) => (
                    <button
                      key={nextFilter}
                      onClick={() => setFilter(nextFilter)}
                      className={`px-3 py-1 text-[10px] font-bold rounded-sm transition-colors ${
                        filter === nextFilter
                          ? "bg-surface-bright text-on-surface"
                          : "text-on-surface-variant hover:text-on-surface"
                      }`}
                    >
                      {nextFilter}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                {campaignsLoading ? (
                  <div className="p-6 space-y-3">
                    {[1, 2, 3].map((item) => (
                      <div
                        key={item}
                        className="h-14 bg-surface-container-high rounded animate-pulse"
                      ></div>
                    ))}
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-surface-container-lowest/50">
                      <tr>
                        {[
                          "Campagne / Influenceur",
                          "Plateforme",
                          "Statut",
                          "Budget (DZA)",
                          "Impact NSS",
                        ].map((heading, index) => (
                          <th
                            key={heading}
                            className={`px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ${
                              index > 1 ? "text-center" : ""
                            }`}
                          >
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-container-highest/30">
                      {filteredCampaigns.map((campaign) => (
                        <tr
                          key={campaign.id}
                          onClick={() =>
                            setSelectedCampaign(
                              campaign.id === selectedCampaign ? null : campaign.id,
                            )
                          }
                          className={`hover:bg-surface-container-high/40 transition-colors group cursor-pointer ${
                            selectedCampaign === campaign.id
                              ? "bg-surface-container-high/60"
                              : ""
                          } ${campaign.status === "ANNULEE" ? "opacity-50" : ""}`}
                          data-testid={`campaign-row-${campaign.id}`}
                        >
                          <td className="px-6 py-5">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-surface-container-high rounded flex items-center justify-center overflow-hidden border border-surface-container-highest shrink-0">
                                <span className="material-symbols-outlined text-primary text-sm">
                                  campaign
                                </span>
                              </div>
                              <div>
                                <p className="text-sm font-bold group-hover:text-primary transition-colors">
                                  {campaign.name}
                                </p>
                                <p className="text-[10px] text-on-surface-variant">
                                  {campaign.influencer}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <span className="text-xs font-medium text-on-surface-variant">
                              {campaign.platform}
                            </span>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <StatusBadge status={campaign.status} />
                          </td>
                          <td className="px-6 py-5 text-right">
                            <p className="text-sm font-headline font-bold">
                              {formatBudget(campaign.budget_dza)}
                            </p>
                          </td>
                          <td className="px-6 py-5 text-right">
                            {selectedCampaign === campaign.id && impactData.uplift_pct != null ? (
                              <div className="flex items-center justify-end gap-1 text-tertiary">
                                <span className="material-symbols-outlined text-sm">
                                  trending_up
                                </span>
                                <span className="text-sm font-bold">
                                  {formatDelta(impactData.uplift_pct)}
                                </span>
                              </div>
                            ) : (
                              <span className="text-[10px] font-bold text-on-surface-variant">
                                -
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Top Performeur (Mois)
                </p>
                <div className="mt-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full border-2 border-primary/20 p-0.5 flex items-center justify-center bg-surface-container-highest">
                    <span className="material-symbols-outlined text-primary text-sm">
                      person
                    </span>
                  </div>
                  <div>
                    <h4 className="font-headline font-bold text-lg">
                      {allCampaigns[0]?.influencer || "Aucun influenceur"}
                    </h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-on-surface-variant">
                        {allCampaigns[0]?.type || "Campagne"}
                      </span>
                      <span className="w-1 h-1 bg-on-surface-variant rounded-full"></span>
                      <span className="text-xs text-tertiary">
                        {allCampaigns[0]?.platform || "Plateforme non renseignée"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-tertiary/5 rounded-full blur-3xl group-hover:bg-tertiary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Budget Total Engage
                </p>
                <div className="mt-3">
                  <h4 className="font-headline font-black text-xl tracking-tight">
                    {allCampaigns
                      .reduce((sum, campaign) => sum + (campaign.budget_dza || 0), 0)
                      .toLocaleString("fr-FR")}
                    <span className="text-sm font-normal text-on-surface-variant ml-1">
                      DZA
                    </span>
                  </h4>
                  <div className="w-full h-1 bg-surface-container-highest mt-2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{
                        width: `${Math.min(
                          100,
                          allCampaigns.length ? (allCampaigns.length / 10) * 100 : 0,
                        )}%`,
                      }}
                    ></div>
                  </div>
                  <p className="text-[10px] text-on-surface-variant mt-1 uppercase font-bold">
                    {allCampaigns.length} campagne(s) chargee(s)
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
