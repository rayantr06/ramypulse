"""Helpers purs pour la page Admin Sources Wave 5.1."""

from __future__ import annotations

import json

import pandas as pd

from core.connectors.source_config import materialize_secret_reference


_SOURCE_COLUMNS = [
    "source_id",
    "client_id",
    "source_name",
    "platform",
    "owner_type",
    "source_type",
    "fetch_mode",
    "credential_ref",
    "is_active",
    "last_sync_at",
    "last_sync_status",
    "latest_health_score",
    "raw_document_count",
    "normalized_count",
    "enriched_count",
]

_PLATFORM_CONFIG_FIELDS = {
    "facebook": "page_url",
    "google_maps": "place_url",
    "youtube": "channel_id",
    "instagram": "profile_url",
}

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


def _parse_json_mapping(raw: str) -> dict[str, str] | None:
    if not raw.strip():
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Le mapping JSON doit etre un objet.")
    return {str(key): str(value) for key, value in parsed.items()}


def _config_from_record(record: dict) -> dict:
    raw_config = record.get("config_json") or {}
    if isinstance(raw_config, dict):
        return dict(raw_config)
    if isinstance(raw_config, str) and raw_config.strip():
        try:
            parsed = json.loads(raw_config)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def build_source_config_json(
    *,
    platform: str,
    fetch_mode: str,
    snapshot_path: str,
    mapping_raw: str,
    secret_value: str,
    secret_label: str,
    platform_value: str = "",
) -> dict[str, object]:
    """Construit une config source PRD stable a partir des champs du formulaire admin."""
    config_json: dict[str, object] = {
        "fetch_mode": (fetch_mode or "snapshot").strip() or "snapshot",
    }
    if snapshot_path.strip():
        config_json["snapshot_path"] = snapshot_path.strip()
    parsed_mapping = _parse_json_mapping(mapping_raw)
    if parsed_mapping:
        config_json["column_mapping"] = parsed_mapping

    platform_field = _PLATFORM_CONFIG_FIELDS.get(platform)
    if platform_field and platform_value.strip():
        config_json[platform_field] = platform_value.strip()

    if secret_value.strip():
        config_json = materialize_secret_reference(
            config_json,
            secret_value=secret_value.strip(),
            label=secret_label,
        )
    return config_json


def build_sources_frame(records: list[dict]) -> pd.DataFrame:
    """Construit le tableau principal des sources."""
    rows = []
    for record in records:
        config = _config_from_record(record)
        rows.append(
            {
                **record,
                "fetch_mode": config.get("fetch_mode", "snapshot"),
                "credential_ref": config.get("credential_ref"),
            }
        )
    frame = _stable_frame(rows, _SOURCE_COLUMNS)
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
        if (row.get("last_sync_status") in {"failed", "failed_downstream"})
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
