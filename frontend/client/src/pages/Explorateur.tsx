import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { apiRequest } from "@/lib/queryClient";
import type { SearchResult, VerbatimsResponse } from "@shared/schema";

const SOURCES = [
  { id: "facebook", label: "Facebook", icon: "social_leaderboard", color: "#1877F2" },
  { id: "google_maps", label: "Google Maps", icon: "location_on", color: "#EA4335" },
  { id: "youtube", label: "YouTube", icon: "video_library", color: "#FF0000" },
  { id: "instagram", label: "Instagram", icon: "photo_camera", color: "#E4405F" },
  { id: "import", label: "Import", icon: "file_upload", color: "#9ca3af" },
];

const MOCK_RESULTS: SearchResult[] = [
  { id: "1", source: "Facebook", content: "\"Le goût du Ramy Citron est exceptionnel, très frais!\"", relevance_score: 98, sentiment: "très_positif", wilaya: "Alger", created_at: "2024-01-01" },
  { id: "2", source: "Google Maps", content: "\"Excellent jus pour accompagner les repas traditionnels.\"", relevance_score: 94, sentiment: "positif", wilaya: "Oran", created_at: "2024-01-01" },
  { id: "3", source: "Instagram", content: "\"Packaging très coloré qui attire l'œil en rayon.\"", relevance_score: 91, sentiment: "positif", wilaya: "Béjaïa", created_at: "2024-01-01" },
];

const MOCK_VERBATIMS: VerbatimsResponse = {
  items: [
    { id: "1", date: "Aujourd'hui", time: "09:45", source: "Facebook", aspect: "Goût", sentiment: "Positif", wilaya: "Alger", text: "\"J'adore le nouveau packaging du Ramy Fraise, très pratique.\"" },
    { id: "2", date: "Hier", time: "18:20", source: "Google Maps", aspect: "Disponibilité", sentiment: "Négatif", wilaya: "Oran", text: "\"Impossible de trouver du Ramy Citron à Es Senia depuis 3 jours.\"" },
    { id: "3", date: "Hier", time: "14:10", source: "YouTube", aspect: "Prix", sentiment: "Neutre", wilaya: "Constantine", text: "\"Le prix a augmenté un peu mais la qualité reste là.\"" },
    { id: "4", date: "12 Mai", time: "10:00", source: "Instagram", aspect: "Fraîcheur", sentiment: "Très Positif", wilaya: "Béjaïa", text: "\"Toujours aussi frais, parfait pour l'été à la plage.\"" },
  ],
  total: 225,
  page: 1,
  page_size: 50,
  total_pages: 5,
};

function getSentimentClass(sentiment: string) {
  const s = sentiment.toLowerCase();
  if (s.includes("très_positif") || s.includes("très positif")) return "text-emerald-400";
  if (s.includes("positif")) return "text-emerald-500";
  if (s.includes("négatif")) return "text-red-400";
  return "text-gray-400";
}

function getSentimentDot(sentiment: string) {
  const s = sentiment.toLowerCase();
  if (s.includes("très_positif") || s.includes("très positif")) return "bg-emerald-400";
  if (s.includes("positif")) return "bg-emerald-500";
  if (s.includes("négatif")) return "bg-red-500";
  return "bg-gray-400";
}

function getSourceColor(source: string) {
  const src = SOURCES.find(s => s.label.toLowerCase() === source.toLowerCase());
  return src?.color ?? "#9ca3af";
}

function getSourceIcon(source: string) {
  const src = SOURCES.find(s => s.label.toLowerCase() === source.toLowerCase());
  return src?.icon ?? "public";
}

// Map API search response to SearchResult[]
function mapSearchResults(apiData: Record<string, unknown>): SearchResult[] {
  const results = (apiData.results as Array<Record<string, unknown>>) ?? [];
  if (!results.length) return MOCK_RESULTS;
  return results.map((r) => ({
    id: String(r.id ?? ""),
    source: String(r.source ?? r.channel ?? ""),
    content: String(r.content ?? r.text ?? ""),
    relevance_score: Number(r.relevance_score ?? r.score ?? 0),
    sentiment: String(r.sentiment ?? "neutre"),
    wilaya: String(r.wilaya ?? r.region ?? ""),
    created_at: String(r.created_at ?? ""),
  }));
}

// Map API verbatims response to VerbatimsResponse
function mapVerbatimsResponse(apiData: Record<string, unknown>): VerbatimsResponse {
  const rawResults = (apiData.results as Array<Record<string, unknown>>) ?? [];
  return {
    items: rawResults.map((v) => ({
      id: String(v.id ?? ""),
      date: String(v.date ?? v.created_at ?? ""),
      time: String(v.time ?? ""),
      source: String(v.source ?? v.channel ?? ""),
      aspect: String(v.aspect ?? ""),
      sentiment: String(v.sentiment ?? ""),
      wilaya: String(v.wilaya ?? v.region ?? ""),
      text: String(v.text ?? v.content ?? ""),
    })),
    total: Number(apiData.total ?? 0),
    page: Number(apiData.page ?? 1),
    page_size: Number(apiData.page_size ?? 50),
    total_pages: Number(apiData.total_pages ?? 1),
  };
}

export default function Explorateur() {
  const [query, setQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [activeSources, setActiveSources] = useState<string[]>(["facebook"]);
  const [page, setPage] = useState(1);

  const { data: results, isLoading: searchLoading } = useQuery<SearchResult[]>({
    queryKey: ["/api/explorer/search", activeSearch, activeSources],
    queryFn: async () => {
      if (!activeSearch) return MOCK_RESULTS;
      try {
        const params = new URLSearchParams();
        params.set("q", activeSearch);
        params.set("limit", "10");
        if (activeSources.length === 1) params.set("channel", activeSources[0]);
        const res = await apiRequest("GET", `/api/explorer/search?${params}`);
        const apiData = await res.json();
        return mapSearchResults(apiData);
      } catch {
        return MOCK_RESULTS;
      }
    },
    enabled: !!activeSearch,
  });

  const { data: verbatims, isLoading: verbatimsLoading } = useQuery<VerbatimsResponse>({
    queryKey: ["/api/explorer/verbatims", page, activeSources],
    queryFn: async () => {
      try {
        const params = new URLSearchParams();
        params.set("page", String(page));
        params.set("page_size", "50");
        if (activeSources.length === 1) params.set("channel", activeSources[0]);
        const res = await apiRequest("GET", `/api/explorer/verbatims?${params}`);
        const apiData = await res.json();
        return mapVerbatimsResponse(apiData);
      } catch {
        return MOCK_VERBATIMS;
      }
    },
  });

  const toggleSource = (id: string) => {
    setActiveSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const searchResults = results ?? MOCK_RESULTS;
  const verbatimsData = verbatims ?? MOCK_VERBATIMS;

  return (
    <AppShell>
      <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
        {/* Page Header */}
        <section>
          <h2 className="text-3xl font-extrabold font-headline tracking-tighter text-on-surface">
            Explorateur
          </h2>
          <p className="text-on-surface-variant font-body text-sm mt-1">
            Recherche sémantique et verbatims à travers l'écosystème digital
          </p>
        </section>

        {/* Search Section */}
        <section className="space-y-4">
          {/* Main search bar */}
          <div className="relative group">
            <div className="absolute -inset-0.5 pulse-gradient rounded-xl blur opacity-10 group-focus-within:opacity-30 transition duration-1000"></div>
            <div className="relative flex items-center bg-surface-container-high p-2 rounded-xl">
              <span className="material-symbols-outlined ml-4 text-on-surface-variant">psychology</span>
              <input
                className="flex-1 bg-transparent border-none text-on-surface placeholder:text-gray-600 px-4 py-3 focus:ring-0 focus:outline-none text-base"
                placeholder="Recherche en langage naturel (ex: 'Que pensent les clients du goût à Alger ?')"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && setActiveSearch(query)}
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

          {/* Source filter chips */}
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
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-xs font-semibold transition-colors">
              <span className="material-symbols-outlined text-sm">tune</span>
              Filtrer
            </button>
          </div>
        </section>

        {/* Search Results */}
        {(activeSearch || searchResults.length > 0) && (
          <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchLoading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="bg-surface-container p-5 rounded-lg animate-pulse h-36"></div>
                ))
              : searchResults.map((result) => (
                  <div
                    key={result.id}
                    className="bg-surface-container p-5 rounded-lg border border-outline-variant/5 hover:border-primary/20 transition-all group cursor-pointer"
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
                          {result.source}
                        </span>
                      </div>
                      <span className="text-[10px] font-black text-tertiary bg-tertiary/10 px-2 py-1 rounded">
                        {result.relevance_score}% PERTINENCE
                      </span>
                    </div>
                    <p className="text-on-surface text-sm italic mb-4 leading-relaxed line-clamp-2">
                      {result.content}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-tight ${getSentimentClass(result.sentiment)}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${getSentimentDot(result.sentiment)}`}></span>
                        {result.sentiment}
                      </span>
                      <button className="text-on-surface-variant hover:text-primary transition-colors">
                        <span className="material-symbols-outlined text-lg">open_in_new</span>
                      </button>
                    </div>
                  </div>
                ))}
          </section>
        )}

        {/* Verbatims Table */}
        <section className="bg-surface-container rounded-xl overflow-hidden border border-outline-variant/5">
          <div className="p-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold font-headline text-on-surface">Tous les verbatims</h3>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Base de données complète des interactions clients
              </p>
            </div>
            <button className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-highest text-on-surface-variant text-[10px] font-black uppercase tracking-widest hover:text-on-surface transition-colors">
              <span className="material-symbols-outlined text-base">download</span>
              Exporter
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low border-y border-outline-variant/10">
                  {["Date", "Source", "Aspect", "Sentiment", "Wilaya", "Verbatim"].map((col) => (
                    <th
                      key={col}
                      className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-widest"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {verbatimsLoading
                  ? Array.from({ length: 4 }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan={6} className="px-6 py-4">
                          <div className="h-4 bg-surface-container-high rounded animate-pulse"></div>
                        </td>
                      </tr>
                    ))
                  : verbatimsData.items.map((verbatim) => (
                      <tr
                        key={verbatim.id}
                        className="hover:bg-surface-container-high transition-colors cursor-pointer"
                        data-testid={`verbatim-row-${verbatim.id}`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="text-xs font-bold text-on-surface">{verbatim.date}</span>
                            <span className="text-[10px] text-on-surface-variant">{verbatim.time}</span>
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
                            <span className="text-xs font-medium text-on-surface">{verbatim.source}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded-full bg-surface-container-highest text-[10px] font-bold text-on-surface border border-outline-variant/20">
                            {verbatim.aspect}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`flex items-center gap-1.5 text-[10px] font-bold uppercase ${getSentimentClass(verbatim.sentiment)}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${getSentimentDot(verbatim.sentiment)}`}></span>
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
                    ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-6 border-t border-outline-variant/10 flex items-center justify-between">
            <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
              Page {verbatimsData.page} sur {verbatimsData.total_pages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="w-8 h-8 flex items-center justify-center rounded bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors disabled:opacity-30"
                data-testid="btn-prev-page"
              >
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                onClick={() => setPage((p) => Math.min(verbatimsData.total_pages, p + 1))}
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

      {/* FAB */}
      <button className="fixed bottom-8 right-8 w-14 h-14 pulse-gradient rounded-full shadow-2xl flex items-center justify-center text-on-primary-fixed hover:scale-110 active:scale-95 transition-transform z-50">
        <span className="material-symbols-outlined text-xl font-bold">chat</span>
      </button>
    </AppShell>
  );
}
