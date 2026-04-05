export interface ExplorerInsightResult {
  source: string;
  content: string;
  relevance_score: number;
  sentiment: string;
  aspect: string;
}

export interface ExplorerAiView {
  title: string;
  summary: string;
  bullets: string[];
  coverageLabel: string;
}

function normalizeAspect(value: string) {
  const aspect = value?.trim();
  return aspect && aspect !== "n/a" ? aspect : "signal général";
}

function dominantSentiment(results: ExplorerInsightResult[]) {
  const counts = new Map<string, number>();
  for (const result of results) {
    const key = result.sentiment || "Neutre";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "Neutre";
}

export function buildExplorerAiView(
  results: ExplorerInsightResult[],
  query: string,
): ExplorerAiView | null {
  if (!query.trim() || results.length === 0) {
    return null;
  }

  const topResults = [...results]
    .sort((a, b) => b.relevance_score - a.relevance_score)
    .slice(0, 3);
  const topAspects = Array.from(
    new Set(topResults.map((result) => normalizeAspect(result.aspect))),
  );
  const sources = Array.from(
    new Set(topResults.map((result) => result.source).filter(Boolean)),
  );
  const tone = dominantSentiment(topResults);

  return {
    title: "RAG Insight",
    summary: `Pour "${query}", les signaux les plus pertinents pointent surtout vers ${topAspects.join(", ")} avec une tonalité dominante ${tone.toLowerCase()}.`,
    bullets: topResults.map(
      (result) =>
        `${result.sentiment} sur ${normalizeAspect(result.aspect)} via ${result.source} (${result.relevance_score}% de pertinence)`,
    ),
    coverageLabel: `${topResults.length} résultats clés • ${sources.length} sources`,
  };
}
