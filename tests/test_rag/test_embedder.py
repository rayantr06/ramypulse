"""Tests TDD pour core/rag/embedder.py.

_get_model() est patché pour éviter le chargement du modèle (~1 GB)
et contourner les conflits de versions torch/torchvision.
On teste : shape, préfixes E5 (query:/passage:), normalisation L2, batch vide.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.rag.embedder import Embedder  # noqa: E402

DIM = 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_model(n: int, dim: int = DIM) -> MagicMock:
    """Crée un mock de SentenceTransformer retournant n vecteurs aléatoires."""
    model = MagicMock()
    model.encode.return_value = np.random.randn(n, dim).astype(np.float32)
    return model


# ---------------------------------------------------------------------------
# Tests shape
# ---------------------------------------------------------------------------

def test_embed_documents_retourne_shape_n_768() -> None:
    """embed_documents sur 3 textes → shape (3, 768)."""
    with patch.object(Embedder, "_get_model", return_value=_fake_model(3)):
        result = Embedder().embed_documents(["a", "b", "c"])
    assert result.shape == (3, DIM)


def test_embed_query_retourne_shape_1_768() -> None:
    """embed_query → shape (1, 768)."""
    with patch.object(Embedder, "_get_model", return_value=_fake_model(1)):
        result = Embedder().embed_query("question test")
    assert result.shape == (1, DIM)


def test_embed_batch_vide_retourne_array_vide() -> None:
    """embed_documents([]) → shape (0, 768), sans appel au modèle."""
    mock_model = MagicMock()
    with patch.object(Embedder, "_get_model", return_value=mock_model):
        result = Embedder().embed_documents([])
    assert result.shape == (0, DIM)
    mock_model.encode.assert_not_called()


# ---------------------------------------------------------------------------
# Tests préfixes E5
# ---------------------------------------------------------------------------

def test_embed_documents_prefixe_passage() -> None:
    """Chaque texte doit être préfixé 'passage: ' avant l'encoding."""
    mock_model = _fake_model(2)
    with patch.object(Embedder, "_get_model", return_value=mock_model):
        Embedder().embed_documents(["texte1", "texte2"])
    texts_passed = mock_model.encode.call_args[0][0]
    assert all(t.startswith("passage: ") for t in texts_passed)


def test_embed_query_prefixe_query() -> None:
    """La requête doit être préfixée 'query: ' avant l'encoding."""
    mock_model = _fake_model(1)
    with patch.object(Embedder, "_get_model", return_value=mock_model):
        Embedder().embed_query("ma question")
    texts_passed = mock_model.encode.call_args[0][0]
    assert texts_passed[0].startswith("query: ")


# ---------------------------------------------------------------------------
# Tests normalisation L2
# ---------------------------------------------------------------------------

def test_embed_documents_vecteurs_l2_normalises() -> None:
    """Les vecteurs de sortie doivent avoir une norme L2 ≈ 1.0."""
    raw = np.random.randn(4, DIM).astype(np.float32)
    mock_model = MagicMock()
    mock_model.encode.return_value = raw.copy()
    with patch.object(Embedder, "_get_model", return_value=mock_model):
        result = Embedder().embed_documents(["a", "b", "c", "d"])
    norms = np.linalg.norm(result, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_embed_query_vecteur_l2_normalise() -> None:
    """Le vecteur requête doit avoir une norme L2 ≈ 1.0."""
    raw = np.random.randn(1, DIM).astype(np.float32)
    mock_model = MagicMock()
    mock_model.encode.return_value = raw.copy()
    with patch.object(Embedder, "_get_model", return_value=mock_model):
        result = Embedder().embed_query("test")
    assert abs(float(np.linalg.norm(result)) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# Test dtype
# ---------------------------------------------------------------------------

def test_embed_documents_dtype_float32() -> None:
    """L'output doit être float32 (requis par FAISS)."""
    with patch.object(Embedder, "_get_model", return_value=_fake_model(2)):
        result = Embedder().embed_documents(["a", "b"])
    assert result.dtype == np.float32
