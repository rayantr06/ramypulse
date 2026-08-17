"""Planificateur déterministe des synchronisations dues."""

from __future__ import annotations

import importlib
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import config
from core.ingestion.orchestrator import IngestionOrchestrator


def _config_module():
    """Retourne le module config courant, même après reload dans les tests."""
    return importlib.import_module("config")


def _get_connection(db_path=None) -> sqlite3.Connection:
    cfg = _config_module()
    resolved_db_path = db_path or getattr(cfg, "SQLITE_DB_PATH", config.SQLITE_DB_PATH)
    connection = sqlite3.connect(str(resolved_db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    elif " " in text and "T" in text and "+" not in text and "-" not in text[-6:]:
        text = text.replace(" ", "+", 1)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_due(source: sqlite3.Row, now: datetime) -> bool:
    last_sync_at = _parse_iso_datetime(source["last_sync_at"])
    if last_sync_at is None:
        return True
    frequency = int(source["sync_frequency_minutes"] or 60)
    return last_sync_at + timedelta(minutes=frequency) <= now


def _group_sources(rows: list[sqlite3.Row]) -> list[tuple[str, list[sqlite3.Row]]]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[row["coverage_key"] or row["source_id"]].append(row)

    ordered: list[tuple[str, list[sqlite3.Row]]] = []
    for coverage_key in sorted(grouped):
        group_rows = sorted(
            grouped[coverage_key],
            key=lambda row: (
                int(row["source_priority"] or 999),
                row["updated_at"] or "",
                row["source_id"],
            ),
        )
        ordered.append((coverage_key, group_rows))
    return ordered


def run_due_syncs(
    *,
    now: str | datetime | None = None,
    client_id: str | None = None,
    db_path=None,
) -> dict:
    """Exécute les synchronisations dues en respectant priorité et fallback."""
    cfg = _config_module()
    effective_client_id = (
        str(client_id).strip()
        if isinstance(client_id, str) and str(client_id).strip()
        else getattr(cfg, "DEFAULT_CLIENT_ID", config.DEFAULT_CLIENT_ID)
    )
    current_time = (
        _parse_iso_datetime(now)
        if isinstance(now, str)
        else (now.astimezone(timezone.utc) if isinstance(now, datetime) else datetime.now(timezone.utc))
    )
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    with _get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM sources
            WHERE client_id = ? AND is_active = 1
            ORDER BY coverage_key, source_priority, updated_at
            """,
            [effective_client_id],
        ).fetchall()

    due_rows = [row for row in rows if _is_due(row, current_time)]
    orchestrator = IngestionOrchestrator(db_path=db_path)
    groups_payload: list[dict] = []
    scheduled_count = 0

    for coverage_key, group_rows in _group_sources(due_rows):
        attempts: list[dict] = []
        winner_source_id: str | None = None
        winner_status: str | None = None

        for row in group_rows:
            try:
                result = orchestrator.run_source_sync(
                    source_id=row["source_id"],
                    run_mode="scheduled",
                    client_id=effective_client_id,
                )
                attempt = {
                    "source_id": row["source_id"],
                    "source_priority": row["source_priority"],
                    "status": result.get("status"),
                    "records_fetched": result.get("records_fetched", 0),
                    "records_inserted": result.get("records_inserted", 0),
                    "records_failed": result.get("records_failed", 0),
                }
                attempts.append(attempt)

                is_winner = (
                    result.get("status") == "success"
                    and max(result.get("records_inserted", 0), result.get("records_fetched", 0)) > 0
                )
                if is_winner:
                    winner_source_id = row["source_id"]
                    winner_status = result.get("status")
                    scheduled_count += 1
                    break
            except Exception as exc:
                attempts.append(
                    {
                        "source_id": row["source_id"],
                        "source_priority": row["source_priority"],
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        if winner_source_id is not None or attempts:
            groups_payload.append(
                {
                    "coverage_key": coverage_key,
                    "winner_source_id": winner_source_id,
                    "winner_status": winner_status,
                    "attempts": attempts,
                }
            )

    return {
        "tick_at": current_time.isoformat(),
        "groups_processed": len(groups_payload),
        "sources_scheduled": scheduled_count,
        "groups": groups_payload,
    }
