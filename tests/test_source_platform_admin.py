"""Tests TDD pour l'administration des sources Wave 5.1/5.2."""

from __future__ import annotations

import json
import sqlite3
import sys
import types
import importlib
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


@pytest.fixture
def platform_db(tmp_path, monkeypatch):
    """Base SQLite temporaire pour les tests d'admin sources."""
    db_path = tmp_path / "platform_sources.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    return db_path


@pytest.fixture
def temp_secret_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige le store local de secrets vers un fichier temporaire."""
    secret_store = tmp_path / "secrets.json"
    monkeypatch.setattr(_config_module(), "SECRETS_STORE_PATH", secret_store, raising=False)
    return secret_store


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


def test_instagram_connector_charge_un_snapshot(tmp_path: Path) -> None:
    """Le connecteur Instagram doit charger un snapshot local."""
    from core.connectors.instagram_connector import InstagramConnector

    snapshot = tmp_path / "instagram.parquet"
    pd.DataFrame(
        [
            {
                "review": "Ramy instagram tres bon",
                "channel": "instagram",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/instagram/1",
            },
            {
                "review": "Ramy instagram dispo",
                "channel": "instagram",
                "timestamp": "2026-03-20T11:00:00",
                "source_url": "https://example.test/instagram/2",
            },
        ]
    ).to_parquet(snapshot, index=False)

    connector = InstagramConnector()
    documents = connector.fetch_documents(
        {
            "source_id": "src-instagram-001",
            "client_id": "client-a",
            "source_name": "Instagram Ramy",
            "platform": "instagram",
            "source_type": "instagram_profile",
            "owner_type": "owned",
            "auth_mode": "file_snapshot",
            "config_json": {
                "snapshot_path": str(snapshot),
                "profile_url": "https://instagram.com/ramy",
                "column_mapping": {"review": "text"},
            },
        }
    )

    assert len(documents) == 2
    assert documents[0]["raw_text"]
    assert documents[0]["raw_metadata"]["channel"] == "instagram"
    assert documents[0]["raw_metadata"]["source_id"] == "src-instagram-001"


def test_instagram_connector_rejette_les_lignes_d_une_autre_plateforme(tmp_path: Path) -> None:
    """Un snapshot Instagram ne doit pas ingérer des lignes Facebook."""
    from core.connectors.instagram_connector import InstagramConnector

    snapshot = tmp_path / "instagram_wrong_platform.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/1",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = InstagramConnector()
    documents = connector.fetch_documents(
        {
            "source_id": "src-instagram-wrong",
            "client_id": "client-a",
            "source_name": "Instagram Ramy",
            "platform": "instagram",
            "source_type": "instagram_profile",
            "owner_type": "owned",
            "auth_mode": "file_snapshot",
            "config_json": {
                "snapshot_path": str(snapshot),
                "profile_url": "https://instagram.com/ramy",
                "column_mapping": {"text": "text"},
            },
        }
    )

    assert documents == []


@pytest.mark.parametrize(
    "platform",
    ["facebook", "google_maps", "youtube"],
)
def test_platform_connector_respecte_fetch_mode_collector(
    tmp_path: Path,
    monkeypatch,
    platform: str,
) -> None:
    """Le mode collector doit etre prioritaire sur un snapshot local existant."""
    connector_path = {
        "facebook": "core.connectors.facebook_connector",
        "google_maps": "core.connectors.google_maps_connector",
        "youtube": "core.connectors.youtube_connector",
    }[platform]
    class_name = {
        "facebook": "FacebookConnector",
        "google_maps": "GoogleMapsConnector",
        "youtube": "YouTubeConnector",
    }[platform]
    required_config = {
        "facebook": {"page_url": "https://facebook.com/ramy"},
        "google_maps": {"place_url": "https://maps.google.com/?cid=1"},
        "youtube": {"channel_id": "UC123"},
    }[platform]
    module = __import__(connector_path, fromlist=[class_name])
    connector_cls = getattr(module, class_name)

    snapshot = tmp_path / f"{platform}.parquet"
    pd.DataFrame(
        [
            {
                "text": f"{platform} snapshot",
                "channel": platform,
                "timestamp": "2026-03-20T10:00:00",
                "source_url": f"https://example.test/{platform}/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = connector_cls()
    scraper_module_name = connector.scraper_modules[0]
    fake_module = types.ModuleType(scraper_module_name)
    fake_module.collect = lambda source=None, credentials=None: pd.DataFrame(
        [
            {
                "text": f"{platform} collector",
                "channel": platform,
                "timestamp": "2026-03-20T11:00:00",
                "source_url": f"https://example.test/{platform}/collector",
            }
        ]
    )
    monkeypatch.setitem(sys.modules, scraper_module_name, fake_module)

    documents = connector.fetch_documents(
        {
            "source_id": f"src-{platform}-collector",
            "client_id": "client-a",
            "source_name": f"{platform} source",
            "platform": platform,
            "source_type": f"{platform}_feed",
            "owner_type": "owned",
            "auth_mode": "file_snapshot",
            "config_json": {
                "fetch_mode": "collector",
                "snapshot_path": str(snapshot),
                **required_config,
            },
        }
    )

    assert len(documents) == 1
    assert documents[0]["raw_text"] == f"{platform} collector"
    assert documents[0]["raw_metadata"]["source_url"].endswith("/collector")


def test_facebook_connector_exige_un_identifiant_en_mode_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Facebook en collector doit exiger un identifiant ou une URL de page."""
    from core.connectors.facebook_connector import FacebookConnector

    snapshot = tmp_path / "facebook_snapshot.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = FacebookConnector()
    scraper_module_name = connector.scraper_modules[0]
    fake_module = types.ModuleType(scraper_module_name)
    fake_module.collect = lambda source=None, credentials=None: pd.DataFrame(
        [
            {
                "text": "facebook collector",
                "channel": "facebook",
                "timestamp": "2026-03-20T11:00:00",
                "source_url": "https://example.test/facebook/collector",
            }
        ]
    )
    monkeypatch.setitem(sys.modules, scraper_module_name, fake_module)

    with pytest.raises(ValueError, match="page_id|page_url"):
        connector.fetch_documents(
            {
                "source_id": "src-facebook-missing-id",
                "client_id": "client-a",
                "source_name": "Facebook Ramy",
                "platform": "facebook",
                "source_type": "facebook_feed",
                "owner_type": "owned",
                "auth_mode": "file_snapshot",
                "config_json": {
                    "fetch_mode": "collector",
                    "snapshot_path": str(snapshot),
                },
            }
        )


def test_facebook_connector_utilise_le_collecteur_en_mode_collector(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Facebook doit passer par le collecteur quand le mode collector est demande."""
    from core.connectors.facebook_connector import FacebookConnector

    snapshot = tmp_path / "facebook_snapshot.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = FacebookConnector()
    scraper_module_name = connector.scraper_modules[0]
    fake_module = types.ModuleType(scraper_module_name)
    fake_module.collect = lambda source=None, credentials=None: pd.DataFrame(
        [
            {
                "text": "facebook collector",
                "channel": "facebook",
                "timestamp": "2026-03-20T11:00:00",
                "source_url": "https://example.test/facebook/collector",
            }
        ]
    )
    monkeypatch.setitem(sys.modules, scraper_module_name, fake_module)

    documents = connector.fetch_documents(
        {
            "source_id": "src-facebook-collector",
            "client_id": "client-a",
            "source_name": "Facebook Ramy",
            "platform": "facebook",
            "source_type": "facebook_feed",
            "owner_type": "owned",
            "auth_mode": "file_snapshot",
            "config_json": {
                "fetch_mode": "collector",
                "page_url": "https://facebook.com/ramy",
                "snapshot_path": str(snapshot),
            },
        }
    )

    assert len(documents) == 1
    assert documents[0]["raw_text"] == "facebook collector"
    assert documents[0]["raw_metadata"]["source_url"].endswith("/collector")


def test_orchestrator_selecte_instagram_connector(tmp_path: Path) -> None:
    """L'orchestrateur doit router Instagram vers le connecteur dedie."""
    from core.ingestion.orchestrator import IngestionOrchestrator

    orchestrator = IngestionOrchestrator(db_path=str(tmp_path / "instagram.db"))
    source = {
        "platform": "instagram",
        "source_type": "instagram_profile",
    }

    connector = orchestrator._select_connector(source)

    assert connector.__class__.__name__ == "InstagramConnector"


def test_create_source_conserve_config_json_chaine(tmp_path: Path) -> None:
    """create_source doit persister config_json sans double-encodage."""
    from core.ingestion.orchestrator import IngestionOrchestrator

    orchestrator = IngestionOrchestrator(db_path=str(tmp_path / "config.db"))
    config_json = json.dumps(
        {
            "fetch_mode": "snapshot",
            "snapshot_path": "data/raw/import.csv",
        },
        ensure_ascii=False,
    )

    source = orchestrator.create_source(
        {
            "client_id": "client-config",
            "source_name": "Import config",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
            "config_json": config_json,
        }
    )

    stored = orchestrator.get_source(source["source_id"], client_id="client-config")

    assert stored is not None
    assert stored["config_json"] == config_json


def test_run_source_sync_utilise_config_import_persistee_sans_kwargs(tmp_path: Path) -> None:
    """Un import batch doit reutiliser la config persistée quand les kwargs runtime manquent."""
    from core.database import DatabaseManager
    from core.ingestion.orchestrator import IngestionOrchestrator

    database = DatabaseManager(str(tmp_path / "tenant.db"))
    database.create_tables()
    database.close()

    csv_path = tmp_path / "tenant.csv"
    pd.DataFrame(
        [
            {
                "review": "tenant safe",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
            }
        ]
    ).to_csv(csv_path, index=False)

    orchestrator = IngestionOrchestrator(db_path=str(tmp_path / "tenant.db"))
    source = orchestrator.create_source(
        {
            "client_id": "client-a",
            "source_name": "Import persisted config",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
            "config_json": {
                "snapshot_path": str(csv_path),
                "column_mapping": {"review": "text"},
            },
        }
    )

    result = orchestrator.run_source_sync(
        source["source_id"],
        client_id="client-a",
    )

    assert result["status"] == "success"
    assert result["records_fetched"] == 1
    assert result["records_inserted"] == 1


def test_run_source_sync_sans_client_id_utilise_le_client_par_defaut_et_refuse_un_client_non_defaut(
    tmp_path: Path,
) -> None:
    """Le client implicite doit rester le client par defaut, pas un acces cross-tenant."""
    from config import DEFAULT_CLIENT_ID
    from core.database import DatabaseManager
    from core.ingestion.orchestrator import IngestionOrchestrator

    database = DatabaseManager(str(tmp_path / "tenant-default.db"))
    database.create_tables()
    database.close()

    csv_default = tmp_path / "default.csv"
    csv_owner = tmp_path / "owner.csv"
    pd.DataFrame(
        [
            {
                "review": "default client",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
            }
        ]
    ).to_csv(csv_default, index=False)
    pd.DataFrame(
        [
            {
                "review": "owner client",
                "channel": "facebook",
                "timestamp": "2026-03-20T11:00:00",
            }
        ]
    ).to_csv(csv_owner, index=False)

    orchestrator = IngestionOrchestrator(db_path=str(tmp_path / "tenant-default.db"))
    default_source = orchestrator.create_source(
        {
            "source_name": "Import default",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )
    owner_source = orchestrator.create_source(
        {
            "client_id": "client-owner",
            "source_name": "Import owner",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "auth_mode": "file_upload",
        }
    )

    default_result = orchestrator.run_source_sync(
        default_source["source_id"],
        manual_file_path=str(csv_default),
        column_mapping={"review": "text"},
    )

    assert default_result["status"] == "success"
    assert default_result["records_inserted"] == 1
    assert orchestrator.get_source(default_source["source_id"])["client_id"] == DEFAULT_CLIENT_ID

    with pytest.raises(KeyError):
        orchestrator.run_source_sync(
            owner_source["source_id"],
            manual_file_path=str(csv_owner),
            column_mapping={"review": "text"},
        )


def test_materialize_secret_reference_ne_stocke_pas_le_secret_brut(
    temp_secret_store: Path,
) -> None:
    """Le helper source_config doit convertir un secret brut en reference locale."""
    from core.connectors.source_config import materialize_secret_reference
    from core.security.secret_manager import resolve_secret

    config_payload = {"fetch_mode": "collector"}

    updated = materialize_secret_reference(
        config_payload,
        secret_value="super-secret-token",
        label="facebook-collector",
    )

    assert "super-secret-token" not in str(updated)
    assert updated["credential_ref"].startswith("local:")
    assert resolve_secret(updated["credential_ref"]) == "super-secret-token"


@pytest.mark.parametrize("fetch_mode", ["collector", "api"])
def test_platform_connector_ne_fall_pas_vers_snapshot_si_collecteur_indisponible(
    tmp_path: Path,
    fetch_mode: str,
) -> None:
    """Collector/api doit echouer sans servir un snapshot si le collecteur est absent."""
    from core.connectors.facebook_connector import FacebookConnector

    snapshot = tmp_path / f"facebook_{fetch_mode}.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = FacebookConnector()

    if fetch_mode == "api":
        # API mode requires credentials; it should raise an error if missing
        with pytest.raises(ValueError, match="access_token"):
            connector.fetch_documents(
                {
                    "source_id": f"src-facebook-{fetch_mode}",
                    "client_id": "client-a",
                    "source_name": "Facebook Ramy",
                    "platform": "facebook",
                    "source_type": "facebook_feed",
                    "owner_type": "owned",
                    "auth_mode": "file_snapshot",
                    "config_json": {
                        "fetch_mode": fetch_mode,
                        "page_id": "123456789",
                        "page_url": "https://facebook.com/ramy",
                        "snapshot_path": str(snapshot),
                    },
                }
            )
    else:
        # Collector mode should not fall back to snapshot when unavailable
        documents = connector.fetch_documents(
            {
                "source_id": f"src-facebook-{fetch_mode}",
                "client_id": "client-a",
                "source_name": "Facebook Ramy",
                "platform": "facebook",
                "source_type": "facebook_feed",
                "owner_type": "owned",
                "auth_mode": "file_snapshot",
                "config_json": {
                    "fetch_mode": fetch_mode,
                    "page_url": "https://facebook.com/ramy",
                    "snapshot_path": str(snapshot),
                },
            }
        )
        assert documents == []


def test_platform_connector_rejette_fetch_mode_invalide(tmp_path: Path) -> None:
    """Un fetch_mode invalide doit etre rejete via le chemin runtime du connecteur."""
    from core.connectors.facebook_connector import FacebookConnector

    snapshot = tmp_path / "facebook.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = FacebookConnector()

    with pytest.raises(ValueError, match="fetch_mode"):
        connector.fetch_documents(
            {
                "source_id": "src-facebook-invalid-mode",
                "client_id": "client-a",
                "source_name": "facebook source",
                "platform": "facebook",
                "source_type": "facebook_feed",
                "owner_type": "owned",
                "auth_mode": "file_snapshot",
                "config_json": {
                    "fetch_mode": "stream",
                    "page_url": "https://facebook.com/ramy",
                    "snapshot_path": str(snapshot),
                },
            }
        )


def test_platform_connector_propage_une_typeerror_interne_du_collector(tmp_path: Path, monkeypatch) -> None:
    """Une TypeError interne du collecteur ne doit pas etre confondue avec un mauvais appel."""
    from core.connectors.facebook_connector import FacebookConnector

    snapshot = tmp_path / "facebook.parquet"
    pd.DataFrame(
        [
            {
                "text": "facebook snapshot",
                "channel": "facebook",
                "timestamp": "2026-03-20T10:00:00",
                "source_url": "https://example.test/facebook/snapshot",
            }
        ]
    ).to_parquet(snapshot, index=False)

    connector = FacebookConnector()
    scraper_module_name = connector.scraper_modules[0]
    fake_module = types.ModuleType(scraper_module_name)

    def collect(source=None, credentials=None):
        raise TypeError("collector bug interne")

    fake_module.collect = collect
    monkeypatch.setitem(sys.modules, scraper_module_name, fake_module)

    with pytest.raises(TypeError, match="collector bug interne"):
        connector.fetch_documents(
            {
                "source_id": "src-facebook-typeerror",
                "client_id": "client-a",
                "source_name": "facebook source",
                "platform": "facebook",
                "source_type": "facebook_feed",
                "owner_type": "owned",
                "auth_mode": "file_snapshot",
                "config_json": {
                    "fetch_mode": "collector",
                    "page_url": "https://facebook.com/ramy",
                    "snapshot_path": str(snapshot),
                },
            }
        )


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

    sync_result = orchestrator.run_source_sync(
        source["source_id"],
        manual_file_path=str(csv_path),
        column_mapping={"review": "text"},
        client_id="client-trace",
    )
    compute_source_health(source["source_id"], db_path=str(platform_db), client_id="client-trace")

    service = SourceAdminService(db_path=str(platform_db))
    trace = service.get_source_trace(source["source_id"], client_id="client-trace")

    assert sync_result["normalization"]["processed_count"] == 2
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


def test_build_sources_frame_affiche_fetch_mode_et_credential_ref() -> None:
    """Le tableau sources doit rendre visibles fetch_mode et la reference de secret."""
    from ui_helpers.source_admin_helpers import build_sources_frame

    frame = build_sources_frame(
        [
            {
                "source_id": "src-instagram-001",
                "client_id": "client-a",
                "source_name": "Instagram Ramy",
                "platform": "instagram",
                "owner_type": "owned",
                "source_type": "instagram_profile",
                "is_active": 1,
                "config_json": {
                    "fetch_mode": "collector",
                    "credential_ref": "local:instagram-001",
                },
                "last_sync_status": "success",
                "latest_health_score": 92.0,
                "raw_document_count": 12,
                "normalized_count": 12,
                "enriched_count": 12,
            }
        ]
    )

    assert "fetch_mode" in frame.columns
    assert "credential_ref" in frame.columns
    assert frame.iloc[0]["fetch_mode"] == "collector"
    assert frame.iloc[0]["credential_ref"] == "local:instagram-001"


def test_build_source_config_json_ajoute_fetch_mode_secret_et_identifiant_plateforme(monkeypatch) -> None:
    """Le helper UI doit construire une config exploitable pour une source collector."""
    from ui_helpers.source_admin_helpers import build_source_config_json

    monkeypatch.setattr(
        "ui_helpers.source_admin_helpers.materialize_secret_reference",
        lambda config, **kwargs: {**config, "credential_ref": "local:facebook-collector"},
    )

    config_payload = build_source_config_json(
        platform="facebook",
        fetch_mode="collector",
        snapshot_path="data/raw/facebook_raw.parquet",
        mapping_raw='{"review": "text"}',
        secret_value="super-secret-token",
        secret_label="facebook-collector",
        platform_value="https://facebook.com/ramy",
    )

    assert config_payload["fetch_mode"] == "collector"
    assert config_payload["snapshot_path"] == "data/raw/facebook_raw.parquet"
    assert config_payload["column_mapping"] == {"review": "text"}
    assert config_payload["page_url"] == "https://facebook.com/ramy"
    assert config_payload["credential_ref"] == "local:facebook-collector"
