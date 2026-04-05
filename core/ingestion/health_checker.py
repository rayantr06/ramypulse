"""Calcul de santé des sources Wave 5.1."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

import config
from core.alerts.alert_manager import create_alert


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection(db_path=None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path or config.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _health_alert_severity(health_score: float) -> str:
    """Mappe un score de sante faible vers une severite d'alerte."""
    if health_score < 30:
        return "critical"
    if health_score < 45:
        return "high"
    return "medium"


def _maybe_create_health_alert(
    *,
    source_id: str,
    source_name: str,
    client_id: str,
    snapshot: dict,
    threshold: float,
) -> str | None:
    """Cree une alerte dedupee si le score de sante est sous le seuil."""
    if float(snapshot["health_score"]) >= float(threshold):
        return None

    freshness = snapshot["freshness_hours"]
    freshness_label = f"{freshness:.2f}h" if isinstance(freshness, (int, float)) else "inconnue"
    return create_alert(
        title=f"Sante degradee: {source_name}",
        description=(
            f"La source {source_name} est sous le seuil de sante ({snapshot['health_score']:.2f} < {threshold:.2f}). "
            f"Success rate {snapshot['success_rate_pct']:.2f}% ; fraicheur {freshness_label}."
        ),
        severity=_health_alert_severity(float(snapshot["health_score"])),
        alert_payload={
            "rule_id": "source_health",
            "source_id": source_id,
            "source_name": source_name,
            "health_score": snapshot["health_score"],
            "success_rate_pct": snapshot["success_rate_pct"],
            "freshness_hours": snapshot["freshness_hours"],
            "records_fetched_avg": snapshot["records_fetched_avg"],
            "threshold": threshold,
        },
        dedup_key=f"source_health:{source_id}",
        navigation_url=f"/admin-sources?source_id={source_id}",
        client_id=client_id,
    )


def compute_source_health(
    source_id: str,
    *,
    db_path=None,
    client_id: str | None = None,
    emit_alert: bool = False,
    threshold: float | None = None,
) -> dict:
    """Calcule un score simple de santé et persiste un snapshot."""
    with _get_connection(db_path) as connection:
        if client_id:
            source = connection.execute(
                """
                SELECT client_id, source_name, freshness_sla_hours, last_sync_at
                FROM sources
                WHERE source_id = ? AND client_id = ?
                """,
                (source_id, client_id),
            ).fetchone()
        else:
            source = connection.execute(
                """
                SELECT client_id, source_name, freshness_sla_hours, last_sync_at
                FROM sources
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()
        if source is None:
            raise KeyError(source_id)

        runs = connection.execute(
            """
            SELECT status, records_fetched
            FROM source_sync_runs
            WHERE source_id = ?
            ORDER BY started_at DESC
            LIMIT 10
            """,
            (source_id,),
        ).fetchall()

        total_runs = len(runs)
        success_count = sum(1 for row in runs if row["status"] == "success")
        success_rate_pct = round((success_count / total_runs) * 100.0, 2) if total_runs else 0.0
        records_fetched_avg = round(
            sum(float(row["records_fetched"] or 0) for row in runs) / total_runs,
            2,
        ) if total_runs else 0.0

        freshness_hours = None
        freshness_score = 0.0
        if source["last_sync_at"]:
            last_sync_at = datetime.fromisoformat(str(source["last_sync_at"]).replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_sync_at.astimezone(timezone.utc)
            freshness_hours = round(delta.total_seconds() / 3600.0, 2)
            sla_hours = max(1, int(source["freshness_sla_hours"] or 24))
            freshness_score = max(0.0, 100.0 - (freshness_hours / sla_hours) * 100.0)

        health_score = round((success_rate_pct * 0.6) + (freshness_score * 0.4), 2)
        snapshot = {
            "snapshot_id": f"health-{uuid.uuid4()}",
            "source_id": source_id,
            "client_id": source["client_id"],
            "health_score": health_score,
            "success_rate_pct": success_rate_pct,
            "freshness_hours": freshness_hours,
            "records_fetched_avg": records_fetched_avg,
            "computed_at": _now(),
        }
        connection.execute(
            """
            INSERT INTO source_health_snapshots (
                snapshot_id, source_id, health_score, success_rate_pct,
                freshness_hours, records_fetched_avg, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["snapshot_id"],
                snapshot["source_id"],
                snapshot["health_score"],
                snapshot["success_rate_pct"],
                snapshot["freshness_hours"],
                snapshot["records_fetched_avg"],
                snapshot["computed_at"],
            ),
        )
        connection.commit()
    alert_id = None
    effective_threshold = float(threshold if threshold is not None else config.SOURCE_HEALTH_THRESHOLD)
    if emit_alert:
        alert_id = _maybe_create_health_alert(
            source_id=source_id,
            source_name=str(source["source_name"] or source_id),
            client_id=str(source["client_id"]),
            snapshot=snapshot,
            threshold=effective_threshold,
        )
    snapshot["alert_id"] = alert_id
    snapshot["alert_created"] = 1 if alert_id else 0
    return snapshot
