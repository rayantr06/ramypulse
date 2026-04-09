"""Helpers to insert watch collector outputs into raw_documents."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import config
from core.database import DatabaseManager
from core.ingestion.content_identity import extract_canonical_url, resolve_or_create_content_item

_SAFE_KEY_RE = re.compile(r"[^a-z0-9_-]+")


def _resolve_db_path(db_path: str | Path | None = None) -> str:
    return str(db_path or config.SQLITE_DB_PATH)


def _ensure_schema(db_path: str | Path | None = None) -> None:
    DatabaseManager(_resolve_db_path(db_path)).create_tables()


def _get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(_resolve_db_path(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def build_watch_source_id(client_id: str, collector_key: str) -> str:
    """Build a stable raw-document source identifier for watch collectors."""
    safe_client_id = _SAFE_KEY_RE.sub("-", str(client_id or "").strip().lower()).strip("-")
    safe_collector_key = _SAFE_KEY_RE.sub("-", str(collector_key or "").strip().lower()).strip("-")
    return f"watch:{safe_client_id}:{safe_collector_key}"


def insert_watch_documents(
    *,
    client_id: str,
    collector_key: str,
    documents: Iterable[dict[str, object]],
    run_id: str,
    db_path: str | Path | None = None,
) -> int:
    """Persist collector outputs into ``raw_documents`` and return the inserted count."""
    _ensure_schema(db_path)
    source_id = build_watch_source_id(client_id, collector_key)
    inserted = 0

    with _get_connection(db_path) as connection:
        for document in documents:
            raw_document_id = _new_id("raw")
            canonical_url = extract_canonical_url(
                raw_payload=document.get("raw_payload"),
                raw_metadata=document.get("raw_metadata"),
                explicit_url=document.get("source_url"),
            )
            content_item_id, canonical_key, canonical_url = resolve_or_create_content_item(
                connection,
                client_id=client_id,
                platform=collector_key,
                external_content_id=document.get("external_document_id"),
                canonical_url=canonical_url,
                owner_type="market",
                coverage_key=source_id,
                checksum_sha256=document.get("checksum_sha256"),
                fallback_id=raw_document_id,
            )
            connection.execute(
                """
                INSERT INTO raw_documents (
                    raw_document_id, client_id, source_id, sync_run_id, external_document_id,
                    raw_payload, raw_text, raw_metadata, checksum_sha256,
                    content_item_id, platform, canonical_url, canonical_key,
                    collected_at, is_normalized, normalizer_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_document_id,
                    client_id,
                    source_id,
                    run_id,
                    document.get("external_document_id"),
                    json.dumps(document.get("raw_payload") or {}, ensure_ascii=False, default=str),
                    document.get("raw_text"),
                    json.dumps(document.get("raw_metadata") or {}, ensure_ascii=False, default=str),
                    document.get("checksum_sha256"),
                    content_item_id,
                    collector_key,
                    canonical_url,
                    canonical_key,
                    document.get("collected_at") or _now(),
                    0,
                    None,
                    _now(),
                ),
            )
            inserted += 1
        connection.commit()

    return inserted
