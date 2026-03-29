"""Tests TDD pour core/rag/vector_store.py.

Utilise de vrais vecteurs aléatoires 768-dim (FAISS est léger, pas de mock).
Teste : add/search, save/load, remplacement index, gestion k > ntotal.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.rag.vector_store import VectorStore  # noqa: E402

DIM = 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_vecs(n: int, dim: int = DIM) -> np.ndarray:
    """Génère n vecteurs aléatoires normalisés L2."""
    vecs = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


def _make_meta(n: int) -> list[dict]:
    return [
        {
            "text": f"avis produit numéro {i}",
            "channel": "facebook",
            "source_url": f"http://fb/{i}",
            "timestamp": "2024-01-01",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests add + search
# ---------------------------------------------------------------------------

def test_add_et_search_retourne_k_resultats() -> None:
    """Après add(10 vecs), search(k=3) doit retourner 3 résultats."""
    vs = VectorStore()
    vs.add(_rand_vecs(10), _make_meta(10))
    results = vs.search(_rand_vecs(1), k=3)
    assert len(results) == 3


def test_search_retourne_tuples_metadata_score_index() -> None:
    """Chaque résultat est un tuple (dict_metadata, float_score, int_index)."""
    vs = VectorStore()
    vs.add(_rand_vecs(5), _make_meta(5))
    results = vs.search(_rand_vecs(1), k=2)
    for meta, score, idx in results:
        assert isinstance(meta, dict)
        assert "text" in meta
        assert "channel" in meta
        assert "source_url" in meta
        assert isinstance(score, float)
        assert isinstance(idx, int)


def test_metadata_accessible_apres_add() -> None:
    """vs.metadata doit refléter exactement les dicts passés à add()."""
    vs = VectorStore()
    metas = _make_meta(4)
    vs.add(_rand_vecs(4), metas)
    assert len(vs.metadata) == 4
    assert vs.metadata[0]["text"] == "avis produit numéro 0"


def test_add_remplace_index_existant() -> None:
    """Un second appel à add() recrée l'index (pas d'accumulation)."""
    vs = VectorStore()
    vs.add(_rand_vecs(5), _make_meta(5))
    vs.add(_rand_vecs(3), _make_meta(3))
    assert vs.index.ntotal == 3
    assert len(vs.metadata) == 3


def test_search_k_superieur_taille_index() -> None:
    """Si k > ntotal, retourner tous les documents disponibles (pas d'erreur)."""
    vs = VectorStore()
    vs.add(_rand_vecs(3), _make_meta(3))
    results = vs.search(_rand_vecs(1), k=10)
    assert len(results) == 3


def test_search_index_vide_retourne_liste_vide() -> None:
    """Recherche dans un index vide → liste vide."""
    vs = VectorStore()
    results = vs.search(_rand_vecs(1), k=5)
    assert results == []


# ---------------------------------------------------------------------------
# Tests save / load
# ---------------------------------------------------------------------------

def test_save_et_load_preservent_ntotal(tmp_path: pytest.TempPathFactory) -> None:
    """Après save/load, ntotal doit être identique."""
    vs = VectorStore()
    vs.add(_rand_vecs(8), _make_meta(8))
    path = str(tmp_path / "idx")
    vs.save(path)
    vs2 = VectorStore.load(path)
    assert vs2.index.ntotal == 8


def test_save_et_load_preservent_metadata(tmp_path: pytest.TempPathFactory) -> None:
    """Après save/load, la metadata doit être identique."""
    vs = VectorStore()
    metas = _make_meta(6)
    vs.add(_rand_vecs(6), metas)
    path = str(tmp_path / "idx")
    vs.save(path)
    vs2 = VectorStore.load(path)
    assert len(vs2.metadata) == 6
    assert vs2.metadata[2]["text"] == "avis produit numéro 2"


def test_save_et_load_recherche_fonctionnelle(tmp_path: pytest.TempPathFactory) -> None:
    """L'index rechargé depuis disque doit retourner k résultats corrects."""
    vs = VectorStore()
    vs.add(_rand_vecs(10), _make_meta(10))
    path = str(tmp_path / "idx")
    vs.save(path)
    vs2 = VectorStore.load(path)
    results = vs2.search(_rand_vecs(1), k=5)
    assert len(results) == 5
    for meta, score, idx in results:
        assert "text" in meta


def test_search_retourne_index_positionnel() -> None:
    """Chaque résultat de search doit inclure l'index positionnel dans metadata."""
    vs = VectorStore()
    vs.add(_rand_vecs(5), _make_meta(5))
    results = vs.search(_rand_vecs(1), k=3)
    for meta, score, idx in results:
        assert isinstance(idx, int)
        assert 0 <= idx < 5
        assert vs.metadata[idx] is meta


# ---------------------------------------------------------------------------
# Tests add_incremental + ntotal
# ---------------------------------------------------------------------------

def test_add_incremental_accumule_vecteurs() -> None:
    """Deux ajouts incrémentaux doivent accumuler les vecteurs et metadata."""
    vs = VectorStore()
    vs.add_incremental(_rand_vecs(10), _make_meta(10))
    vs.add_incremental(_rand_vecs(5), _make_meta(5))

    assert vs.ntotal == 15
    assert len(vs.metadata) == 15


def test_add_incremental_3_fois_sans_rebuild() -> None:
    """Trois appels successifs à add_incremental doivent conserver l'accumulation."""
    vs = VectorStore()
    vs.add_incremental(_rand_vecs(4), _make_meta(4))
    vs.add_incremental(_rand_vecs(3), _make_meta(3))
    vs.add_incremental(_rand_vecs(2), _make_meta(2))

    assert vs.ntotal == 9
    assert len(vs.metadata) == 9


def test_search_apres_add_incremental() -> None:
    """La recherche doit retrouver des vecteurs ajoutés lors d'un second lot."""
    vs = VectorStore()
    first_batch = _rand_vecs(5)
    second_batch = _rand_vecs(3)

    vs.add_incremental(first_batch, _make_meta(5))
    vs.add_incremental(second_batch, _make_meta(3))

    query = second_batch[1]
    results = vs.search(query, k=3)

    assert results
    top_meta, _, top_idx = results[0]
    assert top_idx >= 5
    assert top_meta["text"] == "avis produit numéro 1"


def test_add_incremental_sur_index_vide() -> None:
    """Un premier ajout incrémental sur un store vide doit fonctionner."""
    vs = VectorStore()

    vs.add_incremental(_rand_vecs(6), _make_meta(6))

    assert vs.ntotal == 6
    assert len(vs.metadata) == 6


def test_ntotal_property() -> None:
    """La propriété ntotal doit refléter le nombre réel de vecteurs indexés."""
    vs = VectorStore()
    assert vs.ntotal == 0

    vs.add_incremental(_rand_vecs(7), _make_meta(7))
    assert vs.ntotal == 7


def test_save_load_apres_incremental(tmp_path: pytest.TempPathFactory) -> None:
    """save/load doit préserver un index construit par ajouts incrémentaux."""
    vs = VectorStore()
    vs.add_incremental(_rand_vecs(5), _make_meta(5))
    vs.add_incremental(_rand_vecs(4), _make_meta(4))

    path = str(tmp_path / "idx_incremental")
    vs.save(path)
    reloaded = VectorStore.load(path)

    assert reloaded.ntotal == 9
    assert len(reloaded.metadata) == 9
