"""Tests TDD pour core/rag/retriever.py.

Utilise un VectorStore réel (vecteurs aléatoires) + Embedder mocké.
Vérifie : nombre de résultats, clés, url non vides, scores RRF > 0, robustesse.
"""
import os
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.rag.retriever import Retriever  # noqa: E402
from core.rag.vector_store import VectorStore  # noqa: E402

DIM = 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_vecs(n: int, dim: int = DIM) -> np.ndarray:
    vecs = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


def _make_store(n: int = 10) -> VectorStore:
    vs = VectorStore()
    vecs = _rand_vecs(n)
    metas = [
        {
            "text": f"Le jus Ramy a un goût excellent numéro {i}",
            "channel": "facebook",
            "source_url": f"http://fb/{i}",
            "timestamp": "2024-01-01",
        }
        for i in range(n)
    ]
    vs.add(vecs, metas)
    return vs


def _mock_embedder() -> MagicMock:
    """Retourne un Embedder mocké dont embed_query produit un vecteur aléatoire."""
    embedder = MagicMock()
    embedder.embed_query.return_value = _rand_vecs(1)
    return embedder


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_retrieve_retourne_top_k_resultats() -> None:
    """retrieve(question, top_k=5) doit retourner 5 résultats."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    results = retriever.retrieve("goût Ramy", top_k=5)
    assert len(results) == 5


def test_chaque_resultat_possede_les_cles_requises() -> None:
    """Chaque résultat doit avoir text, channel, url, timestamp, score."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.retrieve("emballage", top_k=3):
        assert "text" in r
        assert "channel" in r
        assert "url" in r
        assert "timestamp" in r
        assert "score" in r


def test_chaque_resultat_a_une_url_non_vide() -> None:
    """url ne doit pas être une chaîne vide (source obligatoire)."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.retrieve("prix", top_k=5):
        assert r["url"] != ""


def test_scores_rrf_sont_positifs() -> None:
    """Les scores RRF doivent être strictement positifs."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.retrieve("disponibilité", top_k=3):
        assert r["score"] > 0.0


def test_retrieve_top_k_superieur_corpus() -> None:
    """Si top_k > taille du corpus, retourner tout le corpus (pas d'erreur)."""
    retriever = Retriever(_make_store(3), _mock_embedder())
    results = retriever.retrieve("fraîcheur", top_k=20)
    assert 0 < len(results) <= 3


def test_retrieve_corpus_vide_retourne_liste_vide() -> None:
    """Avec un VectorStore vide, retrieve doit retourner []."""
    vs = VectorStore()  # index vide
    retriever = Retriever(vs, _mock_embedder())
    results = retriever.retrieve("question", top_k=5)
    assert results == []


def test_resultats_tries_par_score_decroissant() -> None:
    """Les résultats doivent être triés du score RRF le plus élevé au plus bas."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    results = retriever.retrieve("goût", top_k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
