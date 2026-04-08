export interface ExplorerInsightResult {
  source: string;
  content: string;
  relevance_score: number;
  sentiment: string;
  aspect: string;
  source_url?: string;
}

export interface ExplorerAiEvidence {
  text: string;
  source: string;
  sentiment: string;
  aspect: string;
  relevanceScore: number;
  sourceUrl: string;
}

export interface ExplorerAiView {
  title: string;
  summary: string;
  coverageLabel: string;
  evidence: ExplorerAiEvidence[];
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

export function toDisplayRelevanceScores(scores: number[]): number[] {
  if (scores.length === 0) {
    return [];
  }

  const maxScore = Math.max(...scores);
  if (!Number.isFinite(maxScore) || maxScore <= 0) {
    return scores.map(() => 0);
  }

  return scores.map((score) => {
    const normalized = Math.max(score, 0) / maxScore;
    return Math.max(1, Math.min(100, Math.round(normalized * 100)));
  });
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
    coverageLabel: `${topResults.length} résultats clés • ${sources.length} sources`,
    evidence: topResults.map((result) => ({
      text: result.content,
      source: result.source,
      sentiment: result.sentiment,
      aspect: normalizeAspect(result.aspect),
      relevanceScore: result.relevance_score,
      sourceUrl: result.source_url ?? "",
    })),
  };
}
