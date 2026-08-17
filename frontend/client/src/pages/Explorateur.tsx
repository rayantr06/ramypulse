import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { SignalAnalysisPanel } from "@/components/explorer/SignalAnalysisPanel";
import { PageHeader } from "@/components/PageHeader";
import { EmptyTenantState } from "@/components/EmptyTenantState";
import { buildExplorerAiView, toDisplayRelevanceScores } from "@/lib/explorerAiView";
import { apiRequest } from "@/lib/queryClient";
import {
  mapExplorerSearchResults,
  mapExplorerVerbatims,
} from "@/lib/apiMappings";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { toast } from "@/hooks/use-toast";
import { convertToCSV, downloadCSV } from "@/lib/csvExport";
import { STITCH_AVATARS } from "@/lib/stitchAssets";
import { formatSlmLabel, parseSlmAnalysis, type SlmAnalysisEnvelope } from "@/lib/slmV04";
import { useTenantId } from "@/lib/tenantContext";

const SENTIMENT_OPTIONS = [
  { value: "positif", label: "Positif" },
  { value: "negatif", label: "Négatif" },
  { value: "neutre", label: "Neutre" },
  { value: "mixte", label: "Mixte" },
] as const;
const WILAYA_OPTIONS = [
  "Alger", "Oran", "Constantine", "Annaba", "Blida", "Batna", "Sétif", "Tizi Ouzou",
  "Béjaïa", "Djelfa", "Biskra", "Mostaganem", "Tlemcen", "Médéa", "Msila",
];

const SOURCES = [
  { id: "facebook", label: "Facebook", icon: "social_leaderboard", color: "#1877F2" },
  { id: "google_maps", label: "Google Maps", icon: "location_on", color: "#EA4335" },
  { id: "youtube", label: "YouTube", icon: "video_library", color: "#FF0000" },
  { id: "instagram", label: "Instagram", icon: "photo_camera", color: "#E4405F" },
  { id: "import", label: "Import", icon: "file_upload", color: "#9ca3af" },
];

interface SearchResultView {
  id: string;
  source: string;
  content: string;
  relevance_score: number;
  sentiment: string;
  aspect: string;
  source_url: string;
  wilaya: string;
  created_at: string;
  analysis: SlmAnalysisEnvelope | null;
}

interface VerbatimView {
  id: string;
  date: string;
  time: string;
  source: string;
  aspect: string;
  sentiment: string;
  wilaya: string;
  text: string;
  source_url: string;
  analysis: SlmAnalysisEnvelope | null;
}

interface VerbatimsView {
  items: VerbatimView[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function getSentimentClass(sentiment: string) {
  const normalized = sentiment.toLowerCase();
  if (
    normalized.includes("tres_positif") ||
    normalized.includes("tres positif") ||
    normalized.includes("très positif")
  ) {
    return "text-emerald-400";
  }
  if (
    normalized.includes("tres_negatif") ||
    normalized.includes("tres negatif") ||
    normalized.includes("très négatif")
  ) {
    return "text-red-700";
  }
  if (normalized.includes("positif")) return "text-emerald-500";
  if (normalized.includes("negatif") || normalized.includes("négatif")) {
    return "text-red-400";
  }
  if (normalized.includes("mixte")) return "text-insight";
  return "text-gray-400";
}

function getSentimentDot(sentiment: string) {
  const normalized = sentiment.toLowerCase();
  if (
    normalized.includes("tres_positif") ||
    normalized.includes("tres positif") ||
    normalized.includes("très positif")
  ) {
    return "bg-emerald-400";
  }
  if (
    normalized.includes("tres_negatif") ||
    normalized.includes("tres negatif") ||
    normalized.includes("très négatif")
  ) {
    return "bg-red-900/30";
  }
  if (normalized.includes("positif")) return "bg-emerald-500";
  if (normalized.includes("negatif") || normalized.includes("négatif")) return "bg-red-500";
  if (normalized.includes("mixte")) return "bg-insight";
  return "bg-gray-400";
}

function getSourceColor(source: string) {
  const found = SOURCES.find((item) => item.id === source.toLowerCase());
  return found?.color ?? "#9ca3af";
}

function getSourceIcon(source: string) {
  const found = SOURCES.find((item) => item.id === source.toLowerCase());
  return found?.icon ?? "public";
}

function getSourceLabel(source: string) {
  const found = SOURCES.find((item) => item.id === source.toLowerCase());
  return found?.label ?? source;
}

function formatSentimentLabel(sentiment: string) {
  const normalized = sentiment.toLowerCase();
  if (normalized.includes("tres_positif") || normalized.includes("tres positif")) {
    return "Très Positif";
  }
  if (normalized.includes("tres_negatif") || normalized.includes("tres negatif")) {
    return "Très Négatif";
  }
  if (normalized.includes("positif")) return "Positif";
  if (normalized.includes("negatif")) return "Négatif";
  if (normalized.includes("mixte")) return "Mixte";
  return "Neutre";
}

function formatDateParts(timestamp: string): { date: string; time: string } {
  if (!timestamp) return { date: "-", time: "-" };
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return { date: timestamp, time: "-" };

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfInputDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round(
    (startOfToday.getTime() - startOfInputDay.getTime()) / (24 * 60 * 60 * 1000),
  );

  const relativeDateLabel =
    diffDays === 0
      ? "Aujourd'hui"
      : diffDays === 1
        ? "Hier"
        : date.toLocaleDateString("fr-FR", {
            day: "numeric",
            month: "short",
          });

  return {
    date: relativeDateLabel,
    time: date.toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
}

function payloadRecords(value: unknown): Record<string, unknown>[] {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return [];
  const results = (value as Record<string, unknown>).results;
  return Array.isArray(results)
    ? results.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object" && !Array.isArray(item))
    : [];
}

function recordString(record: Record<string, unknown> | undefined, key: string, fallback: string) {
  const value = record?.[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

function mapSearchView(value: unknown): SearchResultView[] {
  const results = mapExplorerSearchResults(value);
  const rawResults = payloadRecords(value);
  const displayScores = toDisplayRelevanceScores(results.map((result) => result.score));

  return results.map((result, index) => ({
    id: `${result.channel}-${index}-${result.score}`,
    source: result.channel || "import",
    content: result.text,
    relevance_score: displayScores[index] ?? 0,
    sentiment: formatSentimentLabel(result.sentiment_label || "neutre"),
    aspect: result.aspect || "—",
    source_url: result.source_url || "",
    wilaya: recordString(rawResults[index], "wilaya", "—"),
    created_at: recordString(rawResults[index], "timestamp", ""),
    analysis: parseSlmAnalysis(rawResults[index]),
  }));
}

function mapVerbatimsView(value: unknown): VerbatimsView {
  const verbatims = mapExplorerVerbatims(value);
  const rawResults = payloadRecords(value);
  return {
    items: verbatims.results.map((item, index) => {
      const parts = formatDateParts(item.timestamp);
      return {
        id: `${item.channel}-${index}-${item.timestamp}`,
        date: parts.date,
        time: parts.time,
        source: item.channel,
        aspect: item.aspect || "—",
        sentiment: formatSentimentLabel(item.sentiment_label || "neutre"),
        wilaya: item.wilaya || "—",
        text: item.text,
        source_url: item.source_url || "",
        analysis: parseSlmAnalysis(rawResults[index]),
      };
    }),
    total: verbatims.total,
    page: verbatims.page,
    page_size: verbatims.page_size,
    total_pages: verbatims.total_pages,
  };
}

export default function Explorateur() {
  const tenantId = useTenantId();
  const [query, setQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [activeSources, setActiveSources] = useState<string[]>(["facebook"]);
  const [page, setPage] = useState(1);
  const [filterSentiment, setFilterSentiment] = useState<string>("");
  const [filterWilaya, setFilterWilaya] = useState<string>("");
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [selectedSearchId, setSelectedSearchId] = useState<string | null>(null);

  const handleExportVerbatims = async () => {
    try {
      const params = new URLSearchParams({ page_size: "1000" });
      if (channelFilter) params.set("channel", channelFilter);
      if (filterSentiment) params.set("sentiment", filterSentiment);
      if (filterWilaya) params.set("wilaya", filterWilaya);
      const res = await apiRequest("GET", `/api/explorer/verbatims?${params.toString()}`);
      const data = await res.json() as unknown;
      const rawItems = Array.isArray(data) ? data : ((data as Record<string, unknown>).items ?? (data as Record<string, unknown>).verbatims ?? []) as unknown[];

      if (rawItems.length === 0) {
        toast({ title: "Aucun verbatim à exporter" });
        return;
      }

      const mapped = (rawItems as Record<string, unknown>[]).map((item) => {
        const parts = formatDateParts(String(item.timestamp ?? ""));
        return {
          source: String(item.channel ?? ""),
          sentiment: formatSentimentLabel(String(item.sentiment_label ?? "neutre")),
          content: String(item.text ?? ""),
          wilaya: String(item.wilaya ?? "—"),
          date: parts.date,
          aspect: String(item.aspect ?? "—"),
        };
      });

      const csv = convertToCSV(mapped, [
        { key: "source", header: "Source" },
        { key: "sentiment", header: "Sentiment" },
        { key: "content", header: "Contenu" },
        { key: "wilaya", header: "Wilaya" },
        { key: "date", header: "Date" },
        { key: "aspect", header: "Aspect" },
      ]);
      const today = new Date().toISOString().split("T")[0];
      downloadCSV(csv, `verbatims_${today}.csv`);
      toast({ title: `Export téléchargé (${mapped.length} verbatims)` });
    } catch (err) {
      toast({
        title: "Erreur d'export",
        description: err instanceof Error ? err.message : "Impossible d'exporter",
        variant: "destructive",
      });
    }
  };

  const channelFilter = activeSources.length === 1 ? activeSources[0] : null;

  const { data: results, isLoading: searchLoading } = useQuery<SearchResultView[]>({
    queryKey: ["/api/explorer/search", { tenantId, query: activeSearch, channel: channelFilter }],
    queryFn: async () => {
      if (!activeSearch.trim()) return [];
      const params = new URLSearchParams();
      params.set("q", activeSearch);
      params.set("limit", "10");
      if (channelFilter) params.set("channel", channelFilter);
      const res = await apiRequest("GET", `/api/explorer/search?${params.toString()}`);
      return mapSearchView(await res.json());
    },
    enabled: Boolean(activeSearch.trim()),
  });

  const { data: ragData, isLoading: ragLoading } = useQuery<{
    query: string;
    answer: string;
    confidence: string;
    chunks: Array<{ text: string; channel: string; source_url: string; url: string; sentiment_label: string; aspect: string; score: number }>;
  }>({
    queryKey: ["/api/explorer/rag", { tenantId, query: activeSearch }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("q", activeSearch);
      params.set("limit", "5");
      const res = await apiRequest("GET", `/api/explorer/rag?${params.toString()}`);
      return res.json() as Promise<{
        query: string;
        answer: string;
        confidence: string;
        chunks: Array<{ text: string; channel: string; source_url: string; url: string; sentiment_label: string; aspect: string; score: number }>;
      }>;
    },
    enabled: Boolean(activeSearch.trim()),
    staleTime: 60_000,
  });

  const { data: verbatims, isLoading: verbatimsLoading } = useQuery<VerbatimsView>({
    queryKey: [
      "/api/explorer/verbatims",
      { tenantId, page, channel: channelFilter, sentiment: filterSentiment, wilaya: filterWilaya },
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", "50");
      if (channelFilter) params.set("channel", channelFilter);
      if (filterSentiment) params.set("sentiment", filterSentiment);
      if (filterWilaya) params.set("wilaya", filterWilaya);
      const res = await apiRequest("GET", `/api/explorer/verbatims?${params.toString()}`);
      return mapVerbatimsView(await res.json());
    },
  });

  const toggleSource = (id: string) => {
    setActiveSources((previous) =>
      previous.includes(id)
        ? previous.filter((currentId) => currentId !== id)
        : [...previous, id],
    );
    setPage(1);
  };

  const searchResults = results ?? [];

  const aiInsight = useMemo(() => {
    if (!ragData?.answer || ragData.chunks.length === 0) {
      return buildExplorerAiView(searchResults, activeSearch);
    }
    const scores = ragData.chunks.map((c) => c.score ?? 0);
    const displayScores = toDisplayRelevanceScores(scores);
    const uniqueSources = new Set(ragData.chunks.map((c) => c.channel).filter(Boolean));
    const confidenceLabel: Record<string, string> = { high: "haute", medium: "moyenne", low: "basse" };
    return {
      summary: ragData.answer,
      coverageLabel: `${ragData.chunks.length} signaux • confiance ${confidenceLabel[ragData.confidence] ?? ragData.confidence}`,
      evidence: ragData.chunks.map((chunk, i) => ({
        text: chunk.text,
        source: chunk.channel || "import",
        sentiment: formatSentimentLabel(chunk.sentiment_label || "neutre"),
        aspect: (chunk.aspect?.trim() && chunk.aspect !== "n/a") ? chunk.aspect : "signal général",
        relevanceScore: displayScores[i] ?? 0,
        sourceUrl: chunk.url || chunk.source_url || "",
      })),
      _uniqueSources: uniqueSources.size,
    };
  }, [activeSearch, ragData, searchResults]);
  const verbatimsData = useMemo(() => {
    return (
      verbatims ?? {
        items: [],
        total: 0,
        page: 1,
        page_size: 50,
        total_pages: 1,
      }
    );
  }, [verbatims]);
  const selectedSignal = useMemo(
    () => verbatimsData.items.find((item) => item.id === selectedSignalId) ?? verbatimsData.items[0] ?? null,
    [selectedSignalId, verbatimsData.items],
  );
  const selectedSearchSignal = useMemo(
    () => searchResults.find((item) => item.id === selectedSearchId) ?? null,
    [searchResults, selectedSearchId],
  );
  const selectedDetail = selectedSearchSignal
    ? {
        text: selectedSearchSignal.content,
        source: selectedSearchSignal.source,
        sourceUrl: selectedSearchSignal.source_url,
        dateLabel: selectedSearchSignal.created_at || "Résultat de recherche",
        wilaya: selectedSearchSignal.wilaya,
        sentiment: selectedSearchSignal.sentiment,
        aspect: selectedSearchSignal.aspect,
        analysis: selectedSearchSignal.analysis,
      }
    : selectedSignal
      ? {
          text: selectedSignal.text,
          source: selectedSignal.source,
          sourceUrl: selectedSignal.source_url,
          dateLabel: `${selectedSignal.date} à ${selectedSignal.time}`,
          wilaya: selectedSignal.wilaya,
          sentiment: selectedSignal.sentiment,
          aspect: selectedSignal.aspect,
          analysis: selectedSignal.analysis,
        }
      : null;
  const enrichedSignalsCount = useMemo(
    () => verbatimsData.items.filter((item) => item.analysis !== null).length,
    [verbatimsData.items],
  );

  const shouldShowEmptyTenantState =
    !activeSearch.trim() &&
    !searchLoading &&
    !verbatimsLoading &&
    verbatimsData.total === 0;

  if (shouldShowEmptyTenantState) {
    return (
      <AppShell
        avatarSrc={STITCH_AVATARS.explorateur.src}
        avatarAlt={STITCH_AVATARS.explorateur.alt}
      >
        <div className="p-8 max-w-7xl mx-auto w-full">
          <EmptyTenantState
            title="L'explorateur attend les premières mentions"
            description="Dès que la watchlist remonte assez de documents, vous pourrez lancer des questions, consulter les sources et inspecter les verbatims multi-canaux."
          />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      avatarSrc={STITCH_AVATARS.explorateur.src}
      avatarAlt={STITCH_AVATARS.explorateur.alt}
    >
      <div className="mx-auto w-full max-w-[1600px] space-y-8 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <PageHeader
          eyebrow="Comprendre"
          tone="insight"
          title="Explorer les avis clients"
          description="Recherchez un sujet en langage naturel, puis consultez les verbatims, leurs sources et les éléments qui expliquent le résultat."
        />

        <section className="space-y-4">
          <div className="relative">
            <div className="relative flex min-w-0 items-center rounded-xl border border-insight/20 bg-insight-container/45 p-2 focus-within:border-insight/45">
              <span className="material-symbols-outlined ml-4 text-insight">
                search
              </span>
              <input
                className="min-w-0 flex-1 border-none bg-transparent px-3 py-3 text-base text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-0 sm:px-4"
                placeholder="Recherche en langage naturel (ex: 'Que pensent les clients du goût à Alger ?')"
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") return;
                  setActiveSearch(query);
                }}
                data-testid="search-input"
              />
              <button
                onClick={() => setActiveSearch(query)}
                className="flex shrink-0 items-center gap-2 rounded-lg bg-insight px-3 py-2.5 text-sm font-bold text-white transition-colors hover:bg-insight/90 sm:px-6"
                data-testid="btn-search"
              >
                <span className="material-symbols-outlined text-lg">search</span>
                <span className="hidden sm:inline">Explorer</span>
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[10px] font-black uppercase tracking-widest text-on-surface-variant mr-2">
              Sources :
            </span>
            {SOURCES.map((source) => {
              const isActive = activeSources.includes(source.id);
              return (
                <button
                  key={source.id}
                  onClick={() => toggleSource(source.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
                    isActive
                      ? "bg-surface-container-highest text-primary border border-primary/20"
                      : "bg-surface-container hover:bg-surface-container-high text-on-surface-variant"
                  }`}
                  data-testid={`filter-source-${source.id}`}
                >
                  <span
                    className="material-symbols-outlined text-sm"
                    style={{ color: isActive ? source.color : undefined }}
                  >
                    {source.icon}
                  </span>
                  {source.label}
                </button>
              );
            })}
            <div className="h-6 w-px bg-outline-variant/20 mx-1"></div>
            <Popover>
              <PopoverTrigger asChild>
                <button
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-xs font-semibold transition-colors"
                  type="button"
                >
                  <span className="material-symbols-outlined text-sm">tune</span>
                  Filtrer
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-60 space-y-4 p-4">
                <div className="space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                    Sentiment
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SENTIMENT_OPTIONS.map((sentiment) => (
                      <button
                        key={sentiment.value}
                        type="button"
                        onClick={() => {
                          setFilterSentiment((previous) => previous === sentiment.value ? "" : sentiment.value);
                          setPage(1);
                        }}
                        className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-colors ${
                          filterSentiment === sentiment.value
                            ? "bg-primary text-on-primary-fixed"
                            : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                        }`}
                      >
                        {sentiment.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                    Wilaya
                  </p>
                  <select
                    className="w-full bg-surface-container-high border-none rounded text-xs py-1.5 px-2 focus:ring-1 focus:ring-primary/40 focus:outline-none"
                    value={filterWilaya}
                    onChange={(event) => {
                      setFilterWilaya(event.target.value);
                      setPage(1);
                    }}
                  >
                    <option value="">Toutes</option>
                    {WILAYA_OPTIONS.map((wilaya) => (
                      <option key={wilaya} value={wilaya}>
                        {wilaya}
                      </option>
                    ))}
                  </select>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </section>

        {(activeSearch || searchResults.length > 0) && (
          <>
            {(ragLoading || aiInsight) && activeSearch && (
              <div
                className="bg-surface-container rounded-xl border border-tertiary/15 overflow-hidden"
                data-testid="explorer-ai-insight"
              >
                <div className="px-5 py-4 border-b border-outline-variant/10 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-widest text-tertiary">
                      RAG Insight
                    </p>
                    <p className="text-xs text-on-surface-variant mt-1">
                      Synthèse IA ancrée dans les résultats actuels
                    </p>
                  </div>
                  {aiInsight && (
                    <span className="text-[10px] font-bold uppercase tracking-wide text-on-surface-variant">
                      {aiInsight.coverageLabel}
                    </span>
                  )}
                </div>
                <div className="p-5 grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-5">
                  {ragLoading && !aiInsight ? (
                    <div className="col-span-full space-y-3">
                      <div className="h-4 bg-surface-container-high rounded animate-pulse w-3/4"></div>
                      <div className="h-4 bg-surface-container-high rounded animate-pulse w-full"></div>
                      <div className="h-4 bg-surface-container-high rounded animate-pulse w-1/2"></div>
                    </div>
                  ) : aiInsight ? (
                    <>
                      <div>
                        <p className="text-sm leading-relaxed text-on-surface">{aiInsight.summary}</p>
                      </div>
                      <div className="space-y-2">
                        {aiInsight.evidence.map((evidence, index) => (
                          <article
                            key={`${evidence.source}-${index}-${evidence.relevanceScore}`}
                            className="bg-surface-container-high rounded-lg px-3 py-3 border border-outline-variant/10"
                          >
                            <p className="text-sm leading-relaxed text-on-surface">
                              "{evidence.text}"
                            </p>
                            <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-on-surface-variant">
                              <span>{evidence.sentiment}</span>
                              <span>•</span>
                              <span>{evidence.aspect}</span>
                              <span>•</span>
                              <span>{getSourceLabel(evidence.source)}</span>
                              <span>•</span>
                              <span>{evidence.relevanceScore}% de pertinence</span>
                            </div>
                            {evidence.sourceUrl ? (
                              <a
                                className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                                href={evidence.sourceUrl}
                                rel="noreferrer"
                                target="_blank"
                              >
                                Voir la source
                                <span className="material-symbols-outlined text-sm">open_in_new</span>
                              </a>
                            ) : null}
                          </article>
                        ))}
                      </div>
                    </>
                  ) : null}
                </div>
              </div>
            )}

          <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="bg-surface-container p-5 rounded-lg animate-pulse h-36"
                ></div>
              ))
            ) : searchResults.length === 0 ? (
              <div className="bg-surface-container p-5 rounded-lg border border-outline-variant/5 text-sm text-on-surface-variant col-span-full">
                Aucun résultat pour cette recherche.
              </div>
            ) : (
              searchResults.map((result) => {
                const isSelected = selectedSearchId === result.id;
                return (
                <div
                  key={result.id}
                  className={`rounded-lg border p-5 transition-all group ${
                    isSelected
                      ? "border-insight/30 bg-insight-container/40"
                      : "border-outline-variant/5 bg-surface-container hover:border-primary/20"
                  }`}
                  data-testid={`search-result-${result.id}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-7 h-7 rounded flex items-center justify-center"
                        style={{ backgroundColor: `${getSourceColor(result.source)}18` }}
                      >
                        <span
                          className="material-symbols-outlined text-sm"
                          style={{ color: getSourceColor(result.source) }}
                        >
                          {getSourceIcon(result.source)}
                        </span>
                      </div>
                      <span className="text-[10px] font-bold text-on-surface-variant uppercase">
                        {getSourceLabel(result.source)}
                      </span>
                    </div>
                    <span className="text-[10px] font-black text-tertiary bg-tertiary/10 px-2 py-1 rounded">
                      {result.relevance_score}% PERTINENCE
                    </span>
                  </div>
                  <p className="text-on-surface text-sm italic mb-3 leading-relaxed line-clamp-2">
                    {result.content}
                  </p>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span
                        className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-tight ${getSentimentClass(result.sentiment)}`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${getSentimentDot(result.sentiment)}`}
                        ></span>
                        {result.sentiment}
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-wide text-on-surface-variant">
                        {result.aspect}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold text-insight transition-colors hover:bg-insight-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-insight/40"
                        onClick={() => {
                          setSelectedSearchId(result.id);
                          setSelectedSignalId(null);
                          requestAnimationFrame(() => {
                            document.getElementById("signal-dossier")?.scrollIntoView({ block: "start" });
                          });
                        }}
                        aria-pressed={isSelected}
                      >
                        Ouvrir le dossier
                        <span className="material-symbols-outlined text-sm">arrow_forward</span>
                      </button>
                      {result.source_url ? (
                        <a
                          className="inline-flex items-center gap-1 text-on-surface-variant hover:text-primary transition-colors"
                          href={result.source_url}
                          rel="noreferrer"
                          target="_blank"
                          aria-label={`Ouvrir la source ${getSourceLabel(result.source)}`}
                        >
                          <span className="material-symbols-outlined text-lg">open_in_new</span>
                        </a>
                      ) : null}
                    </div>
                  </div>
                </div>
                );
              })
            )}
          </section>
          </>
        )}

        <section className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.08fr)_minmax(24rem,0.92fr)]" aria-label="Signaux et analyse détaillée">
          <div className="cling-panel min-w-0 overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant px-5 py-4 sm:px-6">
              <div>
                <h2 className="font-headline text-base font-bold text-on-surface">Signaux collectés</h2>
                <p className="mt-0.5 text-[10px] text-on-surface-variant">
                  Sélectionnez un verbatim pour ouvrir son dossier d’analyse.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {enrichedSignalsCount > 0 ? (
                  <span className="rounded-full bg-insight-container px-2.5 py-1 text-[10px] font-semibold text-insight">
                    {enrichedSignalsCount} analysé{enrichedSignalsCount > 1 ? "s" : ""} en V0.4
                  </span>
                ) : null}
                <button
                  className="inline-flex h-8 items-center gap-2 rounded-full bg-surface-container-high px-3 text-[10px] font-semibold text-on-surface-variant transition-colors hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  type="button"
                  onClick={handleExportVerbatims}
                >
                  <span className="material-symbols-outlined text-sm">download</span>
                  Exporter
                </button>
              </div>
            </div>

            <div className="divide-y divide-outline-variant">
              {verbatimsLoading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="space-y-3 px-5 py-4 sm:px-6">
                    <div className="h-3 w-1/3 animate-pulse rounded bg-surface-container-high" />
                    <div className="h-4 w-full animate-pulse rounded bg-surface-container-high" />
                    <div className="h-3 w-2/3 animate-pulse rounded bg-surface-container-high" />
                  </div>
                ))
              ) : verbatimsData.items.length === 0 ? (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm font-semibold text-on-surface">Aucun signal pour cette sélection</p>
                  <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-on-surface-variant">
                    Retirez un filtre ou choisissez une autre source pour élargir la recherche.
                  </p>
                </div>
              ) : (
                verbatimsData.items.map((verbatim) => {
                  const isSelected = selectedSignal?.id === verbatim.id;
                  const annotation = verbatim.analysis?.annotation;
                  const aspectLabels = annotation?.aspects.slice(0, 2).map((aspect) => aspect.family) ?? [verbatim.aspect];
                  return (
                    <article
                      key={verbatim.id}
                      className={`relative transition-colors ${isSelected ? "bg-primary-fixed" : "bg-surface hover:bg-surface-container-low"}`}
                      data-testid={`verbatim-row-${verbatim.id}`}
                    >
                      <button
                        type="button"
                        className="w-full px-5 py-4 pr-12 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary sm:px-6 sm:pr-14"
                        onClick={() => {
                          setSelectedSignalId(verbatim.id);
                          setSelectedSearchId(null);
                        }}
                        aria-pressed={isSelected}
                      >
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-on-surface-variant">
                          <span className="font-semibold text-on-surface">{getSourceLabel(verbatim.source)}</span>
                          <span>·</span>
                          <span>{verbatim.date} à {verbatim.time}</span>
                          <span>·</span>
                          <span>{verbatim.wilaya}</span>
                          {annotation ? (
                            <span className="ml-auto rounded-full bg-insight-container px-2 py-0.5 font-semibold text-insight">SLM V0.4</span>
                          ) : null}
                        </div>
                        <p className="mt-2 line-clamp-2 text-sm leading-5 text-on-surface" dir="auto">{verbatim.text}</p>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold ${getSentimentClass(verbatim.sentiment)}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${getSentimentDot(verbatim.sentiment)}`} />
                            {verbatim.sentiment}
                          </span>
                          {annotation?.sentiment.emotion && annotation.sentiment.emotion !== "aucune" ? (
                            <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-[9px] font-semibold text-on-surface-variant">
                              {formatSlmLabel(annotation.sentiment.emotion)}
                            </span>
                          ) : null}
                          {aspectLabels.filter(Boolean).map((aspect) => (
                            <span key={aspect} className="rounded-full bg-surface-container-high px-2 py-0.5 text-[9px] font-semibold text-on-surface-variant">
                              {formatSlmLabel(aspect)}
                            </span>
                          ))}
                        </div>
                      </button>
                      {verbatim.source_url ? (
                        <a
                          className="absolute right-4 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                          href={verbatim.source_url}
                          rel="noreferrer"
                          target="_blank"
                          aria-label={`Ouvrir la source ${getSourceLabel(verbatim.source)}`}
                        >
                          <span className="material-symbols-outlined text-base">open_in_new</span>
                        </a>
                      ) : null}
                    </article>
                  );
                })
              )}
            </div>

            <div className="flex items-center justify-between border-t border-outline-variant px-5 py-4 sm:px-6">
              <span className="text-[10px] font-semibold text-on-surface-variant">
                {verbatimsData.total} signal{verbatimsData.total > 1 ? "s" : ""} · page {verbatimsData.page}/{Math.max(1, verbatimsData.total_pages)}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                  disabled={page === 1}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-30"
                  data-testid="btn-prev-page"
                  aria-label="Page précédente"
                >
                  <span className="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <button
                  onClick={() => setPage((currentPage) => Math.min(verbatimsData.total_pages, currentPage + 1))}
                  disabled={page >= verbatimsData.total_pages}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-30"
                  data-testid="btn-next-page"
                  aria-label="Page suivante"
                >
                  <span className="material-symbols-outlined text-sm">chevron_right</span>
                </button>
              </div>
            </div>
          </div>

          {selectedDetail ? (
            <div id="signal-dossier">
              <SignalAnalysisPanel
                text={selectedDetail.text}
                sourceLabel={getSourceLabel(selectedDetail.source)}
                sourceUrl={selectedDetail.sourceUrl}
                dateLabel={selectedDetail.dateLabel}
                locationLabel={selectedDetail.wilaya}
                legacySentiment={selectedDetail.sentiment}
                legacyAspect={selectedDetail.aspect}
                analysis={selectedDetail.analysis}
              />
            </div>
          ) : (
            <aside className="cling-panel flex min-h-72 items-center justify-center p-8 text-center">
              <div className="max-w-sm">
                <span className="material-symbols-outlined text-3xl text-insight">manage_search</span>
                <h2 className="mt-3 font-headline text-base font-bold text-on-surface">Sélectionnez un signal</h2>
                <p className="mt-2 text-xs leading-5 text-on-surface-variant">Son sentiment, ses aspects, ses intentions et ses preuves apparaîtront ici.</p>
              </div>
            </aside>
          )}
        </section>
      </div>
    </AppShell>
  );
}
