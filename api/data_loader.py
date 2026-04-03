"""Cache partagé pour le chargement du fichier Parquet annoté.

Fournit un TTL (Time-To-Live) pour éviter la recharge du fichier
volumineux à chaque requête API. Thread-safe via un verrou.
"""

import logging
import os
import threading
import time

import pandas as pd

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_df_cache: pd.DataFrame | None = None
_cache_time: float = 0.0


def load_annotated(ttl: int = 300) -> pd.DataFrame:
    """Charge le dataset annoté en mémoire avec un TTL.

    Args:
        ttl: Durée de validité du cache en secondes (défaut 300).

    Returns:
        DataFrame annoté, ou DataFrame vide si le fichier est absent.
    """
    global _df_cache, _cache_time

    current_time = time.time()

    if _df_cache is not None and (current_time - _cache_time) < ttl:
        return _df_cache

    with _lock:
        # Double-check après acquisition du verrou
        if _df_cache is not None and (time.time() - _cache_time) < ttl:
            return _df_cache

        parquet_path = str(config.ANNOTATED_PARQUET_PATH)
        try:
            if os.path.exists(parquet_path):
                logger.info("Chargement de %s en mémoire...", parquet_path)
                _df_cache = pd.read_parquet(parquet_path)
                _cache_time = time.time()
                return _df_cache
            else:
                logger.warning("Fichier introuvable: %s", parquet_path)
                return pd.DataFrame()
        except Exception as e:
            logger.error("Erreur de chargement Parquet: %s", e)
            return pd.DataFrame()
