import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExplorerAiView,
  toDisplayRelevanceScores,
} from "../client/src/lib/explorerAiView";

test("buildExplorerAiView summarizes the strongest search results", () => {
  const view = buildExplorerAiView(
    [
      {
        source: "facebook",
        content: "Très bon goût et texture agréable.",
        relevance_score: 100,
        sentiment: "Très Positif",
        aspect: "goût",
        source_url: "https://facebook.test/post-1",
      },
      {
        source: "instagram",
        content: "Le prix reste un peu élevé.",
        relevance_score: 98,
        sentiment: "Négatif",
        aspect: "prix",
        source_url: "https://instagram.test/post-2",
      },
      {
        source: "facebook",
        content: "Bonne fraîcheur globale.",
        relevance_score: 90,
        sentiment: "Positif",
        aspect: "fraîcheur",
        source_url: "https://facebook.test/post-3",
      },
    ],
    "ramy goût alger",
  );

  assert.equal(view?.title, "RAG Insight");
  assert.match(view?.summary ?? "", /ramy goût alger/i);
  assert.match(view?.summary ?? "", /goût|prix|fraîcheur/i);
  assert.match(view?.summary ?? "", /tonalité dominante/i);
  assert.match(view?.coverageLabel ?? "", /résultats clés • 2 sources/i);
  assert.equal(view?.evidence.length, 3);
  assert.equal(view?.evidence[0]?.text, "Très bon goût et texture agréable.");
  assert.equal(view?.evidence[0]?.source, "facebook");
  assert.equal(view?.evidence[0]?.sourceUrl, "https://facebook.test/post-1");
  assert.equal(view?.evidence[0]?.relevanceScore, 100);
});

test("buildExplorerAiView returns null for empty search results", () => {
  assert.equal(buildExplorerAiView([], "ramy"), null);
});

test("toDisplayRelevanceScores rescales raw RRF scores into readable percentages", () => {
  assert.deepEqual(
    toDisplayRelevanceScores([0.01639344, 0.01612903, 0.01470588]),
    [100, 98, 90],
  );
  assert.deepEqual(toDisplayRelevanceScores([]), []);
});
