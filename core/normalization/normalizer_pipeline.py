"""Pipeline batch de normalisation vers normalized_records et enriched_signals."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

import config
from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH
from core.analysis import absa_engine
from core.analysis.slm_v04_client import analyze_with_slm
from core.analysis.slm_v04_compiler import legacy_projection
import core.entity_resolver as entity_resolver
from core.ingestion.normalizer import normalize
from core.watchlists.watchlist_manager import get_watchlist

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
    # Préférer absa_adapter (context-aware + sarcasm) si disponible et opérationnel,
    # sinon fallback transparent sur absa_engine (pas de modèle chargé = normal en dev/CI)
    try:
        from core.analysis import absa_adapter as _engine
        return _engine.analyze_text(text)
    except Exception:
        pass
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


def _monitoring_context(
    *,
    client_id: str,
    source_metadata: dict,
) -> tuple[dict[str, object], str | None]:
    explicit_target = source_metadata.get("monitoring_target")
    if isinstance(explicit_target, dict) and explicit_target.get("scope"):
        return explicit_target, str(source_metadata.get("topic") or "").strip() or None

    watchlist_id = str(source_metadata.get("watchlist_id") or "").strip()
    watchlist = get_watchlist(watchlist_id, client_id=client_id) if watchlist_id else None
    filters = (watchlist or {}).get("filters") or {}
    brand_name = str(filters.get("brand_name") or "").strip()
    product_name = str(filters.get("product_name") or "").strip()
    keywords = list(filters.get("keywords") or [])
    if brand_name:
        target: dict[str, object] = {
            "scope": "organisation",
            "entity_name": brand_name,
            "entity_type": "marque",
        }
    elif product_name or keywords:
        target = {
            "scope": "secteur",
            "entity_name": None,
            "entity_type": None,
        }
    else:
        target = {
            "scope": "espace_public",
            "entity_name": None,
            "entity_type": None,
        }
    topic = product_name or (str(keywords[0]) if keywords else None)
    return target, topic


def _analyze_slm_v04(
    text: str,
    *,
    client_id: str,
    source_metadata: dict,
) -> dict[str, object] | None:
    if not config.SLM_V04_ENABLED:
        return None
    monitoring_target, topic = _monitoring_context(
        client_id=client_id,
        source_metadata=source_metadata,
    )
    try:
        result = analyze_with_slm(
            text,
            monitoring_target=monitoring_target,
            topic=topic,
        )
        annotation = result.compilation.annotation
        return {
            "annotation": annotation,
            "raw_model_output": result.raw_model_output,
            "validation_status": result.compilation.validation_status,
            "model_version": result.model_version,
            "compiler_version": result.compilation.compiler_version,
            "inference_ms": result.inference_ms,
            "annotation_created_at": result.created_at or _now(),
            "legacy_projection": legacy_projection(annotation) if annotation else None,
        }
    except Exception as exc:
        logger.warning("SLM V0.4 unavailable, keeping historical analysis: %s", exc)
        return {
            "annotation": None,
            "raw_model_output": None,
            "validation_status": "transport_error",
            "model_version": None,
            "compiler_version": None,
            "inference_ms": None,
            "annotation_created_at": _now(),
            "legacy_projection": None,
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
            analysis = _analyze_text(normalized.get("cleaned_raw") or normalized["normalized"])
            client_id_value = payload.get("client_id") or DEFAULT_CLIENT_ID
            slm_analysis = _analyze_slm_v04(
                normalized.get("cleaned_raw") or normalized["normalized"],
                client_id=client_id_value,
                source_metadata=raw_metadata,
            )
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
                    client_id_value,
                    payload["source_id"],
                    payload["raw_document_id"],
                    normalized["normalized"],
                    raw_text,
                    raw_metadata.get("channel"),
                    raw_metadata.get("source_url"),
                    raw_metadata.get("published_at")
                    or raw_metadata.get("date")
                    or payload.get("collected_at"),
                    normalized.get("language"),
                    normalized.get("script_detected"),
                    json.dumps(normalized, ensure_ascii=False),
                    _now(),
                ),
            )

            aspects = [str(item) for item in analysis.get("aspects", [])]
            first_aspect = aspects[0] if aspects else None
            projected = (slm_analysis or {}).get("legacy_projection") or {}
            sentiment_label = projected.get("sentiment_label") or analysis.get("global_sentiment")
            first_aspect = projected.get("aspect") or first_aspect
            annotation = (slm_analysis or {}).get("annotation")
            connection.execute(
                """
                INSERT INTO enriched_signals (
                    signal_id, client_id, normalized_record_id, source_id, sentiment_label,
                    confidence, aspect, aspects, aspect_sentiments, brand, competitor,
                    product, product_line, sku, wilaya, source_url, channel,
                    event_timestamp, normalizer_version, annotation_json, raw_model_output,
                    validation_status, model_version, compiler_version, inference_ms,
                    annotation_created_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("sig"),
                    client_id_value,
                    normalized_record_id,
                    payload["source_id"],
                    sentiment_label,
                    analysis.get("confidence"),
                    first_aspect,
                    json.dumps(
                        [item.get("family") for item in annotation.get("aspects", [])]
                        if annotation
                        else aspects,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        annotation.get("aspects", [])
                        if annotation
                        else analysis.get("aspect_sentiments", []),
                        ensure_ascii=False,
                    ),
                    resolved.get("brand"),
                    resolved.get("competitor"),
                    resolved.get("product"),
                    resolved.get("product_line"),
                    resolved.get("sku"),
                    resolved.get("wilaya"),
                    raw_metadata.get("source_url") or payload.get("canonical_url"),
                    raw_metadata.get("channel"),
                    raw_metadata.get("published_at")
                    or raw_metadata.get("date")
                    or payload.get("collected_at"),
                    normalizer_version,
                    json.dumps(annotation, ensure_ascii=False) if annotation else None,
                    (slm_analysis or {}).get("raw_model_output"),
                    (slm_analysis or {}).get("validation_status"),
                    (slm_analysis or {}).get("model_version"),
                    (slm_analysis or {}).get("compiler_version"),
                    (slm_analysis or {}).get("inference_ms"),
                    (slm_analysis or {}).get("annotation_created_at"),
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
