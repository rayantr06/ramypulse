"""Routeur FastAPI pour l'exploration des verbatims RamyPulse.

Fournit une recherche RAG hybride (FAISS + BM25) et une exploration
paginée/filtrée du fichier Parquet annoté.
"""

import logging
import math
import os
from typing import Optional

from fastapi import APIRouter, HTTPException

import config
from api.data_loader import load_annotated
from core.rag.embedder import Embedder
from core.rag.retriever import Retriever
from core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explorer", tags=["Explorer"])

_retriever = None


def _build_fallback_metadata() -> list[dict]:
    """Construit un corpus metadata minimal depuis le dataset annoté."""
    df = load_annotated()
    if df.empty:
        return []

    return [
        {
            "text": str(row.get("text", "") or ""),
            "channel": str(row.get("channel", "") or ""),
            "source_url": str(row.get("source_url", "") or ""),
            "timestamp": str(row.get("timestamp", "") or ""),
            "aspect": str(row.get("aspect", "") or ""),
            "sentiment_label": str(row.get("sentiment_label", "") or ""),
        }
        for row in df.fillna("").to_dict(orient="records")
    ]


def _get_retriever() -> Retriever:
    """Initialise et met en cache le retriever RAG."""
    global _retriever
    if _retriever is not None:
        return _retriever

    try:
        faiss_path = str(config.FAISS_INDEX_PATH)
        if os.path.exists(f"{faiss_path}.faiss"):
            vs = VectorStore.load(faiss_path)
            logger.info("VectorStore FAISS chargé depuis %s", faiss_path)
        else:
            logger.info("Index FAISS absent (%s.faiss) — recherche dégradée", faiss_path)
            vs = VectorStore()
            vs.metadata = _build_fallback_metadata()
    except Exception as e:
        logger.warning("Impossible de charger VectorStore: %s", e)
        vs = VectorStore()
        vs.metadata = _build_fallback_metadata()

    embedder = Embedder()
    _retriever = Retriever(vector_store=vs, embedder=embedder)
    return _retriever


@router.get("/search")
def search_verbatims(q: str, limit: int = 10, channel: Optional[str] = None):
    """Recherche RAG hybride (FAISS + BM25) dans le corpus de verbatims."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Le paramètre 'q' ne peut pas être vide.")

    try:
        retriever = _get_retriever()
        results = retriever.search(question=q, top_k=limit)

        if channel:
            results = [r for r in results if r.get("channel") == channel]

        return {"query": q, "results": results, "total": len(results)}
    except Exception as e:
        logger.error("Erreur RAG search: %s", e)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/verbatims")
def list_verbatims(
    channel: Optional[str] = None,
    aspect: Optional[str] = None,
    sentiment: Optional[str] = None,
    wilaya: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    """Exploration classique, filtrée et paginée des données annotées."""
    try:
        df = load_annotated()
        if df.empty:
            return {"results": [], "total": 0, "page": page, "page_size": page_size}

        if channel:
            df = df[df["channel"] == channel]
        if aspect:
            df = df[df["aspect"] == aspect]
        if sentiment:
            df = df[df["sentiment_label"] == sentiment]
        if wilaya and "wilaya" in df.columns:
            df = df[df["wilaya"] == wilaya]

        total = len(df)

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        import json
        results = json.loads(df_page.to_json(orient="records", date_format="iso"))

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size > 0 else 0,
        }
    except Exception as e:
        logger.error("Erreur list_verbatims: %s", e)
        raise HTTPException(status_code=500, detail="Data retrieval failed")
