"""Gestion CRUD des watchlists RamyPulse."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime

import config

logger = logging.getLogger(__name__)

_DEFAULT_FILTERS = {
    "channel": None,
    "aspect": None,
    "wilaya": None,
    "product": None,
    "sentiment": None,
    "period_days": 7,
    "min_volume": 10,
}
_VALID_SCOPE_TYPES = {"product", "region", "channel", "cross_dimension"}
_REQUIRED_COLUMNS = {
    "watchlist_id",
    "client_id",
    "watchlist_name",
    "description",
    "scope_type",
    "filters",
    "is_active",
    "created_at",
    "updated_at",
}


def _get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite courte duree avec row_factory activee."""
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
    """Serialise un dictionnaire vers une chaine JSON SQLite."""
    return json.dumps(value or {}, ensure_ascii=False)


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid.uuid4())


def _now() -> str:
    """Retourne un timestamp ISO courant."""
    return datetime.now().isoformat()


def _normalize_text(value: object) -> str | None:
    """Normalise une valeur texte simple pour stockage et comparaison."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_int(value: object, default: int) -> int:
    """Normalise un entier de filtre avec valeur de repli."""
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_filters(filters: dict | None) -> dict:
    """Valide et complete la structure de filtres contractuelle."""
    payload = dict(_DEFAULT_FILTERS)
    payload.update(filters or {})
    normalized = {
        "channel": _normalize_text(payload.get("channel")),
        "aspect": _normalize_text(payload.get("aspect")),
        "wilaya": _normalize_text(payload.get("wilaya")),
        "product": _normalize_text(payload.get("product")),
        "sentiment": _normalize_text(payload.get("sentiment")),
        "period_days": max(1, _normalize_int(payload.get("period_days"), 7)),
        "min_volume": max(0, _normalize_int(payload.get("min_volume"), 10)),
    }
    return normalized


def _validate_scope_type(scope_type: str) -> str:
    """Valide le type de perimetre de watchlist."""
    if scope_type not in _VALID_SCOPE_TYPES:
        raise ValueError(f"scope_type invalide: {scope_type}")
    return scope_type


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
    """Liste les colonnes disponibles pour une table SQLite."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_watchlists_table(connection: sqlite3.Connection) -> None:
    """Garantit la presence de la table watchlists conforme au contrat."""
    if _table_exists(connection, "watchlists"):
        columns = _table_columns(connection, "watchlists")
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            raise RuntimeError(
                "Schema watchlists incompatible avec INTERFACES.md: "
                f"colonnes manquantes {sorted(missing)}"
            )
        return

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlists (
            watchlist_id TEXT PRIMARY KEY,
            client_id TEXT DEFAULT 'ramy_client_001',
            watchlist_name TEXT NOT NULL,
            description TEXT,
            scope_type TEXT,
            filters TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    connection.commit()


def _row_to_watchlist(row: sqlite3.Row | None) -> dict | None:
    """Convertit une ligne SQLite en dictionnaire de watchlist."""
    if row is None:
        return None
    payload = dict(row)
    payload["filters"] = _normalize_filters(_deserialize_dict(payload.get("filters")))
    payload["is_active"] = int(payload.get("is_active", 0))
    return payload


def create_watchlist(
    name: str,
    description: str,
    scope_type: str,
    filters: dict,
) -> str:
    """Cree une watchlist et retourne son identifiant."""
    if not name or not str(name).strip():
        raise ValueError("name est requis")

    normalized_scope_type = _validate_scope_type(scope_type)
    normalized_filters = _normalize_filters(filters)
    watchlist_id = _new_id()
    timestamp = _now()

    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        connection.execute(
            """
            INSERT INTO watchlists (
                watchlist_id,
                client_id,
                watchlist_name,
                description,
                scope_type,
                filters,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                watchlist_id,
                config.DEFAULT_CLIENT_ID,
                str(name).strip(),
                description.strip() if description else "",
                normalized_scope_type,
                _serialize_dict(normalized_filters),
                1,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    logger.info("Watchlist creee: %s", watchlist_id)
    return watchlist_id


def list_watchlists(is_active: bool = True) -> list[dict]:
    """Liste les watchlists avec filtres deserialises automatiquement."""
    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        sql = "SELECT * FROM watchlists"
        params: list[object] = []
        if is_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY created_at DESC, watchlist_id DESC"
        rows = connection.execute(sql, params).fetchall()

    return [_row_to_watchlist(row) for row in rows]


def get_watchlist(watchlist_id: str) -> dict | None:
    """Retourne une watchlist complete ou None si absente."""
    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        row = connection.execute(
            "SELECT * FROM watchlists WHERE watchlist_id = ?",
            (watchlist_id,),
        ).fetchone()
    return _row_to_watchlist(row)


def update_watchlist(watchlist_id: str, updates: dict) -> bool:
    """Met a jour une watchlist avec un sous-ensemble arbitraire de champs."""
    current = get_watchlist(watchlist_id)
    if current is None:
        return False

    if not updates:
        return True

    allowed = {
        "client_id",
        "watchlist_name",
        "description",
        "scope_type",
        "filters",
        "is_active",
    }
    payload = {key: value for key, value in dict(updates).items() if key in allowed}
    if not payload:
        return True

    if "watchlist_name" in payload:
        name = str(payload["watchlist_name"]).strip()
        if not name:
            raise ValueError("watchlist_name est requis")
        payload["watchlist_name"] = name

    if "scope_type" in payload:
        payload["scope_type"] = _validate_scope_type(str(payload["scope_type"]))

    if "filters" in payload:
        payload["filters"] = _serialize_dict(_normalize_filters(payload["filters"]))

    if "description" in payload:
        payload["description"] = str(payload["description"] or "").strip()

    if "is_active" in payload:
        payload["is_active"] = 1 if bool(payload["is_active"]) else 0

    payload["updated_at"] = _now()
    assignments = ", ".join(f"{column} = ?" for column in payload)
    params = list(payload.values()) + [watchlist_id]

    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        cursor = connection.execute(
            f"UPDATE watchlists SET {assignments} WHERE watchlist_id = ?",
            params,
        )
        connection.commit()

    updated = cursor.rowcount > 0
    if updated:
        logger.info("Watchlist mise a jour: %s", watchlist_id)
    return updated


def deactivate_watchlist(watchlist_id: str) -> bool:
    """Desactive une watchlist sans la supprimer."""
    return update_watchlist(watchlist_id, {"is_active": 0})
