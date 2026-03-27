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


def test_search_retourne_tuples_metadata_score() -> None:
    """Chaque résultat est un tuple (dict_metadata, float_score)."""
    vs = VectorStore()
    vs.add(_rand_vecs(5), _make_meta(5))
    results = vs.search(_rand_vecs(1), k=2)
    for meta, score in results:
        assert isinstance(meta, dict)
        assert "text" in meta
        assert "channel" in meta
        assert "source_url" in meta
        assert isinstance(score, float)


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
    for meta, score in results:
        assert "text" in meta
