"""Services de lecture/admin pour la couche sources Wave 5.1."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from datetime import datetime, timezone

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH


def _get_connection(db_path=None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path or SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _parse_config_json(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceAdminService:
    """Expose les lectures admin branchées sur sources, runs et snapshots."""

    def __init__(self, db_path=None) -> None:
        self.db_path = str(db_path or SQLITE_DB_PATH)

    def _source_where_clause(
        self,
        *,
        client_id: str,
        platform: str | None = None,
        owner_type: str | None = None,
        status: str = "all",
        source_id: str | None = None,
    ) -> tuple[str, list]:
        clauses = ["s.client_id = ?"]
        params: list = [client_id]
        if source_id:
            clauses.append("s.source_id = ?")
            params.append(source_id)
        if platform and platform != "all":
            clauses.append("s.platform = ?")
            params.append(platform)
        if owner_type and owner_type != "all":
            clauses.append("s.owner_type = ?")
            params.append(owner_type)
        if status == "active":
            clauses.append("s.is_active = 1")
        elif status == "inactive":
            clauses.append("s.is_active = 0")
        return " AND ".join(clauses), params

    @staticmethod
    def _row_to_source_dict(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        payload = dict(row)
        payload["config_json"] = _parse_config_json(payload.get("config_json"))
        return payload

    def list_sources(
        self,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        platform: str | None = None,
        owner_type: str | None = None,
        status: str = "all",
        source_id: str | None = None,
    ) -> list[dict]:
        where_clause, params = self._source_where_clause(
            client_id=client_id,
            platform=platform,
            owner_type=owner_type,
            status=status,
            source_id=source_id,
        )
        with _get_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    s.*,
                    latest_run.status AS last_sync_status,
                    latest_run.started_at AS last_sync_started_at,
                    latest_run.records_fetched AS last_records_fetched,
                    latest_run.records_inserted AS last_records_inserted,
                    latest_run.records_failed AS last_records_failed,
                    latest_health.health_score AS latest_health_score,
                    latest_health.success_rate_pct AS latest_success_rate_pct,
                    latest_health.computed_at AS latest_health_computed_at,
                    COALESCE(raw_counts.raw_document_count, 0) AS raw_document_count,
                    COALESCE(norm_counts.normalized_count, 0) AS normalized_count,
                    COALESCE(sig_counts.enriched_count, 0) AS enriched_count
                FROM sources s
                LEFT JOIN source_sync_runs latest_run
                    ON latest_run.sync_run_id = (
                        SELECT ssr.sync_run_id
                        FROM source_sync_runs ssr
                        WHERE ssr.source_id = s.source_id
                        ORDER BY ssr.started_at DESC, ssr.created_at DESC
                        LIMIT 1
                    )
                LEFT JOIN source_health_snapshots latest_health
                    ON latest_health.snapshot_id = (
                        SELECT shs.snapshot_id
                        FROM source_health_snapshots shs
                        WHERE shs.source_id = s.source_id
                        ORDER BY shs.computed_at DESC
                        LIMIT 1
                    )
                LEFT JOIN (
                    SELECT source_id, COUNT(*) AS raw_document_count
                    FROM raw_documents
                    GROUP BY source_id
                ) raw_counts ON raw_counts.source_id = s.source_id
                LEFT JOIN (
                    SELECT source_id, COUNT(*) AS normalized_count
                    FROM normalized_records
                    GROUP BY source_id
                ) norm_counts ON norm_counts.source_id = s.source_id
                LEFT JOIN (
                    SELECT source_id, COUNT(*) AS enriched_count
                    FROM enriched_signals
                    GROUP BY source_id
                ) sig_counts ON sig_counts.source_id = s.source_id
                WHERE {where_clause}
                ORDER BY s.is_active DESC, s.updated_at DESC, s.source_name ASC
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_source_dict(row) for row in rows]

    def list_sync_runs(
        self,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        source_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        where_clause, params = self._source_where_clause(
            client_id=client_id,
            source_id=source_id,
        )
        params.append(limit)
        with _get_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    ssr.*,
                    s.client_id,
                    s.source_name,
                    s.platform
                FROM source_sync_runs ssr
                INNER JOIN sources s ON s.source_id = ssr.source_id
                WHERE {where_clause}
                ORDER BY ssr.started_at DESC, ssr.created_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_health_snapshots(
        self,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        source_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        where_clause, params = self._source_where_clause(
            client_id=client_id,
            source_id=source_id,
        )
        params.append(limit)
        with _get_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    shs.*,
                    s.client_id,
                    s.source_name,
                    s.platform
                FROM source_health_snapshots shs
                INNER JOIN sources s ON s.source_id = shs.source_id
                WHERE {where_clause}
                ORDER BY shs.computed_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_source_trace(
        self,
        source_id: str,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> dict:
        source_rows = self.list_sources(client_id=client_id, source_id=source_id)
        if not source_rows:
            raise KeyError(source_id)
        source = source_rows[0]
        sync_runs = self.list_sync_runs(client_id=client_id, source_id=source_id, limit=1)
        health_rows = self.list_health_snapshots(client_id=client_id, source_id=source_id, limit=1)
        return {
            **source,
            "latest_sync_run": sync_runs[0] if sync_runs else None,
            "latest_health_snapshot": health_rows[0] if health_rows else None,
        }

    def update_source(
        self,
        source_id: str,
        updates: dict,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> dict:
        current = self.get_source_trace(source_id, client_id=client_id)
        payload = dict(updates)
        if "config_json" in payload and isinstance(payload["config_json"], dict):
            payload["config_json"] = json.dumps(payload["config_json"], ensure_ascii=False)
        payload["updated_at"] = _now()

        assignments = ", ".join(f"{column} = ?" for column in payload.keys())
        params = list(payload.values()) + [source_id, client_id]
        with _get_connection(self.db_path) as connection:
            cursor = connection.execute(
                f"""
                UPDATE sources
                SET {assignments}
                WHERE source_id = ? AND client_id = ?
                """,
                tuple(params),
            )
            connection.commit()
        if cursor.rowcount == 0:
            raise KeyError(source_id)
        return self.get_source_trace(source_id, client_id=client_id)
