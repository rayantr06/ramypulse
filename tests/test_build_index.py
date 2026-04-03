"""Tests TDD pour scripts/04_build_index.py.

Teste: chargement annotated, embedding, index FAISS, BM25, sauvegarde.
Embedder est mocké pour éviter le chargement du modèle (~1 GB).
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

DIM = 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_annotated_parquet(path: Path, n: int = 10) -> Path:
    """Crée un fichier annotated.parquet minimal."""
    rows = [
        {
            "text": f"Le jus Ramy est bon numéro {i} avec un goût excellent",
            "channel": "facebook",
            "source_url": f"http://fb/{i}",
            "timestamp": "2026-01-01",
            "sentiment_label": "positif",
            "confidence": 0.85,
            "aspects": ["goût"],
            "aspect_sentiments": [{"aspect": "goût", "mention": "bon", "sentiment": "positif", "confidence": 0.85}],
        }
        for i in range(n)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _mock_embedder():
    """Retourne un Embedder mocké retournant des vecteurs aléatoires."""
    embedder = MagicMock()

    def fake_embed_documents(texts):
        vecs = np.random.randn(len(texts), DIM).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms

    embedder.embed_documents.side_effect = fake_embed_documents
    return embedder


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_build_index_cree_fichiers_faiss(tmp_path: Path) -> None:
    """build_index doit créer les fichiers .faiss et .json dans embeddings_dir."""
    from scripts.build_index_04 import build_index

    annotated = _make_annotated_parquet(tmp_path / "annotated.parquet", 5)
    emb_dir = tmp_path / "embeddings"

    with patch("scripts.build_index_04.Embedder", return_value=_mock_embedder()):
        build_index(input_path=annotated, embeddings_dir=emb_dir)

    assert (emb_dir / "faiss_index.faiss").exists()
    assert (emb_dir / "faiss_index.json").exists()


def test_build_index_cree_bm25_pickle(tmp_path: Path) -> None:
    """build_index doit créer un fichier bm25.pkl dans embeddings_dir."""
    from scripts.build_index_04 import build_index

    annotated = _make_annotated_parquet(tmp_path / "annotated.parquet", 5)
    emb_dir = tmp_path / "embeddings"

    with patch("scripts.build_index_04.Embedder", return_value=_mock_embedder()):
        build_index(input_path=annotated, embeddings_dir=emb_dir)

    assert (emb_dir / "bm25.pkl").exists()


def test_index_faiss_rechargeable(tmp_path: Path) -> None:
    """L'index FAISS sauvegardé doit être rechargeable avec VectorStore.load."""
    from scripts.build_index_04 import build_index
    from core.rag.vector_store import VectorStore

    annotated = _make_annotated_parquet(tmp_path / "annotated.parquet", 8)
    emb_dir = tmp_path / "embeddings"

    with patch("scripts.build_index_04.Embedder", return_value=_mock_embedder()):
        build_index(input_path=annotated, embeddings_dir=emb_dir)

    vs = VectorStore.load(str(emb_dir / "faiss_index"))
    assert vs.index.ntotal == 8
    assert len(vs.metadata) == 8


def test_metadata_contient_text_et_channel(tmp_path: Path) -> None:
    """Les metadata de l'index doivent contenir text, channel, source_url, timestamp."""
    from scripts.build_index_04 import build_index
    from core.rag.vector_store import VectorStore

    annotated = _make_annotated_parquet(tmp_path / "annotated.parquet", 3)
    emb_dir = tmp_path / "embeddings"

    with patch("scripts.build_index_04.Embedder", return_value=_mock_embedder()):
        build_index(input_path=annotated, embeddings_dir=emb_dir)

    vs = VectorStore.load(str(emb_dir / "faiss_index"))
    meta = vs.metadata[0]
    assert "text" in meta
    assert "channel" in meta
    assert "source_url" in meta
    assert "timestamp" in meta


def test_fichier_vide_ne_crashe_pas(tmp_path: Path) -> None:
    """Un annotated.parquet vide ne doit pas lever d'exception."""
    from scripts.build_index_04 import build_index

    annotated = tmp_path / "annotated.parquet"
    pd.DataFrame(columns=["text", "channel", "source_url", "timestamp"]).to_parquet(annotated, index=False)
    emb_dir = tmp_path / "embeddings"

    with patch("scripts.build_index_04.Embedder", return_value=_mock_embedder()):
        build_index(input_path=annotated, embeddings_dir=emb_dir)


def test_wrapper_cli_bootstrap_repo_root() -> None:
    """Le wrapper CLI doit se lancer depuis la racine du repo sans ModuleNotFoundError."""
    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["RAMYPULSE_BUILD_INDEX_DRY_RUN"] = "1"

    result = subprocess.run(
        [sys.executable, "scripts/04_build_index.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "DRY_RUN_OK" in result.stdout
