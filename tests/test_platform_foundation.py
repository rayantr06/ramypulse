"""Tests de fondation plateforme Wave 5.1 / 5.2."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


@pytest.fixture
def platform_db(tmp_path, monkeypatch):
    """Base SQLite temporaire pour les tests plateforme."""
    db_path = tmp_path / "platform.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    return db_path


def test_database_cree_les_tables_plateforme_wave5(platform_db) -> None:
    """create_tables() doit provisionner les tables PRD plateforme de base."""
    from core.database import DatabaseManager

    database = DatabaseManager(str(platform_db))
    database.create_tables()
    rows = database.connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    names = {row["name"] for row in rows}

    required = {
        "clients",
        "sources",
        "source_sync_runs",
        "raw_documents",
        "normalized_records",
        "enriched_signals",
        "regions",
        "distributors",
        "source_health_snapshots",
    }
    assert required.issubset(names)
    database.close()


def test_batch_import_connector_et_normalization_pipeline_creent_la_trace_complete(
    platform_db,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Un import batch doit alimenter raw_documents puis normalized_records/enriched_signals."""
    from core.database import DatabaseManager
    from core.ingestion.orchestrator import IngestionOrchestrator
    import core.analysis.absa_engine as absa_engine
    import core.entity_resolver as entity_resolver

    database = DatabaseManager(str(platform_db))
    database.create_tables()
    database.close()

    monkeypatch.setattr(
        absa_engine,
        "analyze_text",
        lambda text, aspects=None: {
            "global_sentiment": "positif",
            "aspects": ["goût"],
            "aspect_sentiments": {"goût": "positif"},
            "confidence": 0.88,
        },
    )
    monkeypatch.setattr(
        entity_resolver,
        "resolve_text",
        lambda text, source_metadata=None: {
            "brand": "ramy",
            "product": "ramy_citron",
            "product_line": "ramy",
            "sku": None,
            "wilaya": "oran",
            "competitor": None,
            "resolution_evidence": [],
            "resolution_confidence": 0.8,
            "matched_keywords": ["ramy"],
        },
    )

    csv_path = tmp_path / "client_reviews.csv"
    pd.DataFrame(
        [
            {
                "review": "Ramy citron bnin",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/1",
            },
            {
                "review": "Ramy disponible fi Oran",
                "channel": "facebook",
                "timestamp": "2026-03-20T11:00:00",
                "source_url": "https://example.test/2",
            },
        ]
    ).to_csv(csv_path, index=False)

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "source_name": "Import CSV client",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
            "config_json": {"default_channel": "facebook"},
        }
    )

    sync_result = orchestrator.run_source_sync(
        source_id=source["source_id"],
        manual_file_path=str(csv_path),
        column_mapping={"review": "text"},
        run_mode="manual",
    )
    normalization_result = orchestrator.run_normalization_cycle(batch_size=10)

    assert sync_result["status"] == "success"
    assert sync_result["records_inserted"] == 2
    assert normalization_result["processed_count"] == 2

    with sqlite3.connect(platform_db) as connection:
        raw_count = connection.execute("SELECT COUNT(*) FROM raw_documents").fetchone()[0]
        normalized_count = connection.execute("SELECT COUNT(*) FROM normalized_records").fetchone()[0]
        enriched_count = connection.execute("SELECT COUNT(*) FROM enriched_signals").fetchone()[0]
        row = connection.execute(
            """
            SELECT sentiment_label, product, wilaya, normalizer_version
            FROM enriched_signals
            ORDER BY created_at
            LIMIT 1
            """
        ).fetchone()
        raw_flags = connection.execute(
            "SELECT COUNT(*) FROM raw_documents WHERE is_normalized = 1"
        ).fetchone()[0]

    assert raw_count == 2
    assert normalized_count == 2
    assert enriched_count == 2
    assert raw_flags == 2
    assert row[0] == "positif"
    assert row[1] == "ramy_citron"
    assert row[2] == "oran"
    assert row[3]


def test_health_checker_persiste_un_snapshot_source(platform_db) -> None:
    """Le moteur de santé doit calculer un score et persister un snapshot."""
    from core.database import DatabaseManager
    from core.ingestion.health_checker import compute_source_health
    from core.ingestion.orchestrator import IngestionOrchestrator

    database = DatabaseManager(str(platform_db))
    database.create_tables()
    database.close()

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "source_name": "Google Maps Oran",
            "platform": "google_maps",
            "source_type": "public_reviews",
            "owner_type": "market",
            "auth_mode": "public",
            "freshness_sla_hours": 24,
        }
    )

    with sqlite3.connect(platform_db) as connection:
        connection.execute(
            """
            INSERT INTO source_sync_runs (
                sync_run_id, source_id, run_mode, status, records_fetched,
                records_inserted, records_failed, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-1",
                source["source_id"],
                "scheduled",
                "success",
                20,
                18,
                2,
                "2026-03-20T08:00:00",
                "2026-03-20T08:02:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO source_sync_runs (
                sync_run_id, source_id, run_mode, status, records_fetched,
                records_inserted, records_failed, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-2",
                source["source_id"],
                "scheduled",
                "failed",
                0,
                0,
                1,
                "2026-03-21T08:00:00",
                "2026-03-21T08:01:00",
            ),
        )
        connection.execute(
            "UPDATE sources SET last_sync_at = ? WHERE source_id = ?",
            ("2026-03-21T08:01:00", source["source_id"]),
        )
        connection.commit()

    result = compute_source_health(source["source_id"], db_path=str(platform_db))

    assert 0.0 <= result["health_score"] <= 100.0
    assert result["source_id"] == source["source_id"]

    with sqlite3.connect(platform_db) as connection:
        row = connection.execute(
            """
            SELECT health_score, success_rate_pct, freshness_hours
            FROM source_health_snapshots
            WHERE source_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            (source["source_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == result["health_score"]


def test_orchestrator_resout_credential_ref_pour_la_sync(
    platform_db,
    monkeypatch,
) -> None:
    """run_source_sync doit transmettre les credentials resolus depuis credential_ref."""
    from core.ingestion.orchestrator import IngestionOrchestrator
    from core.security.secret_manager import store_secret

    secret_store = Path(platform_db).with_name("secrets.json")
    monkeypatch.setattr(config, "SECRETS_STORE_PATH", secret_store, raising=False)

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    credential_ref = store_secret("collector-token", label="facebook")
    source = orchestrator.create_source(
        {
            "source_name": "Facebook credential ref",
            "platform": "facebook",
            "source_type": "facebook_feed",
            "owner_type": "owned",
            "auth_mode": "token",
            "config_json": {
                "fetch_mode": "collector",
                "page_url": "https://facebook.com/ramy",
                "credential_ref": credential_ref,
            },
        }
    )

    captured: dict[str, object] = {}

    class _FakeFacebookConnector:
        def fetch_documents(self, source: dict, *, credentials=None, **kwargs) -> list[dict]:
            captured["credentials"] = credentials
            return []

    orchestrator._connectors["facebook"] = _FakeFacebookConnector()

    result = orchestrator.run_source_sync(source["source_id"])

    assert result["status"] == "success"
    assert captured["credentials"]["token"] == "collector-token"
