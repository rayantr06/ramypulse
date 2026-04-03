"""
Helper pour le chargement en cache partagé des fichiers Parquet volumineux (annotated.parquet).
"""
import time
import pandas as pd
import logging
import os
import config

logger = logging.getLogger(__name__)

_df_cache = None
_cache_time = 0

def load_annotated(ttl: int = 300) -> pd.DataFrame:
    """
    Charge le dataset annoté en mémoire avec un TTL (Time-To-Live).
    Idéal pour éviter la recharge du fichier massif à chaque requête RAG ou Dashboard.
    """
    global _df_cache, _cache_time
    
    current_time = time.time()
    
    if _df_cache is not None and (current_time - _cache_time) < ttl:
        return _df_cache
        
    try:
        if os.path.exists(config.ANNOTATED_PARQUET_PATH):
            logger.info(f"Chargement de {config.ANNOTATED_PARQUET_PATH} en mémoire...")
            _df_cache = pd.read_parquet(config.ANNOTATED_PARQUET_PATH)
            _cache_time = current_time
            return _df_cache
        else:
            logger.warning(f"Fichier introuvable: {config.ANNOTATED_PARQUET_PATH}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Erreur de chargement Parquet: {e}")
        return pd.DataFrame()
