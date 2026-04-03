"""Helpers purs pour la page Admin Sources Wave 5.1."""

from __future__ import annotations

import pandas as pd


_SOURCE_COLUMNS = [
    "source_id",
    "client_id",
    "source_name",
    "platform",
    "owner_type",
    "source_type",
    "is_active",
    "last_sync_at",
    "last_sync_status",
    "latest_health_score",
    "raw_document_count",
    "normalized_count",
    "enriched_count",
]

_SYNC_RUN_COLUMNS = [
    "sync_run_id",
    "source_id",
    "client_id",
    "status",
    "records_fetched",
    "records_inserted",
    "records_failed",
    "started_at",
    "ended_at",
    "error_message",
]

_HEALTH_COLUMNS = [
    "snapshot_id",
    "source_id",
    "client_id",
    "health_score",
    "success_rate_pct",
    "freshness_hours",
    "records_fetched_avg",
    "computed_at",
]


def filter_source_records(
    records: list[dict],
    *,
    platform: str | None = None,
    owner_type: str | None = None,
    status: str = "all",
) -> list[dict]:
    """Filtre les enregistrements de sources déjà chargés en mémoire."""
    filtered = list(records)
    if platform and platform != "all":
        filtered = [row for row in filtered if row.get("platform") == platform]
    if owner_type and owner_type != "all":
        filtered = [row for row in filtered if row.get("owner_type") == owner_type]
    if status == "active":
        filtered = [row for row in filtered if bool(row.get("is_active"))]
    elif status == "inactive":
        filtered = [row for row in filtered if not bool(row.get("is_active"))]
    return filtered


def _stable_frame(records: list[dict], columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[columns]


def build_sources_frame(records: list[dict]) -> pd.DataFrame:
    """Construit le tableau principal des sources."""
    frame = _stable_frame(records, _SOURCE_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(
        by=["is_active", "latest_health_score", "source_name"],
        ascending=[False, False, True],
        na_position="last",
    )


def build_source_sync_runs_frame(records: list[dict]) -> pd.DataFrame:
    """Construit le tableau des runs de synchronisation."""
    frame = _stable_frame(records, _SYNC_RUN_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(by=["started_at", "sync_run_id"], ascending=[False, False], na_position="last")


def build_health_snapshots_frame(records: list[dict]) -> pd.DataFrame:
    """Construit le tableau des snapshots de santé."""
    frame = _stable_frame(records, _HEALTH_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(by=["computed_at", "snapshot_id"], ascending=[False, False], na_position="last")


def compute_source_metrics(records: list[dict]) -> dict[str, int]:
    """Calcule les KPIs synthétiques pour la page admin sources."""
    total = len(records)
    active = sum(1 for row in records if bool(row.get("is_active")))
    platforms = len({row.get("platform") for row in records if row.get("platform")})
    degraded = sum(
        1
        for row in records
        if (row.get("last_sync_status") == "failed")
        or (
            row.get("latest_health_score") is not None
            and float(row.get("latest_health_score")) < 60.0
        )
    )
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "platforms": platforms,
        "degraded": degraded,
    }
