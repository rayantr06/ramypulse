"""Recherche hybride dense (FAISS) + sparse (BM25) avec fusion RRF pour RamyPulse.

Reciprocal Rank Fusion : score(d) = Σ 1 / (60 + rank_i)
"""
import logging

import numpy as np
from rank_bm25 import BM25Okapi

from core.rag.embedder import Embedder
from core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

_RRF_K = 60  # constante de régularisation standard


class Retriever:
    """Recherche hybride FAISS (dense) + BM25 (sparse) fusionnée par RRF."""

    def __init__(self, vector_store: VectorStore, embedder: Embedder) -> None:
        """Initialise le retriever et construit l'index BM25 en mémoire.

        Args:
            vector_store: Index FAISS avec metadata.
            embedder: Modèle d'embedding pour la recherche dense.
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self._corpus: list[str] = [m.get("text", "") for m in vector_store.metadata]
        if self._corpus:
            tokenized = [doc.lower().split() for doc in self._corpus]
            self.bm25: BM25Okapi | None = BM25Okapi(tokenized)
        else:
            self.bm25 = None

    def retrieve(self, question: str, top_k: int = 5) -> list[dict]:
        """Recherche hybride dense + sparse avec fusion RRF.

        Args:
            question: Question de l'utilisateur.
            top_k: Nombre de résultats à retourner.

        Returns:
            Liste de dicts {text, channel, url, timestamp, score},
            triée par score RRF décroissant.
        """
        n_docs = len(self.vector_store.metadata)
        if n_docs == 0:
            return []

        k_fetch = min(top_k * 2, n_docs)

        # 1. Recherche dense (FAISS)
        query_vec = self.embedder.embed_query(question)
        dense_results = self.vector_store.search(query_vec, k=k_fetch)

        # 2. Recherche sparse (BM25)
        tokens = question.lower().split()
        if self.bm25 is not None:
            bm25_scores = self.bm25.get_scores(tokens)
            bm25_ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k_fetch]
        else:
            bm25_ranked = []

        # 3. RRF fusion — clé = index dans le corpus
        rrf: dict[int, float] = {}

        for rank, (meta, _) in enumerate(dense_results):
            idx = self._corpus_index(meta.get("text", ""))
            if idx is not None:
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)

        for rank, idx in enumerate(bm25_ranked):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)

        # 4. Trier par score décroissant, retourner top_k
        sorted_indices = sorted(rrf, key=rrf.__getitem__, reverse=True)[:top_k]

        results = []
        for idx in sorted_indices:
            meta = self.vector_store.metadata[idx]
            results.append(
                {
                    "text": meta.get("text", ""),
                    "channel": meta.get("channel", ""),
                    "url": meta.get("source_url", ""),
                    "timestamp": meta.get("timestamp", ""),
                    "score": round(rrf[idx], 8),
                }
            )
        return results

    def _corpus_index(self, text: str) -> int | None:
        """Retrouve l'index d'un texte dans le corpus interne.

        Args:
            text: Texte exact à rechercher.

        Returns:
            Index entier dans self._corpus, ou None si absent.
        """
        for i, t in enumerate(self._corpus):
            if t == text:
                return i
        return None
