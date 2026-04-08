"""Tests TDD pour core/rag/retriever.py.

Utilise un VectorStore réel (vecteurs aléatoires) + Embedder mocké.
Vérifie : API search/retrieve, résultats, provenance, RRF, doublons, robustesse.
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
    """search(question, top_k=5) doit retourner 5 résultats."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    results = retriever.search("goût Ramy", top_k=5)
    assert len(results) == 5


def test_chaque_resultat_possede_les_cles_requises() -> None:
    """Chaque résultat doit avoir text, channel, url, timestamp, score."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.search("emballage", top_k=3):
        assert "text" in r
        assert "channel" in r
        assert "url" in r
        assert "timestamp" in r
        assert "score" in r


def test_chaque_resultat_a_une_url_non_vide() -> None:
    """url ne doit pas être une chaîne vide (source obligatoire)."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.search("prix", top_k=5):
        assert r["url"] != ""


def test_scores_rrf_sont_positifs() -> None:
    """Les scores RRF doivent être strictement positifs."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    for r in retriever.search("disponibilité", top_k=3):
        assert r["score"] > 0.0


def test_retrieve_top_k_superieur_corpus() -> None:
    """Si top_k > taille du corpus, retourner tout le corpus (pas d'erreur)."""
    retriever = Retriever(_make_store(3), _mock_embedder())
    results = retriever.search("fraîcheur", top_k=20)
    assert 0 < len(results) <= 3


def test_retrieve_corpus_vide_retourne_liste_vide() -> None:
    """Avec un VectorStore vide, search doit retourner []."""
    vs = VectorStore()  # index vide
    retriever = Retriever(vs, _mock_embedder())
    results = retriever.search("question", top_k=5)
    assert results == []


def test_bm25_fallback_works_with_metadata_even_without_dense_index() -> None:
    """Sans vecteurs FAISS mais avec metadata, BM25 doit encore renvoyer des résultats."""
    vs = VectorStore()
    vs.metadata = [
        {
            "text": "gout excellent ramy",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2024-01-01",
            "aspect": "gout",
            "sentiment_label": "positif",
        },
        {
            "text": "prix trop eleve",
            "channel": "facebook",
            "source_url": "http://fb/2",
            "timestamp": "2024-01-02",
            "aspect": "prix",
            "sentiment_label": "negatif",
        },
    ]

    embedder = _mock_embedder()
    retriever = Retriever(vs, embedder)
    results = retriever.search("gout", top_k=2)

    assert len(results) >= 1
    assert results[0]["source_url"] == "http://fb/1"
    assert results[0]["aspect"] == "gout"
    embedder.embed_query.assert_not_called()


def test_bm25_fallback_retourne_vide_si_aucun_terme_ne_matche() -> None:
    """Sans overlap lexical, le fallback sparse ne doit pas inventer des résultats."""
    vs = VectorStore()
    vs.metadata = [
        {
            "text": "gout excellent ramy",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2024-01-01",
        },
        {
            "text": "prix trop eleve",
            "channel": "facebook",
            "source_url": "http://fb/2",
            "timestamp": "2024-01-02",
        },
    ]

    retriever = Retriever(vs, _mock_embedder())

    assert retriever.search("introuvable", top_k=5) == []


def test_bm25_fallback_ne_pad_pas_avec_des_lignes_hors_sujet() -> None:
    """Le fallback sparse doit retourner seulement les documents avec overlap lexical."""
    vs = VectorStore()
    vs.metadata = [
        {
            "text": "gout excellent ramy",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2024-01-01",
        },
        {
            "text": "prix trop eleve",
            "channel": "facebook",
            "source_url": "http://fb/2",
            "timestamp": "2024-01-02",
        },
        {
            "text": "service lent en magasin",
            "channel": "facebook",
            "source_url": "http://fb/3",
            "timestamp": "2024-01-03",
        },
    ]

    retriever = Retriever(vs, _mock_embedder())
    results = retriever.search("gout", top_k=5)

    assert [result["source_url"] for result in results] == ["http://fb/1"]


def test_bm25_fallback_matche_malgre_les_accents() -> None:
    """Le fallback sparse doit rapprocher 'gout' et 'goût' en mode dégradé."""
    vs = VectorStore()
    vs.metadata = [
        {
            "text": "Le goût est excellent",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2024-01-01",
        }
    ]

    retriever = Retriever(vs, _mock_embedder())
    results = retriever.search("gout", top_k=5)

    assert [result["source_url"] for result in results] == ["http://fb/1"]


def test_resultats_tries_par_score_decroissant() -> None:
    """Les résultats doivent être triés du score RRF le plus élevé au plus bas."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    results = retriever.search("goût", top_k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_reste_un_alias_de_search() -> None:
    """L'ancienne API retrieve() doit rester compatible avec search()."""
    retriever = Retriever(_make_store(10), _mock_embedder())
    assert retriever.retrieve("goût", top_k=4) == retriever.search("goût", top_k=4)


def test_chunks_avec_textes_identiques_restent_distincts() -> None:
    """Deux chunks identiques en texte mais différents en metadata doivent tous deux être conservés."""
    vs = VectorStore()
    vecs = _rand_vecs(2)
    meta = [
        {
            "text": "Le jus Ramy est excellent",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2024-01-01",
        },
        {
            "text": "Le jus Ramy est excellent",
            "channel": "youtube",
            "source_url": "http://yt/2",
            "timestamp": "2024-01-02",
        },
    ]
    vs.add(vecs, meta)
    embedder = _mock_embedder()
    embedder.embed_query.return_value = vecs[:1]

    retriever = Retriever(vs, embedder)
    results = retriever.search("jus Ramy", top_k=2)

    assert len(results) == 2
    assert {r["url"] for r in results} == {"http://fb/1", "http://yt/2"}


def test_dense_results_contribuent_apres_reconstruction_metadata() -> None:
    """Le retriever doit fonctionner même si les objets metadata sont reconstruits (ex: save/load)."""
    vs = VectorStore()
    vecs = _rand_vecs(3)
    meta = [
        {"text": "texte alpha unique", "channel": "facebook", "source_url": "http://fb/a", "timestamp": "2024-01-01"},
        {"text": "texte beta unique", "channel": "youtube", "source_url": "http://yt/b", "timestamp": "2024-01-02"},
        {"text": "texte gamma unique", "channel": "audio", "source_url": "http://au/c", "timestamp": "2024-01-03"},
    ]
    vs.add(vecs, meta)

    embedder = _mock_embedder()
    embedder.embed_query.return_value = vecs[:1]

    retriever = Retriever(vs, embedder)

    # Simuler une reconstruction des objets metadata (comme après save/load)
    vs.metadata = [dict(m) for m in vs.metadata]

    results = retriever.search("texte alpha", top_k=3)
    assert len(results) == 3
    urls = {r["url"] for r in results}
    assert "http://fb/a" in urls
