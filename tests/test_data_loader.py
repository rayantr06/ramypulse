"""Tests du loader canonique annotated -> SQLite puis parquet."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pandas as pd

import config
from api import data_loader
from core.database import DatabaseManager


def _reset_loader_cache() -> None:
    data_loader._df_cache = None
    data_loader._cache_time = 0.0


def _seed_sqlite_signal(db_path: Path) -> None:
    database = DatabaseManager(db_path)
    database.create_tables()
    database.close()

    content_item_id = f"cnt-{uuid.uuid4()}"
    raw_document_id = f"raw-{uuid.uuid4()}"
    normalized_record_id = f"norm-{uuid.uuid4()}"
    source_id = "src-loader"

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO sources (
                source_id, client_id, source_name, platform, source_type, owner_type,
                auth_mode, config_json, is_active, sync_frequency_minutes,
                freshness_sla_hours, source_purpose, source_priority, coverage_key,
                credential_id, last_sync_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                "ramy_client_001",
                "Loader Source",
                "facebook",
                "managed_page",
                "owned",
                None,
                "{}",
                1,
                60,
                24,
                "owned_content",
                1,
                "owned:facebook:loader",
                None,
                None,
                "2026-04-03T10:00:00Z",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO content_items (
                content_item_id, client_id, platform, external_content_id,
                canonical_url, canonical_key, owner_type, coverage_key,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content_item_id,
                "ramy_client_001",
                "facebook",
                "fb-loader-1",
                "https://facebook.com/posts/sql-1",
                "facebook:fb-loader-1",
                "owned",
                "owned:facebook:loader",
                "2026-04-03T10:00:00Z",
                "2026-04-03T10:00:00Z",
            ),
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
                "ramy_client_001",
                source_id,
                "run-loader",
                "fb-loader-1",
                "{}",
                "texte canonique",
                '{"source_url":"https://facebook.com/posts/sql-1"}',
                "sha-loader-1",
                content_item_id,
                "facebook",
                "https://facebook.com/posts/sql-1",
                "facebook:fb-loader-1",
                "2026-04-03T10:00:00Z",
                1,
                "wave5.2-local",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO normalized_records (
                normalized_record_id, client_id, source_id, raw_document_id,
                text, text_original, channel, source_url, published_at, language,
                script_detected, normalized_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_record_id,
                "ramy_client_001",
                source_id,
                raw_document_id,
                "texte canonique",
                "texte canonique",
                "facebook",
                "https://facebook.com/posts/sql-1",
                "2026-04-03T10:00:00Z",
                "fr",
                "latin",
                "{}",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO enriched_signals (
                signal_id, client_id, normalized_record_id, source_id, sentiment_label,
                confidence, aspect, aspects, aspect_sentiments, brand, competitor,
                product, product_line, sku, wilaya, region_id, distributor_id,
                source_url, channel, event_timestamp, normalizer_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sig-loader-1",
                "ramy_client_001",
                normalized_record_id,
                source_id,
                "positif",
                0.91,
                "gout",
                '["gout"]',
                "[]",
                "Ramy",
                None,
                "Ramy Citron",
                "Citron",
                None,
                "Alger",
                None,
                None,
                "https://facebook.com/posts/sql-1",
                "facebook",
                "2026-04-03T10:00:00Z",
                "wave5.2-local",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.commit()


def test_load_annotated_prefers_sqlite_and_exports_parquet(monkeypatch, tmp_path: Path) -> None:
    """Le loader doit préférer SQLite canonique et exporter annotated.parquet."""
    db_path = tmp_path / "signals.db"
    parquet_path = tmp_path / "annotated.parquet"
    _seed_sqlite_signal(db_path)

    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(data_loader.config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "ANNOTATED_PARQUET_PATH", parquet_path, raising=False)
    monkeypatch.setattr(data_loader.config, "ANNOTATED_PARQUET_PATH", parquet_path, raising=False)
    _reset_loader_cache()

    df = data_loader.load_annotated(ttl=0)

    assert not df.empty
    assert df.iloc[0]["text"] == "texte canonique"
    assert df.iloc[0]["source_url"] == "https://facebook.com/posts/sql-1"
    assert df.iloc[0]["product"] == "Ramy Citron"
    assert parquet_path.exists()


def test_load_annotated_falls_back_to_parquet_when_sqlite_empty(monkeypatch, tmp_path: Path) -> None:
    """Le loader doit revenir au parquet si SQLite canonique est vide."""
    db_path = tmp_path / "empty.db"
    parquet_path = tmp_path / "annotated.parquet"
    DatabaseManager(db_path).create_tables()
    pd.DataFrame(
        [
            {
                "text": "depuis parquet",
                "channel": "facebook",
                "source_url": "https://example.test/post/1",
                "timestamp": "2026-04-03T10:00:00Z",
                "sentiment_label": "positif",
            }
        ]
    ).to_parquet(parquet_path, index=False)

    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(data_loader.config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "ANNOTATED_PARQUET_PATH", parquet_path, raising=False)
    monkeypatch.setattr(data_loader.config, "ANNOTATED_PARQUET_PATH", parquet_path, raising=False)
    _reset_loader_cache()

    df = data_loader.load_annotated(ttl=0)

    assert not df.empty
    assert df.iloc[0]["text"] == "depuis parquet"
