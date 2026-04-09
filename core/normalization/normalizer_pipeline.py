"""Pipeline batch de normalisation vers normalized_records et enriched_signals."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH
from core.analysis import absa_engine
import core.entity_resolver as entity_resolver
from core.ingestion.normalizer import normalize

logger = logging.getLogger(__name__)

DEFAULT_NORMALIZER_VERSION = "wave5.2-local"


def _get_connection(db_path=None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path or SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _analyze_text(text: str) -> dict:
    analyze_fn = getattr(absa_engine, "analyze_text", None)
    if callable(analyze_fn):
        return analyze_fn(text)
    raise RuntimeError("absa_engine.analyze_text indisponible")


def _resolve_entities(text: str, source_metadata: dict, db_path=None) -> dict:
    resolve_fn = getattr(entity_resolver, "resolve_text", None)
    if callable(resolve_fn):
        try:
            return resolve_fn(text, source_metadata=source_metadata, db_path=db_path)
        except TypeError:
            return resolve_fn(text, source_metadata=source_metadata)
    return {
        "brand": None,
        "product": None,
        "product_line": None,
        "sku": None,
        "wilaya": None,
        "competitor": None,
    }


def run_normalization_job(
    batch_size: int = 200,
    db_path=None,
    normalizer_version: str = DEFAULT_NORMALIZER_VERSION,
    client_id: str | None = None,
    source_id: str | None = None,
    sync_run_id: str | None = None,
) -> dict:
    """Traite les raw_documents non normalisés et écrit les tables cibles."""
    with _get_connection(db_path) as connection:
        params: list = []
        where_clauses = ["is_normalized = 0"]
        if client_id:
            where_clauses.append("client_id = ?")
            params.append(client_id)
        if source_id:
            where_clauses.append("source_id = ?")
            params.append(source_id)
        if sync_run_id:
            where_clauses.append("sync_run_id = ?")
            params.append(sync_run_id)
        where_clause = "WHERE " + " AND ".join(where_clauses)
        params.append(batch_size)
        rows = connection.execute(
            f"""
            SELECT *
            FROM raw_documents
            {where_clause}
            ORDER BY collected_at ASC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()

        processed_count = 0
        for row in rows:
            payload = dict(row)
            raw_text = str(payload.get("raw_text") or "")
            normalized = normalize(raw_text)
            raw_metadata = json.loads(payload.get("raw_metadata") or "{}")
            analysis = _analyze_text(normalized["normalized"])
            resolved = _resolve_entities(normalized["normalized"], raw_metadata, db_path=db_path)

            normalized_record_id = _new_id("norm")
            connection.execute(
                """
                INSERT INTO normalized_records (
                    normalized_record_id, client_id, source_id, raw_document_id, text,
                    text_original, channel, source_url, published_at, language,
                    script_detected, normalized_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_record_id,
                    payload.get("client_id") or DEFAULT_CLIENT_ID,
                    payload["source_id"],
                    payload["raw_document_id"],
                    normalized["normalized"],
                    raw_text,
                    raw_metadata.get("channel"),
                    raw_metadata.get("source_url"),
                    payload.get("collected_at"),
                    normalized.get("language"),
                    normalized.get("script_detected"),
                    json.dumps(normalized, ensure_ascii=False),
                    _now(),
                ),
            )

            aspects = [str(item) for item in analysis.get("aspects", [])]
            first_aspect = aspects[0] if aspects else None
            connection.execute(
                """
                INSERT INTO enriched_signals (
                    signal_id, client_id, normalized_record_id, source_id, sentiment_label,
                    confidence, aspect, aspects, aspect_sentiments, brand, competitor,
                    product, product_line, sku, wilaya, source_url, channel,
                    event_timestamp, normalizer_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("sig"),
                    payload.get("client_id") or DEFAULT_CLIENT_ID,
                    normalized_record_id,
                    payload["source_id"],
                    analysis.get("global_sentiment"),
                    analysis.get("confidence"),
                    first_aspect,
                    json.dumps(aspects, ensure_ascii=False),
                    json.dumps(analysis.get("aspect_sentiments", []), ensure_ascii=False),
                    resolved.get("brand"),
                    resolved.get("competitor"),
                    resolved.get("product"),
                    resolved.get("product_line"),
                    resolved.get("sku"),
                    resolved.get("wilaya"),
                    raw_metadata.get("source_url"),
                    raw_metadata.get("channel"),
                    payload.get("collected_at"),
                    normalizer_version,
                    _now(),
                ),
            )

            connection.execute(
                """
                UPDATE raw_documents
                SET is_normalized = 1,
                    normalizer_version = ?
                WHERE raw_document_id = ?
                """,
                (normalizer_version, payload["raw_document_id"]),
            )
            processed_count += 1

        connection.commit()

    logger.info("Normalization job complete: %s documents", processed_count)
    return {
        "processed_count": processed_count,
        "normalizer_version": normalizer_version,
    }
