"""Construction de l'index FAISS et du modèle BM25 pour RamyPulse.

Charge ``data/processed/annotated.parquet``, génère les embeddings via
multilingual-e5-base, construit l'index FAISS HNSW et sauvegarde le tout
dans ``data/embeddings/``. Construit aussi l'index BM25 en pickle.
"""

from __future__ import annotations

import logging
import pickle
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.rag.embedder import Embedder
from core.rag.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _build_metadata(dataframe: pd.DataFrame) -> list[dict]:
    """Construit la liste de metadata pour l'index FAISS."""
    metadata = []
    for row in dataframe.itertuples(index=False):
        metadata.append({
            "text": getattr(row, "text", ""),
            "channel": getattr(row, "channel", ""),
            "source_url": getattr(row, "source_url", ""),
            "timestamp": getattr(row, "timestamp", ""),
        })
    return metadata


def _build_bm25(texts: list[str], output_path: Path) -> None:
    """Construit et sauvegarde le modèle BM25 en pickle."""
    from rank_bm25 import BM25Okapi

    tokenized = [re.findall(r"\w+", text.lower()) for text in texts]
    bm25 = BM25Okapi(tokenized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fh:
        pickle.dump(bm25, fh)
    logger.info("BM25 sauvegardé : %s (%d documents)", output_path, len(texts))


def build_index(
    input_path: Path | None = None,
    embeddings_dir: Path | None = None,
) -> None:
    """Orchestre la construction de l'index FAISS et du BM25.

    Args:
        input_path: Chemin vers annotated.parquet.
        embeddings_dir: Répertoire de sortie pour les index.
    """
    input_path = Path(input_path) if input_path is not None else config.PROCESSED_DATA_DIR / "annotated.parquet"
    embeddings_dir = Path(embeddings_dir) if embeddings_dir is not None else config.EMBEDDINGS_DIR
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Chargement de %s", input_path)
    dataframe = pd.read_parquet(input_path)

    if dataframe.empty:
        logger.warning("DataFrame vide, aucun index à construire.")
        return

    texts = dataframe["text"].tolist()
    metadata = _build_metadata(dataframe)

    logger.info("Génération des embeddings pour %d textes...", len(texts))
    embedder = Embedder()
    vectors = embedder.embed_documents(texts)

    logger.info("Construction de l'index FAISS HNSW...")
    vs = VectorStore()
    vs.add(vectors, metadata)

    index_path = str(embeddings_dir / "faiss_index")
    vs.save(index_path)

    _build_bm25(texts, embeddings_dir / "bm25.pkl")

    logger.info("=== RÉSUMÉ INDEX ===")
    logger.info("Documents  : %d", len(texts))
    logger.info("Dimension  : %d", vectors.shape[1])
    logger.info("FAISS      : %s", index_path)
    logger.info("BM25       : %s", embeddings_dir / "bm25.pkl")
    logger.info("====================")


if __name__ == "__main__":
    build_index()
