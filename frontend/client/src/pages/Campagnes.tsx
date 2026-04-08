import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import {
  buildCampaignCreatePayload,
  mapCampaign,
  mapCampaignOverview,
  mapCampaignImpact,
} from "@/lib/apiMappings";
import { filterCampaignViews } from "@/lib/pageSearchFilters";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

const CAMPAIGN_ROW_AVATARS = [
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAe-qHYLr1lBNJS2zW04-OeHhIs6Wi51BhptWX8z5YE72TYHQwxKDQDrHAAaU6tNYs4tE14HJpPKa-GjTEGy2fD_Bflkxz_ZIYGlHvFu7fr5As5IJ8_V9fsuM5PzTgmgq46CmsW1UmDTSs5MoaA5hF0oeKg72_o8zGp1mnMUB5b3IlPzNGtiYzmYvx_bRQhWyEgKNavdL-AhhbFRIuCgbdcG_NS7cgJlrIFIn8OdwQHEIvhsxHl78Fc8T3qJhSnmCAQi0nsrorqgzIb",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCohVkqL6sywZosVDw1uvnbJcW6yvRyreNc9MsFDE52JQIwm683p7H05E8pp6PDN4FrOGVp_LPf3Mz8vs1tpbQGN_4_F_e-jV0H8AeJ3QgWRcVG3_SHYpJMn18XxqGVguSX4HG969i-tTBIYSVko6V3rrU7CBZPf_4u-_YYSGRp9_swBjxU-BPyThIv6rNTTvZtQBpYrA3myVSnpRkRdbjke4Ld-yGT-SHiFLwcuL3AYz-00ah3j9M7dUIqHEF3PldkbM4TtZoyiezH",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCIdDfm2qBDICiHPJBx5Pnebx6vFO_aqoL32jzyEgrWyqnxYiMJhBW5J8jv8MXzhmUfj_yrQDGvw-sRS85hbAw5Dcn5VSSpqSMSH9aJSG59yzALTJE_fVPOwT2NWtZvWIddO_k_uDgY5qb4T-bgZKowU-A0ShQKenKoXm6z9ugemufP-a3j_V32B6swTwx39SHWunxQ3UkDrbup44hiFST1DCBC8gpsgZxYxWuc9asZ0scZyOJ0uGpHXKI9ArZ2rOabXrkqNH_aIz0G",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAKOS9oMsA1t7QfbZF0fVNW8W4XoMinVLWZoYhLDT2fVlVGjdNvHbeOyVk61ThnnAFZdk10hzE-OtFP8GuaUr0Dsj2pExS5aQMbxI3HY4fKC2gD_W850m1WeRhHSr9Y9Ca3Uj6gvMKsk6OlsW8K1UaX22U7gBMXKUJohmQWZMWfodDSwPhfCO0rnteceKoqechbptW4Sc3V_5r2pbiiivaV1r7DGKtzB3KNbwf50rqYBlF4FiZQqPLAoksGt2GH_YoIfP2BGQdxiaJw",
];

const PLATFORM_ICON_ASSETS: Record<string, { src: string; className: string }> = {
  instagram: {
    src: "https://lh3.googleusercontent.com/aida-public/AB6AXuDUDUCBMLfYEFc5K7ORw-d2EC3eSsOQmxwUpSvXWbY39J89JjcdLyEorfN8jH2FpON5ArO4-GA2wpejl0f6G4j6ClzGTSoFzmms6_np5GfQSuFxwO5h9VVsTHTaV2IQWnI99OjToOHVuLPHCSZYkY_cm8IsJkE4X6IoSnz5GHxeTPSXMcZhNXxtEK4FMf2aLmJ3tLfAUKwq_73yZ_znIRmzvpZEI9pvGdTkGg0aOfSBtvRJLK-_BNpKSz-_07gmFzutSvhbFeo_IoBt",
    className: "w-4 h-4 grayscale opacity-60",
  },
  youtube: {
    src: "https://lh3.googleusercontent.com/aida-public/AB6AXuB24SDONEWt2EJ_Xo5W5wuM0juWMaPiKFdjy9NJPjoMvZVhWbbH3uWCfoMAtZpxtIkCUKyh4n2vXadtU3bD78eHrPtjTQ2_G74iTWb5gdEF8ZlwlOfn2NlNefEZmk2_s752OtGFIQCWmquyPoZzfTF0cJeUx9wWMml1U4SBk1AxCGQFF1mpMBwCUZ-2gNny6YO0uQxCGN9nLbL0OJfzKsInc0uOmDh2Er1NmteOF51eQiwb2qFGVnkoNBqA4Bf1Qk2ZWRCCSe_gqnv_",
    className: "w-5 h-5",
  },
  facebook: {
    src: "https://lh3.googleusercontent.com/aida-public/AB6AXuCw1mz7XrLrX9bg5g5QIL66d44Wjpa6HewmD8YpHlpNEc75xogUaejHtLfGLQIJjYLMgcZ2nfjJ2F7M-HiZNJNPELtVW3U-_V0S8VrhGPK6DtcNmnEBudyXVYDB1XhToGJz3_oURO8_F2WmfvvgFj6ecZdh9oRNHdKXRdWF1PPXUwZ5QlSW5eALIOvAoMnqSLzFVnDV2dfWjQoHpuQ0hYCLp-nSGLi4T7lchS9t-HqReQbc9N6QdG7SDLkJgCbMseKBxJfEXkdaA9hl",
    className: "w-4 h-4 grayscale opacity-60",
  },
};

const TOP_PERFORMER_AVATAR =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCIzPFiI1I621n9zcK0kxo-q6Msxqqls35FxSRtfx-19ykBbB_8c3CXueUs9nGtgZOJ-OZic6T92CKFD3HNo721iojRJYb7CF6GIVF7AtGgC_miiV8noUEYFqHUxH40pGulzFbyy82XRSUanacopAv5Iv5E7sq43dWFFVfLOLjSmF8VFpBtrBtzUvihifOZoVNITsBRDV4Sd36Y6NRWNiuRRXfjwRtjWfKinFsBYPkGSy2vthpdMoihyr-EF-_GjTXo8ctMwQ_HtVWN";

const ROWS_PER_PAGE = 4;

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

interface CampaignStatsView {
  quarterlyBudgetCommitted: number;
  quarterlyBudgetAllocation: number;
  quarterLabel: string;
  activeCampaignsCount: number;
  topPerformer: {
    campaign_id: string;
    campaign_name: string | null;
    influencer_handle: string | null;
    platform: string | null;
    status: string | null;
    budget_dza: number | null;
    roi_pct: number | null;
    engagement_rate: number | null;
    signal_count: number;
    sentiment_breakdown: Record<string, number>;
    negative_aspects: string[];
    selection_basis: string | null;
  } | null;
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

function mapCampaignStatsView(value: unknown): CampaignStatsView {
  const stats = mapCampaignOverview(value);
  return {
    quarterlyBudgetCommitted: stats.quarterly_budget_committed,
    quarterlyBudgetAllocation: stats.quarterly_budget_allocation,
    quarterLabel: stats.quarter_label,
    activeCampaignsCount: stats.active_campaigns_count,
    topPerformer: stats.top_performer
      ? {
          campaign_id: stats.top_performer.campaign_id,
          campaign_name: stats.top_performer.campaign_name ?? null,
          influencer_handle: stats.top_performer.influencer_handle ?? null,
          platform: stats.top_performer.platform ?? null,
          status: stats.top_performer.status ?? null,
          budget_dza: stats.top_performer.budget_dza ?? null,
          roi_pct: stats.top_performer.roi_pct ?? null,
          engagement_rate: stats.top_performer.engagement_rate ?? null,
          signal_count: stats.top_performer.signal_count,
          sentiment_breakdown: stats.top_performer.sentiment_breakdown,
          negative_aspects: stats.top_performer.negative_aspects,
          selection_basis: stats.top_performer.selection_basis ?? null,
        }
      : null,
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

function formatPct(value: number | null): string | null {
  if (value == null) return null;
  return `${value > 0 ? "+" : ""}${value}%`;
}

function safeRatio(value: number | null, max: number | null): number {
  if (value == null || max == null || max <= 0) return 0;
  return Math.max(0, Math.min(100, (value / max) * 100));
}

function campaignVisualAt(index: number): string {
  return CAMPAIGN_ROW_AVATARS[index % CAMPAIGN_ROW_AVATARS.length];
}

function platformAsset(platform: string) {
  return PLATFORM_ICON_ASSETS[platform.toLowerCase()] ?? null;
}

function campaignMetaLine(campaign: CampaignView): string {
  if (campaign.status === "ACTIVE") {
    return `${campaign.influencer} • ${campaign.end_date === "-" ? "En cours" : `Jusqu'au ${campaign.end_date}`}`;
  }
  if (campaign.status === "PLANIFIEE") {
    return `${campaign.influencer} • Démarre le ${campaign.start_date}`;
  }
  if (campaign.status === "TERMINEE") {
    return `${campaign.influencer} • Terminée`;
  }
  return "Archive Interne";
}

function budgetMetaLine(campaign: CampaignView): string {
  if (campaign.status === "ACTIVE") return `Total: ${formatBudget(campaign.budget_dza)} DA`;
  if (campaign.status === "PLANIFIEE") return "Engagement prévu";
  if (campaign.status === "TERMINEE") return "Consommé";
  return "";
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ACTIVE: "bg-tertiary/10 text-tertiary",
    PLANIFIEE: "bg-secondary-container text-on-secondary-container",
    TERMINEE: "bg-surface-container-highest text-on-surface-variant",
    ANNULEE: "bg-error/10 text-error",
  };
  const labelMap: Record<string, string> = {
    ACTIVE: "Active",
    PLANIFIEE: "PlanifiÃ©e",
    TERMINEE: "TerminÃ©e",
    ANNULEE: "AnnulÃ©e",
  };

  return (
    <span
      className={`px-2 py-1 rounded-sm text-[10px] font-bold uppercase tracking-widest ${
        map[status] ?? "bg-surface-container text-on-surface-variant"
      }`}
    >
      {labelMap[status] ?? status}
    </span>
  );
}

export default function Campagnes() {
  const [filter, setFilter] = useState<CampaignFilter>("TOUTES");
  const [currentPage, setCurrentPage] = useState(1);
  const [isComposerOpen, setIsComposerOpen] = useState(true);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const createFormSectionRef = useRef<HTMLDivElement | null>(null);
  const campaignNameInputRef = useRef<HTMLInputElement | null>(null);
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

  const { data: stats } = useQuery<CampaignStatsView>({
    queryKey: ["/api/campaigns/overview"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/campaigns/overview");
      return mapCampaignStatsView(await res.json());
    },
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
    const tabFiltered = allCampaigns.filter((campaign) => {
      if (filter === "ACTIVES") return campaign.status === "ACTIVE";
      if (filter === "ARCHIVES") {
        return campaign.status === "TERMINEE" || campaign.status === "ANNULEE";
      }
      return true;
    });
    return filterCampaignViews(tabFiltered, searchQuery);
  }, [allCampaigns, filter, searchQuery]);

  useEffect(() => {
    if (!filteredCampaigns.length) {
      setSelectedCampaign(null);
      return;
    }
    if (!selectedCampaign || !filteredCampaigns.some((campaign) => campaign.id === selectedCampaign)) {
      setSelectedCampaign(filteredCampaigns[0]?.id ?? null);
    }
  }, [filteredCampaigns, selectedCampaign]);

  const totalPages = Math.max(1, Math.ceil(filteredCampaigns.length / ROWS_PER_PAGE));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const pagedCampaigns = filteredCampaigns.slice(
    (safeCurrentPage - 1) * ROWS_PER_PAGE,
    safeCurrentPage * ROWS_PER_PAGE,
  );

  const impactData = impact ?? {
    pre_campaign_nss: null,
    during_campaign_nss: null,
    post_campaign_nss: null,
    uplift_pct: null,
    retention_pct: null,
    ai_insight: "Analyse d'impact disponible dès qu'une campagne est sélectionnée.",
  };

  const statsData = stats ?? {
    quarterlyBudgetCommitted: 0,
    quarterlyBudgetAllocation: 0,
    quarterLabel: "Trimestre courant",
    activeCampaignsCount: 0,
    topPerformer: null,
  };

  const activeNss = impactData.during_campaign_nss;
  const postCampaignDeltaPct =
    impactData.during_campaign_nss != null &&
    impactData.post_campaign_nss != null &&
    impactData.during_campaign_nss !== 0
      ? Number(
          (
            ((impactData.post_campaign_nss - impactData.during_campaign_nss) /
              impactData.during_campaign_nss) *
            100
          ).toFixed(1),
        )
      : null;
  const totalBudget = statsData.quarterlyBudgetCommitted;
  const quarterlyAllocation = statsData.quarterlyBudgetAllocation;
  const allocationPct = Math.min(
    100,
    quarterlyAllocation > 0 ? Math.round((totalBudget / quarterlyAllocation) * 100) : 0,
  );
  const topPerformer = statsData.topPerformer;
  const topPerformerMetrics = [
    topPerformer?.roi_pct != null ? `ROI ${formatPct(topPerformer.roi_pct)}` : null,
    topPerformer?.engagement_rate != null
      ? `Engagement ${formatPct(topPerformer.engagement_rate)}`
      : null,
    topPerformer && topPerformer.signal_count > 0
      ? `${topPerformer.signal_count} signaux`
      : null,
  ].filter(Boolean);

  const focusCampaignComposer = () => {
    setIsComposerOpen(true);
    createFormSectionRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    window.setTimeout(() => {
      campaignNameInputRef.current?.focus();
    }, 120);
  };

  return (
    <AppShell
      headerSearchPlaceholder="Rechercher une campagne..."
      onSearch={setSearchQuery}
      avatarSrc={STITCH_AVATARS.campagnes.src}
      avatarAlt={STITCH_AVATARS.campagnes.alt}
      sidebarFooterAvatarSrc={STITCH_AVATARS.campagnes.src}
      sidebarFooterAvatarAlt={STITCH_AVATARS.campagnes.alt}
      sidebarFooterSubtitle="Ramy Pulse Pro"
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
              onClick={focusCampaignComposer}
              className="px-6 py-2 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed text-xs font-bold transition-transform active:scale-95 shadow-lg shadow-primary/10 rounded-sm"
              data-testid="btn-create-campaign"
              type="button"
            >
              CRÉER UNE CAMPAGNE
            </button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <section className="col-span-12 lg:col-span-4 space-y-6">
            <div
              ref={createFormSectionRef}
              className="bg-surface-container-low rounded-lg p-6 flex flex-col gap-5"
            >
              <div className="flex items-center justify-between border-b border-surface-container-highest pb-4">
                <h3 className="font-headline font-bold text-lg">Nouvelle Campagne</h3>
                <button
                  className="material-symbols-outlined text-primary cursor-pointer"
                  onClick={() => setIsComposerOpen((current) => !current)}
                  type="button"
                >
                  {isComposerOpen ? "expand_less" : "expand_more"}
                </button>
              </div>
              {isComposerOpen ? (
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
                    ref={campaignNameInputRef}
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
                      <option value="tiktok">TikTok</option>
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
                      placeholder="500,000"
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
                      Début
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
                    Mots-clés
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
              ) : (
                <button
                  className="w-full py-3 bg-surface-container-high text-on-surface text-xs font-bold uppercase tracking-widest rounded-sm hover:bg-surface-bright transition-colors"
                  onClick={focusCampaignComposer}
                  type="button"
                >
                  Ouvrir le formulaire
                </button>
              )}
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
                      label: "Pré-campagne",
                      value: impactData.pre_campaign_nss,
                      color: "bg-on-surface-variant",
                      textColor: "text-on-surface-variant",
                      delta: "— Base",
                      deltaTone: "text-on-surface-variant/40",
                      deltaIcon: null,
                    },
                    {
                      label: "Pendant",
                      value: impactData.during_campaign_nss,
                      color: "bg-primary",
                      textColor: "text-primary",
                      delta: formatDelta(impactData.uplift_pct),
                      deltaTone: "text-tertiary",
                      deltaIcon:
                        impactData.uplift_pct != null && impactData.uplift_pct < 0
                          ? "arrow_drop_down"
                          : "arrow_drop_up",
                    },
                    {
                      label: "Post-campagne",
                      value: impactData.post_campaign_nss,
                      color: "bg-tertiary",
                      textColor: "text-tertiary",
                      delta:
                        postCampaignDeltaPct == null
                          ? "—"
                          : `${postCampaignDeltaPct > 0 ? "+" : ""}${postCampaignDeltaPct}%`,
                      deltaTone:
                        postCampaignDeltaPct != null && postCampaignDeltaPct < 0
                          ? "text-error"
                          : "text-tertiary",
                      deltaIcon:
                        postCampaignDeltaPct == null
                          ? null
                          : postCampaignDeltaPct < 0
                            ? "arrow_drop_down"
                            : "arrow_drop_up",
                    },
                  ].map(({ label, value, color, textColor, delta, deltaTone, deltaIcon }) => (
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
                        <div className={`flex items-center text-[10px] font-bold ${deltaTone}`}>
                          {deltaIcon ? (
                            <span className="material-symbols-outlined text-sm">
                              {deltaIcon}
                            </span>
                          ) : null}
                          {delta}
                        </div>
                      ) : (
                        <span className="text-[10px] text-on-surface-variant/40">—</span>
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
                    {statsData.activeCampaignsCount}{" "}
                    campagnes actives sur le marché algérien
                  </p>
                </div>
                <div className="flex items-center gap-1 bg-surface-container-highest p-1 rounded-sm">
                  {(["TOUTES", "ACTIVES", "ARCHIVES"] as const).map((nextFilter) => (
                    <button
                      key={nextFilter}
                      onClick={() => {
                        setFilter(nextFilter);
                        setCurrentPage(1);
                      }}
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
                      {pagedCampaigns.map((campaign, index) => {
                        const iconAsset = platformAsset(campaign.platform);
                        return (
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
                              <div className="w-10 h-10 bg-surface-container-high rounded flex items-center justify-center overflow-hidden border border-surface-container-highest shrink-0">
                                <img
                                  alt={`Campaign visual ${index + 1}`}
                                  className="w-full h-full object-cover"
                                  src={campaignVisualAt(index)}
                                />
                              </div>
                              <div>
                                <p className="text-sm font-bold group-hover:text-primary transition-colors">
                                  {campaign.name}
                                </p>
                                <p className="text-[10px] text-on-surface-variant">
                                  {campaignMetaLine(campaign)}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <div className="flex justify-center">
                              <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center">
                                {iconAsset ? (
                                  <img
                                    alt={`${campaign.platform} icon`}
                                    className={iconAsset.className}
                                    src={iconAsset.src}
                                  />
                                ) : (
                                  <span className="material-symbols-outlined text-on-surface-variant text-sm">
                                    language
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5 text-center">
                            <StatusBadge status={campaign.status} />
                          </td>
                          <td className="px-6 py-5 text-right">
                            <p className="text-sm font-headline font-bold">
                              {formatBudget(campaign.budget_dza)}
                            </p>
                            <p className="text-[10px] text-on-surface-variant">
                              {budgetMetaLine(campaign)}
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
                                —
                              </span>
                            )}
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="p-4 bg-surface-container-lowest/30 flex items-center justify-between">
                <p className="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">
                  {`Page ${safeCurrentPage} de ${totalPages}`}
                </p>
                <div className="flex gap-2">
                  <button
                    className="w-8 h-8 flex items-center justify-center bg-surface-container-high text-on-surface-variant hover:text-on-surface rounded-sm disabled:opacity-40"
                    disabled={safeCurrentPage <= 1}
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    type="button"
                  >
                    <span className="material-symbols-outlined text-sm">chevron_left</span>
                  </button>
                  <button
                    className="w-8 h-8 flex items-center justify-center bg-surface-container-high text-on-surface rounded-sm disabled:opacity-40"
                    disabled={safeCurrentPage >= totalPages}
                    onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                    type="button"
                  >
                    <span className="material-symbols-outlined text-sm text-primary">
                      chevron_right
                    </span>
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Top Performeur (Mois)
                </p>
                <div className="mt-4 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full border-2 border-primary/20 p-1">
                    <img
                      alt="Top performer avatar"
                      className="w-full h-full rounded-full object-cover"
                      src={TOP_PERFORMER_AVATAR}
                    />
                  </div>
                  <div>
                    <h4 className="font-headline font-bold text-lg">
                      {topPerformer?.influencer_handle ||
                        topPerformer?.campaign_name ||
                        "Aucune campagne prioritaire"}
                    </h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-on-surface-variant">
                        {topPerformer?.campaign_name || "Campagne"}
                      </span>
                      <span className="w-1 h-1 bg-on-surface-variant rounded-full"></span>
                      <span className="text-xs text-tertiary">
                        {topPerformer?.platform || "Plateforme non renseignée"}
                      </span>
                    </div>
                    {topPerformerMetrics.length > 0 ? (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {topPerformerMetrics.map((metric) => (
                          <span
                            key={metric}
                            className="px-2 py-1 rounded-sm bg-surface-container-high text-[10px] font-bold uppercase tracking-widest text-on-surface-variant"
                          >
                            {metric}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                        BasÃ© sur {topPerformer?.selection_basis || "budget_dza"}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              <div className="bg-surface-container-low rounded-lg p-6 relative overflow-hidden group">
                <div className="absolute right-[-10%] top-[-20%] w-32 h-32 bg-tertiary/5 rounded-full blur-3xl group-hover:bg-tertiary/10 transition-all"></div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  Budget Total Engagé
                </p>
                <div className="mt-4">
                  <h4 className="font-headline font-black text-2xl tracking-tight">
                    {totalBudget.toLocaleString("fr-FR")}
                    <span className="text-sm font-normal text-on-surface-variant ml-1">
                      DZA
                    </span>
                  </h4>
                  <div className="w-full h-1 bg-surface-container-highest mt-3 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${allocationPct}%` }}
                    ></div>
                  </div>
                  <p className="text-[10px] text-on-surface-variant mt-2 uppercase font-bold">
                    {allocationPct}% de l'allocation trimestrielle ({statsData.quarterLabel})
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
