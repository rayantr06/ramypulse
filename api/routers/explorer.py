import logging
import math
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from api.data_loader import load_annotated
from core.rag.retriever import Retriever
from core.rag.vector_store import VectorStore
from core.rag.embedder import Embedder
import config
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explorer", tags=["Explorer"])

# Hybrid Retriever (cached strictly per request or instantiated once)
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        try:
            faiss_path = str(getattr(config, "FAISS_INDEX_PATH", "data/embeddings/faiss_index"))
            if os.path.exists(f"{faiss_path}.faiss"):
                vs = VectorStore.load(faiss_path)
            else:
                vs = VectorStore()
        except Exception as e:
            logger.warning(f"Impossible de charger VectorStore : {e}")
            vs = VectorStore()
            
        embedder = Embedder()
        _retriever = Retriever(vector_store=vs, embedder=embedder)
    return _retriever

@router.get("/search")
def search_verbatims(q: str, limit: int = 10, channel: Optional[str] = None):
    """Recherche RAG hybride (Faiss + BM25) dans le corpus de verbatims."""
    try:
        retriever = get_retriever()
        # The retriever currently doesn't support filter_dict natively in this stub
        results = retriever.search(question=q, top_k=limit)
        
        # Post-filter if channel is provided
        if channel:
            results = [r for r in results if r.get("channel") == channel]
            
        return {"query": q, "results": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Erreur RAG search: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/verbatims")
def list_verbatims(
    channel: str = None, 
    aspect: str = None, 
    sentiment: str = None, 
    wilaya: str = None,
    page: int = 1, 
    page_size: int = 50
):
    """Exploration classique, filtrée et paginée des données du fichier Parquet."""
    try:
        df = load_annotated()
        if df.empty:
            return {"results": [], "total": 0, "page": page, "page_size": page_size}
            
        # Applications des filtres stricts
        if channel:
            df = df[df['channel'] == channel]
        if aspect:
            df = df[df['aspect'] == aspect]
        if sentiment:
            df = df[df['sentiment_label'] == sentiment]
        if wilaya:
            df = df[df['wilaya'] == wilaya]
            
        total = len(df)
        
        # Pagination pandas
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        df_page = df.iloc[start_idx:end_idx]
        
        # Convertir en dictionnaires pour l'API
        results = df_page.to_dict('records')
        
        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size > 0 else 0
        }
    except Exception as e:
        logger.error(f"Erreur list_verbatims: {e}")
        raise HTTPException(status_code=500, detail="Data retrieval failed")
