import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Campaign, CampaignEngagementSummary, CampaignPost, CredentialSummary } from "@shared/schema";
import {
  mapCampaign,
  mapCampaignEngagementSummary,
  mapCampaignPost,
  mapCredentialSummary,
} from "@/lib/apiMappings";
import { apiRequest } from "@/lib/queryClient";
import { toast } from "@/hooks/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface CampaignPostFormState {
  platform: string;
  post_platform_id: string;
  post_url: string;
  entity_type: string;
  entity_name: string;
  credential_id: string;
}

interface MetricsFormState {
  likes: string;
  comments: string;
  shares: string;
  views: string;
  reach: string;
  impressions: string;
  saves: string;
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

function blankCampaignPostForm(): CampaignPostFormState {
  return {
    platform: "instagram",
    post_platform_id: "",
    post_url: "",
    entity_type: "brand",
    entity_name: "",
    credential_id: "",
  };
}

function blankMetricsForm(): MetricsFormState {
  return {
    likes: "0",
    comments: "0",
    shares: "0",
    views: "0",
    reach: "0",
    impressions: "0",
    saves: "0",
  };
}

function buildMetricsPayload(form: MetricsFormState): Record<string, number> {
  return {
    likes: Number(form.likes || 0),
    comments: Number(form.comments || 0),
    shares: Number(form.shares || 0),
    views: Number(form.views || 0),
    reach: Number(form.reach || 0),
    impressions: Number(form.impressions || 0),
    saves: Number(form.saves || 0),
  };
}

export function AdminCampaignOpsView() {
  const queryClientHook = useQueryClient();
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [postForm, setPostForm] = useState<CampaignPostFormState>(blankCampaignPostForm());
  const [metricsForm, setMetricsForm] = useState<MetricsFormState>(blankMetricsForm());
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [revenueInput, setRevenueInput] = useState("");
  const [opsError, setOpsError] = useState<string | null>(null);

  const { data: campaigns, isLoading: campaignsLoading } = useQuery<Campaign[]>({
    queryKey: ["/api/campaigns"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/campaigns");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapCampaign);
    },
  });

  const { data: credentials } = useQuery<CredentialSummary[]>({
    queryKey: ["/api/social-metrics/credentials"],
    queryFn: async () => {
      const res = await apiRequest("GET", "/api/social-metrics/credentials");
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapCredentialSummary);
    },
  });

  const { data: posts, isLoading: postsLoading } = useQuery<CampaignPost[]>({
    queryKey: ["/api/social-metrics/campaigns", selectedCampaignId, "posts"],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/social-metrics/campaigns/${selectedCampaignId}/posts`);
      const payload = await res.json();
      return (Array.isArray(payload) ? payload : []).map(mapCampaignPost);
    },
    enabled: Boolean(selectedCampaignId),
  });

  const { data: engagementSummary, isLoading: engagementLoading } =
    useQuery<CampaignEngagementSummary>({
      queryKey: ["/api/social-metrics/campaigns", selectedCampaignId, "summary"],
      queryFn: async () => {
        const res = await apiRequest("GET", `/api/social-metrics/campaigns/${selectedCampaignId}`);
        return mapCampaignEngagementSummary(await res.json());
      },
      enabled: Boolean(selectedCampaignId),
    });

  const campaignOptions = campaigns ?? [];
  const credentialOptions = credentials ?? [];
  const campaignPosts = posts ?? [];

  const selectedCampaign = useMemo(
    () => campaignOptions.find((campaign) => campaign.campaign_id === selectedCampaignId) ?? null,
    [campaignOptions, selectedCampaignId],
  );

  useEffect(() => {
    if (!campaignOptions.length) {
      setSelectedCampaignId(null);
      return;
    }
    setSelectedCampaignId((current) =>
      current && campaignOptions.some((campaign) => campaign.campaign_id === current)
        ? current
        : campaignOptions[0].campaign_id,
    );
  }, [campaignOptions]);

  useEffect(() => {
    setRevenueInput(
      selectedCampaign?.revenue_dza != null ? String(selectedCampaign.revenue_dza) : "",
    );
  }, [selectedCampaign]);

  useEffect(() => {
    if (!campaignPosts.length) {
      setSelectedPostId(null);
      return;
    }
    setSelectedPostId((current) =>
      current && campaignPosts.some((post) => post.post_id === current)
        ? current
        : campaignPosts[0].post_id,
    );
  }, [campaignPosts]);

  const invalidateCampaignOps = () => {
    queryClientHook.invalidateQueries({ queryKey: ["/api/campaigns"] });
    if (selectedCampaignId) {
      queryClientHook.invalidateQueries({
        queryKey: ["/api/social-metrics/campaigns", selectedCampaignId, "posts"],
      });
      queryClientHook.invalidateQueries({
        queryKey: ["/api/social-metrics/campaigns", selectedCampaignId, "summary"],
      });
    }
  };

  const addPostMutation = useMutation({
    mutationFn: async (payload: { campaignId: string; form: CampaignPostFormState }) => {
      const res = await apiRequest("POST", `/api/social-metrics/campaigns/${payload.campaignId}/posts`, {
        platform: payload.form.platform,
        post_platform_id: payload.form.post_platform_id,
        post_url: payload.form.post_url || undefined,
        entity_type: payload.form.entity_type,
        entity_name: payload.form.entity_name || undefined,
        credential_id: payload.form.credential_id || undefined,
      });
      return mapCampaignPost(await res.json());
    },
    onSuccess: () => {
      setPostForm(blankCampaignPostForm());
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const deletePostMutation = useMutation({
    mutationFn: async (postId: string) => {
      await apiRequest("DELETE", `/api/social-metrics/posts/${postId}`);
    },
    onSuccess: () => {
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const collectMetricsMutation = useMutation({
    mutationFn: async (campaignId: string) => {
      const res = await apiRequest("POST", `/api/social-metrics/campaigns/${campaignId}/collect`);
      return res.json();
    },
    onSuccess: () => {
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const manualMetricsMutation = useMutation({
    mutationFn: async (payload: { postId: string; form: MetricsFormState }) => {
      const res = await apiRequest(
        "POST",
        `/api/social-metrics/posts/${payload.postId}/metrics/manual`,
        buildMetricsPayload(payload.form),
      );
      return res.json();
    },
    onSuccess: () => {
      setMetricsForm(blankMetricsForm());
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const screenshotMutation = useMutation({
    mutationFn: async (payload: { postId: string; file: File; form: MetricsFormState }) => {
      const formData = new FormData();
      formData.append("file", payload.file);
      for (const [key, value] of Object.entries(buildMetricsPayload(payload.form))) {
        formData.append(key, String(value));
      }
      const res = await apiRequest(`/api/social-metrics/posts/${payload.postId}/metrics/screenshot`, {
        method: "POST",
        body: formData,
      });
      return res.json();
    },
    onSuccess: () => {
      setMetricsForm(blankMetricsForm());
      setScreenshotFile(null);
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const revenueMutation = useMutation({
    mutationFn: async (payload: { campaignId: string; revenue_dza: number }) => {
      const res = await apiRequest(
        "PATCH",
        `/api/social-metrics/campaigns/${payload.campaignId}/revenue`,
        { revenue_dza: payload.revenue_dza },
      );
      return res.json();
    },
    onSuccess: () => {
      setOpsError(null);
      invalidateCampaignOps();
    },
    onError: (error: Error) => {
      toast({ title: "Erreur", description: error.message || "Une erreur est survenue", variant: "destructive" });
    },
  });

  const handleAddPost = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCampaignId) {
      setOpsError("Aucune campagne sélectionnée.");
      return;
    }
    if (!postForm.post_platform_id.trim()) {
      setOpsError("post_platform_id est requis.");
      return;
    }
    addPostMutation.mutate({ campaignId: selectedCampaignId, form: postForm });
  };

  const handleManualMetrics = () => {
    if (!selectedPostId) {
      setOpsError("Sélectionne un post avant la saisie manuelle.");
      return;
    }
    manualMetricsMutation.mutate({ postId: selectedPostId, form: metricsForm });
  };

  const handleScreenshotUpload = () => {
    if (!selectedPostId) {
      setOpsError("Sélectionne un post avant l'upload.");
      return;
    }
    if (!screenshotFile) {
      setOpsError("Ajoute une capture avant l'upload.");
      return;
    }
    screenshotMutation.mutate({ postId: selectedPostId, file: screenshotFile, form: metricsForm });
  };

  const handleRevenueSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCampaignId) {
      setOpsError("Aucune campagne sélectionnée.");
      return;
    }
    const revenue_dza = Number(revenueInput);
    if (!Number.isFinite(revenue_dza) || revenue_dza < 0) {
      setOpsError("revenue_dza doit être un entier positif.");
      return;
    }
    revenueMutation.mutate({ campaignId: selectedCampaignId, revenue_dza });
  };

  return (
    <div className="grid grid-cols-12 gap-8 items-start">
      <div className="col-span-12 lg:col-span-7 space-y-6">
        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Campaign Ops</p>
              <h2 className="text-xl font-headline font-bold mt-1">Engagement & Sentiment Operations</h2>
            </div>
            <select className="w-full max-w-sm bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={selectedCampaignId ?? ""} onChange={(event) => setSelectedCampaignId(event.target.value || null)}>
              {campaignOptions.map((campaign) => (
                <option key={campaign.campaign_id} value={campaign.campaign_id}>{campaign.campaign_name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Résumé campagne</p>
              <h3 className="text-lg font-bold mt-1">{selectedCampaign?.campaign_name || "Aucune campagne sélectionnée"}</h3>
            </div>
            <button onClick={() => selectedCampaignId && collectMetricsMutation.mutate(selectedCampaignId)} disabled={!selectedCampaignId || collectMetricsMutation.isPending} className="bg-surface-container-high text-on-surface px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50">
              {collectMetricsMutation.isPending ? "Collecte..." : "Collecter via API"}
            </button>
          </div>
          {campaignsLoading || engagementLoading ? (
            <div className="h-24 bg-surface-container-high rounded animate-pulse"></div>
          ) : engagementSummary ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Posts liés", value: engagementSummary.post_count },
                { label: "Engagement rate", value: `${engagementSummary.engagement_rate ?? 0}%` },
                { label: "Signals", value: engagementSummary.signal_count },
                { label: "Aspects négatifs", value: engagementSummary.negative_aspects.join(", ") || "Aucun" },
              ].map((item) => (
                <div key={item.label} className="bg-surface-container-high p-4 rounded-lg">
                  <div className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold">{item.label}</div>
                  <div className="mt-2 text-lg font-bold text-on-surface">{item.value}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-on-surface-variant">Aucune donnée de campagne disponible.</div>
          )}
        </div>

        <div className="bg-surface-container rounded-xl border border-white/5 overflow-hidden">
          <div className="p-6 border-b border-white/5">
            <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Posts liés</p>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-container-high/30">
              <tr>
                {["Post", "Plateforme", "Entity", "Credential", "Actions"].map((heading) => (
                  <th key={heading} className="px-6 py-3 font-bold opacity-70 text-xs uppercase">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {postsLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4">
                    <div className="h-10 bg-surface-container-high rounded animate-pulse"></div>
                  </td>
                </tr>
              ) : campaignPosts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-6 text-on-surface-variant">Aucun post lié à cette campagne.</td>
                </tr>
              ) : (
                campaignPosts.map((post) => (
                  <tr key={post.post_id} className={selectedPostId === post.post_id ? "bg-surface-container-high/40" : ""}>
                    <td className="px-6 py-4">
                      <button onClick={() => setSelectedPostId(post.post_id)} className="text-left hover:text-primary">
                        <div className="font-semibold">{post.post_platform_id}</div>
                        <div className="text-xs text-on-surface-variant">{post.post_url || "URL non fournie"}</div>
                      </button>
                    </td>
                    <td className="px-6 py-4">{post.platform}</td>
                    <td className="px-6 py-4">{post.entity_name || post.entity_type || "n/a"}</td>
                    <td className="px-6 py-4 text-xs text-on-surface-variant">{post.credential_id || "Aucun"}</td>
                    <td className="px-6 py-4 text-right">
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <button disabled={deletePostMutation.isPending} className="text-xs font-bold text-error disabled:opacity-40">
                            Retirer le post
                          </button>
                        </AlertDialogTrigger>
                        <AlertDialogContent className="bg-surface-container border-outline-variant/20">
                          <AlertDialogHeader>
                            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
                            <AlertDialogDescription>
                              Cette action est irréversible. Le post sera définitivement supprimé.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel className="bg-surface-container-high text-on-surface">Annuler</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-error text-on-error hover:bg-error/80"
                              onClick={() => deletePostMutation.mutate(post.post_id)}
                            >
                              Supprimer
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-5 space-y-6">
        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">Ajouter un post lié</p>
          <form className="space-y-4" onSubmit={handleAddPost}>
            <div className="grid grid-cols-2 gap-4">
              <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={postForm.platform} onChange={(event) => setPostForm({ ...postForm, platform: event.target.value })}>
                {PLATFORM_OPTIONS.filter((option) => option.value !== "import").map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={postForm.entity_type} onChange={(event) => setPostForm({ ...postForm, entity_type: event.target.value })}>
                {CREDENTIAL_ENTITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
            <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="post_platform_id" value={postForm.post_platform_id} onChange={(event) => setPostForm({ ...postForm, post_platform_id: event.target.value })} />
            <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="URL du post" value={postForm.post_url} onChange={(event) => setPostForm({ ...postForm, post_url: event.target.value })} />
            <div className="grid grid-cols-2 gap-4">
              <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="text" placeholder="Entity Name" value={postForm.entity_name} onChange={(event) => setPostForm({ ...postForm, entity_name: event.target.value })} />
              <select className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" value={postForm.credential_id} onChange={(event) => setPostForm({ ...postForm, credential_id: event.target.value })}>
                <option value="">Aucun credential</option>
                {credentialOptions.map((credential) => (
                  <option key={credential.credential_id} value={credential.credential_id}>{credential.entity_name} · {credential.platform}</option>
                ))}
              </select>
            </div>
            <button type="submit" disabled={addPostMutation.isPending || !selectedCampaignId} className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
              {addPostMutation.isPending ? "Ajout..." : "Lier le post à la campagne"}
            </button>
          </form>
        </div>

        <div className="bg-surface-container p-6 rounded-xl border border-white/5 space-y-4">
          <div>
            <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">Collecte & evidence</p>
            <h3 className="text-lg font-bold mt-1">{selectedPostId ? `Post sélectionné: ${selectedPostId}` : "Aucun post sélectionné"}</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(metricsForm).map(([key, value]) => (
              <div key={key}>
                <label className="block text-xs font-bold text-on-surface-variant mb-1 ml-1 capitalize">{key}</label>
                <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="number" value={value} onChange={(event) => setMetricsForm({ ...metricsForm, [key]: event.target.value })} />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button onClick={handleManualMetrics} disabled={!selectedPostId || manualMetricsMutation.isPending} className="py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
              {manualMetricsMutation.isPending ? "Sauvegarde..." : "Sauver en manuel"}
            </button>
            <button onClick={handleScreenshotUpload} disabled={!selectedPostId || screenshotMutation.isPending} className="py-3 bg-surface-container-high text-on-surface font-bold rounded-lg disabled:opacity-50">
              {screenshotMutation.isPending ? "Upload..." : "Uploader capture"}
            </button>
          </div>
          <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm file:mr-4 file:border-0 file:bg-primary file:text-on-primary file:px-3 file:py-2 file:rounded-lg" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setScreenshotFile(event.target.files?.[0] ?? null)} />
          {opsError ? <p className="text-xs text-error">{opsError}</p> : null}
        </div>

        <div className="bg-surface-container p-6 rounded-xl border border-white/5">
          <p className="text-xs font-bold text-on-surface-variant tracking-widest uppercase mb-5">Revenue attribué</p>
          <form className="space-y-4" onSubmit={handleRevenueSubmit}>
            <input className="w-full bg-surface-container-highest rounded-lg py-2 px-3 text-sm" type="number" placeholder="revenue_dza" value={revenueInput} onChange={(event) => setRevenueInput(event.target.value)} />
            <button type="submit" disabled={!selectedCampaignId || revenueMutation.isPending} className="w-full py-3 bg-primary text-on-primary font-bold rounded-lg disabled:opacity-50">
              {revenueMutation.isPending ? "Mise à jour..." : "Mettre à jour revenue_dza"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
