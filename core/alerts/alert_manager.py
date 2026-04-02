"""Gestion CRUD et deduplication des alertes RamyPulse."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime

import config
from core.watchlists.watchlist_manager import _ensure_watchlists_table

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"new", "acknowledged", "investigating"}
_VALID_STATUSES = _ACTIVE_STATUSES | {"resolved", "dismissed"}
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}
_REQUIRED_COLUMNS = {
    "alert_id",
    "client_id",
    "watchlist_id",
    "alert_rule_id",
    "title",
    "description",
    "severity",
    "status",
    "detected_at",
    "resolved_at",
    "alert_payload",
    "dedup_key",
    "navigation_url",
}


def _get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite courte duree pour les alertes."""
    connection = sqlite3.connect(config.SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _deserialize_dict(value: str | None) -> dict:
    """Deserialise une chaine JSON en dictionnaire Python."""
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _serialize_dict(value: dict | None) -> str:
    """Serialise un dictionnaire Python vers SQLite."""
    return json.dumps(value or {}, ensure_ascii=False)


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid.uuid4())


def _now() -> str:
    """Retourne le timestamp ISO courant."""
    return datetime.now().isoformat()


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Indique si une table SQLite existe deja."""
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Liste les colonnes presentes sur une table."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_alerts_table(connection: sqlite3.Connection) -> None:
    """Garantit la presence de la table alerts conforme au contrat."""
    _ensure_watchlists_table(connection)
    if _table_exists(connection, "alerts"):
        columns = _table_columns(connection, "alerts")
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            raise RuntimeError(
                "Schema alerts incompatible avec INTERFACES.md: "
                f"colonnes manquantes {sorted(missing)}"
            )
        return

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            client_id TEXT DEFAULT 'ramy_client_001',
            watchlist_id TEXT,
            alert_rule_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT,
            status TEXT DEFAULT 'new',
            detected_at TEXT,
            resolved_at TEXT,
            alert_payload TEXT,
            dedup_key TEXT,
            navigation_url TEXT,
            FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id)
        )
        """
    )
    connection.commit()


def _row_to_alert(row: sqlite3.Row | None) -> dict | None:
    """Convertit une ligne SQLite en dictionnaire d'alerte."""
    if row is None:
        return None
    payload = dict(row)
    payload["alert_payload"] = _deserialize_dict(payload.get("alert_payload"))
    return payload


def create_alert(
    title: str,
    description: str,
    severity: str,
    alert_payload: dict,
    watchlist_id: str | None = None,
    dedup_key: str | None = None,
    navigation_url: str | None = None,
) -> str | None:
    """Cree une alerte ou retourne None si la deduplication bloque un doublon."""
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"severity invalide: {severity}")
    if not isinstance(alert_payload, dict):
        raise ValueError("alert_payload doit etre un dict")
    if not title or not str(title).strip():
        raise ValueError("title est requis")

    alert_rule_id = alert_payload.get("rule_id") or alert_payload.get("alert_rule_id")
    detected_at = _now()

    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        if dedup_key:
            duplicate = connection.execute(
                """
                SELECT alert_id
                FROM alerts
                WHERE dedup_key = ?
                  AND status IN ('new', 'acknowledged', 'investigating')
                LIMIT 1
                """,
                (dedup_key,),
            ).fetchone()
            if duplicate is not None:
                logger.info("Alerte dedupliquee: %s", dedup_key)
                return None

        alert_id = _new_id()
        connection.execute(
            """
            INSERT INTO alerts (
                alert_id,
                client_id,
                watchlist_id,
                alert_rule_id,
                title,
                description,
                severity,
                status,
                detected_at,
                resolved_at,
                alert_payload,
                dedup_key,
                navigation_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                config.DEFAULT_CLIENT_ID,
                watchlist_id,
                str(alert_rule_id) if alert_rule_id else None,
                str(title).strip(),
                str(description or "").strip(),
                severity,
                "new",
                detected_at,
                None,
                _serialize_dict(alert_payload),
                dedup_key,
                navigation_url,
            ),
        )
        connection.commit()

    logger.info("Alerte creee: %s", alert_id)
    return alert_id


def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Liste les alertes avec payload JSON automatiquement deserialise."""
    clauses = []
    params: list[object] = []
    if status is not None:
        if status not in _VALID_STATUSES:
            raise ValueError(f"status invalide: {status}")
        clauses.append("status = ?")
        params.append(status)
    if severity is not None:
        if severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity invalide: {severity}")
        clauses.append("severity = ?")
        params.append(severity)

    sql = "SELECT * FROM alerts"
    if clauses:
        sql += f" WHERE {' AND '.join(clauses)}"
    sql += " ORDER BY detected_at DESC, alert_id DESC LIMIT ?"
    params.append(max(1, int(limit)))

    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        rows = connection.execute(sql, params).fetchall()

    return [_row_to_alert(row) for row in rows]


def update_alert_status(alert_id: str, status: str) -> bool:
    """Met a jour le statut d'une alerte selon le cycle de vie autorise."""
    if status not in _VALID_STATUSES:
        raise ValueError(f"status invalide: {status}")

    resolved_at = _now() if status in {"resolved", "dismissed"} else None
    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        cursor = connection.execute(
            """
            UPDATE alerts
            SET status = ?, resolved_at = ?
            WHERE alert_id = ?
            """,
            (status, resolved_at, alert_id),
        )
        connection.commit()

    updated = cursor.rowcount > 0
    if updated:
        logger.info("Alerte %s -> %s", alert_id, status)
    return updated


def get_alert(alert_id: str) -> dict | None:
    """Retourne une alerte complete ou None si absente."""
    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        row = connection.execute(
            "SELECT * FROM alerts WHERE alert_id = ?",
            (alert_id,),
        ).fetchone()
    return _row_to_alert(row)
