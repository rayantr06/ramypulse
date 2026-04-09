from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

import config
from api.data_loader import load_annotated, reset_cache
from core.tenancy.artifact_refresh import refresh_tenant_artifacts
from core.tenancy.tenant_paths import get_tenant_paths


def _write_tenant_parquet(client_id: str, root: Path, text: str) -> Path:
    """Write a tenant-scoped annotated parquet file for the test."""
    parquet_path = root / "tenants" / client_id / "processed" / "annotated.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"text": text, "channel": "web_search"}]).to_parquet(parquet_path, index=False)
    return parquet_path


def _seed_tenant_sqlite(db_path: Path, client_id: str, text: str) -> None:
    """Seed the minimum SQLite shape needed by the annotated loader."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS content_items (
                content_item_id TEXT,
                canonical_url TEXT,
                external_content_id TEXT,
                coverage_key TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_documents (
                raw_document_id TEXT,
                content_item_id TEXT,
                canonical_url TEXT,
                external_document_id TEXT,
                collected_at TEXT
            );
            CREATE TABLE IF NOT EXISTS normalized_records (
                normalized_record_id TEXT,
                raw_document_id TEXT,
                text TEXT,
                channel TEXT,
                source_url TEXT,
                published_at TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS enriched_signals (
                signal_id TEXT,
                client_id TEXT,
                normalized_record_id TEXT,
                sentiment_label TEXT,
                confidence REAL,
                channel TEXT,
                aspect TEXT,
                wilaya TEXT,
                event_timestamp TEXT,
                source_url TEXT,
                brand TEXT,
                competitor TEXT,
                product TEXT,
                product_line TEXT,
                sku TEXT,
                created_at TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO content_items (content_item_id, canonical_url, external_content_id, coverage_key) VALUES (?, ?, ?, ?)",
            (
                f"content-{client_id}",
                f"https://example.test/{client_id}",
                f"external-{client_id}",
                f"coverage-{client_id}",
            ),
        )
        connection.execute(
            """
            INSERT INTO raw_documents (
                raw_document_id, content_item_id, canonical_url, external_document_id, collected_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"raw-{client_id}",
                f"content-{client_id}",
                f"https://example.test/{client_id}",
                f"external-{client_id}",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO normalized_records (
                normalized_record_id, raw_document_id, text, channel, source_url, published_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"norm-{client_id}",
                f"raw-{client_id}",
                text,
                "web_search",
                f"https://example.test/{client_id}",
                "2026-04-03T10:00:00Z",
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO enriched_signals (
                signal_id, client_id, normalized_record_id, sentiment_label, confidence, channel,
                aspect, wilaya, event_timestamp, source_url, brand, competitor, product,
                product_line, sku, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"sig-{client_id}",
                client_id,
                f"norm-{client_id}",
                "positif",
                0.91,
                "web_search",
                "gout",
                "Alger",
                "2026-04-03T10:00:00Z",
                f"https://example.test/{client_id}",
                "Ramy",
                None,
                "Ramy Citron",
                "Citron",
                None,
                "2026-04-03T10:00:00Z",
            ),
        )
        connection.commit()


def _write_stale_tenant_artifacts(client_id: str) -> None:
    """Create stale tenant index artifacts for cleanup tests."""
    paths = get_tenant_paths(client_id)
    paths.embeddings_dir.mkdir(parents=True, exist_ok=True)
    paths.annotated_path.parent.mkdir(parents=True, exist_ok=True)
    paths.annotated_path.write_text("stale", encoding="utf-8")
    paths.faiss_index_prefix.with_suffix(".faiss").write_text("stale faiss", encoding="utf-8")
    paths.faiss_index_prefix.with_suffix(".json").write_text("stale json", encoding="utf-8")
    paths.bm25_path.write_text("stale bm25", encoding="utf-8")


def test_get_tenant_paths_rejects_invalid_or_traversal_ids(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)

    for client_id in ["..\\outside", "../outside", "C:/tmp/abs-target", "/tmp/abs-target", "tenant/evil", "tenant.."]:
        try:
            get_tenant_paths(client_id)
        except ValueError as exc:
            assert "Invalid tenant id" in str(exc)
        else:
            raise AssertionError(f"Expected ValueError for {client_id!r}")


def test_load_annotated_uses_tenant_parquet_and_ignores_shared_global(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.SQLITE_DB_PATH", tmp_path / "empty.sqlite")
    monkeypatch.setattr("config.ANNOTATED_PARQUET_PATH", tmp_path / "processed" / "annotated.parquet")
    reset_cache()

    shared_path = tmp_path / "processed" / "annotated.parquet"
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"text": "shared", "channel": "shared"}]).to_parquet(shared_path, index=False)

    tenant_a_path = _write_tenant_parquet("tenant-a", tmp_path, "alpha")
    tenant_b_path = _write_tenant_parquet("tenant-b", tmp_path, "beta")

    assert tenant_a_path == get_tenant_paths("tenant-a").annotated_path
    assert tenant_b_path == get_tenant_paths("tenant-b").annotated_path

    df_a = load_annotated(client_id="tenant-a", ttl=0)
    df_b = load_annotated(client_id="tenant-b", ttl=0)

    assert df_a.iloc[0]["text"] == "alpha"
    assert df_b.iloc[0]["text"] == "beta"


def test_load_annotated_does_not_fall_back_to_shared_global_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.SQLITE_DB_PATH", tmp_path / "empty.sqlite")
    monkeypatch.setattr("config.ANNOTATED_PARQUET_PATH", tmp_path / "processed" / "annotated.parquet")
    reset_cache()

    shared_path = tmp_path / "processed" / "annotated.parquet"
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"text": "shared", "channel": "shared"}]).to_parquet(shared_path, index=False)

    df = load_annotated(client_id="tenant-a", ttl=0)

    assert df.empty


def test_refresh_tenant_artifacts_uses_tenant_sqlite_and_writes_tenant_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    tenant_db = tmp_path / "sqlite" / "tenant-a.sqlite"
    monkeypatch.setattr("config.SQLITE_DB_PATH", tenant_db)
    monkeypatch.setattr("config.ANNOTATED_PARQUET_PATH", tmp_path / "processed" / "annotated.parquet")
    reset_cache()

    shared_path = tmp_path / "processed" / "annotated.parquet"
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"text": "shared", "channel": "shared"}]).to_parquet(shared_path, index=False)

    _seed_tenant_sqlite(tenant_db, "tenant-a", "tenant-a sqlite text")
    tenant_paths = get_tenant_paths("tenant-a")

    captured = {}

    def _fake_build_index(*, input_path=None, embeddings_dir=None):
        captured["input_path"] = Path(input_path)
        captured["embeddings_dir"] = Path(embeddings_dir)

    monkeypatch.setattr("core.tenancy.artifact_refresh.build_index", _fake_build_index)

    summary = refresh_tenant_artifacts(client_id="tenant-a", force=True)

    assert summary["documents"] == 1
    assert tenant_paths.annotated_path.exists()
    assert pd.read_parquet(tenant_paths.annotated_path).iloc[0]["text"] == "tenant-a sqlite text"
    assert captured["input_path"] == tenant_paths.annotated_path
    assert captured["embeddings_dir"] == tenant_paths.embeddings_dir


def test_refresh_tenant_artifacts_force_clears_stale_index_artifacts_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    tenant_db = tmp_path / "sqlite" / "tenant-empty.sqlite"
    monkeypatch.setattr("config.SQLITE_DB_PATH", tenant_db)
    reset_cache()

    _seed_tenant_sqlite(tenant_db, "tenant-empty", "unused")
    with sqlite3.connect(tenant_db) as connection:
        connection.execute("DELETE FROM enriched_signals")
        connection.execute("DELETE FROM normalized_records")
        connection.execute("DELETE FROM raw_documents")
        connection.execute("DELETE FROM content_items")
        connection.commit()

    _write_stale_tenant_artifacts("tenant-empty")
    tenant_paths = get_tenant_paths("tenant-empty")

    summary = refresh_tenant_artifacts(client_id="tenant-empty", force=True)

    assert summary["documents"] == 0
    assert not tenant_paths.annotated_path.exists()
    assert not tenant_paths.faiss_index_prefix.with_suffix(".faiss").exists()
    assert not tenant_paths.faiss_index_prefix.with_suffix(".json").exists()
    assert not tenant_paths.bm25_path.exists()
