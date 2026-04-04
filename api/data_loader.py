"""Loader canonique du dataset annoté RamyPulse.

Privilégie SQLite Wave 5 (`enriched_signals` + `normalized_records`) et
retombe sur `annotated.parquet` quand la base canonique est vide.
Expose aussi un export parquet transitoire pour la compatibilité RAG.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time

import pandas as pd

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_df_cache: pd.DataFrame | None = None
_cache_time: float = 0.0


def reset_cache() -> None:
    """Vide explicitement le cache mémoire du loader."""
    global _df_cache, _cache_time
    _df_cache = None
    _cache_time = 0.0


def _load_from_sqlite() -> pd.DataFrame:
    """Charge le dataset canonique depuis SQLite Wave 5."""
    db_path = str(config.SQLITE_DB_PATH)
    if not os.path.exists(db_path):
        return pd.DataFrame()

    query = """
        SELECT
            nr.text AS text,
            es.sentiment_label,
            es.confidence,
            COALESCE(es.channel, nr.channel, '') AS channel,
            COALESCE(es.aspect, '') AS aspect,
            COALESCE(es.wilaya, '') AS wilaya,
            COALESCE(es.event_timestamp, nr.published_at, rd.collected_at, '') AS timestamp,
            COALESCE(es.source_url, nr.source_url, rd.canonical_url, ci.canonical_url, '') AS source_url,
            COALESCE(es.brand, '') AS brand,
            COALESCE(es.competitor, '') AS competitor,
            COALESCE(es.product, '') AS product,
            COALESCE(es.product_line, '') AS product_line,
            COALESCE(es.sku, '') AS sku,
            COALESCE(ci.content_item_id, rd.content_item_id, '') AS content_item_id,
            COALESCE(ci.external_content_id, rd.external_document_id, '') AS external_content_id,
            COALESCE(ci.coverage_key, '') AS coverage_key
        FROM enriched_signals es
        INNER JOIN normalized_records nr
            ON nr.normalized_record_id = es.normalized_record_id
        LEFT JOIN raw_documents rd
            ON rd.raw_document_id = nr.raw_document_id
        LEFT JOIN content_items ci
            ON ci.content_item_id = rd.content_item_id
        ORDER BY COALESCE(es.event_timestamp, nr.published_at, rd.collected_at, nr.created_at) DESC
    """

    try:
        with sqlite3.connect(db_path) as connection:
            return pd.read_sql_query(query, connection)
    except Exception as exc:
        logger.warning("Erreur de chargement SQLite canonique: %s", exc)
        return pd.DataFrame()


def _export_sqlite_snapshot_to_parquet(df: pd.DataFrame) -> None:
    """Écrit un snapshot parquet dérivé de SQLite pour compatibilité transitoire."""
    parquet_path = config.ANNOTATED_PARQUET_PATH
    try:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(parquet_path, index=False)
    except Exception as exc:
        logger.warning("Impossible d'exporter le snapshot annotated.parquet: %s", exc)


def _load_from_parquet() -> pd.DataFrame:
    """Charge le parquet legacy si présent."""
    parquet_path = str(config.ANNOTATED_PARQUET_PATH)
    try:
        if os.path.exists(parquet_path):
            logger.info("Chargement de %s en mémoire...", parquet_path)
            return pd.read_parquet(parquet_path)
        logger.warning("Fichier introuvable: %s", parquet_path)
    except Exception as exc:
        logger.error("Erreur de chargement Parquet: %s", exc)
    return pd.DataFrame()


def load_annotated(ttl: int = 300) -> pd.DataFrame:
    """Charge le dataset annoté en mémoire avec un TTL."""
    global _df_cache, _cache_time

    current_time = time.time()
    if _df_cache is not None and (current_time - _cache_time) < ttl:
        return _df_cache

    with _lock:
        if _df_cache is not None and (time.time() - _cache_time) < ttl:
            return _df_cache

        sqlite_df = _load_from_sqlite()
        if not sqlite_df.empty:
            _df_cache = sqlite_df
            _cache_time = time.time()
            _export_sqlite_snapshot_to_parquet(sqlite_df)
            return _df_cache

        parquet_df = _load_from_parquet()
        _df_cache = parquet_df
        _cache_time = time.time()
        return _df_cache
