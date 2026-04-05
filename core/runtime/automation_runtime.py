"""Runtime one-shot pour l'automatisation RamyPulse."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import config
from api.data_loader import load_annotated
from core.alerts.alert_detector import run_alert_detection
from core.ingestion.health_checker import compute_source_health
from core.ingestion.scheduler import run_due_syncs
from core.normalization.normalizer_pipeline import run_normalization_job


def _get_connection(db_path=None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path or config.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def run_source_health_cycle(
    *,
    client_id: str = config.DEFAULT_CLIENT_ID,
    db_path=None,
) -> dict:
    """Calcule la santé de toutes les sources actives d'un client."""
    with _get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT source_id
            FROM sources
            WHERE client_id = ? AND is_active = 1
            ORDER BY source_id
            """,
            [client_id],
        ).fetchall()

    snapshots = [
        compute_source_health(
            source_id=row["source_id"],
            client_id=client_id,
            db_path=db_path,
            emit_alert=True,
        )
        for row in rows
    ]
    return {
        "status": "success",
        "sources_checked": len(snapshots),
        "alerts_created": sum(int(snapshot.get("alert_created", 0) or 0) for snapshot in snapshots),
        "snapshots": snapshots,
    }


def run_alert_detection_cycle() -> dict:
    """Lance une détection d'alertes si des données annotées sont disponibles."""
    dataframe = load_annotated()
    if dataframe.empty:
        return {
            "status": "skipped",
            "alerts_created": 0,
            "alert_ids": [],
        }

    alert_ids = run_alert_detection(dataframe)
    return {
        "status": "success",
        "alerts_created": len(alert_ids),
        "alert_ids": alert_ids,
    }


def _skipped_payload() -> dict:
    return {"status": "skipped"}


def run_automation_cycle(
    *,
    client_id: str = config.DEFAULT_CLIENT_ID,
    run_sync: bool = True,
    run_normalization: bool = True,
    run_health: bool = True,
    run_alerts: bool = True,
    batch_size: int = 200,
    now: str | datetime | None = None,
    db_path=None,
) -> dict:
    """Exécute un cycle one-shot du runtime RamyPulse."""
    sync_result = run_due_syncs(client_id=client_id, now=now, db_path=db_path) if run_sync else _skipped_payload()
    normalization_result = (
        run_normalization_job(batch_size=batch_size, client_id=client_id, db_path=db_path)
        if run_normalization
        else _skipped_payload()
    )
    health_result = (
        run_source_health_cycle(client_id=client_id, db_path=db_path)
        if run_health
        else _skipped_payload()
    )
    alerts_result = run_alert_detection_cycle() if run_alerts else _skipped_payload()

    return {
        "client_id": client_id,
        "sync": sync_result,
        "normalization": normalization_result,
        "health": health_result,
        "alerts": alerts_result,
    }
