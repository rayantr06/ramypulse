"""Orchestrateur SQLite de la couche ingestion Wave 5.1."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH
from core.connectors.batch_import_connector import BatchImportConnector
from core.connectors.source_config import parse_source_config, resolve_credentials
from core.connectors.facebook_connector import FacebookConnector
from core.connectors.google_maps_connector import GoogleMapsConnector
from core.connectors.instagram_connector import InstagramConnector
from core.connectors.youtube_connector import YouTubeConnector
from core.database import DatabaseManager
from core.normalization.normalizer_pipeline import run_normalization_job

logger = logging.getLogger(__name__)
SUPPORTED_PLATFORMS = frozenset({"facebook", "google_maps", "youtube", "instagram", "import"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


class IngestionOrchestrator:
    """Fondation SQLite pour le registre de sources et les runs d'ingestion."""

    def __init__(self, db_path=None) -> None:
        self.db_path = str(db_path or SQLITE_DB_PATH)
        self._connectors = {
            "import": BatchImportConnector(),
            "facebook": FacebookConnector(),
            "google_maps": GoogleMapsConnector(),
            "instagram": InstagramConnector(),
            "youtube": YouTubeConnector(),
        }
        database = DatabaseManager(self.db_path)
        database.create_tables()
        database.close()

    def _get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_source(self, payload: dict) -> dict:
        """Crée une source PRD dans la table sources."""
        raw_config_json = payload.get("config_json")
        if isinstance(raw_config_json, str) and raw_config_json.strip():
            stored_config_json = raw_config_json
        elif isinstance(raw_config_json, dict):
            stored_config_json = json.dumps(raw_config_json, ensure_ascii=False)
        else:
            stored_config_json = "{}"
        source = {
            "source_id": payload.get("source_id") or _new_id("src"),
            "client_id": payload.get("client_id") or DEFAULT_CLIENT_ID,
            "source_name": str(payload.get("source_name") or "").strip(),
            "platform": str(payload.get("platform") or "").strip(),
            "source_type": str(payload.get("source_type") or "").strip(),
            "owner_type": str(payload.get("owner_type") or "").strip(),
            "auth_mode": payload.get("auth_mode"),
            "config_json": stored_config_json,
            "is_active": 1 if bool(payload.get("is_active", True)) else 0,
            "sync_frequency_minutes": int(payload.get("sync_frequency_minutes") or 60),
            "freshness_sla_hours": int(payload.get("freshness_sla_hours") or 24),
            "last_sync_at": payload.get("last_sync_at"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        if not source["source_name"]:
            raise ValueError("source_name est requis")
        if not source["platform"] or not source["source_type"] or not source["owner_type"]:
            raise ValueError("platform, source_type et owner_type sont requis")
        if source["platform"] not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Plateforme non supportee: {source['platform']}")

        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO sources (
                    source_id, client_id, source_name, platform, source_type, owner_type,
                    auth_mode, config_json, is_active, sync_frequency_minutes,
                    freshness_sla_hours, last_sync_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(source.values()),
            )
            connection.commit()
        return self.get_source(source["source_id"], client_id=source["client_id"])

    def get_source(self, source_id: str, *, client_id: str | None = None) -> dict | None:
        effective_client_id = client_id or DEFAULT_CLIENT_ID
        with self._get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM sources WHERE source_id = ? AND client_id = ?",
                (source_id, effective_client_id),
            ).fetchone()
        return dict(row) if row else None

    def _select_connector(self, source: dict):
        platform = str(source.get("platform") or "")
        if platform == "import" or str(source.get("source_type") or "") == "batch_import":
            return self._connectors["import"]
        if platform in self._connectors:
            return self._connectors[platform]
        raise ValueError(f"Aucun connecteur pour la plateforme {platform!r}")

    def _start_sync_run(self, source_id: str, run_mode: str) -> str:
        sync_run_id = _new_id("run")
        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO source_sync_runs (
                    sync_run_id, source_id, run_mode, status, records_fetched,
                    records_inserted, records_failed, error_message, started_at, ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sync_run_id, source_id, run_mode, "running", 0, 0, 0, None, _now(), None),
            )
            connection.commit()
        return sync_run_id

    def _finish_sync_run(
        self,
        sync_run_id: str,
        *,
        status: str,
        records_fetched: int,
        records_inserted: int,
        records_failed: int,
        error_message: str | None = None,
    ) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                UPDATE source_sync_runs
                SET status = ?, records_fetched = ?, records_inserted = ?,
                    records_failed = ?, error_message = ?, ended_at = ?
                WHERE sync_run_id = ?
                """,
                (status, records_fetched, records_inserted, records_failed, error_message, _now(), sync_run_id),
            )
            connection.commit()

    def run_source_sync(
        self,
        source_id: str,
        *,
        manual_file_path: str | None = None,
        column_mapping: dict[str, str] | None = None,
        run_mode: str = "manual",
        credentials: dict | None = None,
        client_id: str | None = None,
    ) -> dict:
        """Exécute un run de synchronisation et insère les raw_documents."""
        source = self.get_source(source_id, client_id=client_id)
        if source is None:
            raise KeyError(source_id)

        sync_run_id = self._start_sync_run(source_id, run_mode)
        try:
            connector = self._select_connector(source)
            source_config = parse_source_config(source)
            credentials_payload = {
                **resolve_credentials(source_config),
                **(credentials or {}),
            }
            documents = connector.fetch_documents(
                source,
                credentials=credentials_payload,
                file_path=manual_file_path,
                column_mapping=column_mapping,
            )
            inserted = 0
            with self._get_connection() as connection:
                for document in documents:
                    connection.execute(
                        """
                        INSERT INTO raw_documents (
                            raw_document_id, client_id, source_id, sync_run_id, external_document_id,
                            raw_payload, raw_text, raw_metadata, checksum_sha256,
                            collected_at, is_normalized, normalizer_version, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            _new_id("raw"),
                            source.get("client_id") or DEFAULT_CLIENT_ID,
                            source_id,
                            sync_run_id,
                            document.get("external_document_id"),
                            json.dumps(document.get("raw_payload") or {}, ensure_ascii=False, default=str),
                            document.get("raw_text"),
                            json.dumps(document.get("raw_metadata") or {}, ensure_ascii=False, default=str),
                            document.get("checksum_sha256"),
                            document.get("collected_at") or _now(),
                            0,
                            None,
                            _now(),
                        ),
                    )
                    inserted += 1
                connection.execute(
                    "UPDATE sources SET last_sync_at = ?, updated_at = ? WHERE source_id = ?",
                    (_now(), _now(), source_id),
                )
                connection.commit()

            normalization_result = {
                "processed_count": 0,
                "normalizer_version": None,
            }
            if inserted > 0:
                try:
                    normalization_result = run_normalization_job(
                        batch_size=inserted,
                        db_path=self.db_path,
                        client_id=source.get("client_id") or DEFAULT_CLIENT_ID,
                        source_id=source_id,
                    )
                except Exception as exc:
                    self._finish_sync_run(
                        sync_run_id,
                        status="failed_downstream",
                        records_fetched=len(documents),
                        records_inserted=inserted,
                        records_failed=max(0, len(documents) - inserted),
                        error_message=str(exc),
                    )
                    return {
                        "sync_run_id": sync_run_id,
                        "status": "failed_downstream",
                        "records_fetched": len(documents),
                        "records_inserted": inserted,
                        "records_failed": max(0, len(documents) - inserted),
                        "normalization": normalization_result,
                        "normalization_error": str(exc),
                    }

            self._finish_sync_run(
                sync_run_id,
                status="success",
                records_fetched=len(documents),
                records_inserted=inserted,
                records_failed=max(0, len(documents) - inserted),
            )
            return {
                "sync_run_id": sync_run_id,
                "status": "success",
                "records_fetched": len(documents),
                "records_inserted": inserted,
                "records_failed": max(0, len(documents) - inserted),
                "normalization": normalization_result,
            }
        except Exception as exc:
            self._finish_sync_run(
                sync_run_id,
                status="failed",
                records_fetched=0,
                records_inserted=0,
                records_failed=1,
                error_message=str(exc),
            )
            raise

    def run_normalization_cycle(
        self,
        batch_size: int = 200,
        *,
        client_id: str | None = None,
    ) -> dict:
        """Délègue au pipeline de normalisation Wave 5.2."""
        return run_normalization_job(
            batch_size=batch_size,
            db_path=self.db_path,
            client_id=client_id,
        )
