"""Tests TDD pour l'administration des sources Wave 5.1/5.2."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


@pytest.fixture
def platform_db(tmp_path, monkeypatch):
    """Base SQLite temporaire pour les tests d'admin sources."""
    db_path = tmp_path / "platform_sources.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    return db_path


def _write_import_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _platform_source(*, client_id: str, platform: str, snapshot_path: Path | None = None) -> dict:
    config_json: dict[str, object] = {}
    if snapshot_path is not None:
        config_json["snapshot_path"] = str(snapshot_path)
        config_json["column_mapping"] = {"review": "text"}
    return {
        "source_id": f"src-{client_id}-{platform}",
        "client_id": client_id,
        "source_name": f"{platform} source {client_id}",
        "platform": platform,
        "source_type": f"{platform}_feed" if platform != "google_maps" else "public_reviews",
        "owner_type": "owned",
        "auth_mode": "file_snapshot",
        "config_json": json.dumps(config_json, ensure_ascii=False),
    }


@pytest.mark.parametrize(
    ("connector_path", "class_name", "platform"),
    [
        ("core.connectors.facebook_connector", "FacebookConnector", "facebook"),
        ("core.connectors.google_maps_connector", "GoogleMapsConnector", "google_maps"),
        ("core.connectors.youtube_connector", "YouTubeConnector", "youtube"),
    ],
)
def test_platform_connector_charge_snapshot_configure(
    tmp_path: Path,
    connector_path: str,
    class_name: str,
    platform: str,
) -> None:
    """Chaque connecteur plateforme doit charger un snapshot local configuré."""
    module = __import__(connector_path, fromlist=[class_name])
    connector_cls = getattr(module, class_name)

    snapshot = tmp_path / f"{platform}.parquet"
    pd.DataFrame(
        [
            {
                "review": f"Ramy {platform} tres bon",
                "channel": platform,
                "timestamp": "2026-03-20T10:00:00",
                "source_url": f"https://example.test/{platform}/1",
            },
            {
                "review": f"Ramy {platform} dispo",
                "channel": platform,
                "timestamp": "2026-03-20T11:00:00",
                "source_url": f"https://example.test/{platform}/2",
            },
        ]
    ).to_parquet(snapshot, index=False)

    connector = connector_cls()
    documents = connector.fetch_documents(
        _platform_source(client_id="client-a", platform=platform, snapshot_path=snapshot)
    )

    assert len(documents) == 2
    assert documents[0]["raw_text"]
    assert documents[0]["raw_metadata"]["channel"] == platform
    assert documents[0]["raw_metadata"]["source_id"] == f"src-client-a-{platform}"


def test_source_admin_service_filtre_sources_et_runs_par_client(
    platform_db: Path,
    tmp_path: Path,
) -> None:
    """La lecture admin doit isoler les sources et runs par client_id."""
    from core.database import DatabaseManager
    from core.ingestion.orchestrator import IngestionOrchestrator
    from core.ingestion.source_admin_service import SourceAdminService

    database = DatabaseManager(str(platform_db))
    database.create_tables()
    database.close()

    csv_a = _write_import_csv(
        tmp_path / "client_a.csv",
        [{"review": "ramy client a", "channel": "facebook", "timestamp": "2026-03-20T10:00:00"}],
    )
    csv_b = _write_import_csv(
        tmp_path / "client_b.csv",
        [{"review": "ramy client b", "channel": "facebook", "timestamp": "2026-03-20T11:00:00"}],
    )

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source_a = orchestrator.create_source(
        {
            "client_id": "client-a",
            "source_name": "Import client A",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )
    source_b = orchestrator.create_source(
        {
            "client_id": "client-b",
            "source_name": "Import client B",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )

    orchestrator.run_source_sync(
        source_a["source_id"],
        manual_file_path=str(csv_a),
        column_mapping={"review": "text"},
        client_id="client-a",
    )
    orchestrator.run_source_sync(
        source_b["source_id"],
        manual_file_path=str(csv_b),
        column_mapping={"review": "text"},
        client_id="client-b",
    )

    service = SourceAdminService(db_path=str(platform_db))
    sources_a = service.list_sources(client_id="client-a")
    runs_a = service.list_sync_runs(client_id="client-a")

    assert len(sources_a) == 1
    assert sources_a[0]["source_id"] == source_a["source_id"]
    assert runs_a[0]["source_id"] == source_a["source_id"]
    assert all(row["client_id"] == "client-a" for row in sources_a)


def test_source_admin_service_trace_compte_le_pipeline_par_source(
    platform_db: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """La vue admin doit exposer la traçabilité source -> raw -> normalized -> enriched."""
    from core.database import DatabaseManager
    from core.ingestion.health_checker import compute_source_health
    from core.ingestion.orchestrator import IngestionOrchestrator
    from core.ingestion.source_admin_service import SourceAdminService
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
            "confidence": 0.91,
        },
    )
    monkeypatch.setattr(
        entity_resolver,
        "resolve_text",
        lambda text, source_metadata=None, db_path=None: {
            "brand": "ramy",
            "product": "ramy_orange",
            "product_line": "ramy",
            "sku": None,
            "wilaya": "oran",
            "competitor": None,
            "resolution_evidence": [],
            "resolution_confidence": 0.82,
            "matched_keywords": ["ramy"],
        },
    )

    csv_path = _write_import_csv(
        tmp_path / "trace.csv",
        [
            {"review": "ramy orange bnin", "channel": "facebook", "timestamp": "2026-03-20T10:00:00"},
            {"review": "ramy orange disponible", "channel": "facebook", "timestamp": "2026-03-20T11:00:00"},
        ],
    )

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "client_id": "client-trace",
            "source_name": "Import trace",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )

    orchestrator.run_source_sync(
        source["source_id"],
        manual_file_path=str(csv_path),
        column_mapping={"review": "text"},
        client_id="client-trace",
    )
    normalization = orchestrator.run_normalization_cycle(batch_size=10, client_id="client-trace")
    compute_source_health(source["source_id"], db_path=str(platform_db), client_id="client-trace")

    service = SourceAdminService(db_path=str(platform_db))
    trace = service.get_source_trace(source["source_id"], client_id="client-trace")

    assert normalization["processed_count"] == 2
    assert trace["client_id"] == "client-trace"
    assert trace["raw_document_count"] == 2
    assert trace["normalized_count"] == 2
    assert trace["enriched_count"] == 2
    assert trace["latest_sync_run"]["status"] == "success"
    assert trace["latest_health_snapshot"]["source_id"] == source["source_id"]


def test_run_source_sync_refuse_un_client_id_etranger(
    platform_db: Path,
    tmp_path: Path,
) -> None:
    """Une synchronisation ne doit pas exposer une source d'un autre client."""
    from core.database import DatabaseManager
    from core.ingestion.orchestrator import IngestionOrchestrator

    database = DatabaseManager(str(platform_db))
    database.create_tables()
    database.close()

    csv_path = _write_import_csv(
        tmp_path / "forbidden.csv",
        [{"review": "ramy", "channel": "facebook", "timestamp": "2026-03-20T10:00:00"}],
    )

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "client_id": "client-owner",
            "source_name": "Import owner",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )

    with pytest.raises(KeyError):
        orchestrator.run_source_sync(
            source["source_id"],
            manual_file_path=str(csv_path),
            column_mapping={"review": "text"},
            client_id="client-other",
        )


def test_source_admin_helpers_construisent_les_frames_wave5() -> None:
    """Les helpers admin doivent exposer des tableaux stables pour sources, runs et santé."""
    from ui_helpers.source_admin_helpers import (
        build_health_snapshots_frame,
        build_source_sync_runs_frame,
        build_sources_frame,
    )

    sources_frame = build_sources_frame(
        [
            {
                "source_id": "src-1",
                "client_id": "client-a",
                "source_name": "Facebook Ramy",
                "platform": "facebook",
                "owner_type": "owned",
                "is_active": 1,
                "last_sync_at": "2026-03-20T10:00:00",
                "last_sync_status": "success",
                "latest_health_score": 84.0,
                "raw_document_count": 12,
                "normalized_count": 10,
                "enriched_count": 10,
            }
        ]
    )
    runs_frame = build_source_sync_runs_frame(
        [
            {
                "sync_run_id": "run-1",
                "source_id": "src-1",
                "client_id": "client-a",
                "status": "success",
                "records_fetched": 10,
                "records_inserted": 10,
                "started_at": "2026-03-20T10:00:00",
            }
        ]
    )
    health_frame = build_health_snapshots_frame(
        [
            {
                "snapshot_id": "health-1",
                "source_id": "src-1",
                "client_id": "client-a",
                "health_score": 92.5,
                "success_rate_pct": 100.0,
                "computed_at": "2026-03-20T10:05:00",
            }
        ]
    )

    assert "client_id" in sources_frame.columns
    assert "last_sync_status" in sources_frame.columns
    assert "latest_health_score" in sources_frame.columns
    assert list(runs_frame.columns)[:4] == ["sync_run_id", "source_id", "client_id", "status"]
    assert list(health_frame.columns)[:4] == ["snapshot_id", "source_id", "client_id", "health_score"]
