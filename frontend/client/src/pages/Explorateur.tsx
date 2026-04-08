import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { buildExplorerAiView, toDisplayRelevanceScores } from "@/lib/explorerAiView";
import { apiRequest } from "@/lib/queryClient";
import {
  mapExplorerSearchResults,
  mapExplorerVerbatims,
} from "@/lib/apiMappings";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

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
  if (normalized.includes("positif")) return "text-emerald-500";
  if (normalized.includes("negatif") || normalized.includes("négatif")) {
    return "text-red-400";
  }
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
  if (normalized.includes("positif")) return "bg-emerald-500";
  if (normalized.includes("negatif") || normalized.includes("négatif")) return "bg-red-500";
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
  if (normalized.includes("positif")) return "Positif";
  if (normalized.includes("negatif")) return "Négatif";
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

function mapSearchView(value: unknown): SearchResultView[] {
  const results = mapExplorerSearchResults(value);
  const displayScores = toDisplayRelevanceScores(results.map((result) => result.score));

  return results.map((result, index) => ({
    id: `${result.channel}-${index}-${result.score}`,
    source: result.channel || "import",
    content: result.text,
    relevance_score: displayScores[index] ?? 0,
    sentiment: formatSentimentLabel(result.sentiment_label || "neutre"),
    aspect: result.aspect || "n/a",
    source_url: result.source_url || "",
    wilaya: "n/a",
    created_at: "",
  }));
}

function mapVerbatimsView(value: unknown): VerbatimsView {
  const verbatims = mapExplorerVerbatims(value);
  return {
    items: verbatims.results.map((item, index) => {
      const parts = formatDateParts(item.timestamp);
      return {
        id: `${item.channel}-${index}-${item.timestamp}`,
        date: parts.date,
        time: parts.time,
        source: item.channel,
        aspect: item.aspect || "n/a",
        sentiment: formatSentimentLabel(item.sentiment_label || "neutre"),
        wilaya: item.wilaya || "n/a",
        text: item.text,
        source_url: item.source_url || "",
      };
    }),
    total: verbatims.total,
    page: verbatims.page,
    page_size: verbatims.page_size,
    total_pages: verbatims.total_pages,
  };
}

export default function Explorateur() {
  const [query, setQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [activeSources, setActiveSources] = useState<string[]>(["facebook"]);
  const [page, setPage] = useState(1);

  const channelFilter = activeSources.length === 1 ? activeSources[0] : null;

  const { data: results, isLoading: searchLoading } = useQuery<SearchResultView[]>({
    queryKey: ["/api/explorer/search", activeSearch, channelFilter],
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

  const { data: verbatims, isLoading: verbatimsLoading } = useQuery<VerbatimsView>({
    queryKey: ["/api/explorer/verbatims", page, channelFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", "50");
      if (channelFilter) params.set("channel", channelFilter);
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
  const aiInsight = useMemo(
    () => buildExplorerAiView(searchResults, activeSearch),
    [searchResults, activeSearch],
  );
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

  return (
    <AppShell
      avatarSrc={STITCH_AVATARS.explorateur.src}
      avatarAlt={STITCH_AVATARS.explorateur.alt}
    >
      <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
        <section>
          <h2 className="text-3xl font-extrabold font-headline tracking-tighter text-on-surface">
            Explorateur
          </h2>
          <p className="text-on-surface-variant font-body text-sm mt-1">
            Recherche sémantique et verbatims à travers l'écosystème digital
          </p>
        </section>

        <section className="space-y-4">
          <div className="relative group">
            <div className="absolute -inset-0.5 pulse-gradient rounded-xl blur opacity-10 group-focus-within:opacity-30 transition duration-1000"></div>
            <div className="relative flex items-center bg-surface-container-high p-2 rounded-xl">
              <span className="material-symbols-outlined ml-4 text-on-surface-variant">
                psychology
              </span>
              <input
                className="flex-1 bg-transparent border-none text-on-surface placeholder:text-gray-600 px-4 py-3 focus:ring-0 focus:outline-none text-base"
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
                className="pulse-gradient text-on-primary-fixed font-bold px-6 py-2.5 rounded-lg flex items-center gap-2 transition-transform active:scale-95 shadow-lg text-sm"
                data-testid="btn-search"
              >
                <span className="material-symbols-outlined text-lg">search</span>
                Explorer
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
            <button
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-xs font-semibold transition-colors"
              type="button"
            >
              <span className="material-symbols-outlined text-sm">tune</span>
              Filtrer
            </button>
          </div>
        </section>

        {(activeSearch || searchResults.length > 0) && (
          <>
            {aiInsight ? (
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
                  <span className="text-[10px] font-bold uppercase tracking-wide text-on-surface-variant">
                    {aiInsight.coverageLabel}
                  </span>
                </div>
                <div className="p-5 grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-5">
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
                          “{evidence.text}”
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
                </div>
              </div>
            ) : null}

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
              searchResults.map((result) => (
                <div
                  key={result.id}
                  className="bg-surface-container p-5 rounded-lg border border-outline-variant/5 hover:border-primary/20 transition-all group"
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
                    {result.source_url ? (
                      <a
                        className="inline-flex items-center gap-1 text-on-surface-variant hover:text-primary transition-colors"
                        href={result.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        <span className="material-symbols-outlined text-lg">open_in_new</span>
                      </a>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </section>
          </>
        )}

        <section className="bg-surface-container rounded-xl overflow-hidden border border-outline-variant/5">
          <div className="p-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold font-headline text-on-surface">
                Tous les verbatims
              </h3>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Base de données complète des interactions clients
              </p>
            </div>
            <button
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-highest text-on-surface-variant text-[10px] font-black uppercase tracking-widest hover:text-on-surface transition-colors"
              type="button"
            >
              <span className="material-symbols-outlined text-base">download</span>
              Exporter
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low border-y border-outline-variant/10">
                  {["Date", "Source", "Aspect", "Sentiment", "Wilaya", "Verbatim"].map(
                    (column) => (
                      <th
                        key={column}
                        className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-widest"
                      >
                        {column}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {verbatimsLoading ? (
                  Array.from({ length: 4 }).map((_, index) => (
                    <tr key={index}>
                      <td colSpan={6} className="px-6 py-4">
                        <div className="h-4 bg-surface-container-high rounded animate-pulse"></div>
                      </td>
                    </tr>
                  ))
                ) : verbatimsData.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-sm text-on-surface-variant">
                      Aucun verbatim disponible pour cette sélection.
                    </td>
                  </tr>
                ) : (
                  verbatimsData.items.map((verbatim) => (
                    <tr
                      key={verbatim.id}
                      className="hover:bg-surface-container-high transition-colors"
                      data-testid={`verbatim-row-${verbatim.id}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-on-surface">
                            {verbatim.date}
                          </span>
                          <span className="text-[10px] text-on-surface-variant">
                            {verbatim.time}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span
                            className="material-symbols-outlined text-lg"
                            style={{ color: getSourceColor(verbatim.source) }}
                          >
                            {getSourceIcon(verbatim.source)}
                          </span>
                          {verbatim.source_url ? (
                            <a
                              className="text-xs font-medium text-on-surface hover:text-primary transition-colors inline-flex items-center gap-1"
                              href={verbatim.source_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              {getSourceLabel(verbatim.source)}
                              <span className="material-symbols-outlined text-sm">open_in_new</span>
                            </a>
                          ) : (
                            <span className="text-xs font-medium text-on-surface">
                              {getSourceLabel(verbatim.source)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded-full bg-surface-container-highest text-[10px] font-bold text-on-surface border border-outline-variant/20">
                          {verbatim.aspect}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`flex items-center gap-1.5 text-[10px] font-bold uppercase ${getSentimentClass(verbatim.sentiment)}`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${getSentimentDot(verbatim.sentiment)}`}
                          ></span>
                          {verbatim.sentiment}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-on-surface">
                        {verbatim.wilaya}
                      </td>
                      <td className="px-6 py-4 text-sm text-on-surface-variant max-w-xs truncate">
                        {verbatim.text}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="p-6 border-t border-outline-variant/10 flex items-center justify-between">
            <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
              Page {verbatimsData.page} sur {verbatimsData.total_pages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                disabled={page === 1}
                className="w-8 h-8 flex items-center justify-center rounded bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors disabled:opacity-30"
                data-testid="btn-prev-page"
              >
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                onClick={() =>
                  setPage((currentPage) =>
                    Math.min(verbatimsData.total_pages, currentPage + 1),
                  )
                }
                disabled={page === verbatimsData.total_pages}
                className="w-8 h-8 flex items-center justify-center rounded bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors disabled:opacity-30"
                data-testid="btn-next-page"
              >
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
