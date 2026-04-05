import assert from "node:assert/strict";
import test from "node:test";

import { buildExplorerAiView } from "../client/src/lib/explorerAiView";

test("buildExplorerAiView summarizes the strongest search results", () => {
  const view = buildExplorerAiView(
    [
      {
        source: "facebook",
        content: "Très bon goût et texture agréable.",
        relevance_score: 92,
        sentiment: "TrÃ¨s Positif",
        aspect: "goût",
      },
      {
        source: "instagram",
        content: "Le prix reste un peu élevé.",
        relevance_score: 87,
        sentiment: "NÃ©gatif",
        aspect: "prix",
      },
      {
        source: "facebook",
        content: "Bonne fraîcheur globale.",
        relevance_score: 80,
        sentiment: "Positif",
        aspect: "fraîcheur",
      },
    ],
    "ramy goût alger",
  );

  assert.equal(view?.title, "RAG Insight");
  assert.match(view?.summary ?? "", /ramy goût alger/i);
  assert.match(view?.summary ?? "", /goût|prix|fraîcheur/i);
  assert.equal(view?.bullets.length, 3);
});

test("buildExplorerAiView returns null for empty search results", () => {
  assert.equal(buildExplorerAiView([], "ramy"), null);
});
