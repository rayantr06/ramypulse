"""SQLite persistence helpers for tracked watch runs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import config
from core.database import DatabaseManager


def _resolve_db_path(db_path: str | Path | None = None) -> str:
    return str(db_path or config.SQLITE_DB_PATH)


def _ensure_schema(db_path: str | Path | None = None) -> None:
    database = DatabaseManager(_resolve_db_path(db_path))
    try:
        database.create_tables()
    finally:
        database.close()


def _get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(_resolve_db_path(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _normalize_channels(requested_channels: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in requested_channels:
        channel = str(item or "").strip()
        if not channel or channel in seen:
            continue
        seen.add(channel)
        normalized.append(channel)
    return normalized


def _row_to_step(row: sqlite3.Row) -> dict[str, object]:
    return {
        "step_key": row["step_key"],
        "stage": row["stage"],
        "collector_key": row["collector_key"],
        "status": row["status"],
        "records_seen": int(row["records_seen"] or 0),
        "error_message": row["error_message"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def create_watch_run(
    client_id: str,
    watchlist_id: str,
    requested_channels: list[str] | tuple[str, ...],
    *,
    db_path: str | Path | None = None,
) -> str:
    """Create a tracked watch run row and return its identifier."""
    _ensure_schema(db_path)
    run_id = _new_id("watch-run")
    timestamp = _now()
    channels = _normalize_channels(requested_channels)

    with _get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO watch_runs (
                run_id, client_id, watchlist_id, requested_channels, stage, status,
                records_collected, error_message, created_at, updated_at, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                client_id,
                watchlist_id,
                json.dumps(channels, ensure_ascii=False),
                "queued",
                "queued",
                0,
                None,
                timestamp,
                timestamp,
                None,
                None,
            ),
        )
        connection.commit()
    return run_id


def set_stage(
    run_id: str,
    stage: str,
    *,
    status: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Update the current run stage, optionally with a status transition."""
    _ensure_schema(db_path)
    timestamp = _now()
    with _get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT started_at FROM watch_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)

        fields = ["stage = ?", "updated_at = ?"]
        params: list[object] = [stage, timestamp]
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if row["started_at"] is None and stage != "queued":
            fields.append("started_at = ?")
            params.append(timestamp)
        params.append(run_id)
        connection.execute(
            f"UPDATE watch_runs SET {', '.join(fields)} WHERE run_id = ?",
            params,
        )
        connection.commit()


def start_step(
    run_id: str,
    step_key: str,
    *,
    stage: str | None = None,
    collector_key: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Mark a step as running and create the row if needed."""
    _ensure_schema(db_path)
    timestamp = _now()
    with _get_connection(db_path) as connection:
        existing = connection.execute(
            """
            SELECT step_id, collector_key
            FROM watch_run_steps
            WHERE run_id = ? AND step_key = ?
            """,
            (run_id, step_key),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO watch_run_steps (
                    step_id, run_id, step_key, stage, collector_key, status,
                    records_seen, error_message, created_at, updated_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("watch-step"),
                    run_id,
                    step_key,
                    stage,
                    collector_key,
                    "running",
                    0,
                    None,
                    timestamp,
                    timestamp,
                    timestamp,
                    None,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE watch_run_steps
                SET stage = ?, collector_key = ?, status = ?, error_message = ?,
                    updated_at = ?, started_at = COALESCE(started_at, ?), finished_at = NULL
                WHERE run_id = ? AND step_key = ?
                """,
                (
                    stage,
                    collector_key or existing["collector_key"],
                    "running",
                    None,
                    timestamp,
                    timestamp,
                    run_id,
                    step_key,
                ),
            )
        connection.commit()

    if stage is not None:
        set_stage(run_id, stage, status="running", db_path=db_path)


def finish_step(
    run_id: str,
    step_key: str,
    *,
    status: str,
    records_seen: int = 0,
    error_message: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Finalize a step row with a terminal status."""
    _ensure_schema(db_path)
    timestamp = _now()
    with _get_connection(db_path) as connection:
        existing = connection.execute(
            """
            SELECT 1
            FROM watch_run_steps
            WHERE run_id = ? AND step_key = ?
            """,
            (run_id, step_key),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO watch_run_steps (
                    step_id, run_id, step_key, stage, collector_key, status,
                    records_seen, error_message, created_at, updated_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("watch-step"),
                    run_id,
                    step_key,
                    None,
                    None,
                    status,
                    int(records_seen),
                    error_message,
                    timestamp,
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE watch_run_steps
                SET status = ?, records_seen = ?, error_message = ?,
                    updated_at = ?, finished_at = ?
                WHERE run_id = ? AND step_key = ?
                """,
                (
                    status,
                    int(records_seen),
                    error_message,
                    timestamp,
                    timestamp,
                    run_id,
                    step_key,
                ),
            )
        connection.commit()


def finish_run(
    run_id: str,
    *,
    status: str,
    records_collected: int | None = None,
    error_message: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Mark a watch run as finished and persist final counters."""
    _ensure_schema(db_path)
    timestamp = _now()
    with _get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT records_collected FROM watch_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        connection.execute(
            """
            UPDATE watch_runs
            SET stage = ?, status = ?, records_collected = ?, error_message = ?,
                updated_at = ?, started_at = COALESCE(started_at, ?), finished_at = ?
            WHERE run_id = ?
            """,
            (
                "finished",
                status,
                int(records_collected if records_collected is not None else row["records_collected"] or 0),
                error_message,
                timestamp,
                timestamp,
                timestamp,
                run_id,
            ),
        )
        connection.commit()


def get_watch_run(
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, object] | None:
    """Return a run payload with its steps keyed by ``step_key``."""
    _ensure_schema(db_path)
    with _get_connection(db_path) as connection:
        run_row = connection.execute(
            "SELECT * FROM watch_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None:
            return None

        step_rows = connection.execute(
            """
            SELECT *
            FROM watch_run_steps
            WHERE run_id = ?
            ORDER BY created_at ASC, step_key ASC
            """,
            (run_id,),
        ).fetchall()

    requested_channels = json.loads(run_row["requested_channels"] or "[]")
    return {
        "run_id": run_row["run_id"],
        "client_id": run_row["client_id"],
        "watchlist_id": run_row["watchlist_id"],
        "requested_channels": requested_channels,
        "stage": run_row["stage"],
        "status": run_row["status"],
        "records_collected": int(run_row["records_collected"] or 0),
        "error_message": run_row["error_message"],
        "created_at": run_row["created_at"],
        "updated_at": run_row["updated_at"],
        "started_at": run_row["started_at"],
        "finished_at": run_row["finished_at"],
        "steps": {
            row["step_key"]: _row_to_step(row)
            for row in step_rows
        },
    }
